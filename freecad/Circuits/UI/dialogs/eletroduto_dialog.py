"""Diálogo com diâmetro, tipo, material, instalação e altura dos eletrodutos selecionados."""
from freecad.Circuits.core import pecas_eletroduto as regras
from freecad.Circuits.core.tables.eletrodutos import DIAMETROS_EXTERNOS
from freecad.Circuits.qt import QtWidgets


class EletrodutoDialog(QtWidgets.QDialog):
    """
    Args:
        quantidade: número de linhas selecionadas.
        atual: valores que vêm preenchidos (``diametro``, ``tipo``, ``material``,
            ``instalacao``, ``altura`` em mm).
    """

    def __init__(self, quantidade, atual=None):
        super().__init__()
        atual = atual or {}
        self.setWindowTitle("Eletroduto")
        self.setMinimumWidth(380)
        layout = QtWidgets.QFormLayout()
        layout.addRow(QtWidgets.QLabel(f"{quantidade} linha(s) selecionada(s)"))

        def combo(opcoes, valor):
            caixa = QtWidgets.QComboBox()
            caixa.addItems(list(opcoes))
            if valor in opcoes:
                caixa.setCurrentIndex(list(opcoes).index(valor))
            return caixa

        self.diametro = combo(list(DIAMETROS_EXTERNOS), atual.get("diametro", "3/4"))
        layout.addRow("Diâmetro [pol]:", self.diametro)
        self.tipo = combo(regras.TIPOS, atual.get("tipo", "Flexível"))
        self.tipo.setToolTip("Rígido: curvas pré-fabricadas, luvas e buchas. Flexível: dobra no lugar.")
        layout.addRow("Tipo:", self.tipo)
        self.material = combo(regras.MATERIAIS, atual.get("material", "PVC"))
        layout.addRow("Material:", self.material)
        self.instalacao = combo(regras.INSTALACOES, atual.get("instalacao", regras.TETO))
        self.instalacao.setToolTip("Piso: tracejado na planta. Aparente: conduletes nas derivações e abraçadeiras.")
        layout.addRow("Instalação:", self.instalacao)

        self.altura = QtWidgets.QDoubleSpinBox()
        self.altura.setRange(-2.0, 20.0)
        self.altura.setDecimals(2)
        self.altura.setSingleStep(0.1)
        self.altura.setToolTip("Do piso do pavimento ao eixo do eletroduto, em metros")
        self.altura.setValue(float(atual.get("altura", regras.ALTURA_PADRAO[self.instalacao.currentText()])) / 1000.0)
        self.instalacao.currentTextChanged.connect(
            lambda texto: self.altura.setValue(regras.ALTURA_PADRAO[texto] / 1000.0))
        layout.addRow("Altura [m]:", self.altura)

        botoes = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("Aplicar")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept)
        btn_cancelar = QtWidgets.QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancelar)
        layout.addRow(botoes)
        self.setLayout(layout)

    def get_dados(self):
        """``diametro``, ``tipo``, ``material``, ``instalacao`` e ``altura`` [mm]."""
        return {
            "diametro": self.diametro.currentText(), "tipo": self.tipo.currentText(),
            "material": self.material.currentText(), "instalacao": self.instalacao.currentText(),
            "altura": round(self.altura.value() * 1000.0, 1),
        }
