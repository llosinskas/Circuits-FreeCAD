"""Comandos para alinhar, distribuir e mudar a escala dos símbolos da planta."""
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.objects.ponto import escala_padrao
from freecad.Circuits.services import alinhamento, escala


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


class EscalaSimbolos:
    """Muda a escala dos símbolos selecionados, ou de todos se nada estiver selecionado."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecao = Gui.Selection.getSelection()
        alvo = f"{len(selecao)} símbolo(s) selecionado(s)" if selecao else "todos os símbolos da planta"
        valor, ok = QtWidgets.QInputDialog.getDouble(
            None, "Escala dos símbolos", f"Escala para {alvo} (1 = tamanho normal, 2 = dobro):",
            escala_padrao(), 0.1, 50.0, 2,
        )
        if not ok:
            return
        alterados, ignorados = escala.aplicar_escala(doc, selecao, valor)
        if not selecao:
            escala.definir_escala_padrao(valor)  # os próximos símbolos já nascem nesta escala
        if ignorados:
            QtWidgets.QMessageBox.information(
                None, "Escala dos símbolos",
                f"{alterados} símbolo(s) alterado(s). {ignorados} objeto(s) não têm escala "
                "(tomada e iluminação antigas, ou objetos que não são símbolos).",
            )

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "escala_simbolos.svg",
            "Escala dos símbolos",
            "Aumenta ou diminui os símbolos selecionados, ou todos os da planta se nada estiver selecionado",
        )


Gui.addCommand("AlinharPontos", AlinharPontos())
Gui.addCommand("EscalaSimbolos", EscalaSimbolos())
Gui.addCommand("DistribuirPontos", DistribuirPontos())
