"""Comandos de cálculos prediais: demanda, gerador diesel, pressurização, bomba de recalque e luminotécnico."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.commands.gerar_unifilar import _escolher_quadro
from freecad.Circuits.core import formularios
from freecad.Circuits.core.functions.Predial import demanda, gerador, luminotecnico, pressurizacao, recalque
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import circuitos, pavimentos
from freecad.Circuits.services import gerador as servico_gerador
from freecad.Circuits.services import luminotecnico as servico_luminotecnico
from freecad.Circuits.UI.dialogs.calculo_dialog import CalculoDialog
from freecad.Circuits.UI.dialogs.ComponentInserter import ComponentInsertionMode

ALIMENTACOES = formularios.ALIMENTACOES
TEXTO_INSERIR = "Inserir motor na planta"


def _inserir_motor(descricao, motor):
    """Cria o ponto de força do motor e deixa o usuário posicioná-lo na planta."""
    if not documento_ou_aviso():
        return
    obj = circuitos.criar_ponto_motor(f"{descricao} {motor['motor_cv']:g} cv", motor)
    if obj:
        App.Console.PrintMessage("Motor criado. Clique na planta para posicionar e defina o circuito dele.\n")
        pavimento = pavimentos.pavimento_para_insercao(App.activeDocument())
        pavimentos.arquivar(App.activeDocument(), obj, pavimento)
        ComponentInsertionMode(obj, cota=pavimentos.cota_no_desenho(App.activeDocument(), obj, pavimento)).start()


class CalcDemanda:
    """Calcula a demanda de um quadro pelos pontos da planta e a grava na planilha."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        quadro = _escolher_quadro(doc, "Demanda do quadro")
        if quadro is None:
            return
        resultado = circuitos.calcular_demanda(doc, quadro)
        if resultado is None:
            texto = (
                "Nenhum ponto elétrico com circuito definido na planta.\n"
                "Insira os pontos e preencha a propriedade Circuito."
            )
        else:
            texto = f"Quadro {quadro.Label}\n\n{demanda.relatorio(resultado)}\n\nValores gravados na planilha do quadro."
        QtWidgets.QMessageBox.information(None, "Demanda do quadro", texto)

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "demanda.svg",
            "Demanda",
            "Calcula a demanda do quadro pelos pontos da planta e grava na planilha",
        )


class CalcGerador:
    """Dimensiona o gerador diesel, o disjuntor, os cabos e o tanque pelas cargas da planilha."""

    TITULO = "Gerador diesel"

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        folha = servico_gerador.planilha(doc)
        if folha is None:
            folha, quadros = servico_gerador.criar(doc)
            origem = (f"com os {quadros} quadros do projeto" if quadros
                      else "com cargas de exemplo (não há quadros no projeto)")
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(folha)
            QtWidgets.QMessageBox.information(
                None, self.TITULO,
                f"Criei a planilha \"{folha.Label}\" {origem}.\n\n"
                "Revise as cargas (uma por linha): tipo, potência, unidade (kW, kVA ou cv), fator de demanda, "
                "partida dos motores e se a carga vai no gerador (S/N). Depois clique de novo em Gerador.",
            )
            return
        try:
            cargas = servico_gerador.ler_cargas(folha)
        except ValueError as erro:
            QtWidgets.QMessageBox.warning(None, self.TITULO, str(erro))
            return

        def calcular(dados):
            resultado = gerador.dimensionar(cargas, **formularios.argumentos_gerador(dados))
            return resultado, gerador.relatorio(resultado)

        dialog = CalculoDialog(self.TITULO, formularios.GERADOR, calcular, "Gravar na planilha", "gerador")
        if dialog.exec_() and dialog.resultado:
            servico_gerador.gravar_resultado(folha, dialog.resultado)
            App.Console.PrintMessage(f"Gerador: {dialog.resultado['gerador_kva']} kVA, gravado em {folha.Label}.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "gerador.svg",
            "Gerador diesel",
            "Dimensiona o gerador diesel pelas cargas, demanda e diversidade: potência, disjuntor, cabos e tanque. "
            "Na primeira vez cria a planilha de cargas com os quadros do projeto",
        )


class CalcPressurizacao:
    """Pré-dimensiona o ventilador de pressurização de escada."""

    CAMPOS = formularios.PRESSURIZACAO

    @staticmethod
    def _calcular(dados):
        dados = dict(dados)
        tensao, _ = ALIMENTACOES[dados.pop("alimentacao")]
        resultado = pressurizacao.dimensionar(tensao=tensao, **dados)
        return resultado, pressurizacao.relatorio(resultado)

    def Activated(self):
        dialog = CalculoDialog("Pressurização de escada", self.CAMPOS, self._calcular, TEXTO_INSERIR, "pressurizacao")
        if dialog.exec_() and dialog.resultado:
            _inserir_motor("Ventilador de pressurização", dialog.resultado["motor"])

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "pressurizacao.svg",
            "Pressurização",
            "Pré-dimensiona o ventilador de pressurização de escada e o motor elétrico",
        )


class CalcRecalque:
    """Pré-dimensiona a bomba de recalque de água fria."""

    CAMPOS = formularios.RECALQUE

    @staticmethod
    def _calcular(dados):
        dados = dict(dados)
        tensao, fases = ALIMENTACOES[dados.pop("alimentacao")]
        resultado = recalque.dimensionar(tensao=tensao, fases=fases, **dados)
        return resultado, recalque.relatorio(resultado)

    def Activated(self):
        dialog = CalculoDialog("Bomba de recalque", self.CAMPOS, self._calcular, TEXTO_INSERIR, "recalque")
        if dialog.exec_() and dialog.resultado:
            _inserir_motor("Bomba de recalque", dialog.resultado["motor"])

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "bomba_recalque.svg",
            "Bomba de recalque",
            "Pré-dimensiona a bomba de recalque de água fria e o motor elétrico",
        )


class DistribuirLuminarias:
    """Calcula e distribui as luminárias dentro do retângulo selecionado na planta."""

    SIMBOLOS = formularios.SIMBOLOS_ILUMINACAO
    CAMPOS = formularios.LUMINOTECNICO

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecionado = servico_luminotecnico.ambiente_selecionado(Gui.Selection.getSelection())
        if selecionado is None:
            QtWidgets.QMessageBox.information(
                None,
                "Luminotécnico",
                "Desenhe um retângulo no contorno do ambiente (barra Desenho), selecione-o e clique de novo.",
            )
            return
        ambiente, x_min, y_min, comprimento, largura = selecionado

        def calcular(dados):
            iluminancia = luminotecnico.ILUMINANCIAS[dados["ambiente"]] or dados["iluminancia"]
            resultado = luminotecnico.dimensionar(
                comprimento, largura, iluminancia, dados["fluxo_luminaria"],
                pe_direito=dados["pe_direito"], plano_trabalho=dados["plano_trabalho"],
                suspensao=dados["suspensao"], fator_utilizacao_informado=dados["fator_utilizacao_informado"],
            )
            return resultado, luminotecnico.relatorio(resultado)

        dialog = CalculoDialog("Luminotécnico", self.CAMPOS, calcular, "Distribuir luminárias", "luminotecnico")
        if not dialog.exec_() or not dialog.resultado:
            return
        dados = dialog.get_dados()
        servico_luminotecnico.distribuir(
            doc, ambiente, x_min, y_min, dialog.resultado["posicoes"],
            self.SIMBOLOS[dados["simbolo"]], dados["potencia"], dados["circuito"],
        )

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "luminotecnico.svg",
            "Luminotécnico",
            "Calcula e distribui as luminárias dentro do retângulo selecionado, pelo método dos lúmens",
        )


Gui.addCommand("CalcDemanda", CalcDemanda())
Gui.addCommand("CalcGerador", CalcGerador())
Gui.addCommand("DistribuirLuminarias", DistribuirLuminarias())
Gui.addCommand("CalcPressurizacao", CalcPressurizacao())
Gui.addCommand("CalcRecalque", CalcRecalque())
