"""Ajudantes comuns aos comandos da bancada."""
import os

import FreeCAD as App

from freecad.Circuits import ICON_PATH
from freecad.Circuits.qt import QtWidgets


def recursos(icone, menu, dica):
    """Dicionário devolvido por ``GetResources`` de um comando."""
    return {"Pixmap": os.path.join(ICON_PATH, icone), "MenuText": menu, "ToolTip": dica}


def documento_ou_aviso():
    """Documento ativo; sem documento, avisa o usuário e devolve None."""
    doc = App.activeDocument()
    if not doc:
        QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento FreeCAD aberto.")
    return doc
