"""Comandos da rede de eletrodutos: encaixe nas caixas e lista de verticais."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import eletrodutos_planta, rede, verticais
from freecad.Circuits.UI.dialogs.descidas_dialog import CAIXA, DescidasDialog


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


class SimbolosVerticais:
    """Desenha na planta os símbolos de subida e descida de eletrodutos e eletrocalhas."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        quantidade = verticais.desenhar_simbolos(doc)
        if not quantidade:
            QtWidgets.QMessageBox.information(
                None, "Subidas e descidas",
                "Nenhuma vertical encontrada: conecte os eletrodutos às caixas, desenhe eletrodutos em alturas "
                "diferentes que se encontram ou eletrocalhas em alturas diferentes.",
            )
            return
        App.Console.PrintMessage(f"{quantidade} símbolo(s) de subida e descida desenhado(s) na planta.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "subidas_descidas.svg",
            "Subidas e descidas",
            "Símbolos de subida e descida na planta: eletroduto até as caixas, entre alturas diferentes "
            "(teto e piso) e eletrocalhas verticais, com diâmetro ou seção e comprimento",
        )


class DetalharVerticais:
    """Desenha um detalhe em elevação de cada tipo de vertical (V1, V2...)."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        quantidade = verticais.desenhar_detalhes(doc)
        if not quantidade:
            QtWidgets.QMessageBox.information(None, "Detalhar verticais", "Nenhuma vertical de eletroduto ou eletrocalha.")
            return
        App.Console.PrintMessage(f"{quantidade} detalhe(s) de verticais desenhado(s) ao lado da planta.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "detalhe_verticais.svg",
            "Detalhar verticais",
            "Detalhe em elevação de cada tipo de vertical de eletroduto e eletrocalha: piso, laje, alturas, "
            "curvas, caixa e quantidade",
        )


class EditarDescidas:
    """Lista as subidas e descidas entre eletrodutos de alturas diferentes para mudar alturas ou pôr caixa."""

    TITULO = "Editar descidas"

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        descidas = eletrodutos_planta.descidas(doc)
        if not descidas:
            QtWidgets.QMessageBox.information(
                None, self.TITULO,
                "Nenhuma descida: ligue dois eletrodutos de alturas diferentes no mesmo ponto da planta "
                "(ex.: um no teto e outro no piso) e marque-os com o botão Eletroduto.",
            )
            return

        def selecionar(indice):
            Gui.Selection.clearSelection()
            for braco in descidas[indice][1]["bracos"]:
                obj = doc.getObject(braco["nome"])
                if obj is not None:
                    Gui.Selection.addSelection(obj)

        dialogo = DescidasDialog(descidas, selecionar)
        if not dialogo.exec_():
            return
        mudancas = dialogo.get_dados()
        if not mudancas:
            return
        doc.openTransaction(self.TITULO)
        try:
            alterados, caixas = 0, 0
            for mudanca in mudancas:
                pav, descida = descidas[mudanca["indice"]]
                alterados += len(eletrodutos_planta.editar_descida(doc, descida, mudanca["de"], mudanca["ate"]))
                if mudanca["forma"] == CAIXA and eletrodutos_planta.caixa_na_descida(doc, pav, descida):
                    caixas += 1
            if caixas:
                rede.conectar(doc)
            refez_3d, refez_simbolos = eletrodutos_planta.atualizar_depois_de_editar(doc)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        extras = [texto for feito, texto in ((refez_3d, "3D refeito"), (refez_simbolos, "símbolos refeitos")) if feito]
        App.Console.PrintMessage(f"Descidas: {alterados} eletroduto(s) com altura nova, {caixas} caixa(s) de passagem"
                                 f"{'; ' + ', '.join(extras) if extras else ''}.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "editar_descidas.svg",
            "Editar descidas",
            "Lista as subidas e descidas entre eletrodutos de alturas diferentes: muda a altura de cima e de "
            "baixo, ou troca as curvas por uma caixa de passagem. Refaz o 3D e os símbolos que já existirem",
        )


Gui.addCommand("ConectarEletrodutos", ConectarEletrodutos())
Gui.addCommand("EditarDescidas", EditarDescidas())
Gui.addCommand("ListaVerticais", ListaVerticais())
Gui.addCommand("SimbolosVerticais", SimbolosVerticais())
Gui.addCommand("DetalharVerticais", DetalharVerticais())
