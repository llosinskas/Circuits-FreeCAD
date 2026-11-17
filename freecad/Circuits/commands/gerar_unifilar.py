"""Comandos do diagrama unifilar e das planilhas de quadro.

Sequência de uso: Novo quadro -> Montar circuitos (a partir da planta) ou
Circuito (manual) -> Unifilar.
"""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.core import quadro as regras_quadro
from freecad.Circuits.services import circuitos, identificacao, planilhas, unifilar
from freecad.Circuits.UI.dialogs.quadro_dialogs import Add_circuito, CriarQuadro


def _criar_quadro(doc):
    """Abre o diálogo de quadro. Devolve a planilha criada, ou None se cancelado."""
    # Com um símbolo de quadro selecionado na planta, a planilha é criada para ele.
    simbolo = identificacao.quadro_selecionado(Gui.Selection.getSelection())
    dialog = CriarQuadro()
    if simbolo is not None:
        dialog.identificacao.setText(str(simbolo.Descricao))
    if not dialog.exec_():
        return None
    dados = dialog.get_dados()
    nome = str(dados["indentificacao"]).strip()
    if not nome:
        QtWidgets.QMessageBox.warning(None, "Planilha do quadro", "Informe a identificação do quadro.")
        return None
    planilha = planilhas.criar_planilha_quadro(doc, dados)
    planilhas.planilha_de_circuitos(planilha)  # a estrutura de circuitos já nasce junto com o quadro
    if simbolo is not None:
        identificacao.vincular_planilha(doc, simbolo, planilha, nome)
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
            "Cria a planilha de dados de um quadro; com um símbolo de quadro selecionado, liga os dois",
        )


class CircuitosQuadro:
    """Abre a planilha de circuitos de um quadro, criando a estrutura se preciso."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        quadro = _escolher_quadro(doc, "Circuitos do quadro")
        if quadro is None:
            return
        planilha = planilhas.planilha_de_circuitos(quadro)
        try:
            planilha.ViewObject.doubleClicked()  # abre a planilha para edição
        except Exception:
            App.Console.PrintMessage(f"Abra a planilha '{planilha.Label}' na árvore do projeto para editar.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "circuitos_quadro.svg",
            "Circuitos do quadro",
            "Abre a planilha de circuitos do quadro: um circuito por linha, lida pelo unifilar",
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


class ComponentesQuadro:
    """Monta a lista de componentes do quadro: disjuntores, DR, DPS e barramentos."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        quadro = _escolher_quadro(doc, "Componentes do quadro")
        if quadro is None:
            return
        try:
            itens = regras_quadro.componentes(planilhas.ler_quadro(quadro), planilhas.ler_circuitos_completos(quadro))
        except ValueError as erro:
            QtWidgets.QMessageBox.warning(None, "Componentes do quadro", str(erro))
            return
        if not itens:
            QtWidgets.QMessageBox.information(
                None, "Componentes do quadro", "O quadro ainda não tem disjuntor geral nem circuitos."
            )
            return
        planilha = planilhas.gravar_componentes(doc, quadro, itens)
        linhas = [f"{item['quantidade']} {item['unidade']}  {item['item']}: {item['especificacao']}" for item in itens]
        linhas += ["", f"Lista gravada na planilha '{planilha.Label}'. Confira com o fabricante antes de comprar."]
        QtWidgets.QMessageBox.information(None, f"Componentes do quadro {quadro.Label}", "\n".join(linhas))

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "componentes_quadro.svg",
            "Componentes",
            "Lista os componentes do quadro: disjuntores, DR, DPS, barramentos e tamanho da caixa",
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
Gui.addCommand("CircuitosQuadro", CircuitosQuadro())
Gui.addCommand("MontarCircuitos", MontarCircuitos())
Gui.addCommand("ComponentesQuadro", ComponentesQuadro())
Gui.addCommand("GerarUnifilar", GerarUnifilar())
Gui.addCommand("GerarPlanilha", GerarPlanilha())
