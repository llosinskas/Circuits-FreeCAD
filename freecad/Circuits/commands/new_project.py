"""Comandos para iniciar projetos, planilhas e modelos da biblioteca."""
import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits import ELECTRIC_LIBRARY_PATH
from freecad.Circuits.commands._base import recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import biblioteca, planilhas
from freecad.Circuits.services.documento import GRUPOS_PROJETO, criar_grupos
from freecad.Circuits.UI.insert_circuit import InsertCircuit


class newProjetctEletrical:
    def Activated(self):
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintError("No active document found.\n")
            return
        criar_grupos(doc, GRUPOS_PROJETO)

    def GetResources(self):
        return recursos("newProject.svg", "Novo Projeto", "Iniciar um novo projeto")


class CreateModel:
    def Activated(self):
        os.makedirs(ELECTRIC_LIBRARY_PATH, exist_ok=True)
        nome, ok = QtWidgets.QInputDialog.getText(None, "Salvar desenho", "Digite o nome do arquivo:")
        if ok and nome.strip():
            biblioteca.criar_modelo(nome.strip())
        else:
            QtWidgets.QMessageBox.warning(None, "Cancelado", "Operação cancelada")

    def GetResources(self):
        return recursos("add_model.svg", "Criar Model", "Botão para criar Models")


class newSpreadsheet:
    def Activated(self):
        planilhas.criar_planilha_circuitos(App.ActiveDocument)

    def GetResources(self):
        return recursos("planilha.svg", "Nova Planilha", "Criar uma nova planilha de circuitos")


class addCircuit:
    def Activated(self):
        InsertCircuit().exec_()

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos("record-svgrepo-com.svg", "Add Planilha", "Adicionar os circuitos na planilha")


class listElements:
    def Activated(self):
        if not os.path.exists(ELECTRIC_LIBRARY_PATH):
            os.makedirs(ELECTRIC_LIBRARY_PATH)
            return

        arquivos = biblioteca.listar_modelos()
        if not arquivos:
            QtWidgets.QMessageBox.information(None, "Nenhum arquivo", "Não há arquivos FCStd na pasta.")
            return

        item, ok = QtWidgets.QInputDialog.getItem(None, "Abrir desenho", "Escolha o arquivo:", arquivos, editable=False)
        if not ok:
            return

        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintError("No active document found.\n")
            return
        biblioteca.importar_modelo(doc, item)

    def GetResources(self):
        return recursos("listElements.svg", "Listar Elementos", "Listar elementos elétricos")


Gui.addCommand("newProjetctEletrical", newProjetctEletrical())
Gui.addCommand("newSpreadsheet", newSpreadsheet())
Gui.addCommand("AddSpreadsheet", addCircuit())
Gui.addCommand("ListElements", listElements())
Gui.addCommand("CreateModel", CreateModel())
