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
}

_PASTA_DA_CATEGORIA = {
    simbolos.TOMADA: "tomadas",
    simbolos.ENERGIA: "energia",
    simbolos.ILUMINACAO: "iluminacao",
    simbolos.QUADRO: "quadros",
}
_PASTA_DO_TIPO = {
    "Switch": "interruptores",
    "Lighting": "iluminacao",
    "Outlet": "tomadas",
    "tomada": "tomadas",
    "ConduitPath": "eletrodutos",
    "eletroduto": "eletrodutos",
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


def cota_de_desenho(cota_piso, altura_montagem):
    """Z do símbolo no desenho [mm]: a cota do piso do pavimento mais a altura de montagem.

    A altura de montagem é sempre medida a partir do piso: a tomada alta tem 2000
    em qualquer pavimento, e no pavimento de cota 3000 fica desenhada em 5000.
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
