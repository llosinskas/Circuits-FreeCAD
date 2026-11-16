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
