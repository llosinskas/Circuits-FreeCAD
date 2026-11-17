"""Comandos de pavimentos: escolher o pavimento ativo e mover símbolos entre pavimentos."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import pavimentos as servico
from freecad.Circuits.UI.dialogs.pavimento_dialog import DefinirPavimentoDialog


class DefinirPavimento:
    """Escolhe o pavimento onde os próximos símbolos entram, ou cria um novo."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        nome, elevacao, altura = servico.sugestao_novo(doc)
        sugestao = {"nome": nome, "elevacao_mm": elevacao, "altura_mm": altura}
        dialog = DefinirPavimentoDialog(servico.resumo(doc), sugestao)
        if not dialog.exec_():
            return
        dados = dialog.get_dados()
        pav = servico.definir(doc, dados["nome"], dados["elevacao_mm"], dados["altura_mm"])
        App.Console.PrintMessage(f"Pavimento ativo: {pav.Label}. Os próximos símbolos entram nele.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "pavimento.svg",
            "Pavimento",
            "Escolhe ou cria o pavimento onde os próximos símbolos entram, cada um na pasta do seu tipo",
        )


class AdicionarNivelBIM:
    """Cria um nível da bancada BIM e o torna o pavimento ativo."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        nome, elevacao, altura = servico.sugestao_novo(doc)
        sugestao = {"nome": nome, "elevacao_mm": elevacao, "altura_mm": altura}
        dialog = DefinirPavimentoDialog(
            servico.resumo(doc), sugestao, titulo="Adicionar nível do BIM", selecionar_sugestao=True
        )
        if not dialog.exec_():
            return
        dados = dialog.get_dados()
        try:
            nivel = servico.criar_nivel_bim(doc, dados["nome"], dados["elevacao_mm"], dados["altura_mm"])
        except Exception as erro:
            QtWidgets.QMessageBox.warning(None, "Adicionar nível do BIM", f"Não foi possível criar o nível: {erro}")
            return
        App.Console.PrintMessage(f"Nível do BIM ativo: {nivel.Label}. Os próximos símbolos entram nele.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "nivel_bim.svg",
            "Nível do BIM",
            "Cria um nível da bancada BIM, com nome, cota e altura, e o torna o pavimento ativo",
        )


class MoverParaPavimento:
    """Move os símbolos selecionados para as pastas de outro pavimento."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecao = [obj for obj in Gui.Selection.getSelection() if servico.chave_do_objeto(obj)]
        if not selecao:
            QtWidgets.QMessageBox.information(
                None, "Mover para pavimento", "Selecione antes os símbolos que quer mover (Ctrl + clique)."
            )
            return
        pavimentos = servico.resumo(doc)
        if not pavimentos:
            QtWidgets.QMessageBox.information(
                None, "Mover para pavimento", "Ainda não há pavimentos. Crie um no botão Pavimento."
            )
            return
        nomes = [p["nome"] for p in pavimentos]
        atual = next((i for i, p in enumerate(pavimentos) if p["ativo"]), 0)
        nome, ok = QtWidgets.QInputDialog.getItem(
            None, "Mover para pavimento", f"Mover {len(selecao)} símbolo(s) para o pavimento:", nomes, atual, False
        )
        if ok:
            movidos = servico.mover(doc, selecao, servico.por_nome(doc, nome))
            App.Console.PrintMessage(f"{movidos} símbolo(s) movido(s) para {nome}.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "mover_pavimento.svg",
            "Mover para pavimento",
            "Move os símbolos selecionados para as pastas de outro pavimento",
        )


Gui.addCommand("DefinirPavimento", DefinirPavimento())
Gui.addCommand("AdicionarNivelBIM", AdicionarNivelBIM())
Gui.addCommand("MoverParaPavimento", MoverParaPavimento())
