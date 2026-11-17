"""Comandos de aterramento: condutor de cobre nu e cálculo da resistência das hastes."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.core import formularios
from freecad.Circuits.core.functions.Predial import aterramento as calculo
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import aterramento
from freecad.Circuits.UI.dialogs.calculo_dialog import CalculoDialog


class CondutorAterramento:
    """Marca as linhas selecionadas como condutor de aterramento de cobre nu."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecao = [obj for obj in Gui.Selection.getSelection() if hasattr(obj, "Points")]
        if not selecao:
            QtWidgets.QMessageBox.information(
                None, "Condutor de aterramento",
                "Desenhe o caminho do condutor com uma linha (barra Desenho), selecione-a e clique de novo.",
            )
            return
        secao, ok = QtWidgets.QInputDialog.getItem(
            None, "Condutor de aterramento", "Seção do cabo de cobre nu [mm²]:", aterramento.SECOES,
            aterramento.SECOES.index(aterramento.SECAO_PADRAO), False,
        )
        if ok:
            marcadas = aterramento.marcar_condutores(doc, selecao, secao)
            App.Console.PrintMessage(f"{marcadas} linha(s) marcada(s) como cabo de cobre nu {secao} mm².\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "condutor_aterramento.svg",
            "Condutor de aterramento",
            "Marca as linhas selecionadas como cabo de cobre nu do aterramento, contado nos quantitativos",
        )


class CalcAterramento:
    """Calcula a resistência de aterramento e o número de hastes."""

    @staticmethod
    def _calcular(dados):
        dados = dict(dados)
        dados.pop("solo")
        resultado = calculo.dimensionar(**dados)
        return resultado, calculo.relatorio(resultado)

    def Activated(self):
        CalculoDialog("Resistência de aterramento", formularios.ATERRAMENTO, self._calcular, "", "aterramento").exec_()

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "calc_aterramento.svg",
            "Resistência de terra",
            "Calcula a resistência das hastes de aterramento em linha e quantas hastes atingem o valor desejado",
        )


Gui.addCommand("CondutorAterramento", CondutorAterramento())
Gui.addCommand("CalcAterramento", CalcAterramento())
