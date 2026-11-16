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
        return recursos(
            "tug.svg",
            "Tomada no ponto",
            "Insere uma tomada 2D no ponto selecionado, ou na origem se nada estiver selecionado",
        )


class Gerar3D:
    def Activated(self):
        doc = App.activeDocument()
        encontradas = tomadas.listar_tomadas(doc)
        if encontradas:
            tomadas.gerar_caixas_tomadas(doc, encontradas)
        doc.recompute()

    def GetResources(self):
        return recursos(
            "tomada3d.svg",
            "Tomadas 3D",
            "Gera a caixa 3D de cada tomada TUG e oculta os símbolos 2D",
        )


class Cabo:
    def Activated(self):
        doc = App.activeDocument()
        cabos.desenhar_cabos_planta(doc, tomadas.listar_tomadas(doc))
        doc.recompute()

    def GetResources(self):
        return recursos(
            "fio.svg",
            "Fiação",
            "Desenha na planta os traços de fase, neutro e terra de cada tomada TUG",
        )


Gui.addCommand("ComponentEletric", ComponentEletric())
Gui.addCommand("Gerar3D", Gerar3D())
Gui.addCommand("Cabo", Cabo())
