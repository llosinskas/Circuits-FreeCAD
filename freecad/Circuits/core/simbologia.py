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
