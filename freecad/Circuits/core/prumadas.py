"""Prumadas verticais do edifício: energia, dados e telefonia, interfone e iluminação de emergência.

Sem FreeCAD. A partir dos andares (nome, cota do piso [mm], unidades) e das quantidades por unidade,
dimensiona cada trecho entre pavimentos (cabos que passam, eletrodutos pela taxa de ocupação da
NBR 5410, 6.2.11.1.6, ou a eletrocalha da energia) e devolve a geometria do esquema vertical, do
símbolo em planta em cada pavimento e das peças 3D, além dos materiais.

A origem de cada sistema (centro de medição, DG de telecomunicações, central de portaria, central de
iluminação de emergência) fica no andar mais baixo; cada andar acima com unidades recebe uma derivação
numa caixa de passagem. Unidades em mm, comprimentos de cabo em m.
"""
import math

from freecad.Circuits.core import ocupacao

# chave -> nome, sigla, origem
SISTEMAS = {
    "energia": ("Energia (alimentadores das unidades)", "E", "Centro de medição"),
    "dados": ("Dados e telefonia", "D", "DG de telecomunicações"),
    "interfone": ("Interfone", "I", "Central de portaria"),
    "emergencia": ("Iluminação de emergência", "IE", "Central de iluminação de emergência"),
}
ORDEM = tuple(SISTEMAS)
FORMAS_ENERGIA = ("Eletroduto por unidade", "Eletrocalha")

PADROES = {
    "sistemas": list(ORDEM),
    "secao_alimentador": 16.0,      # mm², alimentador de cada unidade (fases, neutro e PE iguais)
    "condutores_por_unidade": 4,     # 2 fases, neutro e PE
    "forma_energia": FORMAS_ENERGIA[0],
    "pontos_dados": 2,               # cabos UTP por unidade
    "eletroduto_dados": "1 1/2",
    "cabos_interfone": 1,            # cabo CCI por unidade
    "eletroduto_interfone": "1",
    "circuitos_emergencia": 1,
    "secao_emergencia": 2.5,
    "tipo_eletroduto": "Rígido",
    "folga_cabo_m": 3.0,             # sobra em cada ponta de cabo (caixa e quadro)
}
DIAMETRO_UTP_MM = 6.0          # cabo UTP categoria 6
DIAMETRO_CCI_MM = 4.5          # cabo CCI de 2 pares (interfone)
CONDUTORES_EMERGENCIA = 3      # fase, neutro e PE de cada circuito
ELETRODUTO_MINIMO = "3/4"
LARGURAS_ELETROCALHA = (100, 150, 200, 300, 400, 500, 600)  # mm
ABA_ELETROCALHA_MM = 50.0
TAXA_ELETROCALHA = ocupacao.REFERENCIA_BANDEJA  # 40 % da seção útil
CAIXA_PASSAGEM_MM = (300.0, 120.0, 300.0)  # largura, profundidade, altura (sobrepor/embutir no shaft)
ALTURA_CAIXA_MM = 1200.0       # do piso do andar à base da caixa de passagem
DUTOS_POR_FILA = 6             # na energia com um eletroduto por unidade, filas de até 6 no shaft
PASSO_DUTOS_MM = 70.0
PASSO_SISTEMAS_MM = 450.0

# --- dimensionamento ------------------------------------------------------------------------------

def _br(valor):
    return f"{float(valor):g}".replace(".", ",")



def andar(nome, cota_mm, unidades):
    return {"nome": str(nome), "cota": float(cota_mm), "unidades": int(unidades)}


def parametros_com_padroes(parametros=None):
    resultado = dict(PADROES)
    resultado.update({k: v for k, v in (parametros or {}).items() if v is not None})
    resultado["sistemas"] = [s for s in ORDEM if s in resultado.get("sistemas", ())]
    return resultado


def _internos(tipo):
    return ocupacao.internos_do_tipo(tipo)


def _diametro_externo(nominal, internos):
    return internos.get(nominal, 20.0) + 6.0  # parede do eletroduto, aproximada


def _dutos_fixos(diametros, nominal, internos):
    """Quantos eletrodutos ``nominal`` levam os cabos (repartidos igualmente, pela taxa máxima)."""
    if not diametros:
        return 0, 0.0
    for k in range(1, len(diametros) + 1):
        por_duto = math.ceil(len(diametros) / k)
        if ocupacao.comporta(nominal, [max(diametros)] * por_duto, internos):
            return k, ocupacao.taxa(nominal, [max(diametros)] * por_duto, internos)
    return len(diametros), ocupacao.taxa(nominal, [max(diametros)], internos)


def _eletrodutos(diametros, internos, nominal_fixo=None, minimo=ELETRODUTO_MINIMO):
    """(quantidade, nominal, taxa) para os cabos: o menor eletroduto único ou vários do ``nominal_fixo``."""
    if not diametros:
        return 0, None, 0.0
    if nominal_fixo:
        quantidade, taxa = _dutos_fixos(diametros, nominal_fixo, internos)
        return quantidade, nominal_fixo, taxa
    nominal = ocupacao.eletroduto_minimo(diametros, internos)
    if nominal is not None:
        nominal = ocupacao.maior(nominal, minimo, internos)
        return 1, nominal, ocupacao.taxa(nominal, diametros, internos)
    maior = max(internos, key=lambda n: internos[n])
    quantidade, taxa = _dutos_fixos(diametros, maior, internos)
    return quantidade, maior, taxa


def _eletrocalha(diametros):
    """(largura [mm], taxa) da eletrocalha vertical para os cabos (seção útil largura × aba)."""
    area = sum(ocupacao.area_cabo(d) for d in diametros)
    for largura in LARGURAS_ELETROCALHA:
        taxa = area / (largura * ABA_ELETROCALHA_MM)
        if taxa <= TAXA_ELETROCALHA + 1e-9:
            return largura, taxa
    return LARGURAS_ELETROCALHA[-1], area / (LARGURAS_ELETROCALHA[-1] * ABA_ELETROCALHA_MM)


def _cabos_da_unidade(sistema, p):
    """Diâmetros [mm] dos cabos de uma unidade no sistema."""
    if sistema == "energia":
        return [ocupacao.diametro_do_cabo(p["secao_alimentador"])] * int(p["condutores_por_unidade"])
    if sistema == "dados":
        return [DIAMETRO_UTP_MM] * int(p["pontos_dados"])
    if sistema == "interfone":
        return [DIAMETRO_CCI_MM] * int(p["cabos_interfone"])
    return []


def descricao_trecho(trecho):
    """Texto curto do trecho: ``3 × Ø1 1/2" (24 cabos)`` ou ``Eletrocalha 200 × 50 (48 cabos)``."""
    if trecho.get("eletrocalha"):
        base = f"Eletrocalha {trecho['eletrocalha']} × {ABA_ELETROCALHA_MM:.0f}"
    elif trecho["dutos"]:
        base = f"{trecho['dutos']} × Ø{trecho['nominal']}\"" if trecho["dutos"] > 1 else f"Ø{trecho['nominal']}\""
    else:
        return "-"
    return f"{base} ({trecho['cabos']} cabos)"


def dimensionar(andares, parametros=None):
    """Prumadas dos sistemas escolhidos entre os andares.

    Args:
        andares: [{'nome', 'cota' [mm], 'unidades'}] (``andar``), em qualquer ordem; o mais baixo é a origem.
        parametros: de ``PADROES`` (``sistemas`` escolhe quais).
    Returns:
        {'andares' (em ordem), 'parametros', 'sistemas': {chave: {'nome', 'sigla', 'origem', 'trechos':
         [{'de', 'ate', 'cota_de', 'cota_ate', 'comprimento' [m], 'cabos', 'dutos', 'nominal', 'taxa',
         'eletrocalha'}], 'derivacoes': {andar: unidades}, 'topo' (índice do último andar atendido),
         'avisos'}}, 'avisos'}.
    """
    p = parametros_com_padroes(parametros)
    andares = sorted(andares, key=lambda a: a["cota"])
    resultado = {"andares": andares, "parametros": p, "sistemas": {}, "avisos": []}
    if len(andares) < 2:
        resultado["avisos"].append("a prumada precisa de pelo menos dois pavimentos")
        return resultado
    internos = _internos(p["tipo_eletroduto"])
    com_unidades = [i for i, a in enumerate(andares) if a["unidades"] > 0 and i > 0]
    for chave in p["sistemas"]:
        nome, sigla, origem = SISTEMAS[chave]
        sistema = {"nome": nome, "sigla": sigla, "origem": origem, "trechos": [], "derivacoes": {}, "avisos": []}
        topo = (max(com_unidades) if com_unidades else 0) if chave != "emergencia" else len(andares) - 1
        for i in range(topo):
            de, ate = andares[i], andares[i + 1]
            trecho = {"de": de["nome"], "ate": ate["nome"], "cota_de": de["cota"], "cota_ate": ate["cota"],
                      "comprimento": (ate["cota"] - de["cota"]) / 1000.0, "cabos": 0, "dutos": 0,
                      "nominal": None, "taxa": 0.0, "eletrocalha": None}
            acima = [a for a in andares[i + 1:] if a["unidades"] > 0]
            if chave == "emergencia":
                diametros = [ocupacao.diametro_do_cabo(p["secao_emergencia"])] * (
                    CONDUTORES_EMERGENCIA * int(p["circuitos_emergencia"]))
                trecho["cabos"] = len(diametros)
                trecho["dutos"], trecho["nominal"], trecho["taxa"] = _eletrodutos(diametros, internos)
            elif chave == "energia":
                por_unidade = _cabos_da_unidade("energia", p)
                unidades = sum(a["unidades"] for a in acima)
                trecho["cabos"] = unidades * len(por_unidade)
                if p["forma_energia"] == "Eletrocalha":
                    trecho["eletrocalha"], trecho["taxa"] = _eletrocalha(por_unidade * unidades)
                else:
                    _, nominal, taxa = _eletrodutos(por_unidade, internos)
                    trecho["dutos"], trecho["nominal"], trecho["taxa"] = unidades, nominal, taxa
            else:
                diametros = []
                for a in acima:
                    diametros += _cabos_da_unidade(chave, p) * a["unidades"]
                trecho["cabos"] = len(diametros)
                fixo = p["eletroduto_dados"] if chave == "dados" else p["eletroduto_interfone"]
                trecho["dutos"], trecho["nominal"], trecho["taxa"] = _eletrodutos(diametros, internos, fixo)
            sistema["trechos"].append(trecho)
        for i in range(1, topo + 1):
            if chave == "emergencia" or andares[i]["unidades"] > 0:
                sistema["derivacoes"][andares[i]["nome"]] = andares[i]["unidades"]
        sistema["topo"] = topo
        if chave != "emergencia" and not com_unidades:
            sistema["avisos"].append("nenhum andar acima da origem tem unidades")
        resultado["sistemas"][chave] = sistema
    return resultado


def materiais(resultado):
    """Materiais das prumadas: [(sistema, item, especificação, quantidade, unidade)]."""
    p = resultado["parametros"]
    andares = resultado["andares"]
    linhas = []
    base = andares[0]["cota"] if andares else 0.0
    for chave, s in resultado["sistemas"].items():
        metros, calhas = {}, {}
        for t in s["trechos"]:
            if t["eletrocalha"]:
                calhas[t["eletrocalha"]] = calhas.get(t["eletrocalha"], 0.0) + t["comprimento"]
            elif t["dutos"]:
                metros[t["nominal"]] = metros.get(t["nominal"], 0.0) + t["dutos"] * t["comprimento"]
        for nominal, m in sorted(metros.items(), key=lambda kv: ocupacao.internos_do_tipo(p["tipo_eletroduto"])
                                 .get(kv[0], 0.0)):
            linhas.append((s["nome"], f"Eletroduto {p['tipo_eletroduto'].lower()} Ø{nominal}\"", "prumada",
                           round(m, 1), "m"))
        for largura, m in sorted(calhas.items()):
            linhas.append((s["nome"], f"Eletrocalha vertical {largura} × {ABA_ELETROCALHA_MM:.0f} mm", "prumada",
                           round(m, 1), "m"))
        caixas = len(s["derivacoes"])
        if caixas:
            linhas.append((s["nome"], "Caixa de passagem do andar", "{:.0f} × {:.0f} × {:.0f} mm".format(
                CAIXA_PASSAGEM_MM[0], CAIXA_PASSAGEM_MM[2], CAIXA_PASSAGEM_MM[1]), caixas, "un"))
        folga = float(p["folga_cabo_m"])
        if chave == "emergencia":
            altura = (andares[s["topo"]]["cota"] - base) / 1000.0 if andares else 0.0
            quantidade = (altura + folga) * CONDUTORES_EMERGENCIA * int(p["circuitos_emergencia"])
            linhas.append((s["nome"], f"Cabo {_br(p['secao_emergencia'])} mm² 750 V", "circuito de emergência",
                           round(quantidade, 1), "m"))
            continue
        total = sum((a["cota"] - base) / 1000.0 + folga for a in andares[1:] for _ in range(a["unidades"]))
        if chave == "energia":
            linhas.append((s["nome"], f"Cabo {_br(p['secao_alimentador'])} mm² 750 V",
                           f"alimentadores ({int(p['condutores_por_unidade'])} condutores por unidade)",
                           round(total * int(p["condutores_por_unidade"]), 1), "m"))
        elif chave == "dados":
            linhas.append((s["nome"], "Cabo UTP categoria 6", f"{int(p['pontos_dados'])} por unidade",
                           round(total * int(p["pontos_dados"]), 1), "m"))
        else:
            linhas.append((s["nome"], "Cabo CCI 2 pares", f"{int(p['cabos_interfone'])} por unidade",
                           round(total * int(p["cabos_interfone"]), 1), "m"))
    return linhas


# --- esquema vertical (2D) ------------------------------------------------------------------------

PASSO_ANDAR_ESQUEMA = 1500.0  # o esquema não é em escala: um andar a cada 1,5 m do desenho
COLUNA_ESQUEMA = 2800.0
ALTURA_TEXTO_ESQUEMA = 130.0


def _seta(linhas, x1, y, x2):
    linhas.append((x1, y, x2, y))
    linhas += [(x2, y, x2 - 60.0, y + 35.0), (x2, y, x2 - 60.0, y - 35.0)]


def esquema(resultado, titulo="ESQUEMA VERTICAL DAS PRUMADAS"):
    """Esquema vertical (fora de escala): um andar a cada ``PASSO_ANDAR_ESQUEMA``, uma coluna por sistema.

    Returns:
        {'linhas', 'circulos', 'textos' [(x, y, texto, altura, ângulo)], 'limites'}, em mm do desenho.
    """
    linhas, circulos, textos = [], [], []
    andares = resultado["andares"]
    sistemas = list(resultado["sistemas"].items())
    h = ALTURA_TEXTO_ESQUEMA
    if not andares or not sistemas:
        return {"linhas": [], "circulos": [], "textos": [], "limites": (0.0, 0.0, 0.0, 0.0)}
    x_primeira = 2600.0
    largura = x_primeira + COLUNA_ESQUEMA * len(sistemas)
    y_de = {a["nome"]: i * PASSO_ANDAR_ESQUEMA for i, a in enumerate(andares)}
    for a in andares:
        y = y_de[a["nome"]]
        linhas.append((0.0, y, largura, y))
        textos.append((0.0, y + 30.0, a["nome"], h, 0.0))
        textos.append((0.0, y - h - 30.0, f"{a['cota'] / 1000.0:+.2f}".replace(".", ","), h * 0.8, 0.0))
        if a["unidades"]:
            textos.append((1300.0, y + 30.0, f"{a['unidades']} unid.", h * 0.8, 0.0))
    for k, (chave, s) in enumerate(sistemas):
        x = x_primeira + k * COLUNA_ESQUEMA
        textos.append((x - 150.0, y_de[andares[-1]["nome"]] + PASSO_ANDAR_ESQUEMA * 0.55, f"{s['sigla']} - {s['nome']}",
                       h * 0.8, 0.0))
        # origem embaixo do andar mais baixo
        y0 = -700.0
        linhas += [(x - 700.0, y0 - 250.0, x + 700.0, y0 - 250.0), (x + 700.0, y0 - 250.0, x + 700.0, y0 + 250.0),
                   (x + 700.0, y0 + 250.0, x - 700.0, y0 + 250.0), (x - 700.0, y0 + 250.0, x - 700.0, y0 - 250.0)]
        textos.append((x - 650.0, y0 - 30.0, s["origem"], h * 0.7, 0.0))
        topo = andares[s["topo"]]["nome"] if s["trechos"] else andares[0]["nome"]
        y_topo = y_de[topo] + 300.0
        for dx in (-20.0, 20.0):
            linhas.append((x + dx, y0 + 250.0, x + dx, y_topo))
        for t in s["trechos"]:
            y_meio = (y_de[t["de"]] + y_de[t["ate"]]) / 2.0
            textos.append((x + 80.0, y_meio, descricao_trecho(t), h * 0.75, 0.0))
        for nome, unidades in s["derivacoes"].items():
            y = y_de[nome] + 300.0
            linhas += [(x - 80.0, y - 80.0, x + 80.0, y - 80.0), (x + 80.0, y - 80.0, x + 80.0, y + 80.0),
                       (x + 80.0, y + 80.0, x - 80.0, y + 80.0), (x - 80.0, y + 80.0, x - 80.0, y - 80.0)]
            _seta(linhas, x + 80.0, y, x + 700.0)
            rotulo = "circuito do andar" if chave == "emergencia" else f"{unidades} unid."
            textos.append((x + 720.0, y - h * 0.4, rotulo, h * 0.7, 0.0))
    topo_desenho = y_de[andares[-1]["nome"]] + PASSO_ANDAR_ESQUEMA * 0.55 + 4 * h
    textos.append((0.0, topo_desenho, titulo, h * 1.4, 0.0))
    textos.append((0.0, -1300.0, "Caixa de passagem em cada andar atendido; fora de escala.", h * 0.7, 0.0))
    return {"linhas": linhas, "circulos": circulos, "textos": textos,
            "limites": (-100.0, -1450.0, largura + 400.0, topo_desenho + 2 * h)}


# --- símbolo em planta ----------------------------------------------------------------------------

RAIO_SIMBOLO_MM = 90.0
ALTURA_TEXTO_PLANTA = 70.0


def sentido_no_andar(sistema, indice, andares):
    """'sobe' na origem, 'passa' no meio, 'chega' no último andar atendido; None fora da prumada."""
    topo = sistema.get("topo", 0)
    if not sistema["trechos"] or indice > topo:
        return None
    if indice == 0:
        return "sobe"
    return "chega" if indice == topo else "passa"


def simbolo_planta(resultado, indice):
    """Símbolo das prumadas no andar ``indice``: um círculo com a sigla por sistema e o texto do trecho.

    Returns:
        {'linhas', 'circulos', 'textos', 'limites'} em mm, com a origem no centro do shaft.
    """
    andares = resultado["andares"]
    linhas, circulos, textos = [], [], []
    presentes = []
    for chave, s in resultado["sistemas"].items():
        sentido = sentido_no_andar(s, indice, andares)
        if sentido:
            presentes.append((chave, s, sentido))
    r, h = RAIO_SIMBOLO_MM, ALTURA_TEXTO_PLANTA
    for k, (chave, s, sentido) in enumerate(presentes):
        x = k * 2.6 * r
        circulos.append((x, 0.0, r))
        textos.append((x - len(s["sigla"]) * h * 0.3, -h * 0.4, s["sigla"], h, 0.0))
        if sentido in ("sobe", "passa"):  # seta para cima: a prumada continua
            linhas += [(x + r * 0.7, -r * 0.7, x + r * 1.3, r * 1.3), (x + r * 1.3, r * 1.3, x + r * 0.8, r * 1.2),
                       (x + r * 1.3, r * 1.3, x + r * 1.2, r * 0.8)]
        trecho = s["trechos"][min(indice, len(s["trechos"]) - 1)] if sentido != "chega" else s["trechos"][-1]
        textos.append((0.0, -r - (k + 1) * h * 1.5, f"{s['sigla']}: {descricao_trecho(trecho)} {sentido}", h, 0.0))
    largura = max(1, len(presentes)) * 2.6 * r
    return {"linhas": linhas, "circulos": circulos, "textos": textos,
            "limites": (-r, -r - (len(presentes) + 1) * h * 1.5, largura, r * 1.5)}


AFASTAMENTO_SIMBOLO_MM = (400.0, -300.0)  # do ponto do shaft ao símbolo em planta, no sistema do objeto
LARGURA_LETRA = 0.6  # largura média de uma letra, em alturas de texto


def _gira(x, y, cos_a, sen_a):
    return x * cos_a - y * sen_a, x * sen_a + y * cos_a


def girar(desenho, angulo, deslocamento=(0.0, 0.0)):
    """Gira ``desenho`` (de ``simbolo_planta``) de ``angulo`` graus em torno da origem e o desloca.

    Os textos acompanham a rotação, mas nunca ficam de cabeça para baixo: acima de 90°, o texto vira
    180° e a âncora passa para a outra ponta, ocupando o mesmo lugar.
    """
    a = math.radians(angulo)
    c, s = math.cos(a), math.sin(a)
    dx, dy = deslocamento

    def ponto(x, y):
        gx, gy = _gira(x, y, c, s)
        return gx + dx, gy + dy

    linhas = [(*ponto(x1, y1), *ponto(x2, y2)) for x1, y1, x2, y2 in desenho["linhas"]]
    circulos = [(*ponto(cx, cy), r) for cx, cy, r in desenho["circulos"]]
    textos = []
    for x, y, conteudo, altura, angulo_texto in desenho["textos"]:
        px, py = ponto(x, y)
        total = (angulo_texto + angulo) % 360.0
        if 90.0 < total <= 270.0:
            t = math.radians(total)
            ox, oy = _gira(len(str(conteudo)) * altura * LARGURA_LETRA, altura, math.cos(t), math.sin(t))
            px, py, total = px + ox, py + oy, total - 180.0
        if total > 180.0:
            total -= 360.0
        textos.append((px, py, conteudo, altura, total))
    xs = [v for l in linhas for v in (l[0], l[2])] + [cx + k * r for cx, _, r in circulos for k in (-1, 1)]
    ys = [v for l in linhas for v in (l[1], l[3])] + [cy + k * r for _, cy, r in circulos for k in (-1, 1)]
    xs += [t[0] for t in textos]
    ys += [t[1] for t in textos]
    limites = (min(xs), min(ys), max(xs), max(ys)) if xs else desenho["limites"]
    return {"linhas": linhas, "circulos": circulos, "textos": textos, "limites": limites}


def simbolo_girado(resultado, indice, angulo):
    """``simbolo_planta`` afastado do shaft (``AFASTAMENTO_SIMBOLO_MM``) e girado com o objeto, com a
    origem no ponto do shaft."""
    a = math.radians(angulo)
    deslocamento = _gira(*AFASTAMENTO_SIMBOLO_MM, math.cos(a), math.sin(a))
    return girar(simbolo_planta(resultado, indice), angulo, deslocamento)


# --- 3D -------------------------------------------------------------------------------------------

def pecas_3d(resultado):
    """Peças 3D a partir do ponto do shaft no piso da origem (z = 0): eletrodutos ou eletrocalha de cada
    trecho e a caixa de passagem de cada andar atendido, um sistema ao lado do outro em x.

    Returns:
        [{'tipo', 'cor_tipo' (a chave do sistema), 'rotulo', 'forma': 'cilindro'|'caixa', ...}] em mm.
    """
    pecas = []
    andares = resultado["andares"]
    if not andares:
        return pecas
    base = andares[0]["cota"]
    p = resultado["parametros"]
    internos = _internos(p["tipo_eletroduto"])
    x = 0.0
    for chave, s in resultado["sistemas"].items():
        largura_sistema = PASSO_DUTOS_MM
        for t in s["trechos"]:
            z0, z1 = t["cota_de"] - base, t["cota_ate"] - base
            if t["eletrocalha"]:
                largura = float(t["eletrocalha"])
                largura_sistema = max(largura_sistema, largura)
                pecas.append({"tipo": "eletrocalha", "cor_tipo": chave, "rotulo": f"{s['sigla']} {t['de']}-{t['ate']}",
                              "forma": "caixa", "origem": (x, 0.0, z0), "dims": (largura, ABA_ELETROCALHA_MM, z1 - z0)})
                continue
            raio = _diametro_externo(t["nominal"], internos) / 2.0
            for j in range(t["dutos"]):
                fila, coluna = divmod(j, DUTOS_POR_FILA)
                cx = x + raio + coluna * max(PASSO_DUTOS_MM, 2.4 * raio)
                cy = raio + fila * max(PASSO_DUTOS_MM, 2.4 * raio)
                largura_sistema = max(largura_sistema, cx - x + raio)
                pecas.append({"tipo": "eletroduto", "cor_tipo": chave, "rotulo": f"{s['sigla']} {t['de']}-{t['ate']} {j + 1}",
                              "forma": "cilindro", "origem": (cx, cy, z0), "raio": raio, "comprimento": z1 - z0,
                              "eixo": (0.0, 0.0, 1.0)})
        cx_caixa, cy_caixa, cz_caixa = CAIXA_PASSAGEM_MM
        for nome in s["derivacoes"]:
            cota = next(a["cota"] for a in andares if a["nome"] == nome) - base
            pecas.append({"tipo": "caixa", "cor_tipo": chave, "rotulo": f"{s['sigla']} caixa {nome}", "forma": "caixa",
                          "origem": (x, -cy_caixa, cota + ALTURA_CAIXA_MM), "dims": (cx_caixa, cy_caixa, cz_caixa)})
        x += max(largura_sistema, cx_caixa) + PASSO_SISTEMAS_MM
    return pecas


CORES = {"energia": (0.85, 0.22, 0.15), "dados": (0.15, 0.45, 0.85), "interfone": (0.20, 0.62, 0.30),
         "emergencia": (0.95, 0.70, 0.10)}
