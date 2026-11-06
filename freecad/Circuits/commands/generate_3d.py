"""Comandos de geração de modelos 3D: eletrodutos e caixas."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import caixas_3d, eletrodutos


class Generate3DConduits:
    """Gera os tubos 3D a partir da seleção ou de todos os ConduitPath do documento."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return

        caminhos = Gui.Selection.getSelection() or eletrodutos.listar_caminhos(doc)
        if not caminhos:
            QtWidgets.QMessageBox.information(None, "Aviso", "Selecione uma linha (Wire) para gerar o eletroduto 3D.")
            return

        criados = eletrodutos.gerar_tubos(doc, caminhos)
        App.Console.PrintMessage(f"{criados} eletrodutos 3D gerados com sucesso.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos("conduite.svg", "Gerar Eletrodutos 3D", "Converte caminhos de eletrodutos em tubos 3D")


class Generate3DSwitches:
    """Gera as caixas 3D de interruptores, pontos de iluminação e tomadas."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return

        objetos, tomadas = caixas_3d.listar_alvos(doc)
        if not objetos and not tomadas:
            QtWidgets.QMessageBox.information(
                None,
                "Aviso",
                "Nenhum interruptor, ponto de iluminação ou tomada encontrado no documento.\n"
                "Insira componentes primeiro usando os botões correspondentes.",
            )
            return

        criadas = caixas_3d.gerar_caixas(doc, objetos, tomadas)
        App.Console.PrintMessage(f"{criadas} caixa(s) 3D gerada(s) com sucesso.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "gerar3d_switch.svg",
            "Gerar Caixas 3D (Interruptores/Tomadas/Iluminação)",
            "Gera caixas 3D a partir das medidas dos interruptores, tomadas e pontos de iluminação",
        )


Gui.addCommand("Generate3DConduits", Generate3DConduits())
Gui.addCommand("Generate3DSwitches", Generate3DSwitches())
