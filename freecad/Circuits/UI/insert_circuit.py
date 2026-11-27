"""Diálogo para inserir um circuito na planilha geral de circuitos do projeto."""
import math

from freecad.Circuits.core import nbr5410
from freecad.Circuits.qt import QtWidgets


class InsertCircuit(QtWidgets.QDialog):
    """Formulário de entrada de circuito para a planilha geral de circuitos."""

    def __init__(self, quadros=None):
        super().__init__()
        self.setWindowTitle("Inserir circuito na planilha")
        self.setMinimumWidth(420)

        layout = QtWidgets.QFormLayout()

        self.circuito_id = QtWidgets.QLineEdit()
        self.circuito_id.setPlaceholderText("Ex.: 1, C1")
        layout.addRow("Identificação (ID):", self.circuito_id)

        self.origem = QtWidgets.QComboBox()
        self.origem.setEditable(True)
        opcoes_origem = list(quadros or []) or ["QGBT", "QD01"]
        self.origem.addItems(opcoes_origem)
        layout.addRow("Origem (quadro):", self.origem)

        self.destino = QtWidgets.QLineEdit()
        self.destino.setPlaceholderText("Ex.: Tomadas sala, Iluminação")
        layout.addRow("Destino:", self.destino)

        self.potencia_kw = QtWidgets.QDoubleSpinBox()
        self.potencia_kw.setRange(0.05, 500.0)
        self.potencia_kw.setDecimals(2)
        self.potencia_kw.setValue(1.5)
        self.potencia_kw.setSuffix(" kW")
        layout.addRow("Potência ativa:", self.potencia_kw)

        self.tensao = QtWidgets.QComboBox()
        self.tensao.setEditable(True)
        self.tensao.addItems(["127", "220", "380", "440"])
        self.tensao.setCurrentText("220")
        layout.addRow("Tensão [V]:", self.tensao)

        self.fp = QtWidgets.QDoubleSpinBox()
        self.fp.setRange(0.50, 1.00)
        self.fp.setDecimals(2)
        self.fp.setSingleStep(0.05)
        self.fp.setValue(0.92)
        layout.addRow("Fator de potência:", self.fp)

        self.comprimento = QtWidgets.QDoubleSpinBox()
        self.comprimento.setRange(1.0, 500.0)
        self.comprimento.setDecimals(1)
        self.comprimento.setValue(15.0)
        self.comprimento.setSuffix(" m")
        layout.addRow("Comprimento:", self.comprimento)

        self.metodo = QtWidgets.QComboBox()
        self.metodo.addItems(["B1", "B2", "C", "D", "E", "F"])
        layout.addRow("Método de instalação:", self.metodo)

        self.cabo = QtWidgets.QComboBox()
        self.cabo.addItems(["1.5", "2.5", "4", "6", "10", "16", "25", "35", "50", "70", "95", "120"])
        self.cabo.setCurrentText("2.5")
        layout.addRow("Seção do cabo [mm²]:", self.cabo)

        self.disjuntor = QtWidgets.QComboBox()
        self.disjuntor.addItems(["10", "16", "20", "25", "32", "40", "50", "63", "80", "100", "125"])
        self.disjuntor.setCurrentText("16")
        layout.addRow("Disjuntor [A]:", self.disjuntor)

        self.curva = QtWidgets.QComboBox()
        self.curva.addItems(["B", "C", "D"])
        self.curva.setCurrentText("C")
        layout.addRow("Curva do disjuntor:", self.curva)

        fases_box = QtWidgets.QHBoxLayout()
        self.fase_r = QtWidgets.QCheckBox("R")
        self.fase_s = QtWidgets.QCheckBox("S")
        self.fase_t = QtWidgets.QCheckBox("T")
        self.fase_r.setChecked(True)
        fases_box.addWidget(self.fase_r)
        fases_box.addWidget(self.fase_s)
        fases_box.addWidget(self.fase_t)
        layout.addRow("Fases:", fases_box)

        botoes = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("Gravar na planilha")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QtWidgets.QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancel)
        layout.addRow(botoes)
        self.setLayout(layout)

    def get_dados(self):
        p_kw = float(self.potencia_kw.value())
        fp = float(self.fp.value()) or 1.0
        try:
            tensao = float(self.tensao.currentText().replace(",", "."))
        except ValueError:
            tensao = 220.0
        n_fases = sum(1 for cb in (self.fase_r, self.fase_s, self.fase_t) if cb.isChecked()) or 1
        s_kva = p_kw / fp
        divisor = (math.sqrt(3) * tensao) if n_fases == 3 else tensao
        corrente = (s_kva * 1000.0) / divisor if divisor > 0 else 0.0
        secao = float(self.cabo.currentText())
        comp = float(self.comprimento.value())
        queda = nbr5410.queda_tensao(corrente, comp, secao, tensao, n_fases, fator_potencia=fp)
        return {
            "ID": self.circuito_id.text().strip() or "1",
            "Origem": self.origem.currentText().strip(),
            "Destino": self.destino.text().strip(),
            "Potencia_kW": f"{p_kw:.2f}",
            "Tensao": f"{tensao:g}",
            "FatorPotencia": f"{fp:.2f}",
            "PotenciaAparente_kVA": f"{s_kva:.2f}",
            "Corrente": f"{corrente:.2f}",
            "Comprimento": f"{comp:.1f}",
            "Queda": f"{queda:.2f}",
            "Cabo": self.cabo.currentText(),
            "Metodo": self.metodo.currentText(),
            "FCA": "1.0",
            "FCT": "1.0",
            "Disjuntor": self.disjuntor.currentText(),
            "Curva": self.curva.currentText(),
            "Fase_R": self.fase_r.isChecked(),
            "Fase_S": self.fase_s.isChecked(),
            "Fase_T": self.fase_t.isChecked(),
        }
