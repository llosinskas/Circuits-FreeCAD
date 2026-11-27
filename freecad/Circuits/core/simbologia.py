"""Geometria da simbologia elétrica, independente do FreeCAD."""


def posicoes_fase(fases, neutro, terra, altura):
    """Posição X de cada traço de fase na simbologia de um cabo.

    Os traços ficam à direita dos traços de neutro e terra, por isso o início
    desloca meia altura para cada um deles que existir.

    Args:
        fases: número de fases (1, 2 ou 3); outro valor não desenha nada.
        neutro: o cabo tem condutor neutro.
        terra: o cabo tem condutor terra.
        altura: altura do símbolo.
    Returns:
        Lista com a coordenada X de cada fase.
    """
    if fases not in (1, 2, 3):
        return []
    inicio = (bool(neutro) + bool(terra)) * altura / 2
    return [inicio + indice * altura / 2 for indice in range(int(fases))]


def condutores(ligacao):
    """Condutores de um ponto pela ligação: (número de fases, tem neutro).

    'F+N' é uma fase e neutro; 'F+F' são duas fases, sem neutro; '3F' são três
    fases, sem neutro. Ligação desconhecida vale como 'F+N'.
    """
    return {"F+F": (2, False), "3F": (3, False)}.get(str(ligacao).strip(), (1, True))


def tamanho_efetivo(tamanho, escala=1.0):
    """Tamanho do símbolo com a escala aplicada. Escala zero ou negativa vale 1."""
    return float(tamanho) * (float(escala) if escala and float(escala) > 0 else 1.0)


# --- Fiação na planta (estilo NBR 5444) ------------------------------------------------------------
# Cada condutor é um traço que cruza a linha da fiação; a marca na ponta de cima diz a função:
# fase: traço simples; neutro: bolinha; retorno: bandeirinha inclinada; terra (PE): barra em T.
ORDEM_CONDUTORES = ("F", "N", "R", "T")
NOMES_CONDUTORES = {"F": "Fase", "N": "Neutro", "R": "Retorno", "T": "Terra (PE)"}


def lista_de_condutores(texto):
    """'F+N+T' -> ['F', 'N', 'T']; '2F+T' -> ['F', 'F', 'T']; 'F+2R' -> ['F', 'R', 'R']; '4R' -> R quatro vezes.

    Os condutores saem na ordem fase, neutro, retorno, terra."""
    lista = []
    for parte in str(texto or "").replace(" ", "").upper().split("+"):
        if not parte:
            continue
        letra = parte[-1]
        quantidade = int(parte[:-1]) if parte[:-1].isdigit() else 1
        if letra in ORDEM_CONDUTORES:
            lista += [letra] * quantidade
    return sorted(lista, key=ORDEM_CONDUTORES.index)


def fiacao(condutores, altura):
    """Desenho da fiação: a linha e um traço por condutor, com a marca da função.

    Args:
        condutores: lista de 'F', 'N', 'R', 'T' (``lista_de_condutores``).
        altura: comprimento de cada traço.
    Returns:
        {'linhas': [(x1, y1, x2, y2)], 'circulos': [(cx, cy, r)]}, com a linha em y = 0, de x = 0 até o fim.
    """
    h = float(altura)
    passo = h / 2.0
    marca = h / 5.0
    linhas, circulos = [], []
    if not condutores:
        return {"linhas": linhas, "circulos": circulos}
    linhas.append((0.0, 0.0, passo * (len(condutores) + 1), 0.0))
    for i, condutor in enumerate(condutores):
        x = passo * (i + 1)
        topo = h / 2.0
        linhas.append((x, -h / 2.0, x, topo))
        if condutor == "N":
            circulos.append((x, topo + marca / 2.0, marca / 2.0))
        elif condutor == "R":
            linhas.append((x, topo, x + marca, topo - marca))
        elif condutor == "T":
            linhas.append((x - marca, topo, x + marca, topo))
    return {"linhas": linhas, "circulos": circulos}


def itens_de_legenda_fiacao(usados, tamanho):
    """Linhas da legenda para as marcas de fiação usadas: [(chave, primitivas, descrição)].

    Args:
        usados: letras presentes ('F', 'N', 'R', 'T'), em qualquer ordem.
        tamanho: tamanho do símbolo na legenda.
    """
    descricoes = {"F": "condutor fase: traço simples", "N": "condutor neutro: traço com bolinha",
                  "R": "condutor retorno: traço com bandeirinha", "T": "condutor terra (PE): traço com barra"}
    itens = []
    for letra in ORDEM_CONDUTORES:
        if letra not in usados:
            continue
        desenho = fiacao([letra], tamanho)
        primitivas = [("linha", *l) for l in desenho["linhas"]] + [("circulo", *c) for c in desenho["circulos"]]
        itens.append((f"fiacao_{letra}", primitivas, f"Fiação - {descricoes[letra]}"))
    return itens
