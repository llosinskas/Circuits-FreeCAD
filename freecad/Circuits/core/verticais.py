"""Subidas e descidas de eletrodutos e eletrocalhas: símbolos na planta e detalhes, sem FreeCAD.

Itens verticais vêm de três lugares:

- descidas e subidas do eletroduto até as caixas (``core.rede``, ``verticais``);
- encontros de eletrodutos em alturas diferentes, como do teto para o piso, ou um
  eletroduto que muda de altura num vértice (``core.rede``, ``transicoes``), com o
  sentido de quem vem do quadro (``Rede.sentido_no_no``);
- trechos verticais das eletrocalhas e leitos (``core.bandejas``, ``verticais``).

Símbolo na planta (convenção da bancada):

- eletroduto: círculo com uma seta a 45°; a ponta aponta para o círculo quando
  desce, para fora quando sobe, e as duas quando o eletroduto passa de uma
  altura para outra;
- eletrocalha: a seção (largura × aba) com a diagonal e a mesma seta.

Os detalhes agrupam as verticais iguais (mesmo tipo, diâmetro ou seção, sentido
e alturas) e desenham cada grupo em elevação, com piso, laje e cotas.

Unidades: mm; comprimentos nos textos em m.
"""
import math

from freecad.Circuits.core import bandejas
from freecad.Circuits.core.tables.eletrodutos import DIAMETRO_PADRAO, DIAMETROS_EXTERNOS

SIGLA_BANDEJA = {"eletrocalha_perfurada": "EL", "eletrocalha_lisa": "EL", "leito": "LT"}
SENTIDOS = {"sobe": "sobe", "desce": "desce", "sobe_desce": "sobe/desce"}
TOLERANCIA_PRUMADA_MM = 100.0  # pontas de pavimentos diferentes a até esta distância formam uma prumada
PAVIMENTO, TETO, PISO, PASSA = "pavimento", "teto", "piso", "passa"  # onde a vertical está em relação ao pavimento
# Ordem e texto da legenda: (tipo, nível, sentido) -> descrição; sentido None vale para qualquer um
LEGENDA = [
    ("eletroduto", PAVIMENTO, "desce", "Eletroduto que desce (à caixa ou a outra altura), no pavimento"),
    ("eletroduto", PAVIMENTO, "sobe", "Eletroduto que sobe (à caixa ou a outra altura), no pavimento"),
    ("eletroduto", PAVIMENTO, "sobe_desce", "Eletroduto que sobe e desce no mesmo ponto, no pavimento"),
    ("eletroduto", TETO, None, "Eletroduto que sobe ao pavimento de cima, pelo teto"),
    ("eletroduto", PISO, None, "Eletroduto que desce ao pavimento de baixo, pelo piso"),
    ("eletroduto", PASSA, None, "Eletroduto que passa pelo pavimento, entre os de cima e de baixo"),
    ("eletrocalha", PAVIMENTO, None, "Eletrocalha que muda de altura, no pavimento"),
    ("eletrocalha", TETO, None, "Eletrocalha que sobe ao pavimento de cima, pelo teto"),
    ("eletrocalha", PISO, None, "Eletrocalha que desce ao pavimento de baixo, pelo piso"),
    ("eletrocalha", PASSA, None, "Eletrocalha que passa pelo pavimento, entre os de cima e de baixo"),
]
TAMANHO_PADRAO = 300.0  # comprimento da seta do símbolo [mm]
LARGURA_DETALHE = 2000.0  # espaço de cada detalhe, lado a lado
CAIXA_DETALHE = 100.0  # caixa 4x2" vista de frente, simplificada
RAIO_CURVA_ELETRODUTO_FATOR = 6.0  # raio da curva do eletroduto, em diâmetros externos


def _numero(valor):
    """2.5 -> '2,50'."""
    return f"{float(valor):.2f}".replace(".", ",")


def _cota(valor_mm):
    """Altura em relação ao piso: 2800 -> '+2,80'; -100 -> '-0,10'."""
    metros = float(valor_mm) / 1000.0
    return ("+" if metros >= 0 else "-") + _numero(abs(metros))


def itens_de_eletroduto(descidas, transicoes):
    """Itens verticais de eletroduto.

    Args:
        descidas: ``verticais`` de ``core.rede.analisar`` (caixa, x, y, alturas, sentido, diâmetro).
        transicoes: ``transicoes`` de ``core.rede.analisar``.
    """
    itens = []
    for v in descidas:
        eletroduto, caixa = float(v["altura_eletroduto"]), float(v["altura_caixa"])
        itens.append({
            "tipo": "eletroduto", "x": float(v["x"]), "y": float(v["y"]),
            "sentido": "desce" if v["sentido"] == "descida" else "sobe",
            "de": min(eletroduto, caixa), "ate": max(eletroduto, caixa), "diametro": str(v["diametro"]),
            "local": v.get("caixa", ""), "pavimento": v.get("pavimento", ""), "caixa": True,
        })
    for t in transicoes:
        itens.append({
            "tipo": "eletroduto", "x": float(t["x"]), "y": float(t["y"]), "sentido": t.get("sentido", "sobe_desce"),
            "de": float(t["de"]), "ate": float(t["ate"]), "diametro": str(t["diametro"]),
            "local": f"({t['x'] / 1000:.1f}; {t['y'] / 1000:.1f}) m", "pavimento": t.get("pavimento", ""),
            "caixa": False,
        })
    return itens


def itens_de_eletrocalha(verticais_bandejas):
    """Itens verticais de eletrocalha e leito (``verticais`` de ``core.bandejas.analisar``)."""
    return [{
        "tipo": "eletrocalha", "x": float(v["x"]), "y": float(v["y"]),
        "sentido": "desce" if v.get("sentido") == "desce" else "sobe",
        "de": float(v["de"]), "ate": float(v["ate"]), "tipo_bandeja": v["tipo"],
        "largura": float(v["largura"]), "aba": float(v["aba"]), "angulo": float(v.get("angulo", 0.0)),
        "local": v.get("nome", ""), "pavimento": v.get("pavimento", ""),
    } for v in verticais_bandejas]


def _descricao(item):
    if item["tipo"] == "eletroduto":
        return f'Ø{item["diametro"]}"'
    return f'{SIGLA_BANDEJA.get(item["tipo_bandeja"], "EL")} {item["largura"]:g}x{item["aba"]:g}'


def texto(item):
    """Texto ao lado do símbolo.

    No pavimento: 'Ø3/4" desce 2,50 m'. Entre pavimentos: 'Ø1" sobe ao 1º Pavimento 3,20 m',
    'Ø1" desce ao Térreo 3,20 m' ou 'Ø1" passa (Térreo → 2º Pavimento)'.
    """
    comprimento = _numero((item["ate"] - item["de"]) / 1000.0)
    nivel = item.get("nivel", PAVIMENTO)
    if nivel == TETO:
        return f"{_descricao(item)} sobe ao {item['destino']} {comprimento} m"
    if nivel == PISO:
        return f"{_descricao(item)} desce ao {item['destino']} {comprimento} m"
    if nivel == PASSA:
        return f"{_descricao(item)} passa ({item['origem']} → {item['destino']})"
    return f"{_descricao(item)} {SENTIDOS[item['sentido']]} {comprimento} m"


def _seta(x0, y0, x1, y1, tamanho_ponta):
    """Dois traços da ponta da seta em (x1, y1), apontando de (x0, y0) para lá."""
    angulo = math.atan2(y1 - y0, x1 - x0)
    return [(x1, y1, x1 - tamanho_ponta * math.cos(angulo + d), y1 - tamanho_ponta * math.sin(angulo + d))
            for d in (math.radians(25), -math.radians(25))]


def simbolo(item, tamanho=TAMANHO_PADRAO):
    """Símbolo do item na planta, centrado no ponto da vertical.

    Returns:
        {'linhas': [(x1, y1, x2, y2)], 'circulos': [(cx, cy, raio)], 'texto': (x, y)} [mm].
    """
    tamanho = float(tamanho)
    linhas, circulos = [], []
    c = math.cos(math.radians(45))
    nivel = item.get("nivel", PAVIMENTO)
    entre_pavimentos = nivel in (TETO, PISO, PASSA)
    if item["tipo"] == "eletroduto":
        raio = tamanho / 4
        circulos.append((0.0, 0.0, raio))
        if entre_pavimentos:  # prumada: círculo duplo
            circulos.append((0.0, 0.0, raio * 0.6))
        inicio = (raio * c, raio * c)
    else:
        meia_aba, meia_largura = item["aba"] / 2, item["largura"] / 2
        giro = math.radians(item.get("angulo", 0.0))
        cg, sg = math.cos(giro), math.sin(giro)

        def girar(x, y):
            return (round(x * cg - y * sg, 6), round(x * sg + y * cg, 6))

        cantos = [girar(-meia_aba, -meia_largura), girar(meia_aba, -meia_largura),
                  girar(meia_aba, meia_largura), girar(-meia_aba, meia_largura)]
        linhas += [cantos[i] + cantos[(i + 1) % 4] for i in range(4)]
        linhas.append(cantos[0] + cantos[2])
        if entre_pavimentos:  # prumada: as duas diagonais
            linhas.append(cantos[1] + cantos[3])
        raio = math.hypot(meia_aba, meia_largura)
        inicio = (raio * c, raio * c)
    fim = (tamanho * c, tamanho * c)
    if nivel == PASSA:  # a seta atravessa o símbolo de um lado ao outro
        inicio = (-fim[0], -fim[1])
    linhas.append(inicio + fim)
    ponta = tamanho * 0.15
    if item["sentido"] in ("desce", "sobe_desce"):
        linhas += _seta(fim[0], fim[1], inicio[0], inicio[1], ponta)
    if item["sentido"] in ("sobe", "sobe_desce"):
        linhas += _seta(inicio[0], inicio[1], fim[0], fim[1], ponta)
    return {"linhas": linhas, "circulos": circulos, "texto": (fim[0] + tamanho * 0.1, fim[1])}


def ligacoes_entre_pavimentos(pontas, pavimentos, tolerancia=TOLERANCIA_PRUMADA_MM):
    """Prumadas: pontas soltas do mesmo tipo, no mesmo ponto em planta, em pavimentos diferentes.

    Cada par de pavimentos seguidos (por cota) com pontas no mesmo ponto vira uma
    vertical: no de baixo sai pelo teto (``teto``, sobe), no de cima entra pelo
    piso (``piso``, desce), e nos pavimentos entre os dois ela só passa (``passa``).

    Args:
        pontas: dicionários com ``tipo`` ('eletroduto' ou 'eletrocalha'), ``x``,
            ``y``, ``pavimento``, ``altura`` (do piso do pavimento) e ``nome``;
            eletroduto com ``diametro``; eletrocalha com ``largura``, ``aba``,
            ``tipo_bandeja`` e ``angulo``.
        pavimentos: {nome: cota do piso [mm]}.
    Returns:
        Itens verticais (como os de ``itens_de_eletroduto``), com ``nivel``,
        ``destino`` e, na passagem, ``origem``; alturas ``de`` e ``ate`` sempre a
        partir do piso do pavimento do item. O item ``teto`` tem ``piso_destino``,
        a cota do piso de cima a partir do seu, e ``atravessados``, os pisos do
        meio [(nome, cota a partir do seu)].
    """
    grupos = []
    for p in pontas:
        if p["pavimento"] not in pavimentos:
            continue
        grupo = next((g for g in grupos if g[0]["tipo"] == p["tipo"] and
                      math.hypot(g[0]["x"] - p["x"], g[0]["y"] - p["y"]) <= tolerancia), None)
        if grupo is None:
            grupos.append([p])
        else:
            grupo.append(p)

    itens = []
    for grupo in grupos:
        por_pavimento = {}
        for p in grupo:
            por_pavimento.setdefault(p["pavimento"], p)
        ordem = sorted(por_pavimento.values(), key=lambda p: pavimentos[p["pavimento"]])
        for baixo, cima in zip(ordem, ordem[1:]):
            cota_baixo, cota_cima = pavimentos[baixo["pavimento"]], pavimentos[cima["pavimento"]]
            de_abs, ate_abs = cota_baixo + float(baixo["altura"]), cota_cima + float(cima["altura"])
            base = {chave: baixo[chave] for chave in ("tipo", "diametro", "largura", "aba", "tipo_bandeja", "angulo")
                    if chave in baixo}
            base.update(x=float(baixo["x"]), y=float(baixo["y"]), caixa=False)
            atravessados = [(nome, cota - cota_baixo) for nome, cota in sorted(pavimentos.items(), key=lambda i: i[1])
                            if cota_baixo < cota < cota_cima]
            itens.append(dict(base, pavimento=baixo["pavimento"], nivel=TETO, sentido="sobe", destino=cima["pavimento"],
                              de=de_abs - cota_baixo, ate=ate_abs - cota_baixo, piso_destino=cota_cima - cota_baixo,
                              atravessados=atravessados, local=baixo["nome"]))
            itens.append(dict(base, pavimento=cima["pavimento"], nivel=PISO, sentido="desce", destino=baixo["pavimento"],
                              de=de_abs - cota_cima, ate=ate_abs - cota_cima, local=cima["nome"]))
            for nome, cota in sorted(pavimentos.items(), key=lambda item: item[1]):
                if cota_baixo < cota < cota_cima:
                    itens.append(dict(base, pavimento=nome, nivel=PASSA, sentido="sobe_desce", origem=baixo["pavimento"],
                                      destino=cima["pavimento"], de=de_abs - cota, ate=ate_abs - cota,
                                      local=f"{baixo['nome']} → {cima['nome']}"))
    return itens


def _chave_da_legenda(item):
    nivel = item.get("nivel", PAVIMENTO)
    for indice, (tipo, nivel_legenda, sentido, _) in enumerate(LEGENDA):
        if tipo == item["tipo"] and nivel_legenda == nivel and sentido in (None, item["sentido"]):
            return indice
    return None


def itens_de_legenda(itens, tamanho=TAMANHO_PADRAO):
    """Linhas da legenda para os tipos de vertical usados, na ordem de ``LEGENDA``.

    Returns:
        [(chave, primitivas ('linha', ...) e ('circulo', ...), descrição)].
    """
    usados = sorted({i for i in (_chave_da_legenda(item) for item in itens) if i is not None})
    resultado = []
    for indice in usados:
        tipo, nivel, sentido, descricao = LEGENDA[indice]
        exemplo = {"tipo": tipo, "nivel": nivel, "sentido": sentido or {TETO: "sobe", PISO: "desce"}.get(nivel, "sobe_desce"),
                   "largura": tamanho * 0.5, "aba": tamanho * 0.2, "angulo": 0.0}
        desenho = simbolo(exemplo, tamanho)
        primitivas = [("linha",) + tuple(l) for l in desenho["linhas"]] + [("circulo",) + tuple(c) for c in desenho["circulos"]]
        chave = f"vertical_{tipo}_{nivel}" + (f"_{sentido}" if sentido else "")
        resultado.append((chave, primitivas, descricao))
    return resultado


def materiais_prumadas(itens):
    """Materiais das prumadas, contadas uma vez (pelo item ``teto``, no pavimento de baixo).

    Returns:
        (verticais de eletroduto [{'diametro', 'comprimento' m, 'pavimento'}], para os
        quantitativos como as outras verticais; componentes das eletrocalhas:
        metros, curvas verticais interna (embaixo) e externa (no alto), emendas e
        suportes de parede).
    """
    verticais_eletroduto, somas = [], {}

    def somar(grupo, item, especificacao, unidade, quantidade, pavimento):
        chave = (pavimento, grupo, item, especificacao, unidade)
        somas[chave] = somas.get(chave, 0) + quantidade

    for item in itens:
        if item.get("nivel") != TETO:
            continue
        comprimento = (item["ate"] - item["de"]) / 1000.0
        if item["tipo"] == "eletroduto":
            verticais_eletroduto.append({"diametro": item["diametro"], "comprimento": round(comprimento, 3),
                                         "pavimento": item["pavimento"]})
            continue
        secao = bandejas.medida(item["largura"], item["aba"])
        pav = item["pavimento"]
        somar(bandejas.GRUPO, bandejas.nome_do_tipo(item["tipo_bandeja"]),
              f"{secao}, barras de 3 m (inclui {bandejas.PERDA_BANDEJA:.0%} de perdas)", "m",
              comprimento * (1 + bandejas.PERDA_BANDEJA), pav)
        tipo = f"{bandejas.nome_do_tipo(item['tipo_bandeja'])} {secao}"
        somar(bandejas.GRUPO, bandejas.CURVA_VERTICAL_INTERNA, tipo, "un", 1, pav)
        somar(bandejas.GRUPO, bandejas.CURVA_VERTICAL_EXTERNA, tipo, "un", 1, pav)
        somar(bandejas.GRUPO, "Emenda (par de talas)", secao, "un", 4, pav)  # dois lados de cada curva
        vao = bandejas.VAO_SUPORTE.get(item["tipo_bandeja"], bandejas.VAO_SUPORTE[bandejas.TIPO_PADRAO])
        somar(bandejas.GRUPO_SUPORTES, "Suporte de parede para trecho vertical", f"para largura {item['largura']:g} mm",
              "un", max(1, math.ceil(comprimento * 1000.0 / vao - 1e-9)), pav)
    componentes = [{"pavimento": pav, "grupo": g, "item": i, "especificacao": e, "unidade": u,
                    "quantidade": round(q, 2) if u == "m" else int(q)}
                   for (pav, g, i, e, u), q in sorted(somas.items())]
    return verticais_eletroduto, componentes


def _chave(item):
    if item["tipo"] == "eletroduto":
        medida = (DIAMETROS_EXTERNOS.get(item["diametro"], DIAMETRO_PADRAO), item["diametro"])
    else:
        medida = (item["largura"], item["aba"], item["tipo_bandeja"])
    nivel = item.get("nivel", PAVIMENTO)
    return (0 if item["tipo"] == "eletroduto" else 1, medida, nivel, item["sentido"], round(item["de"]),
            round(item["ate"]), item.get("destino", ""))


def detalhes(itens):
    """Verticais iguais agrupadas num detalhe: V1, V2...

    Returns:
        Lista de itens (o primeiro de cada grupo) com ``id``, ``quantidade`` e
        ``locais`` (nomes, sem repetição), em ordem: eletrodutos, depois
        eletrocalhas; por medida, sentido e alturas.
    """
    grupos = {}
    for item in itens:
        if item.get("nivel") in (PISO, PASSA):
            continue  # a prumada é detalhada uma vez, pelo pavimento de baixo
        grupos.setdefault(_chave(item), []).append(item)
    resultado = []
    for numero, chave in enumerate(sorted(grupos), start=1):
        membros = grupos[chave]
        resultado.append(dict(membros[0], id=f"V{numero}", quantidade=len(membros),
                              locais=sorted({m["local"] for m in membros if m["local"]})))
    return resultado


def geometria_detalhe(detalhe, pe_direito=3000.0):
    """Desenho em elevação de um detalhe, com o piso em y = 0 e o eixo da vertical em x = 0.

    Vista lateral: a vertical e os trechos horizontais na mesma espessura (o
    diâmetro do eletroduto ou a aba da eletrocalha), ligados por curvas em arco
    (raio na linha de centro: 6 diâmetros no eletroduto, a largura na eletrocalha).
    No alto, o trecho segue para a direita; embaixo, para a esquerda; quando a
    vertical vai até uma caixa, a caixa toma o lugar do trecho. Na eletrocalha,
    as curvas verticais (CVE no alto, CVI embaixo). Cotas depois do fim do trecho.

    Returns:
        {'linhas': [(x1, y1, x2, y2)], 'arcos': [(cx, cy, raio, ângulo inicial, varredura)],
        'textos': [(x, y, texto, altura)]} [mm, graus].
    """
    de, ate, pe_direito = float(detalhe["de"]), float(detalhe["ate"]), float(pe_direito)
    altura_texto = 100.0
    if detalhe.get("nivel") == TETO:  # prumada: o piso deste pavimento e o do pavimento de cima
        pe_direito = float(detalhe["piso_destino"])
        rotulo_baixo, rotulo_cima = f"piso {detalhe['pavimento']}", f"piso {detalhe['destino']}"
    else:
        rotulo_baixo, rotulo_cima = "piso", "laje"
    linhas = [(-LARGURA_DETALHE / 2, 0.0, LARGURA_DETALHE / 2, 0.0),
              (-LARGURA_DETALHE / 2, pe_direito, LARGURA_DETALHE / 2, pe_direito)]
    textos = [(-LARGURA_DETALHE / 2, 40.0, rotulo_baixo, altura_texto * 0.8),
              (-LARGURA_DETALHE / 2, pe_direito + 40.0, rotulo_cima, altura_texto * 0.8)]
    for nome, cota in detalhe.get("atravessados", []) if detalhe.get("nivel") == TETO else []:
        linhas.append((-LARGURA_DETALHE / 2, cota, LARGURA_DETALHE / 2, cota))
        textos.append((-LARGURA_DETALHE / 2, cota + 40.0, f"piso {nome}", altura_texto * 0.8))
    textos += [(-LARGURA_DETALHE / 2, max(pe_direito, ate) + 350.0,
               f"{detalhe['id']} · {_descricao(detalhe)} · "
               f"{('prumada ao ' + detalhe['destino']) if detalhe.get('nivel') == TETO else SENTIDOS[detalhe['sentido']]}"
               f" · {detalhe['quantidade']} un",
               altura_texto * 1.2)]

    # Vista lateral: a vertical e os trechos horizontais aparecem na mesma espessura
    # (diâmetro do eletroduto, ou aba da eletrocalha), com as quinas fechadas.
    if detalhe["tipo"] == "eletroduto":
        espessura = DIAMETROS_EXTERNOS.get(detalhe["diametro"], DIAMETRO_PADRAO)
        horizontal = 700.0
        caixa_embaixo = bool(detalhe.get("caixa")) and detalhe["sentido"] == "desce"
        caixa_em_cima = bool(detalhe.get("caixa")) and detalhe["sentido"] == "sobe"
    else:
        espessura = detalhe["aba"]
        horizontal = 800.0
        caixa_embaixo = caixa_em_cima = False
    meia = espessura / 2
    vira_no_alto, vira_embaixo = not caixa_em_cima, not caixa_embaixo
    if detalhe["tipo"] == "eletroduto":
        raio = RAIO_CURVA_ELETRODUTO_FATOR * espessura
    else:
        raio = bandejas.RAIO_CURVA_FATOR * detalhe["largura"]
    # vertical curta demais para as curvas inteiras: o raio diminui até elas se tocarem
    curvas = int(vira_no_alto) + int(vira_embaixo)
    if curvas:
        raio = max(meia, min(raio, (ate - de - curvas * meia) / curvas))
    arcos = []
    topo, base = ate, de  # onde as paredes retas da vertical terminam
    if vira_no_alto:  # curva para a direita no alto: centro à direita, quarto de cima à esquerda
        cx, cy = raio, ate - meia - raio
        arcos += [(cx, cy, raio + meia, 90.0, 90.0), (cx, cy, raio - meia, 90.0, 90.0)]
        linhas += [(cx, ate, meia + horizontal, ate), (cx, ate - espessura, meia + horizontal, ate - espessura)]
        topo = cy
    if vira_embaixo:  # curva para a esquerda embaixo: centro à esquerda, quarto de baixo à direita
        cx, cy = -raio, de + meia + raio
        arcos += [(cx, cy, raio + meia, 270.0, 90.0), (cx, cy, raio - meia, 270.0, 90.0)]
        linhas += [(cx, de, -meia - horizontal, de), (cx, de + espessura, -meia - horizontal, de + espessura)]
        base = cy
    linhas += [(-meia, base, -meia, topo), (meia, base, meia, topo)]
    if caixa_embaixo or caixa_em_cima:
        y = de - CAIXA_DETALHE if caixa_embaixo else ate
        m = CAIXA_DETALHE / 2
        linhas += [(-m, y, m, y), (m, y, m, y + CAIXA_DETALHE), (m, y + CAIXA_DETALHE, -m, y + CAIXA_DETALHE),
                   (-m, y + CAIXA_DETALHE, -m, y)]
    if detalhe["tipo"] == "eletrocalha":
        textos += [(-meia - 450.0, ate + 60.0, "CVE 90°", altura_texto * 0.8),
                   (meia + 60.0, de - 160.0, "CVI 90°", altura_texto * 0.8)]

    x_cota = meia + horizontal + 150.0
    textos += [(x_cota, ate - 40.0, _cota(ate), altura_texto), (x_cota, de - 40.0, _cota(de), altura_texto),
               (x_cota, (de + ate) / 2, f"vertical {_numero((ate - de) / 1000.0)} m", altura_texto * 0.8)]
    if detalhe.get("locais"):
        locais = ", ".join(detalhe["locais"][:6]) + (" ..." if len(detalhe["locais"]) > 6 else "")
        textos.append((-LARGURA_DETALHE / 2, -250.0, locais, altura_texto * 0.7))
    return {"linhas": [tuple(float(v) for v in linha) for linha in linhas], "arcos": arcos, "textos": textos}
