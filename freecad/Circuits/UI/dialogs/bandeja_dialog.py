"""Diálogo com o tipo, a seção e a altura das bandejas (eletrocalhas e leitos) selecionadas."""
from freecad.Circuits.core import bandejas as regras
from freecad.Circuits.qt import QtWidgets


class BandejaDialog(QtWidgets.QDialog):
    """
    Args:
        quantidade: número de linhas selecionadas.
        atual: valores que vêm preenchidos (``tipo``, ``largura``, ``aba``, ``altura`` em mm, ``tampa``).
    """

    def __init__(self, quantidade, atual=None):
        super().__init__()
        atual = atual or {}
        self.setWindowTitle("Bandeja ou leito")
        self.setMinimumWidth(360)
        layout = QtWidgets.QFormLayout()
        layout.addRow(QtWidgets.QLabel(f"{quantidade} linha(s) selecionada(s)"))

        self.tipo = QtWidgets.QComboBox()
        self._tipos = list(regras.TIPOS)
        self.tipo.addItems([regras.TIPOS[t] for t in self._tipos])
        self.tipo.setCurrentIndex(self._tipos.index(atual.get("tipo", regras.TIPO_PADRAO)))
        layout.addRow("Tipo:", self.tipo)

        self.largura = QtWidgets.QComboBox()
        self.largura.addItems([str(v) for v in regras.LARGURAS_MM])
        self.largura.setEditable(True)
        self.largura.setEditText(f"{float(atual.get('largura', regras.LARGURA_PADRAO_MM)):g}")
        self.largura.setToolTip("Largura interna da bandeja, em mm")
        layout.addRow("Largura [mm]:", self.largura)

        self.aba = QtWidgets.QComboBox()
        self.aba.addItems([str(v) for v in regras.ABAS_MM])
        self.aba.setEditable(True)
        self.aba.setEditText(f"{float(atual.get('aba', regras.ABA_PADRAO_MM)):g}")
        self.aba.setToolTip("Altura da lateral (aba), em mm")
        layout.addRow("Aba [mm]:", self.aba)

        self.altura = QtWidgets.QDoubleSpinBox()
        self.altura.setRange(0.0, 20.0)
        self.altura.setDecimals(2)
        self.altura.setSingleStep(0.1)
        self.altura.setValue(float(atual.get("altura", regras.ALTURA_PADRAO_MM)) / 1000.0)
        self.altura.setToolTip("Do piso do pavimento à base da bandeja, em metros")
        layout.addRow("Altura de instalação [m]:", self.altura)

        self.tampa = QtWidgets.QCheckBox("Com tampa")
        self.tampa.setChecked(bool(atual.get("tampa", False)))
        layout.addRow(self.tampa)

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

    @staticmethod
    def _numero(texto, padrao):
        try:
            valor = float(str(texto).replace(",", "."))
        except ValueError:
            return float(padrao)
        return valor if valor > 0 else float(padrao)

    def get_dados(self):
        """``tipo`` (chave de ``core.bandejas.TIPOS``), ``largura``, ``aba`` e ``altura`` em mm, ``tampa``."""
        return {
            "tipo": self._tipos[self.tipo.currentIndex()],
            "largura": self._numero(self.largura.currentText(), regras.LARGURA_PADRAO_MM),
            "aba": self._numero(self.aba.currentText(), regras.ABA_PADRAO_MM),
            "altura": round(self.altura.value() * 1000.0, 1),
            "tampa": self.tampa.isChecked(),
        }
