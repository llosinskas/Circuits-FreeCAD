"""Geometria do diagrama multifilar de um quadro, sem FreeCAD.

No multifilar cada condutor é desenhado separado:

    R  ──┬──────────────┬─────────── barramentos horizontais, de cima para baixo:
    S  ──┼──┬───────────┼──┬──────── fases do quadro, neutro e terra
    N  ──┼──┼──┬────────┼──┼──┬─────
    PE ──┼──┼──┼──┬─────┼──┼──┼──┬──
         │  │  │  │     │  │  │  │   cada circuito desce dos barramentos:
         ●⌒●  │  │     ●⌒●⌒●  │  │   um polo do disjuntor por fase (ligados
         │  │  │  │     │  │  │  │   pelo tracejado), o DR abraçando fases e
        [  DR  ]  │     │  │  │  │   neutro, e o terra direto até a carga
         ▼  ▼  ▼  ▼     ▼  ▼  ▼  ▼
         C1               C2

A entrada vem da esquerda pelo disjuntor geral, com um polo por fase. Os
textos de cada circuito (número, proteção, sensibilidade do DR, seção,
potência e descrição) ficam embaixo dele; a descrição, na vertical.

Usa as mesmas regras de leitura do unifilar (``core.unifilar``): fases pelas
colunas ``Fase_R``, ``Fase_S``, ``Fase_T``; neutro e terra pelas colunas ``Neutro``
e ``Terra``. Todas as medidas são múltiplos de ``h`` (a altura do texto).
"""
from freecad.Circuits.core import unifilar

FASES = "RST"
PASSO_BARRA = 0.6  # distância entre barramentos
PASSO_CONDUTOR = 0.8  # distância entre os condutores de um circuito
FOLGA_CIRCUITOS = 1.6  # espaço entre dois circuitos
X_PRIMEIRO = 1.5  # primeiro circuito, à direita do começo dos barramentos
RAIO_POLO = 0.3  # arco de cada polo do disjuntor
Y_DISJUNTOR = 4.0  # abaixo do último barramento, até o primeiro terminal do polo
Y_DR = 6.2
ALTURA_DR = 0.9
Y_FIM = 9.0  # comprimento dos condutores abaixo do último barramento
RAIO_LIGACAO = 0.07  # ponto de ligação no barramento
ALTURA_TEXTO = 0.4
X_ENTRADA = -6.0  # a entrada começa à esquerda dos barramentos
X_GERAL = -4.0  # primeiro terminal dos polos do disjuntor geral


def barramentos(dados):
    """Nomes dos barramentos do quadro, de cima para baixo: fases, N e PE."""
    n = int(float(str(dados.get("numero_fases") or 3).replace(",", ".") or 3))
    nomes = list(FASES[:max(1, min(3, n))])
    if unifilar._sim(dados.get("neutro", ""), padrao=True):
        nomes.append("N")
    if unifilar._sim(dados.get("terra", ""), padrao=True):
        nomes.append("PE")
    return nomes


def condutores(circuito, barras):
    """Condutores do circuito, na ordem do desenho: fases, N e PE (só os que existem no quadro)."""
    fases = unifilar.fases_do_circuito(circuito) or "R"
    _, neutro, terra = unifilar.condutores_do_circuito(circuito)
    lista = [f for f in fases if f in barras]
    if neutro and "N" in barras:
        lista.append("N")
    if terra and "PE" in barras:
        lista.append("PE")
    return lista or [barras[0]]


def largura_do_circuito(n_condutores, h):
    return ((n_condutores - 1) * PASSO_CONDUTOR + FOLGA_CIRCUITOS + 2 * RAIO_POLO) * h


def _polo_vertical(x, y_topo, h):
    """Polo de disjuntor num condutor vertical: dois terminais e o arco à direita."""
    r = RAIO_POLO * h
    terminal = unifilar.RAIO_TERMINAL * h
    circulos = [(x, y_topo, terminal), (x, y_topo - 2 * r, terminal)]
    arcos = [(x, y_topo - r, r, -90.0, 90.0)]
    return circulos, arcos


def _polo_horizontal(x, y, h):
    """Polo de disjuntor num condutor horizontal: dois terminais e o arco em cima."""
    r = RAIO_POLO * h
    terminal = unifilar.RAIO_TERMINAL * h
    return [(x, y, terminal), (x + 2 * r, y, terminal)], [(x + r, y, r, 0.0, 180.0)]


def _tracejado(x1, y1, x2, y2, h, traco=0.15, vazio=0.1):
    """Linha tracejada (ligação mecânica dos polos)."""
    linhas = []
    comprimento = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    if comprimento <= 0:
        return linhas
    ux, uy = (x2 - x1) / comprimento, (y2 - y1) / comprimento
    d = 0.0
    while d < comprimento:
        fim = min(d + traco * h, comprimento)
        linhas.append((x1 + ux * d, y1 + uy * d, x1 + ux * fim, y1 + uy * fim))
        d = fim + vazio * h
    return linhas


def geometria(dados, circuitos, h):
    """Primitivas do multifilar de um quadro.

    Args:
        dados: dados do quadro (``core.planilha.CABECALHO_QUADRO``: ``numero_fases``,
            ``neutro``, ``terra``, ``indentificacao_painel``, ``origem``, ``tensao``,
            ``curva_disjuntor``, ``corrente_nominal_disjuntor``).
        circuitos: dicionários de ``planilhas.ler_circuitos_completos``.
        h: altura do texto [mm].
    Returns:
        ``linhas``, ``arcos``, ``circulos`` (como ``core.unifilar.geometria``),
        ``textos`` [(x, y, texto, altura, ângulo em graus)], ``largura`` e ``altura``.
    """
    barras = barramentos(dados)
    y_barra = {nome: -i * PASSO_BARRA * h for i, nome in enumerate(barras)}
    y_base = y_barra[barras[-1]]
    linhas, arcos, circulos, textos = [], [], [], []
    texto = ALTURA_TEXTO * h
    r = RAIO_POLO * h
    terminal = unifilar.RAIO_TERMINAL * h

    # Circuitos, da esquerda para a direita
    x = X_PRIMEIRO * h
    y_polo = y_base - Y_DISJUNTOR * h
    y_dr = y_base - Y_DR * h
    y_fim = y_base - Y_FIM * h
    for circuito in circuitos:
        lista = condutores(circuito, barras)
        posicoes = {nome: x + i * PASSO_CONDUTOR * h for i, nome in enumerate(lista)}
        fases = [c for c in lista if c in FASES]
        tem_dr = bool(unifilar.textos(circuito).get("dr"))
        com_dr = fases + (["N"] if "N" in lista else [])
        for nome, xc in posicoes.items():
            circulos.append((xc, y_barra[nome], RAIO_LIGACAO * h))
            trechos = [y_barra[nome]]
            if nome in fases:  # polo do disjuntor
                c, a = _polo_vertical(xc, y_polo, h)
                circulos += c
                arcos += a
                trechos += [y_polo + terminal, y_polo - 2 * r - terminal]
            if tem_dr and nome in com_dr:  # o DR interrompe a linha
                trechos += [y_dr + ALTURA_DR * h / 2, y_dr - ALTURA_DR * h / 2]
            trechos.append(y_fim)
            for topo, base in zip(trechos[::2], trechos[1::2]):
                linhas.append((xc, topo, xc, base))
            s = unifilar.TAMANHO_SETA * h * 0.6  # seta na carga
            linhas += [(xc, y_fim, xc - s * 0.6, y_fim + s), (xc, y_fim, xc + s * 0.6, y_fim + s)]
        if len(fases) > 1:  # polos ligados mecanicamente
            xs = [posicoes[f] for f in fases]
            linhas += _tracejado(xs[0] + r, y_polo - r, xs[-1], y_polo - r, h)
        if tem_dr:
            xs = [posicoes[c] for c in com_dr]
            x1, x2 = min(xs) - 0.3 * h, max(xs) + 0.3 * h
            y1, y2 = y_dr + ALTURA_DR * h / 2, y_dr - ALTURA_DR * h / 2
            linhas += [(x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1)]
        rotulos = unifilar.textos(circuito)
        x_texto = x - 0.2 * h
        if tem_dr:
            xs = [posicoes[c] for c in com_dr]
            textos.append(((min(xs) + max(xs)) / 2 - 0.3 * h, y_dr - 0.15 * h, "DR", texto * 0.8, 0.0))
        linha_texto = y_fim - 0.8 * h
        for chave, fator in (("numero", 1.25), ("protecao", 1.0), ("sensibilidade", 1.0), ("secao", 1.0),
                             ("potencia", 1.0)):
            if rotulos.get(chave):
                conteudo = f"DR {rotulos[chave]}" if chave == "sensibilidade" else rotulos[chave]
                textos.append((x_texto, linha_texto, conteudo, texto * fator, 0.0))
                linha_texto -= 0.6 * h
        if rotulos.get("descricao"):
            textos.append((x + 0.15 * h, linha_texto - 0.1 * h, rotulos["descricao"], texto, -90.0))
        x += largura_do_circuito(len(lista), h)

    # Barramentos e nomes
    x_fim = max(x, (X_PRIMEIRO + 3.0) * h)
    for nome, y in y_barra.items():
        linhas.append((0.0, y, x_fim, y))
        textos.append((x_fim + 0.3 * h, y - 0.15 * h, nome, texto, 0.0))

    # Entrada pela esquerda, com o disjuntor geral nas fases
    fases_quadro = [b for b in barras if b in FASES]
    x0, xg = X_ENTRADA * h, X_GERAL * h
    for nome, y in y_barra.items():
        if nome in fases_quadro:
            c, a = _polo_horizontal(xg, y, h)
            circulos += c
            arcos += a
            linhas += [(x0, y, xg - terminal, y), (xg + 2 * r + terminal, y, 0.0, y)]
        else:
            linhas.append((x0, y, 0.0, y))
        textos.append((x0 - 0.8 * h, y - 0.15 * h, nome, texto * 0.8, 0.0))
    if len(fases_quadro) > 1:
        linhas += _tracejado(xg + r, y_barra[fases_quadro[0]] + r, xg + r, y_barra[fases_quadro[-1]] + r, h)
    curva = str(dados.get("curva_disjuntor", "")).strip()
    corrente = str(dados.get("corrente_nominal_disjuntor", "")).strip()
    if corrente:
        textos.append((xg - 0.2 * h, r + 0.5 * h, f"{curva}{corrente}A", texto, 0.0))
    identificacao = str(dados.get("indentificacao_painel", "")).strip()
    origem = str(dados.get("origem", "")).strip()
    tensao = str(dados.get("tensao", "")).strip()
    titulo = " · ".join(t for t in (f"Multifilar {identificacao}".strip(), f"{tensao} V" if tensao else "") if t)
    textos.append((x0, r + 1.6 * h, titulo, texto * 1.5, 0.0))
    if origem:
        textos.append((x0, r + 0.6 * h, f"de {origem}", texto, 0.0))
    return {"linhas": linhas, "arcos": arcos, "circulos": circulos, "textos": textos,
            "largura": x_fim - x0, "altura": -y_fim + 6 * h}
