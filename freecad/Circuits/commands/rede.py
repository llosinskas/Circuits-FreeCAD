"""Comandos da rede de eletrodutos: encaixe nas caixas, verticais, rota dos circuitos e ocupação."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import eletrodutos_planta, rede, roteamento, verticais
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



class RotaCircuito:
    """Seleciona os eletrodutos e eletrocalhas por onde passa o cabo do circuito, do quadro aos pontos."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecao = Gui.Selection.getSelection()
        rotas = roteamento.rotas_dos_objetos(doc, selecao)
        if not rotas:
            QtWidgets.QMessageBox.information(
                None, "Rota do circuito",
                "Nenhum circuito chega ao quadro pela rede. Defina os circuitos dos pontos e conecte os "
                "eletrodutos às caixas (botão Conectar às caixas).")
            return
        if not selecao and len(rotas) > 1:
            nomes = [r["rotulo"] + (f" ({r['pavimento']})" if r.get("pavimento") else "") for r in rotas]
            escolha, ok = QtWidgets.QInputDialog.getItem(None, "Rota do circuito", "Circuito:", nomes, 0, False)
            if not ok:
                return
            rotas = [rotas[nomes.index(escolha)]]
        Gui.Selection.clearSelection()
        for rota in rotas:
            for nome in rota["objetos"]:
                obj = doc.getObject(nome)
                if obj is not None:
                    Gui.Selection.addSelection(obj)
        texto = "\n\n".join(roteamento.descrever(doc, rota) for rota in rotas[:15])
        if len(rotas) > 15:
            texto += f"\n\n... e mais {len(rotas) - 15} circuito(s)"
        App.Console.PrintMessage(texto + "\n")
        QtWidgets.QMessageBox.information(None, "Rota do circuito", texto)

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "rota_circuito.svg",
            "Rota do circuito",
            "Mostra e seleciona os eletrodutos e eletrocalhas por onde passa o cabo do circuito até o quadro. "
            "Selecione pontos, um quadro ou um eletroduto (os circuitos que passam nele), ou nada para escolher",
        )


class OcupacaoEletrodutos:
    """Conta os cabos de cada trecho pela rota dos circuitos e confere o diâmetro pela taxa de ocupação."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        dados = roteamento.ocupacao(doc)
        if not dados["eletrodutos"] and not dados["bandejas"]:
            QtWidgets.QMessageBox.information(
                None, "Ocupação dos eletrodutos",
                "Nenhum eletroduto com circuito: desenhe e conecte os eletrodutos às caixas primeiro.")
            return
        planilha = roteamento.gravar_planilha(doc, dados)
        pequenos = [e for e in dados["eletrodutos"] if e["pequeno"]]
        linhas = [f"{len(dados['eletrodutos'])} eletroduto(s) e {len(dados['bandejas'])} eletrocalha(s) na "
                  f"planilha '{planilha.Label}'."]
        if not pequenos:
            QtWidgets.QMessageBox.information(None, "Ocupação dos eletrodutos",
                                              "\n".join(linhas + ["", "Todos os eletrodutos comportam os cabos."]))
            return
        linhas += ["", "Acima da taxa de ocupação (NBR 5410, 6.2.11.1.6):"] + [
            f"  {e['nome']}: Ø{e['diametro']} → Ø{e['minimo'] or '?'} ({e['cabos']} cabos, {e['taxa']:.0%})"
            for e in pequenos[:20]]
        if len(pequenos) > 20:
            linhas.append(f"  ... e mais {len(pequenos) - 20}")
        linhas += ["", "Aumentar o diâmetro desses eletrodutos para o sugerido?"]
        resposta = QtWidgets.QMessageBox.question(None, "Ocupação dos eletrodutos", "\n".join(linhas))
        if resposta != QtWidgets.QMessageBox.Yes:
            Gui.Selection.clearSelection()
            for e in pequenos:
                obj = doc.getObject(e["objeto"])
                if obj is not None:
                    Gui.Selection.addSelection(obj)
            return
        doc.openTransaction("Diâmetro dos eletrodutos pela ocupação")
        try:
            trocados = roteamento.aplicar_diametros(doc, dados)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        try:
            eletrodutos_planta.anotar(doc)
        except Exception as erro:
            App.Console.PrintWarning(f"Rótulos dos eletrodutos não atualizados: {erro}\n")
        roteamento.gravar_planilha(doc, roteamento.ocupacao(doc))
        App.Console.PrintMessage("".join(f"{nome}: Ø{de} → Ø{para}\n" for nome, de, para in trocados))

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "ocupacao_eletrodutos.svg",
            "Ocupação eletrodutos",
            "Segue os cabos de cada circuito até o quadro, conta os condutores em cada eletroduto e "
            "eletrocalha e sugere o diâmetro pela taxa de ocupação (53 %, 31 %, 40 %)",
        )


class IdentificarFios:
    """Escreve ao lado de cada eletroduto e eletrocalha os fios que passam nele, por circuito."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        doc.openTransaction("Identificar fios por trecho")
        try:
            total = roteamento.identificar_fios(doc)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        if not total:
            QtWidgets.QMessageBox.information(
                None, "Fios por trecho",
                "Nenhum trecho com fios: defina os circuitos dos pontos e conecte os eletrodutos às caixas.")
            return
        App.Console.PrintMessage(f"{total} texto(s) de fios por trecho na pasta Fiação de cada pavimento.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "fios_trecho.svg",
            "Fios por trecho",
            "Escreve em cada eletroduto e eletrocalha os fios que passam nele (C1 #2,5 F+N+T), seguindo os "
            "circuitos até o quadro. Repetir apaga e escreve de novo",
        )


class MudarAltura:
    """Muda a altura de um eletroduto inteiro, de trechos ou a partir de um vértice (offset do Revit)."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        escolhas = [s for s in Gui.Selection.getSelectionEx() if rede.eh_eletroduto(s.Object)
                    and len(getattr(s.Object, "Points", [])) >= 2]
        if not escolhas:
            QtWidgets.QMessageBox.information(
                None, "Mudar altura",
                "Selecione um eletroduto (ele inteiro), um ou mais trechos dele, ou um vértice: a altura muda "
                "do vértice até a ponta, e ali o eletroduto sobe ou desce, com as curvas e o símbolo na planta.\n\n"
                "Para mudar no meio de um trecho, crie antes um vértice (Add Node).")
            return
        atual = rede.alturas_do_eletroduto(escolhas[0].Object)[0] / 1000.0
        altura, ok = QtWidgets.QInputDialog.getDouble(
            None, "Mudar altura", "Altura do piso até o eletroduto [m]:", atual, -5.0, 100.0, 2)
        if not ok:
            return
        sentido = "fim"
        if any(self._partes(s)[1] for s in escolhas):
            opcoes = ["Do vértice até o fim do eletroduto", "Do início do eletroduto até o vértice"]
            escolha, ok = QtWidgets.QInputDialog.getItem(None, "Mudar altura", "Mudar a altura:", opcoes, 0, False)
            if not ok:
                return
            sentido = "fim" if escolha == opcoes[0] else "inicio"
        doc.openTransaction("Mudar altura do eletroduto")
        try:
            for item in escolhas:
                arestas, vertices = self._partes(item)
                eletrodutos_planta.mudar_altura(item.Object, altura * 1000.0, arestas, vertices, sentido)
            eletrodutos_planta.atualizar_depois_de_editar(doc, sempre=True)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise

    @staticmethod
    def _partes(item):
        """(meios das arestas, vértices) selecionados no eletroduto, em planta."""
        arestas, vertices = [], []
        for nome, forma in zip(item.SubElementNames, item.SubObjects):
            if nome.startswith("Edge"):
                meio = forma.valueAt((forma.FirstParameter + forma.LastParameter) / 2.0)
                arestas.append((meio.x, meio.y))
            elif nome.startswith("Vertex"):
                vertices.append((forma.Point.x, forma.Point.y))
        return arestas, vertices

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "mudar_altura.svg",
            "Mudar altura",
            "Muda a altura do eletroduto selecionado, dos trechos selecionados ou do vértice selecionado até a "
            "ponta. Onde a altura muda, o eletroduto sobe ou desce com curvas, símbolo na planta e 3D, como no Revit",
        )


Gui.addCommand("ConectarEletrodutos", ConectarEletrodutos())
Gui.addCommand("EditarDescidas", EditarDescidas())
Gui.addCommand("ListaVerticais", ListaVerticais())
Gui.addCommand("SimbolosVerticais", SimbolosVerticais())
Gui.addCommand("DetalharVerticais", DetalharVerticais())
Gui.addCommand("RotaCircuito", RotaCircuito())
Gui.addCommand("OcupacaoEletrodutos", OcupacaoEletrodutos())
Gui.addCommand("IdentificarFios", IdentificarFios())
Gui.addCommand("MudarAltura", MudarAltura())
