"""Pavimentos do projeto e as pastas dos símbolos dentro de cada um, sem FreeCAD.

Cada pavimento é uma pasta do documento com as subpastas Tomadas, Pontos de
energia, Iluminação, Interruptores e Quadros e medição. Os símbolos novos
entram na subpasta do tipo deles, dentro do pavimento ativo.

Unidades: cotas e alturas em mm.
"""
from freecad.Circuits.core import simbolos

PAVIMENTO_PADRAO = "Térreo"
ALTURA_PADRAO_MM = 3000.0  # de piso a piso

# chave da pasta -> nome mostrado na árvore, na ordem em que as pastas são criadas
PASTAS = {
    "tomadas": "Tomadas",
    "energia": "Pontos de energia",
    "iluminacao": "Iluminação",
    "interruptores": "Interruptores",
    "quadros": "Quadros e medição",
    "eletrodutos": "Eletrodutos",
    "aterramento": "Aterramento",
}

_PASTA_DA_CATEGORIA = {
    simbolos.TOMADA: "tomadas",
    simbolos.ENERGIA: "energia",
    simbolos.ILUMINACAO: "iluminacao",
    simbolos.QUADRO: "quadros",
    simbolos.COMANDO: "interruptores",
    simbolos.PASSAGEM: "eletrodutos",
    simbolos.ATERRAMENTO: "aterramento",
}
_PASTA_DO_TIPO = {
    "Switch": "interruptores",
    "Lighting": "iluminacao",
    "Outlet": "tomadas",
    "tomada": "tomadas",
    "ConduitPath": "eletrodutos",
    "eletroduto": "eletrodutos",
    "condutor_aterramento": "aterramento",
}


def pasta_do_objeto(tipo, simbolo=""):
    """Chave da pasta de um símbolo, ou None se o objeto não é um símbolo da planta.

    Args:
        tipo: ``Proxy.Type`` do objeto (Ponto, Switch, Lighting, Outlet, ConduitPath),
            'tomada' para a tomada em Sketch ou 'eletroduto' para um Draft Wire marcado como eletroduto.
        simbolo: chave de ``core.simbolos.CATALOGO``, só para o tipo Ponto.
    """
    if tipo == "Ponto":
        dados = simbolos.CATALOGO.get(simbolo)
        return _PASTA_DA_CATEGORIA.get(dados["categoria"]) if dados else None
    return _PASTA_DO_TIPO.get(tipo)


def cota_de_desenho(cota_piso):
    """Z do símbolo 2D na planta [mm]: a cota do piso do pavimento.

    Todos os símbolos de um pavimento ficam no mesmo plano, o do piso; a altura
    de montagem só vale para o modelo 3D (veja ``cota_3d``).
    """
    return float(cota_piso)


def cota_3d(cota_piso, altura_montagem):
    """Z da caixa no modelo 3D [mm]: a cota do piso mais a altura de montagem.

    A altura de montagem é sempre medida a partir do piso: a tomada alta tem 2000
    em qualquer pavimento, e no pavimento de cota 3000 a caixa 3D fica em 5000.
    """
    return float(cota_piso) + float(altura_montagem)


def nome_do_pavimento(texto):
    """Nome sem espaços nas pontas; vazio vale como o pavimento padrão."""
    return " ".join(str(texto).split()) or PAVIMENTO_PADRAO


def sugerir_novo(existentes):
    """Nome, cota e altura sugeridos para o próximo pavimento.

    Args:
        existentes: lista de (nome, cota do piso, altura de piso a piso).
    Returns:
        (nome, cota, altura): o primeiro pavimento é o Térreo, na cota 0; os
        seguintes são '1º Pavimento', '2º Pavimento'..., sobre o mais alto.
    """
    if not existentes:
        return PAVIMENTO_PADRAO, 0.0, ALTURA_PADRAO_MM
    usados = {nome for nome, _, _ in existentes}
    numero = 1
    while f"{numero}º Pavimento" in usados:
        numero += 1
    nome_mais_alto, cota, altura = max(existentes, key=lambda p: p[1])
    return f"{numero}º Pavimento", cota + altura, altura
