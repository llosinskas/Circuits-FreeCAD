"""Comandos das folhas de desenho (TechDraw): nova folha, vistas, cortes, detalhes e arrumação."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.core import folhas as regras
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import folhas

TITULO = "Folhas"


def _perguntar_formato(titulo_padrao="Planta baixa"):
    """(formato, título da folha) escolhidos pelo usuário, ou None."""
    opcoes = [f"{nome} ({l:g} × {a:g} mm)" for nome, (l, a) in regras.FORMATOS.items()]
    padrao = list(regras.FORMATOS).index(regras.FORMATO_PADRAO)
    escolha, ok = QtWidgets.QInputDialog.getItem(None, "Nova folha", "Formato (NBR 10068):", opcoes, padrao, False)
    if not ok:
        return None
    titulo, ok = QtWidgets.QInputDialog.getText(None, "Nova folha", "Conteúdo da folha (carimbo):",
                                                text=titulo_padrao)
    if not ok:
        return None
    return escolha.split()[0], titulo.strip() or titulo_padrao


def _abrir(folha):
    try:
        folha.ViewObject.doubleClicked()
    except Exception:
        pass


def _folha_ou_nova(doc, selecao, titulo_padrao):
    folha = folhas.folha_ativa(doc, selecao)
    if folha is not None:
        return folha
    escolha = _perguntar_formato(titulo_padrao)
    return folhas.nova_folha(doc, *escolha) if escolha else None


def _avisar_se_nao_coube(resultado):
    if resultado and not resultado["cabe"]:
        QtWidgets.QMessageBox.warning(
            None, TITULO,
            "As vistas não cabem na folha nem em 1:1000. Use um formato maior (nova folha) ou "
            "tire alguma vista desta folha e clique em Organizar folha.")


def _com_transacao(doc, nome, funcao):
    doc.openTransaction(nome)
    try:
        resultado = funcao()
        doc.commitTransaction()
        return resultado
    except Exception:
        doc.abortTransaction()
        raise


class NovaFolha:
    """Cria uma folha com margens da NBR 10068 e o carimbo preenchido."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        escolha = _perguntar_formato()
        if not escolha:
            return
        folha = _com_transacao(doc, "Nova folha", lambda: folhas.nova_folha(doc, *escolha))
        _abrir(folha)

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos("folha_nova.svg", "Nova folha",
                        "Cria uma folha A0 a A4 (TechDraw) com as margens da NBR 10068 e o carimbo: projeto, "
                        "obra, cliente, responsável, data e número da folha já preenchidos")


class InserirNaFolha:
    """Põe na folha os pavimentos, grupos e planilhas selecionados, na escala que couber."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecao = Gui.Selection.getSelection()
        objetos = [o for o in selecao if not o.TypeId.startswith("TechDraw::")]
        if not objetos:
            QtWidgets.QMessageBox.information(
                None, TITULO,
                "Selecione na árvore o que vai para a folha: um pavimento (a planta), o diagrama unifilar, "
                "a legenda, as notas, os detalhes das verticais ou uma planilha (quadro de cargas). "
                "Para escolher a folha, selecione-a junto; senão vai para a última.")
            return
        folha = _folha_ou_nova(doc, selecao, objetos[0].Label)
        if folha is None:
            return

        def fazer():
            folhas.inserir(doc, folha, objetos)
            return folhas.organizar(doc, folha)

        _avisar_se_nao_coube(_com_transacao(doc, "Inserir na folha", fazer))
        _abrir(folha)

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos("folha_inserir.svg", "Inserir na folha",
                        "Põe na folha os pavimentos (planta sem o 3D), diagramas, legenda, notas, detalhes e "
                        "planilhas selecionados e arruma tudo na maior escala que couber")


class CorteNaFolha:
    """Corte do modelo 3D pela linha desenhada na planta."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecao = Gui.Selection.getSelection()
        linhas = [o for o in selecao if len(getattr(o, "Points", [])) >= 2]
        if not linhas:
            QtWidgets.QMessageBox.information(
                None, TITULO,
                "Desenhe na planta uma linha onde o corte passa (as setas olham para a direita de quem vai do "
                "primeiro ao segundo ponto), selecione-a e clique de novo.")
            return
        if not folhas.solidos_do_modelo(doc):
            QtWidgets.QMessageBox.information(
                None, TITULO, "O corte é do modelo 3D: gere o Modelo 3D (e as paredes, se houver) primeiro.")
            return
        folha = _folha_ou_nova(doc, selecao, "Cortes")
        if folha is None:
            return

        def fazer():
            for linha in linhas:
                folhas.inserir_corte(doc, folha, linha)
            return folhas.organizar(doc, folha)

        _avisar_se_nao_coube(_com_transacao(doc, "Corte na folha", fazer))
        _abrir(folha)

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos("folha_corte.svg", "Corte na folha",
                        "Com uma linha desenhada na planta selecionada, põe na folha o corte do modelo 3D (letra, "
                        "setas na planta e título Corte A-A)")


class DetalheNaFolha:
    """Ampliação de uma região da planta marcada por um círculo ou outra forma fechada."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecao = Gui.Selection.getSelection()
        regioes = [o for o in selecao if not o.TypeId.startswith("TechDraw::") and hasattr(o, "Shape")
                   and getattr(o.Shape, "isClosed", lambda: False)()]
        if not regioes:
            QtWidgets.QMessageBox.information(
                None, TITULO,
                "Desenhe na planta um círculo (ou retângulo) em volta do que quer detalhar, selecione-o e "
                "clique de novo.")
            return
        folha = _folha_ou_nova(doc, selecao, "Detalhes")
        if folha is None:
            return

        def fazer():
            for regiao in regioes:
                folhas.inserir_detalhe(doc, folha, regiao)
            return folhas.organizar(doc, folha)

        _avisar_se_nao_coube(_com_transacao(doc, "Detalhe na folha", fazer))
        _abrir(folha)

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos("folha_detalhe.svg", "Detalhe na folha",
                        "Com um círculo ou retângulo desenhado na planta selecionado, põe na folha a ampliação "
                        "daquela região (D1, D2...), em escala maior que a da planta")


class OrganizarFolha:
    """Escolhe de novo a escala e arruma as vistas da folha."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        folha = folhas.folha_ativa(doc, Gui.Selection.getSelection())
        if folha is None:
            QtWidgets.QMessageBox.information(None, TITULO, "Nenhuma folha: crie uma com Nova folha.")
            return
        opcoes = ["Automática (a maior que couber)"] + [regras.texto_escala(n) for n in regras.ESCALAS]
        escolha, ok = QtWidgets.QInputDialog.getItem(None, TITULO, f"Escala de '{folha.Label}':", opcoes, 0, False)
        if not ok:
            return
        escala = None if escolha == opcoes[0] else int(escolha.split(":")[1])
        _avisar_se_nao_coube(_com_transacao(doc, "Organizar folha", lambda: folhas.organizar(doc, folha, escala)))
        _abrir(folha)

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos("folha_organizar.svg", "Organizar folha",
                        "Arruma as vistas da folha selecionada (ou da última) fugindo do carimbo, na escala "
                        "escolhida ou na maior que couber, com os títulos embaixo")


class AtualizarFolhas:
    """Refaz o desenho das vistas 2D de todas as folhas com o modelo atual."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        total = _com_transacao(doc, "Atualizar folhas", lambda: folhas.atualizar(doc))
        App.Console.PrintMessage(f"{total} vista(s) atualizada(s) nas folhas.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos("folha_atualizar.svg", "Atualizar folhas",
                        "Redesenha as plantas, diagramas e detalhes das folhas com o projeto atual, mantendo o "
                        "lugar e a escala de cada vista (os cortes se atualizam sozinhos)")


Gui.addCommand("NovaFolha", NovaFolha())
Gui.addCommand("InserirNaFolha", InserirNaFolha())
Gui.addCommand("CorteNaFolha", CorteNaFolha())
Gui.addCommand("DetalheNaFolha", DetalheNaFolha())
Gui.addCommand("OrganizarFolha", OrganizarFolha())
Gui.addCommand("AtualizarFolhas", AtualizarFolhas())
