"""Comandos para dar circuito e comando de interruptor aos pontos da planta."""
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.core.identificacao import proximo_circuito
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import identificacao, planilhas
from freecad.Circuits.UI.dialogs.circuito_dialog import DefinirCircuitoDialog


class DefinirCircuito:
    """Grava o mesmo circuito (e quadro) em todos os pontos selecionados."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecao = [obj for obj in Gui.Selection.getSelection() if identificacao.tem_circuito(obj)]
        if not selecao:
            QtWidgets.QMessageBox.information(
                None, "Definir circuito", "Selecione na planta os pontos que vão para o mesmo circuito (Ctrl + clique)."
            )
            return

        existentes = identificacao.circuitos_existentes(doc)
        atuais = {str(obj.Circuito) for obj in selecao}
        # Pontos que já estão juntos em um circuito: sugere o mesmo; misturados: sugere um novo.
        sugestao = atuais.pop() if len(atuais) == 1 else proximo_circuito(existentes)
        quadros = [quadro.Label for quadro in planilhas.listar_quadros(doc)]
        dialog = DefinirCircuitoDialog(len(selecao), existentes, sugestao, quadros)
        if not dialog.exec_():
            return
        dados = dialog.get_dados()
        if not dados["circuito"]:
            QtWidgets.QMessageBox.warning(None, "Definir circuito", "Informe o número do circuito.")
            return
        alterados = identificacao.definir_circuito(doc, selecao, dados["circuito"], dados["quadro"])
        if alterados < len(selecao):
            QtWidgets.QMessageBox.information(
                None,
                "Definir circuito",
                f"{alterados} de {len(selecao)} ponto(s) alterado(s). As tomadas TUG só aceitam circuito numérico.",
            )

    def IsActive(self):
        return True

    def GetResources(self):
        dados = recursos(
            "definir_circuito.svg",
            "Definir circuito",
            "Coloca os pontos selecionados no mesmo circuito e, se quiser, no mesmo quadro",
        )
        dados["Accel"] = "C, C"
        return dados


class LigarInterruptor:
    """Liga os interruptores selecionados aos pontos de luz selecionados."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        try:
            comando = identificacao.ligar_interruptor(doc, Gui.Selection.getSelection())
        except ValueError as erro:
            QtWidgets.QMessageBox.information(None, "Ligar interruptor", str(erro))
            return
        Gui.getMainWindow().statusBar().showMessage(f"Interruptor ligado aos pontos de luz pelo comando '{comando}'.", 8000)

    def IsActive(self):
        return True

    def GetResources(self):
        dados = recursos(
            "ligar_interruptor.svg",
            "Ligar interruptor",
            "Dá a mesma letra de comando ao interruptor e aos pontos de luz selecionados",
        )
        dados["Accel"] = "C, I"
        return dados


class IdentificarPontos:
    """Escreve ao lado de cada símbolo o circuito, o comando e a potência."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        if not identificacao.anotar(doc):
            QtWidgets.QMessageBox.information(None, "Identificar pontos", "Nenhum ponto elétrico na planta.")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "identificar_pontos.svg",
            "Identificar pontos",
            "Escreve ao lado de cada símbolo o circuito, o comando do interruptor e a potência",
        )


Gui.addCommand("DefinirCircuito", DefinirCircuito())
Gui.addCommand("LigarInterruptor", LigarInterruptor())
Gui.addCommand("IdentificarPontos", IdentificarPontos())
