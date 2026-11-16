"""Comandos de pontos elétricos em planta: tomadas, pontos de energia e iluminação.

Há um comando por símbolo de ``core.simbolos.CATALOGO``, com o ID
``Ponto_<símbolo>``, mais a legenda de símbolos.
"""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.core.simbolos import CATALOGO
from freecad.Circuits.objects.ponto import create_ponto
from freecad.Circuits.qt import QtCore, QtWidgets
from freecad.Circuits.services import alinhamento, legenda
from freecad.Circuits.UI.dialogs.ComponentInserter import ComponentInsertionMode

PREFIXO = "Ponto_"


class InserirPonto:
    """Insere pontos do mesmo símbolo em sequência, até o usuário apertar ESC."""

    def __init__(self, simbolo):
        self.simbolo = simbolo

    def Activated(self):
        if not documento_ou_aviso():
            return
        obj = create_ponto(self.simbolo)
        if obj is None:
            return
        anterior = self._ultimo_fixado()
        if anterior is not None:  # o próximo ponto repete circuito, quadro e rotação
            obj.Circuito = anterior.Circuito
            obj.Quadro = anterior.Quadro
            posicao = obj.Placement
            posicao.Rotation = anterior.Placement.Rotation
            obj.Placement = posicao
        self._em_insercao = obj.Name
        # O próximo ponto só começa depois que o clique atual terminar de ser tratado.
        ComponentInsertionMode(
            obj,
            ao_fixar=lambda: QtCore.QTimer.singleShot(0, self._repetir),
            plano_z0=True,
            referencias=alinhamento.posicoes_dos_simbolos(App.activeDocument(), exceto=obj),
        ).start()

    def _repetir(self):
        self._fixado = getattr(self, "_em_insercao", None)
        self.Activated()

    def _ultimo_fixado(self):
        nome = getattr(self, "_fixado", None)
        doc = App.activeDocument()
        return doc.getObject(nome) if nome and doc else None

    def IsActive(self):
        return True

    def GetResources(self):
        dados = CATALOGO[self.simbolo]
        dica = f"{dados['dica']}. Clique fixa e repete; R gira; Espaço alinha com o vizinho; ESC encerra"
        return recursos(f"simbologia/{self.simbolo}.svg", dados["legenda"], dica)


class LegendaSimbolos:
    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        if not legenda.gerar_legenda(doc):
            QtWidgets.QMessageBox.information(
                None, "Legenda", "Nenhum ponto elétrico na planta. Insira tomadas, pontos de energia ou iluminação."
            )

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "legenda.svg",
            "Legenda",
            "Desenha ao lado da planta a legenda dos símbolos usados no projeto",
        )


for _simbolo in CATALOGO:
    Gui.addCommand(PREFIXO + _simbolo, InserirPonto(_simbolo))
Gui.addCommand("LegendaSimbolos", LegendaSimbolos())
