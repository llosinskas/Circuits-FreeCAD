"""Modelo 3D completo num botão só: caixas, eletrodutos, eletrocalhas e suportes."""
from freecad.Circuits.services import bandejas, caixas_3d, eletrodutos, rede


def gerar_tudo(doc):
    """Gera (ou refaz) todo o modelo 3D do projeto.

    - caixas de todos os símbolos e das tomadas TUG antigas (``caixas_3d``):
      tomadas dentro da parede, atrás do ponto de inserção;
    - tubos de todos os eletrodutos, inclusive as linhas do Draft marcadas;
    - eletrocalhas e leitos com as curvas, tês e reduções, e os suportes.

    Returns:
        {'caixas', 'eletrodutos', 'bandejas', 'suportes'}: quantidades geradas.
    """
    feito = {"caixas": 0, "eletrodutos": 0, "bandejas": 0, "suportes": 0}
    objetos, em_sketch = caixas_3d.listar_alvos(doc)
    if objetos or em_sketch:
        feito["caixas"] = caixas_3d.gerar_caixas(doc, objetos, em_sketch)
    caminhos = rede.listar_eletrodutos(doc)
    if caminhos:
        feito["eletrodutos"] = eletrodutos.gerar_tubos(doc, caminhos)
    if bandejas.listar(doc):
        feito["bandejas"] = bandejas.gerar_3d(doc)
        feito["suportes"] = sum(bandejas.gerar_suportes(doc).values())
    return feito
