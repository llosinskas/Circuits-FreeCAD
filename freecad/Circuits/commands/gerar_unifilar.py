"""Comandos do diagrama unifilar e das planilhas de quadro.

Sequência de uso: Novo quadro -> Montar circuitos (a partir da planta) ou
Circuito (manual) -> Unifilar.
"""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.core import balanceamento
from freecad.Circuits.core import quadro as regras_quadro
from freecad.Circuits.services import circuitos, identificacao, parametros, planilhas, quadro_cargas, unifilar
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
        linhas += [
            "",
            "Dimensionado pela NBR 5410 com os Parâmetros do projeto: seção mínima, capacidade com temperatura e "
            "agrupamento, queda de tensão e seccionamento. Comprimento e agrupamento só entram quando a rede de "
            "eletrodutos chega ao símbolo do quadro; veja as colunas Comprimento, Queda e Critério da planilha.",
        ]
        QtWidgets.QMessageBox.information(None, "Montar circuitos", "\n".join(linhas))

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "montar_circuitos.svg",
            "Montar circuitos",
            "Soma os pontos da planta por circuito, dimensiona cabo e disjuntor pela NBR 5410 (capacidade, "
            "agrupamento, temperatura, queda de tensão) e grava no quadro",
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
            unifilar.gerar_diagrama_gerador(doc)  # só se o projeto tiver gerador calculado

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "unifilar.svg",
            "Unifilar",
            "Gera o diagrama unifilar de cada quadro do projeto e, se houver gerador calculado, o da transferência rede/gerador (QTA)",
        )


class BalancearFases:
    """Redistribui os circuitos de um quadro entre as fases para equilibrar a carga."""

    TITULO = "Balancear fases"

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        quadro = _escolher_quadro(doc, self.TITULO)
        if quadro is None:
            return
        resultado = planilhas.balancear_fases(quadro)
        if resultado is None:
            QtWidgets.QMessageBox.information(
                None, self.TITULO,
                "O quadro ainda não tem circuitos na planilha de circuitos: use Montar circuitos ou preencha a planilha.",
            )
            return
        tensao_fn = parametros.ler(doc)["tensao_fn"]
        texto = (f"Quadro {quadro.Label}\n\n{balanceamento.relatorio(resultado, tensao_fn)}\n\n"
                 "Para manter um circuito numa fase, escreva * depois da fase na planilha (ex.: R*).")
        if not resultado["mudados"]:
            QtWidgets.QMessageBox.information(None, self.TITULO, texto)
            return
        resposta = QtWidgets.QMessageBox.question(
            None, self.TITULO, texto + "\n\nGravar as fases novas na planilha de circuitos?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if resposta != QtWidgets.QMessageBox.Yes:
            return
        doc.openTransaction(self.TITULO)
        planilhas.balancear_fases(quadro, aplicar=True)
        doc.commitTransaction()
        App.Console.PrintMessage(f"{len(resultado['mudados'])} circuito(s) mudaram de fase em {quadro.Label}. "
                                 "Gere o unifilar de novo para atualizar o diagrama.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "balanceamento.svg",
            "Balancear fases",
            "Redistribui os circuitos do quadro entre as fases R, S e T para equilibrar a carga; mostra a carga "
            "e a corrente de cada fase antes e depois e pergunta antes de gravar",
        )


class GerarMultifilar:
    """Gera o diagrama multifilar de cada quadro: um condutor por fase, neutro e terra."""

    def Activated(self):
        doc = documento_ou_aviso()
        if doc:
            feitos = unifilar.gerar_multifilares(doc, _quadros_ou_criar(doc))
            App.Console.PrintMessage(f"{feitos} diagrama(s) multifilar(es) gerado(s).\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "multifilar.svg",
            "Multifilar",
            "Gera o diagrama multifilar de cada quadro: barramentos R, S, T, N e PE, e cada circuito com um "
            "condutor por fase, neutro e terra, os polos do disjuntor e o DR",
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


class QuadroCargas:
    """Quadro de cargas por fase, com desequilíbrio, DRs por grupo e as reservas da NBR 5410."""

    TITULO = "Quadro de cargas"

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        quadro = _escolher_quadro(doc, self.TITULO)
        if quadro is None:
            return
        if not planilhas.ler_circuitos(quadro):
            QtWidgets.QMessageBox.information(
                None, self.TITULO,
                "O quadro ainda não tem circuitos na planilha de circuitos: use Montar circuitos ou preencha a planilha.")
            return
        doc.openTransaction(self.TITULO)
        try:
            faltam = quadro_cargas.reservas_que_faltam(quadro)
            if faltam and QtWidgets.QMessageBox.question(
                    None, self.TITULO,
                    f"A NBR 5410 (6.5.4.7) pede {len(faltam)} circuito(s) de reserva a mais neste quadro "
                    f"({', '.join(r['N_circuito'] for r in faltam)}).\n\nAcrescentar na planilha de circuitos?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
                quadro_cargas.acrescentar_reservas(quadro)
            folha, dados = quadro_cargas.gerar(doc, quadro)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        carga = dados["carga"]
        linhas = [f"Quadro {quadro.Label}: R {carga['R']:.0f} VA · S {carga['S']:.0f} VA · T {carga['T']:.0f} VA",
                  f"Desequilíbrio: {dados['desequilibrio']:.1f} %".replace(".", ",")]
        if dados["grupos_dr"]:
            linhas.append("DRs: " + "; ".join(f"{nome} ({', '.join(n)})" for nome, n in dados["grupos_dr"]))
        if dados["sem_fase"]:
            linhas.append(f"Sem fase (fora da conta): {', '.join(dados['sem_fase'])}")
        if dados["sugestao"]:
            linhas.append("Para equilibrar: " + ", ".join(f"C{n} → {f}" for n, f in dados["sugestao"].items())
                          + ". Use Balancear fases para gravar.")
        linhas.append(f"\nPlanilha \"{folha.Label}\" (para a folha: Inserir na folha).")
        QtWidgets.QMessageBox.information(None, self.TITULO, "\n".join(linhas))

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "quadro_cargas.svg",
            "Quadro de cargas",
            "Monta o quadro de cargas por fase (R, S, T) com o desequilíbrio, os DRs por grupo (coluna Grupo do DR) "
            "e oferece as reservas da NBR 5410",
        )


Gui.addCommand("AddCircuito", AddCircuito())
Gui.addCommand("BalancearFases", BalancearFases())
Gui.addCommand("GerarMultifilar", GerarMultifilar())
Gui.addCommand("CircuitosQuadro", CircuitosQuadro())
Gui.addCommand("MontarCircuitos", MontarCircuitos())
Gui.addCommand("ComponentesQuadro", ComponentesQuadro())
Gui.addCommand("GerarUnifilar", GerarUnifilar())
Gui.addCommand("GerarPlanilha", GerarPlanilha())
Gui.addCommand("QuadroCargas", QuadroCargas())
