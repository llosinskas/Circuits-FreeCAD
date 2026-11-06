"""Estrutura de grupos do documento."""
import FreeCAD as App

GRUPOS_PROJETO = [
    "Arquitetura_referencia",
    "Niveis",
    "Pontos_eletricos",
    "Quadros",
    "Tomadas",
    "Iluminacao",
    "Equipamentos",
    "Eletrodutos",
    "Eletrocalha",
    "Cabos",
    "Aterramento",
    "Tabelas_e_planilhas",
    "Detalhes",
    "Diagramas",
    "Projetos_2D",
]
GRUPOS_QUADRO = [
    "Dados",
    "Estrutura funcional",
    "Estrutura física",
    "Documentacao",
    "Dispositivos",
    "Conexoes",
    "Listagem",
]
GRUPOS_MODELO = ["Simbolo 2D", "Foto", "Modelo 3D", "Descricao", "Detalhes 2D"]


def create_group(name, doc=None):
    """Devolve o grupo com esse nome, criando-o se ainda não existir."""
    if doc is None:
        doc = App.activeDocument()
    if doc is None:
        return None

    group = doc.getObject(name)
    if group is None:
        group = doc.addObject("App::DocumentObjectGroup", name)
    return group


def criar_grupos(doc, nomes):
    for nome in nomes:
        doc.addObject("App::DocumentObjectGroup", nome)
    doc.recompute()
