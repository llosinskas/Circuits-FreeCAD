"""Estrutura de grupos do documento."""
import FreeCAD as App

# A estrutura de pastas do projeto fica em core/estrutura.py e services/estrutura.py.
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
    """Cria os grupos que ainda não existem; repetir o comando não duplica nada."""
    for nome in nomes:
        create_group(nome, doc)
    doc.recompute()
