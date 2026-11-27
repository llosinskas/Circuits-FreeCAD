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
from freecad.Circuits.UI.dialogs.coluna_medicao_dialog import ColunaMedicaoDialog
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
    if quantidade == 1:
        origem = "com o pavimento do projeto (as unidades ficam nele; acrescente os andares, se houver)"
    elif quantidade:
        origem = f"com os {quantidade} pavimentos do projeto (o mais baixo sem unidades)"
    else:
        origem = "com 4 andares de exemplo"
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


def _mostrar(objetos):
    """Seleciona e enquadra os objetos criados (ficam visíveis mesmo se a pasta estava escondida)."""
    try:
        Gui.Selection.clearSelection()
        for obj in objetos:
            vobj = getattr(obj, "ViewObject", None)
            if vobj is not None:
                vobj.Visibility = True
            pais, vistos = list(obj.InList), set()
            while pais:
                pai = pais.pop()
                if pai.Name in vistos or not pai.isDerivedFrom("App::DocumentObjectGroup"):
                    continue
                vistos.add(pai.Name)
                if pai.ViewObject is not None:
                    pai.ViewObject.Visibility = True
                pais += pai.InList
            Gui.Selection.addSelection(obj)
        Gui.SendMsgToActiveView("ViewSelection")
    except Exception:
        pass


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
    """Insere ou edita as colunas de medição paramétricas (padrão Enel SP + ajustes de layout)."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecionada = next(
            (o for o in Gui.Selection.getSelection() if getattr(getattr(o, "Proxy", None), "Type", "") == "ColunaMedicao"),
            None,
        )
        if selecionada is not None:
            dialogo = ColunaMedicaoDialog(servico.ler_propriedades_coluna(selecionada), editando=True)
            if not dialogo.exec_():
                return
            doc.openTransaction("Editar coluna de medição")
            try:
                coluna = servico.atualizar_colunas(doc, selecionada, **dialogo.get_dados())
                doc.commitTransaction()
            except Exception:
                doc.abortTransaction()
                raise
            resumo = "; ".join(coluna.Conjuntos) or "nenhum conjunto"
            avisos = "".join(f"\n  aviso: {a}" for a in coluna.Avisos)
            App.Console.PrintMessage(f"Colunas de medição atualizadas ({coluna.Solucao}): {resumo}.{avisos}\n")
            return

        folha = servico.planilha(doc)
        andares = (_andares(folha) or []) if folha is not None else []
        valores = servico.valores_da_planilha(andares, servico.ler_parametros(folha) if folha is not None else {})
        dialogo = ColunaMedicaoDialog(valores, editando=False)
        if not dialogo.exec_():
            return
        dados = dialogo.get_dados()
        pavimento = pavimentos.pavimento_para_insercao(doc, Gui.Selection.getSelection())
        doc.openTransaction("Colunas de medição")
        try:
            coluna = servico.criar_colunas(doc, pavimento, **dados)
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
            "Insere ou edita (com a coluna selecionada) as colunas de medição paramétricas no padrão Enel SP: "
            "dimensiona caixas, CDPM, barramento e ramal com ajustes de layout e prévia em 3D",
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
        if "descentralizado" not in opcoes:
            dica += ("\nA descentralizada precisa de pelo menos 2 andares com unidades na planilha e de "
                     "\"Andares por centro\" maior que 0 no Centro de medição.\n")
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
        mensagem = (f"{regras.NOMES[solucao]}: {centros}. {len(criados)} objetos na pasta Busway e medição; mova "
                    "à vontade, que o próximo Gerar mantém a posição.")
        App.Console.PrintMessage(mensagem + "\n")
        _mostrar(criados)
        QtWidgets.QMessageBox.information(None, TITULO, mensagem)

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


class MuralMedicao:
    """Desenha (ou refaz) a elevação frontal cotada das colunas de medição: o mural."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecionadas = [o for o in Gui.Selection.getSelection() if servico.eh_coluna(o)]
        colunas = selecionadas or [o for o in doc.Objects if servico.eh_coluna(o)]
        if not colunas:
            QtWidgets.QMessageBox.information(
                None, "Mural de medição",
                "Insira antes as colunas de medição (Coluna de medição ou Gerar centro de medição). O mural é a "
                "elevação frontal cotada delas, como nos desenhos da ET 0018 da Enel SP.")
            return
        doc.openTransaction("Mural de medição")
        try:
            grupos = servico.desenhar_murais(doc, colunas)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        _mostrar([o for g in grupos for o in g.Group])
        App.Console.PrintMessage(f"Mural de medição: {len(grupos)} desenhado(s) na pasta Busway e medição. Mova à "
                                 "vontade: o próximo Mural mantém a posição. Para a folha, selecione o grupo e use "
                                 "Inserir na folha.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "mural_medicao.svg",
            "Mural de medição",
            "Desenha a elevação frontal cotada das colunas de medição selecionadas (ou de todas): caixas P com "
            "medidor, disjuntor e suporte L, CDPM com barramentos, disjuntor geral e DPS, eletroduto de entrada, "
            "piso, cotas e notas (ET 0018 Enel SP, Desenhos 23 e 8.24 a 8.33)",
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
Gui.addCommand("MuralMedicao", MuralMedicao())
