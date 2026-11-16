"""Comandos do diagrama unifilar e das planilhas de quadro.

Sequência de uso: Novo quadro -> Montar circuitos (a partir da planta) ou
Circuito (manual) -> Unifilar.
"""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import circuitos, planilhas, unifilar
from freecad.Circuits.UI.dialogs.quadro_dialogs import Add_circuito, CriarQuadro


def _criar_quadro(doc):
    """Abre o diálogo de quadro. Devolve a planilha criada, ou None se cancelado."""
    dialog = CriarQuadro()
    if not dialog.exec_():
        return None
    dados = dialog.get_dados()
    if not str(dados["indentificacao"]).strip():
        QtWidgets.QMessageBox.warning(None, "Novo quadro", "Informe a identificação do quadro.")
        return None
    planilha = planilhas.criar_planilha_quadro(doc, dados)
    doc.recompute()
    return planilha


def _quadros_ou_criar(doc):
    """Quadros do documento; sem nenhum, abre o diálogo para criar o primeiro."""
    quadros = planilhas.listar_quadros(doc)
    if not quadros:
        _criar_quadro(doc)
        quadros = planilhas.listar_quadros(doc)
    return quadros


def _escolher_quadro(doc, titulo):
    """Um quadro do documento: o único, ou o que o usuário escolher. None se cancelado."""
    quadros = _quadros_ou_criar(doc)
    if not quadros:
        App.Console.PrintWarning("Nenhum quadro no projeto. Crie um quadro primeiro.\n")
        return None
    if len(quadros) == 1:
        return quadros[0]
    nomes = [quadro.Label for quadro in quadros]
    nome, ok = QtWidgets.QInputDialog.getItem(None, titulo, "Quadro:", nomes, 0, False)
    return quadros[nomes.index(nome)] if ok else None


class GerarPlanilha:
    def Activated(self):
        doc = documento_ou_aviso()
        if doc:
            _criar_quadro(doc)

    def GetResources(self):
        return recursos(
            "quadro_novo.svg",
            "Planilha do quadro",
            "Cria a planilha de dados de um quadro: tensão, fases, disjuntor geral e DPS",
        )


class MontarCircuitos:
    """Lê os pontos da planta, dimensiona os circuitos e os grava no quadro."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        quadro = _escolher_quadro(doc, "Montar circuitos")
        if quadro is None:
            return

        gravados, avisos = circuitos.montar_circuitos(doc, quadro)
        if not gravados and not avisos:
            QtWidgets.QMessageBox.information(
                None,
                "Montar circuitos",
                "Nenhum ponto elétrico com circuito definido na planta.\n"
                "Insira tomadas, pontos de energia ou iluminação e preencha a propriedade Circuito.",
            )
            return

        linhas = [f"{len(gravados)} circuito(s) gravado(s) no quadro {quadro.Label}."]
        linhas += [
            f"  Circuito {c['numero']}: {c['destino']}, {c['pontos']} ponto(s), {c['potencia_va']:.0f} VA"
            for c in gravados
        ]
        if avisos:
            linhas += ["", "Avisos:"] + [f"  {aviso}" for aviso in avisos]
        linhas += ["", "O cálculo não considera queda de tensão nem agrupamento: confira antes de usar."]
        QtWidgets.QMessageBox.information(None, "Montar circuitos", "\n".join(linhas))

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "montar_circuitos.svg",
            "Montar circuitos",
            "Soma os pontos da planta por circuito, escolhe cabo e disjuntor e grava no quadro",
        )


class GerarUnifilar:
    def Activated(self):
        doc = documento_ou_aviso()
        if doc:
            unifilar.gerar_diagramas(doc, _quadros_ou_criar(doc))

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "unifilar.svg",
            "Unifilar",
            "Gera o diagrama unifilar de cada quadro do projeto",
        )


class AddCircuito:
    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        quadro = _escolher_quadro(doc, "Adicionar circuito")
        if quadro is None:
            return

        dialog = Add_circuito()
        if dialog.exec_():
            planilhas.adicionar_circuito(quadro, dialog.get_dados())
        doc.recompute()

    def GetResources(self):
        return recursos(
            "adicionar.svg",
            "Circuito",
            "Adiciona ou atualiza manualmente um circuito na planilha de um quadro",
        )


Gui.addCommand("AddCircuito", AddCircuito())
Gui.addCommand("MontarCircuitos", MontarCircuitos())
Gui.addCommand("GerarUnifilar", GerarUnifilar())
Gui.addCommand("GerarPlanilha", GerarPlanilha())
