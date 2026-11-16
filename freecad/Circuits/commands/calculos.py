"""Comandos de cálculos prediais: demanda, pressurização de escada e bomba de recalque."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.commands.gerar_unifilar import _escolher_quadro
from freecad.Circuits.core.functions.Predial import demanda, pressurizacao, recalque
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import circuitos
from freecad.Circuits.UI.dialogs.calculo_dialog import CalculoDialog
from freecad.Circuits.UI.dialogs.ComponentInserter import ComponentInsertionMode

# Rótulo da alimentação -> (tensão [V], fases)
ALIMENTACOES = {
    "Trifásico 380 V": (380, 3),
    "Trifásico 220 V": (220, 3),
    "Monofásico 220 V": (220, 2),
    "Monofásico 127 V": (127, 1),
}
TRIFASICAS = [rotulo for rotulo, (_, fases) in ALIMENTACOES.items() if fases == 3]
TEXTO_INSERIR = "Inserir motor na planta"


def _inserir_motor(descricao, motor):
    """Cria o ponto de força do motor e deixa o usuário posicioná-lo na planta."""
    if not documento_ou_aviso():
        return
    obj = circuitos.criar_ponto_motor(f"{descricao} {motor['motor_cv']:g} cv", motor)
    if obj:
        App.Console.PrintMessage("Motor criado. Clique na planta para posicionar e defina o circuito dele.\n")
        ComponentInsertionMode(obj, plano_z0=True).start()


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


class CalcPressurizacao:
    """Pré-dimensiona o ventilador de pressurização de escada."""

    CAMPOS = [
        {"chave": "numero_portas", "rotulo": "Portas da escada (pavimentos + descarga)", "valor": 12, "minimo": 1},
        {"chave": "portas_abertas", "rotulo": "Portas abertas ao mesmo tempo", "valor": 2},
        {"chave": "tipo_porta", "rotulo": "Tipo de porta", "valor": list(pressurizacao.AREA_FRESTA)},
        {"chave": "largura_porta", "rotulo": "Largura da porta", "valor": 0.9, "minimo": 0.5, "maximo": 3, "sufixo": "m"},
        {"chave": "altura_porta", "rotulo": "Altura da porta", "valor": 2.1, "minimo": 1.5, "maximo": 3, "sufixo": "m"},
        {"chave": "duto", "rotulo": "Duto de insuflamento", "valor": list(pressurizacao.ACRESCIMO_DUTO)},
        {
            "chave": "pressao_total_ventilador", "rotulo": "Pressão total do ventilador (escada + perdas)",
            "valor": 500.0, "minimo": 50, "maximo": 3000, "decimais": 0, "sufixo": "Pa",
        },
        {"chave": "alimentacao", "rotulo": "Alimentação do motor", "valor": TRIFASICAS},
    ]

    @staticmethod
    def _calcular(dados):
        dados = dict(dados)
        tensao, _ = ALIMENTACOES[dados.pop("alimentacao")]
        resultado = pressurizacao.dimensionar(tensao=tensao, **dados)
        return resultado, pressurizacao.relatorio(resultado)

    def Activated(self):
        dialog = CalculoDialog("Pressurização de escada", self.CAMPOS, self._calcular, TEXTO_INSERIR)
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

    CAMPOS = [
        {"chave": "populacao", "rotulo": "População atendida", "valor": 80, "minimo": 1, "maximo": 100000},
        {
            "chave": "consumo_por_pessoa", "rotulo": "Consumo por pessoa",
            "valor": recalque.CONSUMO_POR_PESSOA, "minimo": 1, "maximo": 1000, "decimais": 0, "sufixo": "L/dia",
        },
        {"chave": "altura_geometrica", "rotulo": "Altura geométrica (desnível)", "valor": 40.0, "maximo": 300, "sufixo": "m"},
        {
            "chave": "comprimento_tubulacao", "rotulo": "Comprimento da tubulação (sucção + recalque)",
            "valor": 60.0, "maximo": 2000, "sufixo": "m",
        },
        {
            "chave": "horas", "rotulo": "Funcionamento da bomba por dia",
            "valor": recalque.HORAS_FUNCIONAMENTO, "minimo": 0.5, "maximo": 24, "decimais": 1, "sufixo": "h",
        },
        {"chave": "material", "rotulo": "Material da tubulação", "valor": list(recalque.COEFICIENTE_HAZEN_WILLIAMS)},
        {
            "chave": "rendimento", "rotulo": "Rendimento da bomba",
            "valor": recalque.RENDIMENTO_BOMBA, "minimo": 0.1, "maximo": 1,
        },
        {"chave": "alimentacao", "rotulo": "Alimentação do motor", "valor": list(ALIMENTACOES)},
    ]

    @staticmethod
    def _calcular(dados):
        dados = dict(dados)
        tensao, fases = ALIMENTACOES[dados.pop("alimentacao")]
        resultado = recalque.dimensionar(tensao=tensao, fases=fases, **dados)
        return resultado, recalque.relatorio(resultado)

    def Activated(self):
        dialog = CalculoDialog("Bomba de recalque", self.CAMPOS, self._calcular, TEXTO_INSERIR)
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


Gui.addCommand("CalcDemanda", CalcDemanda())
Gui.addCommand("CalcPressurizacao", CalcPressurizacao())
Gui.addCommand("CalcRecalque", CalcRecalque())
