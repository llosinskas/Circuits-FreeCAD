"""Comando de geração do relatório técnico em PDF."""
import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import quantitativos
from freecad.Circuits.UI.dialogs.report_dialog import ReportDialog


def _caminho_padrao(doc):
    """Sugere salvar na pasta do projeto, se o documento já estiver salvo."""
    if not doc.FileName:
        return "Relatorio_Projeto.pdf"
    pasta = os.path.dirname(doc.FileName)
    nome = os.path.splitext(os.path.basename(doc.FileName))[0]
    return os.path.join(pasta, f"Relatorio_{nome}.pdf")


class GenerateReport:
    def Activated(self):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            QtWidgets.QMessageBox.critical(
                None,
                "Dependência não encontrada",
                "A biblioteca 'reportlab' é necessária para gerar relatórios em PDF.\n"
                "Por favor, instale-a rodando:\n\npip install reportlab\n\n"
                "No seu console do FreeCAD ou no ambiente Python configurado.",
            )
            return

        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento aberto.")
            return

        dialog = ReportDialog()
        if not dialog.exec_():
            return
        opcoes = dialog.get_opcoes()

        caminho, _ = QtWidgets.QFileDialog.getSaveFileName(
            None, "Salvar Relatório PDF", _caminho_padrao(doc), "PDF Files (*.pdf)"
        )
        if not caminho:
            return

        from freecad.Circuits.services.pdf_generator import PDFGenerator

        try:
            PDFGenerator(doc, caminho, opcoes).generate()
            QtWidgets.QMessageBox.information(None, "Sucesso", f"Relatório gerado em:\n{caminho}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "Erro", f"Ocorreu um erro ao gerar o PDF:\n{e}")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "gerarPDF.svg",
            "Relatório PDF",
            "Configura e exporta o relatório técnico do projeto em PDF",
        )


class GerarQuantitativos:
    """Levanta os materiais do projeto e grava a lista em CSV, XLSX e PDF."""

    def Activated(self):
        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento aberto.")
            return
        linhas, fiacao = quantitativos.levantar(doc)
        if not linhas:
            QtWidgets.QMessageBox.information(
                None, "Quantitativos", "Nenhum material encontrado: insira pontos, eletrodutos ou quadros no projeto."
            )
            return
        caminho, _ = QtWidgets.QFileDialog.getSaveFileName(
            None, "Salvar quantitativos (CSV, XLSX e PDF)", quantitativos.caminho_padrao(doc),
            "Quantitativo (*.csv *.xlsx *.pdf)",
        )
        if not caminho:
            return
        try:
            gravados, avisos = quantitativos.exportar(doc, caminho, linhas, fiacao)
        except OSError as erro:
            QtWidgets.QMessageBox.critical(None, "Quantitativos", f"Não foi possível gravar os arquivos:\n{erro}")
            return
        texto = [f"{len(linhas)} item(ns) levantado(s). Arquivos gravados:"] + [f"  {c}" for c in gravados]
        avisos += fiacao["avisos"][:15]
        if len(fiacao["avisos"]) > 15:
            avisos.append(f"... e mais {len(fiacao['avisos']) - 15} aviso(s), listados no PDF.")
        if avisos:
            texto += ["", "Avisos:"] + [f"  {aviso}" for aviso in avisos]
        texto += ["", "Estimativa a partir do desenho: confira antes de comprar."]
        QtWidgets.QMessageBox.information(None, "Quantitativos", "\n".join(texto))

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "quantitativos.svg",
            "Quantitativos",
            "Levanta pontos, caixas, eletrodutos, verticais, fios e quadros e grava em CSV, XLSX e PDF",
        )


Gui.addCommand("GenerateReport", GenerateReport())
Gui.addCommand("GerarQuantitativos", GerarQuantitativos())
