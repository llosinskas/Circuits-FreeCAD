"""Comandos de tomada em Sketch: inserção, conversão para 3D e símbolo do cabo."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import recursos
from freecad.Circuits.services import cabos, tomadas


class ComponentEletric:
    def Activated(self):
        doc = App.activeDocument()
        selecao = Gui.Selection.getSelectionEx()
        ponto = App.Vector(0, 0, 0)
        if selecao and selecao[0].HasSubObjects:
            ponto = selecao[0].PickedPoints[0]
        tomadas.criar_tomada_simples(doc, ponto)

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos("Componentes.svg", "Inserir um componente elétrico", "Inserir um componente no projeto")


class Gerar3D:
    def Activated(self):
        doc = App.activeDocument()
        encontradas = tomadas.listar_tomadas(doc)
        if encontradas:
            tomadas.gerar_caixas_tomadas(doc, encontradas)
        doc.recompute()

    def GetResources(self):
        return recursos("tomadas.svg", "Converter em 3D", "Converter as informações inseridas em modelo 3D")


class Cabo:
    def Activated(self):
        doc = App.activeDocument()
        cabos.desenhar_cabos_planta(doc, tomadas.listar_tomadas(doc))
        doc.recompute()

    def GetResources(self):
        return recursos("fio.svg", "Gerar cabo", "Gera a simbologia do cabo em 2D")


Gui.addCommand("ComponentEletric", ComponentEletric())
Gui.addCommand("Gerar3D", Gerar3D())
Gui.addCommand("Cabo", Cabo())
