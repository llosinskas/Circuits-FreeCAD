"""Comandos utilitários e de desenvolvimento da bancada."""
import importlib
import sys

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.services import estilo

_PACOTE = "freecad.Circuits"
_CHAVE_BANCADA = "CircuitsWorkbench"


class GetSpaces:
    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        for obj in doc.Objects:
            App.Console.PrintMessage(f"  → {obj.Label}\n")

    def GetResources(self):
        return recursos(
            "listar_objetos.svg",
            "Listar objetos",
            "Lista no painel de relatório todos os objetos do documento",
        )


class PintarSketches:
    """Pinta de preto todos os Sketches do documento, inclusive os de projetos antigos."""

    def Activated(self):
        doc = documento_ou_aviso()
        if doc:
            App.Console.PrintMessage(f"{estilo.pintar_todos(doc)} Sketch(es) pintado(s) de preto.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "sketches_pretos.svg",
            "Sketches em preto",
            "Pinta de preto as linhas de todos os Sketches do documento (os novos já nascem pretos)",
        )


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


class ApoiarProjeto:
    """Abre a janela com o QR code do LivePix para apoiar o desenvolvimento da bancada."""

    def Activated(self):
        from freecad.Circuits.UI.dialogs.apoiar_dialog import ApoiarDialog
        ApoiarDialog().exec_()

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "apoiar.svg",
            "Apoiar",
            "Apoie o desenvolvimento da bancada Circuits com um Pix pelo LivePix: abre o QR code para escanear "
            "com o celular e o link para o navegador",
        )


Gui.addCommand("GetSpaces", GetSpaces())
Gui.addCommand("ApoiarProjeto", ApoiarProjeto())
Gui.addCommand("PintarSketches", PintarSketches())
Gui.addCommand("ReiniciarBancada", ReiniciarBancada())
