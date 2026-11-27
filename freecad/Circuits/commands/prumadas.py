"""Comando das prumadas verticais: energia, dados, interfone e iluminação de emergência (2D e 3D)."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.objects.prumada import andares_do_texto
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import alinhamento, pavimentos
from freecad.Circuits.services import prumadas as servico
from freecad.Circuits.UI.dialogs.ComponentInserter import ComponentInsertionMode
from freecad.Circuits.UI.dialogs.prumada_dialog import PrumadaDialog

TITULO = "Prumadas verticais"


def _atuais(obj):
    nomes = ("Energia", "Dados", "Interfone", "IluminacaoEmergencia", "SecaoAlimentador", "CondutoresPorUnidade",
             "FormaEnergia", "PontosDados", "EletrodutoDados", "CabosInterfone", "EletrodutoInterfone",
             "CircuitosEmergencia", "SecaoEmergencia", "TipoEletroduto")
    return {nome: getattr(obj, nome) for nome in nomes if hasattr(obj, nome)}


def _resumo(obj):
    linhas = "\n".join(f"  {linha}" for linha in obj.Resumo[:12])
    mais = f"\n  ... e mais {len(obj.Resumo) - 12} trechos" if len(obj.Resumo) > 12 else ""
    return f"{TITULO}:\n{linhas}{mais}\n"


class ProjetoPrumadas:
    """Insere (ou edita, com a prumada selecionada) as prumadas verticais do edifício."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecionada = next((o for o in Gui.Selection.getSelection() if servico.eh_prumada(o)), None)
        if selecionada is not None:
            dialogo = PrumadaDialog(andares_do_texto(selecionada.Andares), _atuais(selecionada), editando=True)
            if not dialogo.exec_():
                return
            doc.openTransaction(TITULO)
            try:
                servico.atualizar(doc, selecionada, **dialogo.get_dados())
                doc.commitTransaction()
            except Exception:
                doc.abortTransaction()
                raise
            App.Console.PrintMessage(_resumo(selecionada))
            return
        andares = servico.andares_do_projeto(doc)
        if len(andares) < 2:
            QtWidgets.QMessageBox.information(
                None, TITULO, "Crie antes os pavimentos do edifício (Projeto ▾ > Pavimento ou os níveis do BIM): a "
                              "prumada vai do pavimento mais baixo aos de cima. Os andares e as unidades também podem "
                              "ser ajustados na tabela do formulário.")
        dialogo = PrumadaDialog(andares or [], editando=False)
        if not dialogo.exec_():
            return
        dados = dialogo.get_dados()
        if len(dados["Andares"]) < 2:
            QtWidgets.QMessageBox.warning(None, TITULO, "A prumada precisa de pelo menos dois andares na tabela.")
            return
        base = min(dados["Andares"], key=lambda a: a["cota"])
        pavimento = pavimentos.por_nome(doc, base["nome"]) or pavimentos.pavimento_para_insercao(doc)
        doc.openTransaction(TITULO)
        try:
            obj = servico.criar(doc, pavimento, **dados)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        App.Console.PrintMessage(_resumo(obj) + "Clique na planta no ponto do shaft (R gira).\n")

        def desenhar():
            servico.desenhar_2d(doc, obj)
            App.Console.PrintMessage("Prumadas: símbolos em cada pavimento e esquema vertical desenhados.\n")

        cota = pavimentos.elevacao(pavimento) if pavimento is not None else base["cota"]
        # não herda a trava nem a rotação de uma inserção de pontos em sequência
        ComponentInsertionMode._trava_da_sequencia = None
        ComponentInsertionMode._rotacao_da_sequencia = None
        ComponentInsertionMode(obj, ao_fixar=desenhar, cota=cota,
                               referencias=alinhamento.posicoes_dos_simbolos(doc, exceto=obj)).start()

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "prumadas.svg",
            "Prumadas verticais",
            "Projeta as prumadas de energia, dados e telefonia, interfone e iluminação de emergência pelo shaft: "
            "eletrodutos de cada trecho pela ocupação, caixas de passagem, símbolos em cada pavimento, esquema "
            "vertical e 3D. Com uma prumada selecionada, edita",
        )


Gui.addCommand("ProjetoPrumadas", ProjetoPrumadas())
