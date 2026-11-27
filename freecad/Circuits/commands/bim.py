"""Comandos BIM: propriedades IFC nos objetos da bancada e exportação IFC."""
import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import bim


def _resumo(contagem):
    return "\n".join(f"  {classe}: {n}" for classe, n in sorted(contagem.items())) or "  nenhum objeto da bancada"


class PropriedadesBIM:
    """Grava a classe IFC e as propriedades (psets) em todos os objetos da bancada."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        doc.openTransaction("Propriedades BIM")
        try:
            contagem = bim.atualizar_documento(doc)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        QtWidgets.QMessageBox.information(
            None, "Propriedades BIM",
            "Classe IFC (IfcType), atributos e propriedades (IfcProperties) gravados:\n\n" + _resumo(contagem)
            + "\n\nVeja no painel de propriedades, grupos IFC e IFC Attributes.")

    def IsActive(self):
        return App.activeDocument() is not None

    def GetResources(self):
        return recursos(
            "bim_propriedades.svg", "Propriedades BIM",
            "Grava em todos os objetos da bancada a classe IFC (IfcOutlet, IfcLightFixture, IfcSwitchingDevice, "
            "IfcCableCarrierSegment, IfcJunctionBox, IfcElectricDistributionBoard...) e as propriedades "
            "(Pset_ElectricalDeviceCommon, Pset_OutletTypeCommon... e Circuits_Eletrica com circuito, quadro, "
            "comando, pavimento e altura de montagem), para exportar em IFC. Elas também se atualizam sozinhas "
            "quando o objeto muda.")


class ExportarIFC:
    """Atualiza as propriedades BIM e grava o modelo em IFC pelo exportador da bancada BIM."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        try:
            import ifcopenshell  # noqa: F401
        except ImportError:
            QtWidgets.QMessageBox.warning(None, "Exportar IFC",
                                          "O IfcOpenShell não está instalado: a exportação IFC do FreeCAD precisa dele.")
            return
        base = os.path.splitext(doc.FileName)[0] if doc.FileName else os.path.join(os.path.expanduser("~"), doc.Name)
        caminho, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Exportar IFC", base + ".ifc", "IFC (*.ifc)")
        if not caminho:
            return
        selecionados = Gui.Selection.getSelection()
        try:
            contagem, quantidade = bim.exportar(doc, caminho, selecionados or None)
        except Exception as erro:
            QtWidgets.QMessageBox.critical(None, "Exportar IFC", f"Falha na exportação: {erro}")
            return
        QtWidgets.QMessageBox.information(
            None, "Exportar IFC", f"Gravado em {caminho}\n({quantidade} objeto(s) de partida).\n\n"
            "Classes dos objetos da bancada:\n" + _resumo(contagem))

    def IsActive(self):
        return App.activeDocument() is not None

    def GetResources(self):
        return recursos(
            "bim_exportar.svg", "Exportar IFC",
            "Atualiza as propriedades BIM e grava o modelo num arquivo IFC (exportador da bancada BIM). Com objetos "
            "selecionados, exporta só eles; sem seleção, o edifício do BIM, se houver, ou todos os sólidos "
            "(caixas, eletrodutos, eletrocalhas, quadros e colunas em 3D, prumadas).")


Gui.addCommand("PropriedadesBIM", PropriedadesBIM())
Gui.addCommand("ExportarIFC", ExportarIFC())
