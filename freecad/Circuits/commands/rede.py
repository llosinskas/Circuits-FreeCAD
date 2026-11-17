"""Comandos da rede de eletrodutos: encaixe nas caixas e lista de verticais."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import rede


class ConectarEletrodutos:
    """Marca as linhas selecionadas como eletrodutos e prende os vértices delas nas caixas próximas."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecao = Gui.Selection.getSelection()
        if not selecao and not rede.listar_eletrodutos(doc):
            QtWidgets.QMessageBox.information(
                None, "Conectar às caixas",
                "Desenhe os eletrodutos (botão Eletroduto), selecione as linhas e clique de novo.",
            )
            return
        tratados, ligadas, soltas = rede.conectar(doc, selecao)
        linhas = [f"{tratados} eletroduto(s) conectado(s); {ligadas} caixa(s) encaixada(s)."]
        if soltas:
            linhas += ["", "Pontos com circuito ainda sem eletroduto:"] + [f"  {nome}" for nome in soltas[:20]]
            if len(soltas) > 20:
                linhas.append(f"  ... e mais {len(soltas) - 20}")
        QtWidgets.QMessageBox.information(None, "Conectar às caixas", "\n".join(linhas))

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "conectar_caixas.svg",
            "Conectar às caixas",
            "Prende os vértices dos eletrodutos selecionados (ou de todos) nas caixas a até 30 cm",
        )


class ListaVerticais:
    """Grava no documento a planilha com as verticais de cada caixa."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        fiacao = rede.analisar(doc)
        if not fiacao["verticais"]:
            QtWidgets.QMessageBox.information(
                None, "Lista de verticais",
                "Nenhuma vertical: conecte os eletrodutos às caixas (botão Conectar às caixas) primeiro.",
            )
            return
        planilha = rede.gravar_planilha_verticais(doc, fiacao["verticais"])
        total = sum(v["comprimento"] for v in fiacao["verticais"])
        App.Console.PrintMessage(
            f"{len(fiacao['verticais'])} vertical(is), {total:.2f} m no total, na planilha '{planilha.Label}'.\n"
        )
        try:
            planilha.ViewObject.doubleClicked()
        except Exception:
            pass

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "verticais.svg",
            "Lista de verticais",
            "Lista as descidas e subidas de eletroduto até cada caixa, com altura e comprimento",
        )


Gui.addCommand("ConectarEletrodutos", ConectarEletrodutos())
Gui.addCommand("ListaVerticais", ListaVerticais())
