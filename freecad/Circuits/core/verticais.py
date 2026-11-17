"""Subidas e descidas de eletrodutos e eletrocalhas: símbolos na planta e detalhes, sem FreeCAD.

Itens verticais vêm de três lugares:

- descidas e subidas do eletroduto até as caixas (``core.rede``, ``verticais``);
- encontros de eletrodutos em alturas diferentes, como do teto para o piso
  (``core.rede``, ``transicoes``);
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

from freecad.Circuits.core.tables.eletrodutos import DIAMETRO_PADRAO, DIAMETROS_EXTERNOS

SIGLA_BANDEJA = {"eletrocalha_perfurada": "EL", "eletrocalha_lisa": "EL", "leito": "LT"}
SENTIDOS = {"sobe": "sobe", "desce": "desce", "sobe_desce": "sobe/desce"}
TAMANHO_PADRAO = 300.0  # comprimento da seta do símbolo [mm]
LARGURA_DETALHE = 2000.0  # espaço de cada detalhe, lado a lado
CAIXA_DETALHE = 100.0  # caixa 4x2" vista de frente, simplificada


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
            "tipo": "eletroduto", "x": float(t["x"]), "y": float(t["y"]), "sentido": "sobe_desce",
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
    """Texto ao lado do símbolo: 'Ø3/4" desce 2,50 m' ou 'EL 200x50 desce 0,50 m'."""
    comprimento = (item["ate"] - item["de"]) / 1000.0
    return f"{_descricao(item)} {SENTIDOS[item['sentido']]} {_numero(comprimento)} m"


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
    if item["tipo"] == "eletroduto":
        raio = tamanho / 4
        circulos.append((0.0, 0.0, raio))
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
        raio = math.hypot(meia_aba, meia_largura)
        inicio = (raio * c, raio * c)
    fim = (tamanho * c, tamanho * c)
    linhas.append(inicio + fim)
    ponta = tamanho * 0.15
    if item["sentido"] in ("desce", "sobe_desce"):
        linhas += _seta(fim[0], fim[1], inicio[0], inicio[1], ponta)
    if item["sentido"] in ("sobe", "sobe_desce"):
        linhas += _seta(inicio[0], inicio[1], fim[0], fim[1], ponta)
    return {"linhas": linhas, "circulos": circulos, "texto": (fim[0] + tamanho * 0.1, fim[1])}


def _chave(item):
    if item["tipo"] == "eletroduto":
        medida = (DIAMETROS_EXTERNOS.get(item["diametro"], DIAMETRO_PADRAO), item["diametro"])
    else:
        medida = (item["largura"], item["aba"], item["tipo_bandeja"])
    return (0 if item["tipo"] == "eletroduto" else 1, medida, item["sentido"], round(item["de"]), round(item["ate"]))


def detalhes(itens):
    """Verticais iguais agrupadas num detalhe: V1, V2...

    Returns:
        Lista de itens (o primeiro de cada grupo) com ``id``, ``quantidade`` e
        ``locais`` (nomes, sem repetição), em ordem: eletrodutos, depois
        eletrocalhas; por medida, sentido e alturas.
    """
    grupos = {}
    for item in itens:
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
    diâmetro do eletroduto ou a aba da eletrocalha), com as quinas fechadas.
    No alto, o trecho segue para a direita; embaixo, para a esquerda; quando a
    vertical vai até uma caixa, a caixa toma o lugar do trecho. Na eletrocalha,
    as curvas verticais (CVE no alto, CVI embaixo). Cotas depois do fim do trecho.

    Returns:
        {'linhas': [(x1, y1, x2, y2)], 'textos': [(x, y, texto, altura)]} [mm].
    """
    de, ate, pe_direito = float(detalhe["de"]), float(detalhe["ate"]), float(pe_direito)
    linhas = [(-LARGURA_DETALHE / 2, 0.0, LARGURA_DETALHE / 2, 0.0),
              (-LARGURA_DETALHE / 2, pe_direito, LARGURA_DETALHE / 2, pe_direito)]
    altura_texto = 100.0
    textos = [(-LARGURA_DETALHE / 2, 40.0, "piso", altura_texto * 0.8),
              (-LARGURA_DETALHE / 2, pe_direito + 40.0, "laje", altura_texto * 0.8),
              (-LARGURA_DETALHE / 2, pe_direito + 350.0,
               f"{detalhe['id']} · {_descricao(detalhe)} · {SENTIDOS[detalhe['sentido']]} · {detalhe['quantidade']} un",
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
    fora_de = de + espessura if vira_embaixo else de  # parede de fora (x < 0)
    dentro_ate = ate - espessura if vira_no_alto else ate  # parede de dentro (x > 0)
    linhas += [(-meia, fora_de, -meia, ate), (meia, de, meia, dentro_ate)]
    if vira_no_alto:  # segue para a direita no alto
        linhas += [(-meia, ate, meia + horizontal, ate), (meia, ate - espessura, meia + horizontal, ate - espessura)]
    if vira_embaixo:  # segue para a esquerda embaixo
        linhas += [(meia, de, -meia - horizontal, de), (-meia, de + espessura, -meia - horizontal, de + espessura)]
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
    return {"linhas": [tuple(float(v) for v in linha) for linha in linhas], "textos": textos}
