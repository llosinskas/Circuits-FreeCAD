"""Folhas de desenho (TechDraw): formato, carimbo, escala e arrumação das vistas, cortes e detalhes.

Formatos da série A deitados, com as margens da NBR 10068 (25 mm à esquerda, 10 mm
nas outras bordas no A0 e A1 e 7 mm no A2, A3 e A4) e o carimbo no canto inferior
direito (``CARIMBO_LARGURA`` × ``CARIMBO_ALTURA``, medidas da bancada, próximas
das usuais). O carimbo é um modelo SVG do TechDraw com campos editáveis
(``freecad:editable``), gerado por ``modelo_svg``.

Coordenadas da folha em mm, com origem no canto inferior esquerdo (como o TechDraw);
as do SVG do modelo têm o Y para baixo. Escala ``n`` quer dizer 1:n.
"""
import math
import re
from xml.sax.saxutils import escape

FORMATOS = {"A0": (1189.0, 841.0), "A1": (841.0, 594.0), "A2": (594.0, 420.0), "A3": (420.0, 297.0),
            "A4": (297.0, 210.0)}
FORMATO_PADRAO = "A1"
MARGEM_ESQUERDA = 25.0
CARIMBO_LARGURA = 180.0
CARIMBO_ALTURA = 56.0
FOLGA = 5.0  # da margem até a primeira vista e entre o carimbo e as vistas
ESPACO_ENTRE_VISTAS = 10.0
ALTURA_TITULO = 9.0  # título da vista ("PLANTA - TÉRREO" e a escala), embaixo dela

ESCALAS = (1, 2, 5, 10, 20, 25, 50, 75, 100, 125, 200, 250, 500, 1000)
AMPLIACAO_DETALHE = 2.0  # o detalhe sai em pelo menos o dobro da escala da folha

# (chave, rótulo, x, largura, linha) — linhas de 14 mm de cima para baixo, x a partir da esquerda do carimbo
CAMPOS_CARIMBO = (
    ("Projeto", "PROJETO", 0, 180, 0),
    ("Titulo", "CONTEÚDO DA FOLHA", 0, 180, 1),
    ("Obra", "OBRA / ENDEREÇO", 0, 80, 2),
    ("Cliente", "CLIENTE", 80, 60, 2),
    ("Desenho", "DESENHO", 140, 40, 2),
    ("Responsavel", "RESPONSÁVEL TÉCNICO", 0, 70, 3),
    ("Registro", "CREA / CFT", 70, 30, 3),
    ("Data", "DATA", 100, 25, 3),
    ("Escala", "ESCALA", 125, 25, 3),
    ("Folha", "FOLHA", 150, 15, 3),
    ("Revisao", "REV.", 165, 15, 3),
)
ALTURA_LINHA_CARIMBO = 14.0


def margens(formato):
    """(esquerda, direita, baixo, cima) [mm] pela NBR 10068."""
    outra = 10.0 if formato in ("A0", "A1") else 7.0
    return MARGEM_ESQUERDA, outra, outra, outra


def tamanho(formato):
    if formato not in FORMATOS:
        raise ValueError(f"formato desconhecido: {formato}")
    return FORMATOS[formato]


def retangulo_do_carimbo(formato):
    """(x0, y0, x1, y1) do carimbo na folha (Y para cima)."""
    largura, _ = tamanho(formato)
    _, direita, baixo, _ = margens(formato)
    return largura - direita - CARIMBO_LARGURA, baixo, largura - direita, baixo + CARIMBO_ALTURA


def area_util(formato):
    """(x0, y0, x1, y1) onde as vistas podem ficar, dentro das margens e com folga."""
    largura, altura = tamanho(formato)
    esquerda, direita, baixo, cima = margens(formato)
    return esquerda + FOLGA, baixo + FOLGA, largura - direita - FOLGA, altura - cima - FOLGA


def texto_escala(n):
    return f"1:{n:g}"


def escala_do_detalhe(n, ampliacao=AMPLIACAO_DETALHE):
    """Maior escala da lista que amplia a da folha pelo menos ``ampliacao`` vezes (1:50 → 1:25)."""
    alvo = n / ampliacao
    candidatas = [e for e in ESCALAS if e <= alvo]
    return max(candidatas) if candidatas else ESCALAS[0]


def rotulo_folha(numero, total):
    return f"{numero:02d}/{total:02d}"


def proxima_letra(usadas):
    """Letra do próximo corte (A, B, ..., Z, AA, AB...), fora das já usadas."""
    usadas = set(usadas)
    n = 0
    while True:
        k, letra = n, ""
        while True:
            letra = chr(ord("A") + k % 26) + letra
            k = k // 26 - 1
            if k < 0:
                break
        if letra not in usadas:
            return letra
        n += 1


def proximo_detalhe(usados):
    """Nome do próximo detalhe (D1, D2...)."""
    n = 1
    while f"D{n}" in set(usados):
        n += 1
    return f"D{n}"


# --- modelo SVG com o carimbo ----------------------------------------------------------------

def modelo_svg(formato):
    """Modelo do TechDraw: borda nas margens, carimbo com os campos editáveis de ``CAMPOS_CARIMBO``."""
    largura, altura = tamanho(formato)
    esquerda, direita, baixo, cima = margens(formato)
    cx0 = largura - direita - CARIMBO_LARGURA
    cy0 = altura - baixo - CARIMBO_ALTURA  # topo do carimbo no SVG (Y para baixo)
    linhas = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
        'xmlns:freecad="http://www.freecadweb.org/wiki/index.php?title=Svg_Namespace" '
        f'width="{largura:g}mm" height="{altura:g}mm" viewBox="0 0 {largura:g} {altura:g}">',
        f'<!-- Folha {formato} da bancada Circuits: margens da NBR 10068 e carimbo -->',
        '<g style="fill:none;stroke:#000000;stroke-linecap:square">',
        f'<rect x="{esquerda:g}" y="{cima:g}" width="{largura - esquerda - direita:g}" '
        f'height="{altura - cima - baixo:g}" style="stroke-width:0.7"/>',
        f'<rect x="{cx0:g}" y="{cy0:g}" width="{CARIMBO_LARGURA:g}" height="{CARIMBO_ALTURA:g}" '
        'style="stroke-width:0.5"/>',
    ]
    for linha in range(1, 4):
        y = cy0 + linha * ALTURA_LINHA_CARIMBO
        linhas.append(f'<path d="M {cx0:g},{y:g} H {cx0 + CARIMBO_LARGURA:g}" style="stroke-width:0.35"/>')
    divisores = sorted({(x, linha) for _, _, x, _, linha in CAMPOS_CARIMBO if x > 0})
    for x, linha in divisores:
        y = cy0 + linha * ALTURA_LINHA_CARIMBO
        linhas.append(f'<path d="M {cx0 + x:g},{y:g} V {y + ALTURA_LINHA_CARIMBO:g}" style="stroke-width:0.35"/>')
    linhas.append('</g>')
    linhas.append('<g style="font-family:osifont,sans-serif;fill:#000000;stroke:none">')
    for chave, rotulo, x, _, linha in CAMPOS_CARIMBO:
        x0, y0 = cx0 + x + 1.5, cy0 + linha * ALTURA_LINHA_CARIMBO
        grande = chave in ("Projeto", "Titulo")
        linhas.append(f'<text x="{x0:g}" y="{y0 + 3.2:g}" style="font-size:2px">{escape(rotulo)}</text>')
        linhas.append(f'<text freecad:editable="{chave}" x="{x0:g}" y="{y0 + (11.0 if grande else 10.5):g}" '
                      f'style="font-size:{5.0 if grande else 3.2}px"><tspan>{escape(" ")}</tspan></text>')
    linhas += ['</g>', '</svg>', '']
    return "\n".join(linhas)


def campos_do_carimbo():
    return [chave for chave, *_ in CAMPOS_CARIMBO]


# --- arrumação das vistas -----------------------------------------------------------------------

def _fator(vista, n):
    if vista.get("tipo") == "tabela":
        return 1.0  # planilhas: o tamanho já é o da folha
    if vista.get("escala"):
        return 1.0 / float(vista["escala"])
    if vista.get("tipo") == "detalhe":
        return 1.0 / escala_do_detalhe(n)
    return 1.0 / n


def _empacotar(caixas, formato):
    """Prateleiras de cima para baixo, da esquerda para a direita, fugindo do carimbo.

    Args:
        caixas: [(largura, altura)] já com o título, na ordem em que entram.
    Returns:
        [(x0, y_topo)] de cada caixa, ou None se não cabe.
    """
    x0, y0, x1, y1 = area_util(formato)
    carimbo = retangulo_do_carimbo(formato)
    topo_carimbo = carimbo[3] + FOLGA
    limite_com_carimbo = carimbo[0] - FOLGA
    posicoes = [None] * len(caixas)
    ordem = sorted(range(len(caixas)), key=lambda i: -caixas[i][1])
    topo, x, altura_linha = y1, x0, 0.0
    for i in ordem:
        largura, altura = caixas[i]
        while True:
            fundo = topo - max(altura_linha, altura)
            limite = x1 if fundo >= topo_carimbo else limite_com_carimbo
            if x + largura <= limite + 1e-6:
                break
            if x == x0:  # nem sozinha na prateleira ela cabe
                return None
            topo, x, altura_linha = topo - altura_linha - ESPACO_ENTRE_VISTAS, x0, 0.0
        if topo - altura < y0 - 1e-6:
            return None
        posicoes[i] = (x, topo)
        x += largura + ESPACO_ENTRE_VISTAS
        altura_linha = max(altura_linha, altura)
    return posicoes


def organizar(vistas, formato, escala=None):
    """Escolhe a escala da folha e a posição de cada vista.

    Args:
        vistas: [{'nome', 'largura', 'altura' (tamanho no modelo, mm), 'tipo' ('desenho',
            'detalhe', 'corte' ou 'tabela'), 'escala' (opcional, fixa a escala da vista)}].
        formato: 'A0' a 'A4'.
        escala: denominador fixo da folha, ou None para a maior escala de ``ESCALAS`` que cabe.
    Returns:
        {'escala': n, 'cabe': bool, 'vistas': [{'nome', 'x', 'y' (centro do desenho na folha),
        'fator' (1/n da vista), 'escala' (n da vista), 'largura', 'altura' (na folha),
        'titulo_x', 'titulo_y'}]}. Sem nenhuma escala que caiba, ``cabe`` é False e as
        posições são as da menor escala, para o usuário mudar o formato.
    """
    candidatas = [escala] if escala else list(ESCALAS)
    escolhida = None
    for n in candidatas:
        fatores = [_fator(v, n) for v in vistas]
        caixas = [(v["largura"] * f, v["altura"] * f + ALTURA_TITULO) for v, f in zip(vistas, fatores)]
        posicoes = _empacotar(caixas, formato)
        if posicoes is not None:
            escolhida = (n, fatores, caixas, posicoes, True)
            break
    if escolhida is None:
        n = candidatas[-1]
        fatores = [_fator(v, n) for v in vistas]
        caixas = [(v["largura"] * f, v["altura"] * f + ALTURA_TITULO) for v, f in zip(vistas, fatores)]
        x0, _, _, y1 = area_util(formato)
        posicoes, x = [], x0
        for largura, _ in caixas:  # uma ao lado da outra, mesmo saindo da folha
            posicoes.append((x, y1))
            x += largura + ESPACO_ENTRE_VISTAS
        escolhida = (n, fatores, caixas, posicoes, False)
    n, fatores, caixas, posicoes, cabe = escolhida
    resultado = []
    for vista, fator, (largura, altura), (x, topo) in zip(vistas, fatores, caixas, posicoes):
        altura_desenho = altura - ALTURA_TITULO
        resultado.append({
            "nome": vista["nome"], "fator": fator, "escala": round(1.0 / fator, 6), "largura": largura,
            "altura": altura_desenho, "x": x + largura / 2.0, "y": topo - altura_desenho / 2.0,
            "titulo_x": x + largura / 2.0, "titulo_y": topo - altura_desenho - ALTURA_TITULO / 2.0,
        })
    return {"escala": n, "cabe": cabe, "vistas": resultado}


def titulo_da_vista(nome, n, tipo="desenho"):
    """Linhas do título embaixo da vista: o nome em maiúsculas e a escala (a tabela não tem escala)."""
    if tipo == "tabela":
        return [nome.upper()]
    return [nome.upper(), f"ESCALA {texto_escala(n)}"]


# --- desenho 2D na folha (SVG do Draft) ------------------------------------------------------------

_NUMERO = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def _pontos_do_caminho(d):
    """Pontos (x, y) por onde passa um atributo ``d`` de caminho SVG (absoluto ou relativo)."""
    pontos, x, y, inicio = [], 0.0, 0.0, (0.0, 0.0)
    tokens = re.findall(r"[MmLlHhVvAaCcSsQqTtZz]|" + _NUMERO, d)
    comando, i = None, 0
    tamanhos = {"M": 2, "L": 2, "T": 2, "H": 1, "V": 1, "A": 7, "C": 6, "S": 4, "Q": 4}
    while i < len(tokens):
        if re.fullmatch(r"[A-Za-z]", tokens[i]):
            comando = tokens[i]
            i += 1
            if comando in "Zz":
                x, y = inicio
                comando = None
            continue
        if comando is None:
            i += 1
            continue
        letra = comando.upper()
        n = tamanhos[letra]
        valores = [float(v) for v in tokens[i:i + n]]
        if len(valores) < n:
            break
        i += n
        relativo = comando.islower()
        if letra == "H":
            x = x + valores[0] if relativo else valores[0]
        elif letra == "V":
            y = y + valores[0] if relativo else valores[0]
        else:
            pares = [(valores[-2], valores[-1])] if letra == "A" else list(zip(valores[0::2], valores[1::2]))
            for px, py in pares:
                pontos.append((x + px, y + py) if relativo else (px, py))
            ultimo = pares[-1]
            x, y = (x + ultimo[0], y + ultimo[1]) if relativo else ultimo
        pontos.append((x, y))
        if letra == "M":
            inicio = (x, y)
            comando = "l" if relativo else "L"
    return pontos


def limites_do_svg(svg):
    """(xmin, ymin, xmax, ymax) do desenho em unidades do SVG, pelos caminhos, linhas,
    círculos e posições dos textos; None se não há nada."""
    pontos = []
    for d in re.findall(r'\sd="([^"]*)"', svg):
        pontos += _pontos_do_caminho(d)
    for x1, y1, x2, y2 in re.findall(
            r'<line[^>]*?x1="(' + _NUMERO + ')"[^>]*?y1="(' + _NUMERO + ')"[^>]*?x2="(' + _NUMERO +
            ')"[^>]*?y2="(' + _NUMERO + ')"', svg):
        pontos += [(float(x1), float(y1)), (float(x2), float(y2))]
    for elemento in re.findall(r"<(?:circle|ellipse)\b[^>]*>", svg):
        cx = re.search(r'\bcx="(' + _NUMERO + ')"', elemento)
        cy = re.search(r'\bcy="(' + _NUMERO + ')"', elemento)
        r = re.search(r'\br[x]?="(' + _NUMERO + ')"', elemento)
        if cx and cy:
            raio = float(r.group(1)) if r else 0.0
            pontos += [(float(cx.group(1)) - raio, float(cy.group(1)) - raio),
                       (float(cx.group(1)) + raio, float(cy.group(1)) + raio)]
    for elemento in re.findall(r"<text\b[^>]*>", svg):
        translado = re.search(r"translate\(\s*(" + _NUMERO + r")[\s,]+(" + _NUMERO + r")\s*\)", elemento)
        if translado:
            pontos.append((float(translado.group(1)), float(translado.group(2))))
            continue
        x = re.search(r'\bx="(' + _NUMERO + ')"', elemento)
        y = re.search(r'\by="(' + _NUMERO + ')"', elemento)
        if x and y:
            pontos.append((float(x.group(1)), float(y.group(1))))
    if not pontos:
        return None
    xs, ys = [p[0] for p in pontos], [p[1] for p in pontos]
    return min(xs), min(ys), max(xs), max(ys)


ORIGEM_SIMBOLO = 50.0  # o TechDraw centra o símbolo sem viewBox na caixa padrão de 100 × 100


def posicao_do_simbolo(centro_folha, limites, fator):
    """X, Y da vista de símbolo (TechDraw::DrawViewSymbol, cabeçalho sem viewBox, como o
    DrawViewDraft) para o desenho de ``limites`` (unidades do SVG, Y para baixo) ficar
    centrado em ``centro_folha``."""
    xmin, ymin, xmax, ymax = limites
    sx, sy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
    return (centro_folha[0] - (sx - ORIGEM_SIMBOLO) * fator,
            centro_folha[1] + (sy - ORIGEM_SIMBOLO) * fator)


CABECALHO_SVG = ('<svg\n\txmlns="http://www.w3.org/2000/svg" version="1.1"\n'
                 '\txmlns:freecad="http://www.freecadweb.org/wiki/index.php?title=Svg_Namespace">\n')


def montar_simbolo(corpos, recorte=None):
    """SVG da vista: o cabeçalho do DrawViewDraft e os corpos do ``Draft.get_svg``.

    Args:
        recorte: None, ('circulo', cx, cy, r) ou ('retangulo', xmin, ymin, xmax, ymax) em
            unidades do SVG: o desenho fica só dentro dele, com o contorno.
    """
    corpo = "".join(corpos)
    if recorte is None:
        return CABECALHO_SVG + corpo + "</svg>"
    if recorte[0] == "circulo":
        _, cx, cy, r = recorte
        forma = f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}"'
    else:
        _, xmin, ymin, xmax, ymax = recorte
        forma = f'<rect x="{xmin:g}" y="{ymin:g}" width="{xmax - xmin:g}" height="{ymax - ymin:g}"'
    return (CABECALHO_SVG + f'<defs><clipPath id="recorte">{forma}/></clipPath></defs>'
            f'<g clip-path="url(#recorte)">{corpo}</g>'
            f'{forma} style="fill:none;stroke:#000000;stroke-width:{recorte_traco(recorte)}"/></svg>')


def recorte_traco(recorte):
    """Espessura do contorno do recorte em unidades do SVG (fração do tamanho)."""
    tamanho_ = 2 * recorte[3] if recorte[0] == "circulo" else max(recorte[3] - recorte[1], recorte[4] - recorte[2])
    return round(max(tamanho_ / 300.0, 1e-3), 6)


def recorte_do_svg(svg_da_regiao):
    """Recorte de ``montar_simbolo`` pelo SVG do objeto que marca a região (círculo ou outra forma)."""
    circulo = re.search(r"<circle\b[^>]*>", svg_da_regiao)
    if circulo:
        cx = float(re.search(r'\bcx="(' + _NUMERO + ')"', circulo.group(0)).group(1))
        cy = float(re.search(r'\bcy="(' + _NUMERO + ')"', circulo.group(0)).group(1))
        r = float(re.search(r'\br="(' + _NUMERO + ')"', circulo.group(0)).group(1))
        return ("circulo", cx, cy, r)
    limites = limites_do_svg(svg_da_regiao)
    if limites is None:
        return None
    return ("retangulo",) + tuple(limites)


# --- cortes ---------------------------------------------------------------------------------------

def corte(p1, p2):
    """Plano de corte pela linha P1→P2 desenhada na planta.

    Quem olha fica à esquerda da linha e olha para a direita dela (as setas na planta
    apontam para lá). No TechDraw, ``SectionNormal`` e ``Direction`` apontam para quem
    olha (o lado retirado).

    Returns:
        {'origem' (x, y), 'olhar' (x, y), 'normal' (x, y, z), 'xdirecao' (x, y, z), 'comprimento'}.
    """
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    comprimento = math.hypot(dx, dy)
    if comprimento <= 0:
        raise ValueError("a linha de corte não tem comprimento")
    ux, uy = dx / comprimento, dy / comprimento
    olhar = (uy, -ux)
    return {"origem": (float(p1[0]), float(p1[1])), "olhar": olhar, "normal": (-olhar[0], -olhar[1], 0.0),
            "xdirecao": (-ux, -uy, 0.0), "comprimento": comprimento}


def tamanho_do_corte(limites_3d, plano):
    """(largura, altura) [mm do modelo] do corte: extensão dos limites ao longo da linha e em Z.

    Args:
        limites_3d: (xmin, ymin, zmin, xmax, ymax, zmax) do modelo 3D.
    """
    xmin, ymin, zmin, xmax, ymax, zmax = limites_3d
    ux, uy = -plano["xdirecao"][0], -plano["xdirecao"][1]
    projecoes = [x * ux + y * uy for x in (xmin, xmax) for y in (ymin, ymax)]
    return max(projecoes) - min(projecoes), zmax - zmin


def marcas_do_corte(p1, p2, letra, tamanho_seta):
    """Setas e letras do corte na planta, nas duas pontas da linha.

    Returns:
        {'setas': [[(x, y), ...] polilinhas], 'letras': [(x, y, letra)]}.
    """
    plano = corte(p1, p2)
    vx, vy = plano["olhar"]
    s = float(tamanho_seta)
    setas, letras = [], []
    for px, py in (p1, p2):
        ponta = (px + vx * s, py + vy * s)
        lado = (-vy * s * 0.25, vx * s * 0.25)
        base = (px + vx * s * 0.6, py + vy * s * 0.6)
        setas.append([(px, py), ponta])
        setas.append([(base[0] + lado[0], base[1] + lado[1]), ponta, (base[0] - lado[0], base[1] - lado[1])])
        letras.append((ponta[0] + vx * s * 0.4, ponta[1] + vy * s * 0.4, letra))
    return {"setas": setas, "letras": letras}


def titulo_do_corte(letra):
    return f"Corte {letra}-{letra}"
