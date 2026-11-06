"""Comandos de importação de arquivos do QElectroTech.

__author__ = "llosinskas"
__copyright__ = "2025 llosinskas"
__reference__ = "Kliurka"
"""
import os
import xml.etree.ElementTree as ET

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services.eletrodutos import subdividir_linha
from freecad.Circuits.services.qet_import import criar_planilha_fios

_PREFERENCIAS_DOCUMENTO = "User parameter:BaseApp/Preferences/Document"


def _garantir_labels_duplicados():
    """Pede autorização para ativar a preferência DuplicateLabels, se desligada."""
    preferencias = App.ParamGet(_PREFERENCIAS_DOCUMENTO)
    if preferencias.GetBool("DuplicateLabels"):
        return

    dialog = QtWidgets.QMessageBox()
    dialog.setWindowTitle("Elementos duplicados")
    dialog.setText("Para o funcionamento correto só pode existir um elemento com o Label no documento.")
    dialog.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)
    dialog.button(QtWidgets.QMessageBox.Yes).setText("Allow")
    dialog.button(QtWidgets.QMessageBox.Cancel).setText("Cancel")

    if dialog.exec_() == QtWidgets.QMessageBox.Yes:
        preferencias.SetBool("DuplicateLabels", True)
        print("DuplicateLabels has been enabled.")
    else:
        print("Execução do Script cancelada por usuário.")


def _importar_arquivo(doc):
    caminho, _ = QtWidgets.QFileDialog.getOpenFileName(
        None, "Selecione o Arquivo do QEletrotech .qet", "", "Arquivo QET (*.qet)"
    )
    if not caminho:
        print("Sem arquivo selecionado")
        return

    try:
        root = ET.parse(caminho).getroot()
    except ET.ParseError as e:
        QtWidgets.QMessageBox.critical(None, "Error", f"Erro ao abrir o arquivo QET: {str(e)}")
        return

    if not root.findall(".//conductor"):
        QtWidgets.QMessageBox.warning(None, "Warning", "Não há dados de cabos dentro do arquivo do QEletrotech.")
        return

    criar_planilha_fios(doc, os.path.splitext(os.path.basename(caminho))[0], root)


class ImportQET:
    def Activated(self):
        doc = App.activeDocument() or App.newDocument()
        _importar_arquivo(doc)
        _garantir_labels_duplicados()
        doc.recompute()

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "QET-logo.png",
            "Importar .qet",
            "Importar um arquivo do QEletroTech para a geração de componentes 3D e cabos",
        )


class Add_Node:
    def Activated(self):
        selecao = Gui.Selection.getSelection()
        if not selecao:
            print("Linha não selecionada!")
            return
        subdividir_linha(App.activeDocument(), selecao[0])

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "Draft_AddPoint.svg",
            "Adicionar ponto",
            "Adicionar um ponto na linha para edição do caminho dos cabos",
        )


Gui.addCommand("ImportQET", ImportQET())
Gui.addCommand("Add_Node", Add_Node())
