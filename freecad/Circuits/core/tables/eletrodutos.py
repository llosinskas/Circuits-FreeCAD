"""Dados de eletrodutos usados na geração dos tubos 3D."""

# Diâmetro externo em mm por tamanho nominal.
DIAMETROS_EXTERNOS = {
    "1/2": 21.3,
    "3/4": 26.9,
    "1": 33.7,
    "1 1/4": 42.4,
    "1 1/2": 48.3,
    "2": 60.3,
    "3": 88.9,
    "4": 114.3,
}
DIAMETRO_PADRAO = 26.9

# Cor RGB do tubo por nome.
CORES = {
    "Amarelo": (1.0, 0.8, 0.0),
    "Preto": (0.1, 0.1, 0.1),
    "Cinza": (0.6, 0.6, 0.6),
    "Vermelho": (0.8, 0.1, 0.1),
    "Laranja": (1.0, 0.5, 0.0),
    "Azul": (0.1, 0.3, 0.8),
    "Branco": (0.95, 0.95, 0.95),
    "Verde": (0.1, 0.7, 0.2),
}
COR_PADRAO = (0.7, 0.7, 0.7)
