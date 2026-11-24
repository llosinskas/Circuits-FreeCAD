"""Comandos do centro de medição Enel SP: planejamento (busway × medição agrupada), colunas e busway."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.core import centro_medicao as regras
from freecad.Circuits.core import formularios
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import alinhamento, pavimentos
from freecad.Circuits.services import centro_medicao as servico
from freecad.Circuits.UI.dialogs.calculo_dialog import CalculoDialog
from freecad.Circuits.UI.dialogs.ComponentInserter import ComponentInsertionMode

TITULO = "Centro de medição"


def _planilha_ou_criar(doc):
    """A planilha do centro de medição; na primeira vez, cria e explica (devolve None)."""
    folha = servico.planilha(doc)
    if folha is not None:
        return folha
    folha, quantidade = servico.criar(doc)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(folha)
    origem = f"com os {quantidade} pavimentos do projeto" if quantidade else "com 4 andares de exemplo"
    QtWidgets.QMessageBox.information(
        None, TITULO,
        f"Criei a planilha \"{folha.Label}\" {origem}.\n\n"
        "Preencha por pavimento: cota do piso (em relação ao centro de medição), unidades, demanda de cada "
        "unidade [A] e fases. Os preços de referência ficam nas colunas G a I: troque pelas suas cotações.\n\n"
        "Depois clique de novo.",
    )
    return None


def _andares(folha):
    try:
        return servico.ler_andares(folha)
    except ValueError as erro:
        QtWidgets.QMessageBox.warning(None, TITULO, str(erro))
        return None


class PlanejarMedicao:
    """Compara a medição agrupada no térreo com o busway e a medição centralizada, com os custos."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        folha = _planilha_ou_criar(doc)
        if folha is None:
            return
        andares = _andares(folha)
        if andares is None:
            return
        precos = servico.ler_precos(folha)

        def calcular(dados):
            argumentos = formularios.argumentos_centro_medicao(dados)
            resultado = regras.comparar(andares, precos=precos, **argumentos)
            resultado["parametros"] = argumentos
            return resultado, regras.relatorio(resultado)

        dialog = CalculoDialog(TITULO, formularios.CENTRO_MEDICAO, calcular, "Gravar na planilha", "centro_medicao")
        if dialog.exec_() and dialog.resultado:
            servico.gravar_resultado(folha, dialog.resultado, dialog.resultado["parametros"])
            App.Console.PrintMessage(f"Centro de medição: {regras.NOMES[dialog.resultado['recomendada']]} "
                                     f"recomendada, gravado em {folha.Label}.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "centro_medicao.svg",
            "Centro de medição",
            "Planeja o centro de medição pela Enel SP: medição agrupada (caixas P no térreo) ou busway com medição "
            "centralizada nos andares, com queda de tensão, caixas, shaft e custo estimado de cada solução",
        )


class InserirColunaMedicao:
    """Insere as colunas de medição (caixas P e CDPM, padrão Enel) e deixa posicionar na planta."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        folha = servico.planilha(doc)
        andares = (_andares(folha) or []) if folha is not None else []
        total = sum(a["unidades"] for a in andares) or 12
        demanda = max([a["demanda_a"] for a in andares] or [regras.DEMANDA_PADRAO])
        caixas, ok = QtWidgets.QInputDialog.getInt(
            None, "Colunas de medição",
            "Medições (caixas tipo P). Até 30 por agrupamento, 3 sobrepostas e 6 de cada lado da CDPM:",
            total, 1, 600)
        if not ok:
            return
        try:
            grupos = regras.agrupamentos(caixas, min(demanda, regras.CORRENTE_MAX_P))
        except ValueError as erro:
            QtWidgets.QMessageBox.warning(None, "Colunas de medição", str(erro))
            return
        pavimento = pavimentos.pavimento_para_insercao(doc, Gui.Selection.getSelection())
        doc.openTransaction("Colunas de medição")
        try:
            parte = servico.inserir_colunas(doc, grupos, pavimento)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        descricao = ", ".join(f"{g['caixas']} caixas ({g['cdpm']})" for g in grupos)
        App.Console.PrintMessage(f"Colunas de medição: {descricao}. Clique na planta para posicionar (R gira); "
                                 "o fundo das caixas vai para a parede.\n")
        ComponentInsertionMode(parte, cota=pavimentos.elevacao(pavimento),
                               referencias=alinhamento.posicoes_dos_simbolos(doc, exceto=parte)).start()

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "coluna_medicao.svg",
            "Coluna de medição",
            "Insere os agrupamentos de caixas de medição tipo P com a CDPM no padrão Enel (até 30 por agrupamento, "
            "altura da base pela Tabela 29) e posiciona com o mouse",
        )


class InserirBusway:
    """Marca as linhas selecionadas como busway e sobe a prumada com as caixas MEC dos andares."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        linhas = servico.linhas_desenhadas(Gui.Selection.getSelection())
        if not linhas:
            QtWidgets.QMessageBox.information(
                None, "Busway",
                "Desenhe com a Linha ou a Polilinha o caminho do busway, do QDC até o shaft (o último ponto é onde "
                "a prumada sobe), selecione e clique de novo. Com duas linhas de busway, desenhe duas.")
            return
        folha = servico.planilha(doc)
        parametros = servico.ler_parametros(folha) if folha is not None else {}
        if not parametros:
            QtWidgets.QMessageBox.information(
                None, "Busway", "Calcule primeiro o Centro de medição (e grave na planilha): ele dimensiona o "
                                "busway, a queda de tensão e as caixas MEC de cada andar.")
            return
        andares = _andares(folha)
        if andares is None:
            return
        try:
            resultado = regras.busway(andares, **{k: parametros[k] for k in (
                "tensao", "uso", "distancia_horizontal", "comprimento_ramal", "demanda_total_a",
                "altura_ultimo_pavimento") if k in parametros})
        except ValueError as erro:
            QtWidgets.QMessageBox.warning(None, "Busway", str(erro))
            return
        if len(linhas) < len(resultado["linhas"]):
            QtWidgets.QMessageBox.warning(
                None, "Busway", f"O cálculo pede {len(resultado['linhas'])} linhas de busway; selecione "
                                f"{len(resultado['linhas'])} caminhos desenhados (um por linha).")
            return
        base = pavimentos.pavimento_do_objeto(doc, linhas[0]) or pavimentos.pavimento_para_insercao(doc)
        topo = pavimentos.elevacao(base) + resultado["topo"] * 1000.0 if base is not None else resultado["topo"] * 1e3
        doc.openTransaction("Busway")
        try:
            for linha, dados in zip(linhas, resultado["linhas"]):
                servico.criar_prumada(doc, linha, dados, resultado["andares"], base, topo)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        texto = " + ".join(f"{l['nominal']} A (queda {l['queda']:.2f} %)" for l in resultado["linhas"])
        App.Console.PrintMessage(f"Busway: {texto}; caixas MEC em {len(resultado['andares'])} andares.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "busway.svg",
            "Busway",
            "Marca o caminho selecionado (do QDC ao shaft) como busway e sobe a prumada pelos andares, com os "
            "plug-ins e as caixas MEC dimensionados no Centro de medição, em 2D e 3D",
        )


Gui.addCommand("PlanejarMedicao", PlanejarMedicao())
Gui.addCommand("InserirColunaMedicao", InserirColunaMedicao())
Gui.addCommand("InserirBusway", InserirBusway())
