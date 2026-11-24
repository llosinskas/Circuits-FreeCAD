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
    """Insere as colunas de medição paramétricas (padrão Enel) e deixa posicionar na planta."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        folha = servico.planilha(doc)
        andares = (_andares(folha) or []) if folha is not None else []
        valores = servico.valores_da_planilha(andares, servico.ler_parametros(folha) if folha is not None else {})
        medidores, ok = QtWidgets.QInputDialog.getInt(
            None, "Colunas de medição",
            "Medições diretas. Depois, nas propriedades do objeto, dá para mudar medidores, medidores por coluna\n"
            "(até 3), demanda, fases, modelo da caixa (P ou K a O) e CDPM; o dimensionamento e o 3D se refazem.",
            int(valores.get("Medidores", 12)), 1, 2000)
        if not ok:
            return
        if valores.get("Medidores") != medidores:
            valores["DemandaTotal"] = 0.0  # a demanda do edifício valia para outro número de unidades
        valores["Medidores"] = medidores
        pavimento = pavimentos.pavimento_para_insercao(doc, Gui.Selection.getSelection())
        doc.openTransaction("Colunas de medição")
        try:
            coluna = servico.criar_colunas(doc, pavimento, **valores)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        resumo = "; ".join(coluna.Conjuntos) or "nenhum conjunto"
        avisos = "".join(f"\n  aviso: {a}" for a in coluna.Avisos)
        App.Console.PrintMessage(f"Colunas de medição ({coluna.Solucao}): {resumo}.{avisos}\n"
                                 "Clique na planta para posicionar (R gira); o fundo das caixas vai para a parede.\n")
        ComponentInsertionMode(coluna, cota=pavimentos.elevacao(pavimento),
                               referencias=alinhamento.posicoes_dos_simbolos(doc, exceto=coluna)).start()

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "coluna_medicao.svg",
            "Coluna de medição",
            "Insere as colunas de medição paramétricas no padrão Enel SP: escolhe a caixa P (até 3 por coluna e 30 "
            "por agrupamento) ou as coletivas K a O, dimensiona disjuntor geral, barramento e ramal, e desenha em 3D",
        )


class GerarCentroMedicao:
    """Cria ou recria no desenho o centro de medição (único ou descentralizado) a partir da planilha."""

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
        parametros = servico.ler_parametros(folha)
        try:
            comparacao = regras.comparar(andares, precos=servico.ler_precos(folha), **{
                k: parametros[k] for k in ("tensao", "uso", "distancia_horizontal", "comprimento_ramal",
                                           "demanda_total_a", "altura_ultimo_pavimento", "andares_por_centro")
                if k in parametros})
        except ValueError as erro:
            QtWidgets.QMessageBox.warning(None, TITULO, str(erro))
            return
        recomendada = comparacao["recomendada"]
        opcoes = [s for s in regras.SOLUCOES_DESENHAVEIS if s in comparacao["custos"]]
        opcoes.sort(key=lambda s: (s != recomendada, comparacao["custos"][s]["total"]))
        rotulos = [f"{regras.NOMES[s]} – R$ {comparacao['custos'][s]['total']:,.0f}".replace(",", ".")
                   + (" (recomendada)" if s == recomendada else "") for s in opcoes]
        dica = ""
        if recomendada == "busway":
            dica = ("\nA mais barata é o busway: para ele, desenhe o caminho do QDC ao shaft e use o botão Busway.\n")
        escolha, ok = QtWidgets.QInputDialog.getItem(
            None, TITULO, "Solução para desenhar (os objetos gerados antes são recriados no mesmo lugar):" + dica,
            rotulos, 0, False)
        if not ok:
            return
        solucao = opcoes[rotulos.index(escolha)]
        doc.openTransaction("Gerar centro de medição")
        try:
            plano, criados = servico.gerar_centro(doc, andares, solucao, parametros)
            doc.commitTransaction()
        except ValueError as erro:
            doc.abortTransaction()
            QtWidgets.QMessageBox.warning(None, TITULO, str(erro))
            return
        except Exception:
            doc.abortTransaction()
            raise
        centros = "; ".join(f"centro {c['numero']} ({', '.join(c['andares'])}), {c['abrigo']['area']:.1f} m²"
                            for c in plano).replace(".", ",")
        App.Console.PrintMessage(f"{regras.NOMES[solucao]}: {centros}. {len(criados)} objetos na pasta Busway e "
                                 "medição; mova à vontade, que o próximo Gerar mantém a posição.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "gerar_centro_medicao.svg",
            "Gerar centro de medição",
            "Cria ou recria no desenho o centro de medição da planilha: único no térreo ou descentralizado (um "
            "centro a cada grupo de andares, com o ramal de cada um), com as colunas paramétricas e o abrigo. "
            "Recriar mantém o que você moveu",
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
Gui.addCommand("GerarCentroMedicao", GerarCentroMedicao())
