"""Comandos utilitários e de desenvolvimento da bancada."""
import importlib
import sys

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import recursos

_PACOTE = "freecad.Circuits"
_CHAVE_BANCADA = "CircuitsWorkbench"


class GetSpaces:
    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintError("No active document found.\n")
            return
        for obj in doc.Objects:
            App.Console.PrintMessage(f"  → {obj.Label}\n")

    def GetResources(self):
        return recursos("newProject.svg", "Pegar Espaços", "Pegar todos os espaços do projeto")


class ReiniciarBancada:
    """Recarrega todo o código da bancada sem fechar o FreeCAD."""

    def Activated(self):
        try:
            for nome in [m for m in sys.modules if m == _PACOTE or m.startswith(_PACOTE + ".")]:
                del sys.modules[nome]

            Gui.removeWorkbench(_CHAVE_BANCADA)
            importlib.import_module(_PACOTE + ".init_gui")
            Gui.activateWorkbench(_CHAVE_BANCADA)
            Gui.updateGui()
            App.Console.PrintMessage("✓ Bancada recarregada com sucesso!\n")
        except Exception as e:
            App.Console.PrintError(f"Erro ao recarregar bancada: {str(e)}\n")

    def GetResources(self):
        return recursos(
            "recompute.svg",
            "Reiniciar Bancada",
            "Recarregar todos os módulos da bancada sem fechar o FreeCAD",
        )


Gui.addCommand("GetSpaces", GetSpaces())
Gui.addCommand("ReiniciarBancada", ReiniciarBancada())
