"""Geometria do diagrama multifilar de um quadro, sem FreeCAD.

No multifilar cada condutor é desenhado separado. Os barramentos ficam na
vertical, um ao lado do outro (fases do quadro, neutro e terra), e cada
circuito sai deles para a direita, um embaixo do outro:

    R S T N PE
    │ │ │ │ │
    ●─┼─┼─┼─┼──────●⌒●────[DR]────┌──────────────┐
    │ │ │ ●─┼──────────────[  ]────│ C1           │   um polo do disjuntor por
    │ │ │ │ ●──────────────────────│ Iluminação   │   fase (tracejado entre os
    │ │ │ │ │                      └──────────────┘   polos), o DR abraçando
                                                       fases e neutro, o terra
                                                       direto até a carga

A entrada vem de cima, pelo disjuntor geral, com um polo por fase. Cada
circuito termina num retângulo com o número e a descrição; em cima dos
condutores ficam a proteção, o DR, a seção e a potência.

Usa as mesmas regras de leitura do unifilar (``core.unifilar``): fases pelas
colunas ``Fase_R``, ``Fase_S``, ``Fase_T``; neutro e terra pelas colunas ``Neutro``
e ``Terra``. Todas as medidas são múltiplos de ``h`` (a altura do texto).
"""
from freecad.Circuits.core import unifilar

FASES = "RST"
PASSO_BARRA = 0.6  # distância entre barramentos
PASSO_CONDUTOR = 0.8  # distância entre os condutores de um circuito
FOLGA_CIRCUITOS = 2.4  # espaço entre dois circuitos (inclui os textos de cima)
X_PRIMEIRO = 1.5  # primeiro circuito, abaixo do começo dos barramentos
RAIO_POLO = 0.3  # arco de cada polo do disjuntor
X_DISJUNTOR = 2.5  # à direita do último barramento, até o primeiro terminal do polo
X_DR = 5.2
LARGURA_DR = 0.9
X_FIM = 11.0  # os condutores chegam ao retângulo do circuito
LARGURA_CARGA = 5.0  # largura mínima do retângulo do circuito
MARGEM_CARGA = 0.45  # o retângulo passa os condutores disto em cima e embaixo
ALTURA_MINIMA_CARGA = 1.5  # cabe o número e a descrição
RAIO_LIGACAO = 0.07  # ponto de ligação no barramento
ALTURA_TEXTO = 0.4
LARGURA_LETRA = 0.6  # largura de uma letra, em alturas do texto (para o retângulo caber a descrição)
Y_ENTRADA = 4.2  # a entrada começa acima dos barramentos
Y_GERAL = 2.6  # primeiro terminal dos polos do disjuntor geral


def barramentos(dados):
    """Nomes dos barramentos do quadro, da esquerda para a direita: fases, N e PE."""
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


def altura_do_circuito(n_condutores, h):
    """Espaço vertical de um circuito com ``n_condutores``: até a base do retângulo (que tem pelo menos
    ``ALTURA_MINIMA_CARGA``) e a folga até o próximo."""
    ate_a_base = max((n_condutores - 1) * PASSO_CONDUTOR + MARGEM_CARGA, ALTURA_MINIMA_CARGA - MARGEM_CARGA)
    return (ate_a_base + FOLGA_CIRCUITOS - 2 * MARGEM_CARGA) * h


def _polo_horizontal(x, y, h):
    """Polo de disjuntor num condutor horizontal: dois terminais e o arco em cima."""
    r = RAIO_POLO * h
    terminal = unifilar.RAIO_TERMINAL * h
    return [(x, y, terminal), (x + 2 * r, y, terminal)], [(x + r, y, r, 0.0, 180.0)]


def _polo_vertical(x, y_topo, h):
    """Polo de disjuntor num condutor vertical: dois terminais e o arco à direita."""
    r = RAIO_POLO * h
    terminal = unifilar.RAIO_TERMINAL * h
    return [(x, y_topo, terminal), (x, y_topo - 2 * r, terminal)], [(x, y_topo - r, r, -90.0, 90.0)]


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


def _retangulo(x1, y1, x2, y2):
    return [(x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1)]


def geometria(dados, circuitos, h):
    """Primitivas do multifilar de um quadro, na vertical.

    Args:
        dados: dados do quadro (``core.planilha.CABECALHO_QUADRO``: ``numero_fases``,
            ``neutro``, ``terra``, ``indentificacao_painel``, ``origem``, ``tensao``,
            ``curva_disjuntor``, ``corrente_nominal_disjuntor``).
        circuitos: dicionários de ``planilhas.ler_circuitos_completos``.
        h: altura do texto [mm].
    Returns:
        ``linhas``, ``arcos``, ``circulos`` (como ``core.unifilar.geometria``),
        ``textos`` [(x, y, texto, altura, ângulo em graus)], ``cargas`` [(x1, y1, x2, y2)]
        (o retângulo de cada circuito), ``largura`` e ``altura``.
    """
    barras = barramentos(dados)
    x_barra = {nome: i * PASSO_BARRA * h for i, nome in enumerate(barras)}
    x_ultima = x_barra[barras[-1]]
    linhas, arcos, circulos, textos, cargas = [], [], [], [], []
    texto = ALTURA_TEXTO * h
    r = RAIO_POLO * h
    terminal = unifilar.RAIO_TERMINAL * h
    x_polo = x_ultima + X_DISJUNTOR * h
    x_dr = x_ultima + X_DR * h
    x_fim = x_ultima + X_FIM * h
    largura_maxima = x_fim + LARGURA_CARGA * h

    # Circuitos, de cima para baixo
    y = -X_PRIMEIRO * h
    for circuito in circuitos:
        lista = condutores(circuito, barras)
        posicoes = {nome: y - i * PASSO_CONDUTOR * h for i, nome in enumerate(lista)}
        fases = [c for c in lista if c in FASES]
        rotulos = unifilar.textos(circuito)
        tem_dr = bool(rotulos.get("dr"))
        com_dr = fases + (["N"] if "N" in lista else [])
        for nome, yc in posicoes.items():
            circulos.append((x_barra[nome], yc, RAIO_LIGACAO * h))
            trechos = [x_barra[nome]]
            if nome in fases:  # polo do disjuntor
                c, a = _polo_horizontal(x_polo, yc, h)
                circulos += c
                arcos += a
                trechos += [x_polo - terminal, x_polo + 2 * r + terminal]
            if tem_dr and nome in com_dr:  # o DR interrompe a linha
                trechos += [x_dr - LARGURA_DR * h / 2, x_dr + LARGURA_DR * h / 2]
            trechos.append(x_fim)
            for inicio, fim in zip(trechos[::2], trechos[1::2]):
                linhas.append((inicio, yc, fim, yc))
        if len(fases) > 1:  # polos ligados mecanicamente
            ys = [posicoes[f] for f in fases]
            linhas += _tracejado(x_polo + r, ys[0] + r, x_polo + r, ys[-1] + r, h)
        if tem_dr:
            ys = [posicoes[c] for c in com_dr]
            linhas += _retangulo(x_dr - LARGURA_DR * h / 2, max(ys) + 0.3 * h, x_dr + LARGURA_DR * h / 2,
                                 min(ys) - 0.3 * h)
            textos.append((x_dr - 0.3 * h, (max(ys) + min(ys)) / 2 - 0.15 * h, "DR", texto * 0.7, 0.0))

        # Textos em cima dos condutores
        y_texto = y + 0.55 * h
        if rotulos.get("protecao"):
            textos.append((x_polo - 0.2 * h, y_texto + 0.15 * h, rotulos["protecao"], texto, 0.0))
        if rotulos.get("sensibilidade"):
            textos.append((x_dr - 0.8 * h, y_texto + 0.15 * h, rotulos["sensibilidade"], texto * 0.9, 0.0))
        dados_cabo = " · ".join(rotulos[c] for c in ("secao", "potencia") if rotulos.get(c))
        if dados_cabo:
            textos.append((x_dr + LARGURA_DR * h, y_texto + 0.15 * h, dados_cabo, texto * 0.9, 0.0))

        # Retângulo do circuito, com o número e a descrição
        descricao = rotulos.get("descricao", "")
        largura = max(LARGURA_CARGA * h, (len(descricao) * LARGURA_LETRA + 1.0) * texto)
        topo, base = y + MARGEM_CARGA * h, posicoes[lista[-1]] - MARGEM_CARGA * h
        base = min(base, topo - ALTURA_MINIMA_CARGA * h)  # cabe o número e a descrição
        cargas.append((x_fim, topo, x_fim + largura, base))
        linhas += _retangulo(x_fim, topo, x_fim + largura, base)
        textos.append((x_fim + 0.3 * h, topo - 0.65 * h, rotulos.get("numero", ""), texto * 1.25, 0.0))
        if descricao:
            textos.append((x_fim + 0.3 * h, topo - 1.25 * h, descricao, texto, 0.0))
        largura_maxima = max(largura_maxima, x_fim + largura)
        y = min(base, posicoes[lista[-1]]) - (FOLGA_CIRCUITOS - 2 * MARGEM_CARGA) * h

    # Barramentos e nomes
    y_fim = min(y, -(X_PRIMEIRO + 2.0) * h)
    for nome, x in x_barra.items():
        linhas.append((x, 0.0, x, y_fim))

    # Entrada por cima, com o disjuntor geral nas fases
    fases_quadro = [b for b in barras if b in FASES]
    y0, yg = Y_ENTRADA * h, Y_GERAL * h
    for nome, x in x_barra.items():
        if nome in fases_quadro:
            c, a = _polo_vertical(x, yg, h)
            circulos += c
            arcos += a
            linhas += [(x, y0, x, yg + terminal), (x, yg - 2 * r - terminal, x, 0.0)]
        else:
            linhas.append((x, y0, x, 0.0))
        textos.append((x - 0.12 * h, y0 + 0.25 * h, nome, texto * 0.8, 0.0))
    if len(fases_quadro) > 1:
        xs = [x_barra[f] for f in fases_quadro]
        linhas += _tracejado(xs[0] + r, yg - r, xs[-1] + r, yg - r, h)
    curva = str(dados.get("curva_disjuntor", "")).strip()
    corrente = str(dados.get("corrente_nominal_disjuntor", "")).strip()
    if corrente:
        textos.append((x_ultima + 0.8 * h, yg - r - 0.15 * h, f"{curva}{corrente}A", texto, 0.0))
    identificacao = str(dados.get("indentificacao_painel", "")).strip()
    origem = str(dados.get("origem", "")).strip()
    tensao = str(dados.get("tensao", "")).strip()
    titulo = " · ".join(t for t in (f"Multifilar {identificacao}".strip(), f"{tensao} V" if tensao else "") if t)
    textos.append((0.0, y0 + 2.2 * h, titulo, texto * 1.5, 0.0))
    if origem:
        textos.append((0.0, y0 + 1.2 * h, f"de {origem}", texto, 0.0))
    return {"linhas": linhas, "arcos": arcos, "circulos": circulos, "textos": textos, "cargas": cargas,
            "largura": largura_maxima, "altura": y0 + 3.0 * h - y_fim}
