"""Comandos de tomada em Sketch: inserção, conversão para 3D e símbolo do cabo."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import cabos, tomadas


def _sem_tomadas_tug(titulo):
    QtWidgets.QMessageBox.information(
        None, titulo, "Este comando usa as tomadas TUG (botão Tomadas > Tomada TUG), e não há nenhuma na planta."
    )


class ComponentEletric:
    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
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
        doc = documento_ou_aviso()
        if not doc:
            return
        encontradas = tomadas.listar_tomadas(doc)
        if not encontradas:
            _sem_tomadas_tug("Tomadas 3D")
            return
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
        doc = documento_ou_aviso()
        if not doc:
            return
        encontradas = tomadas.listar_tomadas(doc)
        if not encontradas:
            _sem_tomadas_tug("Fiação")
            return
        cabos.desenhar_cabos_planta(doc, encontradas)
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
