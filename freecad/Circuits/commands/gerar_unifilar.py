"""Comandos do diagrama unifilar e das planilhas de quadro."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import recursos
from freecad.Circuits.services import planilhas, unifilar
from freecad.Circuits.UI.dialogs.quadro_dialogs import Add_circuito, CriarQuadro


class GerarPlanilha:
    def Activated(self):
        doc = App.activeDocument()
        dialog = CriarQuadro()
        dialog.exec_()
        planilhas.criar_planilha_quadro(doc, dialog.get_dados())
        doc.recompute()

    def GetResources(self):
        return recursos("planilha.svg", "Gerar unifilar", "Gerar diagrama unifilar dos quadros do projeto")


def _quadros_ou_criar(doc):
    """Quadros do documento; sem nenhum, abre o diálogo para criar o primeiro."""
    quadros = planilhas.listar_quadros(doc)
    if not quadros:
        GerarPlanilha().Activated()
    return quadros


class GerarUnifilar:
    def Activated(self):
        doc = App.activeDocument()
        unifilar.gerar_diagramas(doc, _quadros_ou_criar(doc))

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos("unifilar.svg", "Gerar unifilar", "Gerar diagrama unifilar dos quadros do projeto")


class AddCircuito:
    def Activated(self):
        doc = App.activeDocument()
        quadros = _quadros_ou_criar(doc)
        if not quadros:
            App.Console.PrintWarning("Nenhum quadro encontrado. Gere a planilha do quadro primeiro.\n")
            return

        dialog = Add_circuito()
        if dialog.exec_():
            dados = dialog.get_dados()
            for quadro in quadros:
                planilhas.adicionar_circuito(quadro, dados)
        doc.recompute()

    def GetResources(self):
        return recursos("adicionar.svg", "Adicionar um circuito no diagrama", "Adicionar um circuito no quadro")


Gui.addCommand("AddCircuito", AddCircuito())
Gui.addCommand("GerarUnifilar", GerarUnifilar())
Gui.addCommand("GerarPlanilha", GerarPlanilha())
