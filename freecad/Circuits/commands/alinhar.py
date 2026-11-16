"""Comandos para alinhar e distribuir os símbolos selecionados na planta."""
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import alinhamento


def _selecao_ou_aviso(minimo, titulo):
    """Objetos selecionados, na ordem da seleção; avisa se forem menos que ``minimo``."""
    selecao = [obj for obj in Gui.Selection.getSelection() if hasattr(obj, "Placement")]
    if len(selecao) < minimo:
        QtWidgets.QMessageBox.information(
            None, titulo, f"Selecione pelo menos {minimo} símbolos na planta (Ctrl + clique)."
        )
        return None
    return selecao


class AlinharPontos:
    """Coloca os símbolos selecionados em linha com o primeiro selecionado."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecao = _selecao_ou_aviso(2, "Alinhar")
        if selecao:
            alinhamento.alinhar_objetos(doc, selecao)

    def IsActive(self):
        return True

    def GetResources(self):
        dados = recursos(
            "alinhar.svg",
            "Alinhar",
            "Coloca os símbolos selecionados em linha (horizontal ou vertical) com o primeiro selecionado",
        )
        dados["Accel"] = "A, L"
        return dados


class DistribuirPontos:
    """Espaça igualmente os símbolos selecionados entre os dois das pontas."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecao = _selecao_ou_aviso(3, "Distribuir")
        if selecao:
            alinhamento.distribuir_objetos(doc, selecao)

    def IsActive(self):
        return True

    def GetResources(self):
        dados = recursos(
            "distribuir.svg",
            "Distribuir",
            "Espaça igualmente os símbolos selecionados entre os dois das pontas",
        )
        dados["Accel"] = "A, D"
        return dados


Gui.addCommand("AlinharPontos", AlinharPontos())
Gui.addCommand("DistribuirPontos", DistribuirPontos())
