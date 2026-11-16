"""Comando para iniciar o projeto de um quadro elétrico."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import recursos
from freecad.Circuits.services.documento import GRUPOS_QUADRO, criar_grupos


class NewQuadro:
    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintError("No active document found.\n")
            return
        criar_grupos(doc, GRUPOS_QUADRO)

    def GetResources(self):
        return recursos(
            "estrutura_quadro.svg",
            "Estrutura de quadro",
            "Cria os grupos do projeto de um quadro elétrico: dados, dispositivos, conexões e listagem",
        )


Gui.addCommand("NewQuadro", NewQuadro())
