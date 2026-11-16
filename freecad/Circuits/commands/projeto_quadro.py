"""Comando para iniciar o projeto de um quadro elétrico."""
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.services.documento import GRUPOS_QUADRO, criar_grupos


class NewQuadro:
    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        criar_grupos(doc, GRUPOS_QUADRO)

    def GetResources(self):
        return recursos(
            "estrutura_quadro.svg",
            "Estrutura de quadro",
            "Cria os grupos do projeto de um quadro elétrico: dados, dispositivos, conexões e listagem",
        )


Gui.addCommand("NewQuadro", NewQuadro())
