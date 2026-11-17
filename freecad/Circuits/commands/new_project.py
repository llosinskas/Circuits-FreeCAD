"""Comandos para iniciar projetos, planilhas e modelos da biblioteca."""
import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits import ELECTRIC_LIBRARY_PATH
from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import biblioteca, parametros, pavimentos, planilhas
from freecad.Circuits.services.documento import GRUPOS_PROJETO, criar_grupos
from freecad.Circuits.UI.insert_circuit import InsertCircuit


class newProjetctEletrical:
    def Activated(self):
        doc = App.activeDocument() or App.newDocument("Projeto_eletrico")
        criar_grupos(doc, GRUPOS_PROJETO)
        pavimentos.garantir_ativo(doc)  # nível do BIM ou Térreo; o usuário troca no botão Pavimento
        parametros.planilha(doc, criar=True)  # tensões, aterramento, isolação, limites de queda

    def GetResources(self):
        return recursos(
            "newProject.svg",
            "Novo projeto",
            "Cria os grupos do projeto elétrico e ativa um pavimento (um nível do BIM, ou o Térreo se não houver)",
        )


class ParametrosProjeto:
    """Abre a planilha de parâmetros do projeto, criando-a com os padrões se ainda não existe."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        folha = parametros.planilha(doc, criar=True)
        try:
            folha.ViewObject.doubleClicked()
        except Exception:
            pass
        App.Console.PrintMessage(
            "Parâmetros do projeto: edite a coluna Valor. Montar circuitos usa estes valores na próxima vez.\n"
        )

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "parametros.svg",
            "Parâmetros",
            "Parâmetros do projeto: tensões, curto na entrada, esquema de aterramento, isolação, temperatura, "
            "limites de queda, curvas dos disjuntores e DR, usados no dimensionamento pela NBR 5410",
        )


class CreateModel:
    def Activated(self):
        os.makedirs(ELECTRIC_LIBRARY_PATH, exist_ok=True)
        nome, ok = QtWidgets.QInputDialog.getText(None, "Salvar desenho", "Digite o nome do arquivo:")
        if ok and nome.strip():
            biblioteca.criar_modelo(nome.strip())

    def GetResources(self):
        return recursos(
            "add_model.svg",
            "Criar modelo",
            "Cria um novo modelo de componente (.FCStd) na biblioteca",
        )


class newSpreadsheet:
    def Activated(self):
        doc = documento_ou_aviso()
        if doc:
            planilhas.criar_planilha_circuitos(doc)

    def GetResources(self):
        return recursos(
            "planilha.svg",
            "Planilha de circuitos",
            "Cria a planilha geral de circuitos do projeto",
        )


class addCircuit:
    def Activated(self):
        InsertCircuit().exec_()

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "record-svgrepo-com.svg",
            "Formulário de circuito",
            "Abre o formulário de circuito (em desenvolvimento: ainda não grava os dados)",
        )


class listElements:
    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        os.makedirs(ELECTRIC_LIBRARY_PATH, exist_ok=True)

        arquivos = biblioteca.listar_modelos()
        if not arquivos:
            QtWidgets.QMessageBox.information(None, "Importar modelo", "Não há modelos (.FCStd) na biblioteca.")
            return

        item, ok = QtWidgets.QInputDialog.getItem(None, "Importar modelo", "Escolha o modelo:", arquivos, 0, False)
        if not ok:
            return
        biblioteca.importar_modelo(doc, item)

    def GetResources(self):
        return recursos(
            "listElements.svg",
            "Importar modelo",
            "Escolhe um modelo da biblioteca e o importa para o documento",
        )


Gui.addCommand("newProjetctEletrical", newProjetctEletrical())
Gui.addCommand("newSpreadsheet", newSpreadsheet())
Gui.addCommand("AddSpreadsheet", addCircuit())
Gui.addCommand("ListElements", listElements())
Gui.addCommand("CreateModel", CreateModel())
Gui.addCommand("ParametrosProjeto", ParametrosProjeto())
