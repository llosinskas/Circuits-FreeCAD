"""Biblioteca de modelos .FCStd em Componentes/."""
import os

import FreeCAD as App

from freecad.Circuits import ELECTRIC_LIBRARY_PATH
from freecad.Circuits.services.documento import GRUPOS_MODELO, criar_grupos


def listar_modelos():
    """Nomes dos arquivos .FCStd da biblioteca elétrica."""
    return [f for f in os.listdir(ELECTRIC_LIBRARY_PATH) if f.endswith(".FCStd")]


def criar_modelo(nome):
    """Cria e salva um documento novo de modelo na biblioteca."""
    caminho = os.path.join(ELECTRIC_LIBRARY_PATH, nome + ".FCStd")
    doc = App.newDocument(nome)
    for grupo in GRUPOS_MODELO:
        doc.addObject("App::DocumentObjectGroup", grupo)
    App.ActiveDocument.saveAs(caminho)
    doc.recompute()
    return doc


def _renomear_se_existir(doc, objeto):
    for obj in doc.Objects:
        if obj.Label == objeto.Label:
            obj.Label = f"_{objeto.Label}"
            return True
    return False


def importar_modelo(doc, arquivo):
    """Copia os objetos de um modelo da biblioteca para um grupo do documento."""
    nome = arquivo.split(".")[0]
    pasta = doc.addObject("App::DocumentObjectGroup", nome)
    origem = App.open(os.path.join(ELECTRIC_LIBRARY_PATH, arquivo))

    for obj in origem.Objects:
        if not _renomear_se_existir(doc, obj):
            pasta.addObject(doc.copyObject(obj))

    App.closeDocument(nome)
    doc.recompute()
