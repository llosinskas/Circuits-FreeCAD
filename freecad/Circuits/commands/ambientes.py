"""Comandos dos ambientes: polilinhas a partir dos espaços e pontos automáticos pela NBR 5410."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import ambientes
from freecad.Circuits.UI.dialogs.pontos_auto_dialog import PontosAutoDialog


class GerarAmbientes:
    """Polilinha fechada de cada ambiente, dos espaços do BIM ou das formas selecionadas."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecao = Gui.Selection.getSelection()
        if not selecao and not ambientes.listar_espacos(doc):
            QtWidgets.QMessageBox.information(
                None, "Ambientes",
                "Nenhum espaço no projeto. Crie os espaços (Arquitetura > Espaço, sobre as paredes) ou desenhe o "
                "contorno de cada ambiente com retângulo ou polilinha, selecione e clique de novo.",
            )
            return
        doc.openTransaction("Ambientes")
        try:
            criadas, ignorados = ambientes.gerar_ambientes(doc, selecao or None)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        linhas = [f"{len(criadas)} ambiente(s) em polilinha, na pasta Ambientes do pavimento:"]
        linhas += [f"  {a.NomeAmbiente}: {a.TipoAmbiente}, {a.AreaAmbiente:.2f} m², {a.PerimetroAmbiente:.2f} m"
                   for a in criadas[:25]]
        if ignorados:
            linhas += ["", "Sem contorno fechado (ignorados): " + ", ".join(ignorados[:10])]
        linhas += ["", "Confira o tipo de cada um (propriedade TipoAmbiente) e use Pontos automáticos."]
        QtWidgets.QMessageBox.information(None, "Ambientes", "\n".join(linhas))

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "ambientes.svg",
            "Ambientes",
            "Gera a polilinha de cada ambiente a partir dos espaços da bancada BIM, ou das formas fechadas "
            "selecionadas, com nome, tipo, área e perímetro",
        )


class PontosAutomaticos:
    """Prevê e coloca tomadas, interruptor e luz nos ambientes, só quando o usuário confirma."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecionados = [o for o in Gui.Selection.getSelection() if ambientes.eh_ambiente(o)]
        alvos = selecionados or ambientes.listar_ambientes(doc)
        if not alvos:
            QtWidgets.QMessageBox.information(
                None, "Pontos automáticos", "Nenhum ambiente: use o botão Ambientes primeiro.")
            return

        def prever(indice, tipo):
            return ambientes.plano(doc, alvos[indice], tipo)

        dialogo = PontosAutoDialog(
            [(a.NomeAmbiente, a.TipoAmbiente, a.AreaAmbiente, a.PerimetroAmbiente) for a in alvos], prever)
        if not dialogo.exec_():
            return
        escolhas = dialogo.get_dados()
        doc.openTransaction("Pontos automáticos")
        try:
            tomadas = 0
            for indice, tipo in escolhas:
                tomadas += len(ambientes.gerar_pontos(doc, alvos[indice], tipo)["tomadas"])
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        App.Console.PrintMessage(
            f"Pontos automáticos: {len(escolhas)} ambiente(s), {tomadas} tomada(s), {len(escolhas)} luz(es) e "
            "interruptor(es). Defina os circuitos com Circuitos > Definir circuito.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "pontos_auto.svg",
            "Pontos automáticos",
            "Prevê pela NBR 5410 e coloca nos ambientes as tomadas (pelo perímetro, fora das portas), o "
            "interruptor (ao lado da porta) e a luz (no centro). Mostra a prévia antes de gerar",
        )


Gui.addCommand("GerarAmbientes", GerarAmbientes())
Gui.addCommand("PontosAutomaticos", PontosAutomaticos())
