"""Diálogos de dados do quadro de distribuição e dos circuitos."""
from freecad.Circuits.qt import QtCore, QtWidgets


class CriarQuadro(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dados do Quadro de distribuição")

        layout = QtWidgets.QFormLayout()
        title1 = QtWidgets.QLabel("Informação do quadro")
        title1.setAlignment(QtCore.Qt.AlignCenter)
        layout.addRow(title1)

        self.identificacao = QtWidgets.QLineEdit()
        self.identificacao.setPlaceholderText("Ex. QGBT, QD, QD01, QF01,...")
        layout.addRow("Identificação do quadro", self.identificacao)

        self.bitola = QtWidgets.QLineEdit()
        self.bitola.setPlaceholderText("Ex. 16, 25, 35,...")
        layout.addRow("Bitola do cabo de entrada [mm²]", self.bitola)

        self.origem = QtWidgets.QLineEdit()
        self.origem.setPlaceholderText("Ex. Padrão, QD1, QGBT, ...")
        layout.addRow("Origem", self.origem)

        self.curto = QtWidgets.QLineEdit()
        self.curto.setPlaceholderText("Ex. 3, 5, 6, ...")
        layout.addRow("Nível de curto circuito [kA]", self.curto)

        self.descricao = QtWidgets.QLineEdit()
        self.descricao.setPlaceholderText("Ex. Quadro de iluminação + tomadas, quadro de automação da iluminação")
        layout.addRow("Descrição do quadro", self.descricao)

        self.tensao = QtWidgets.QLineEdit()
        self.tensao.setPlaceholderText("Ex. 127, 220, 380")
        layout.addRow("Tensão de fase do quadro [V]", self.tensao)

        self.n_fases = QtWidgets.QComboBox()
        self.n_fases.addItems(["1", "2", "3"])
        self.n_fases.setPlaceholderText("Ex. 1,2,3")
        layout.addRow("Número de fases do quadro", self.n_fases)

        self.terra = QtWidgets.QCheckBox()
        layout.addRow("Tem terra no quadro?", self.terra)

        self.neutro = QtWidgets.QCheckBox()
        layout.addRow("Tem neutro no quadro", self.neutro)

        title2 = QtWidgets.QLabel("Disjuntor geral do quadro")
        title2.setAlignment(QtCore.Qt.AlignCenter)
        layout.addRow(title2)

        self.curva_disjuntor = QtWidgets.QComboBox()
        self.curva_disjuntor.addItems(["B", "C", "D"])
        layout.addRow("Curva do disjuntor geral", self.curva_disjuntor)

        self.corrente_nominal_disjuntor = QtWidgets.QLineEdit()
        self.corrente_nominal_disjuntor.setPlaceholderText("Ex. 10, 16, 20,...")
        layout.addRow("Corrente nominal do disjuntor geral do quadro [A]", self.corrente_nominal_disjuntor)

        self.corrente_cc_disjuntor = QtWidgets.QLineEdit()
        self.corrente_cc_disjuntor.setPlaceholderText("Ex. 3, 4, 16,...")
        layout.addRow("Corrente de curto circuito do disjuntor [kA]", self.corrente_cc_disjuntor)

        self.pot_quadro = QtWidgets.QLineEdit()
        self.pot_quadro.setPlaceholderText("Ex. 3,5,10,100,...")
        layout.addRow("Potência instalada do quadro [kW]", self.pot_quadro)

        self.demanda = QtWidgets.QLineEdit()
        self.demanda.setPlaceholderText("Ex. 3,4, 5, 100,...")
        layout.addRow("Demanda do quadro de distribuição [kW]", self.demanda)

        self.material = QtWidgets.QLineEdit()
        self.material.setPlaceholderText("Ex. Aço, ABS, Aço inox,...")
        layout.addRow("Material do quadro", self.material)

        self.dps = QtWidgets.QCheckBox()
        layout.addRow("Tem DPS", self.dps)

        self.classe_DPS = QtWidgets.QLineEdit()
        self.classe_DPS.setPlaceholderText("Ex. I, II, III, IV")
        layout.addRow("Classe do DPS", self.classe_DPS)

        self.tensao_DPS = QtWidgets.QLineEdit()
        self.tensao_DPS.setPlaceholderText("Ex. 175, 275,...")
        layout.addRow("Tensão de operação do DPS [V]", self.tensao_DPS)

        self.corrente_DPS = QtWidgets.QLineEdit()
        self.corrente_DPS.setPlaceholderText("Ex. 3, 4, 5, ...")
        layout.addRow("Corrente do DPS [kA]", self.corrente_DPS)

        self.submit_btn = QtWidgets.QPushButton("Criar")
        self.submit_btn.clicked.connect(self.accept)

        self.setLayout(layout)
        layout.addWidget(self.submit_btn)

    def get_dados(self):
        """Valores na ordem das colunas de ``core.planilha.CABECALHO_QUADRO``."""
        return {
            "indentificacao": self.identificacao.text(),
            "bitola_entrada": self.bitola.text(),
            "origem": self.origem.text(),
            "curto_circuito": self.curto.text(),
            "descricao": self.descricao.text(),
            "tensao": self.tensao.text(),
            "n_fases": self.n_fases.currentText(),
            "terra": self.terra.isChecked(),
            "neutro": self.neutro.isChecked(),
            "curva_disjuntor": self.curva_disjuntor.currentText(),
            "corrente_nominal_disjuntor": self.corrente_nominal_disjuntor.text(),
            "corrente_cc_disjuntor": self.corrente_cc_disjuntor.text(),
            "pot_quadro": self.pot_quadro.text(),
            "demanda": self.demanda.text(),
            "material": self.material.text(),
            "dps": self.dps.isChecked(),
            "classe_DPS": self.classe_DPS.text(),
            "tensao_DPS": self.tensao_DPS.text(),
            "corrente_DPS": self.corrente_DPS.text(),
        }


class Add_circuito(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Adicionar Circuito")
        self.setMinimumWidth(350)

        layout = QtWidgets.QFormLayout()

        self.n_circuito = QtWidgets.QLineEdit()
        layout.addRow("Identificação (Nº):", self.n_circuito)

        self.destino = QtWidgets.QLineEdit()
        layout.addRow("Destino do Circuito:", self.destino)

        self.potencia = QtWidgets.QLineEdit()
        layout.addRow("Potência [W ou kW]:", self.potencia)

        self.tensao = QtWidgets.QComboBox()
        self.tensao.addItems(["127", "220", "380"])
        layout.addRow("Tensão [V]:", self.tensao)

        self.corrente = QtWidgets.QLineEdit()
        layout.addRow("Corrente de Projeto [A]:", self.corrente)

        self.cabo = QtWidgets.QComboBox()
        self.cabo.addItems(["1.5", "2.5", "4", "6", "10", "16", "25", "35", "50", "70", "95", "120"])
        layout.addRow("Bitola do Cabo [mm²]:", self.cabo)

        self.disjuntor = QtWidgets.QComboBox()
        self.disjuntor.addItems(["10", "16", "20", "25", "32", "40", "50", "63", "80", "100", "125"])
        layout.addRow("Corrente do Disjuntor [A]:", self.disjuntor)

        self.curva = QtWidgets.QComboBox()
        self.curva.addItems(["B", "C", "D"])
        layout.addRow("Curva do Disjuntor:", self.curva)

        fases_layout = QtWidgets.QHBoxLayout()
        self.fase_r = QtWidgets.QCheckBox("R")
        self.fase_s = QtWidgets.QCheckBox("S")
        self.fase_t = QtWidgets.QCheckBox("T")
        self.fase_r.setChecked(True)
        fases_layout.addWidget(self.fase_r)
        fases_layout.addWidget(self.fase_s)
        fases_layout.addWidget(self.fase_t)
        layout.addRow("Fases:", fases_layout)

        self.neutro = QtWidgets.QCheckBox("Possui Neutro")
        self.neutro.setChecked(True)
        layout.addRow("", self.neutro)

        self.terra = QtWidgets.QCheckBox("Possui Terra")
        self.terra.setChecked(True)
        layout.addRow("", self.terra)

        self.dr = QtWidgets.QCheckBox("Possui Proteção DR")
        layout.addRow("", self.dr)

        self.corrente_dr = QtWidgets.QLineEdit()
        self.corrente_dr.setPlaceholderText("Ex: 30mA")
        layout.addRow("Corrente do DR:", self.corrente_dr)

        self.submit_btn = QtWidgets.QPushButton("Adicionar Circuito")
        self.submit_btn.clicked.connect(self.accept)
        layout.addRow("", self.submit_btn)

        self.setLayout(layout)

    def get_dados(self):
        return {
            "N_circuito": self.n_circuito.text(),
            "Destino": self.destino.text(),
            "Potencia": self.potencia.text(),
            "Tensao": self.tensao.currentText(),
            "Corrente": self.corrente.text(),
            "Cabo": self.cabo.currentText(),
            "Disjuntor": self.disjuntor.currentText(),
            "Curva": self.curva.currentText(),
            "Fase_R": str(self.fase_r.isChecked()),
            "Fase_S": str(self.fase_s.isChecked()),
            "Fase_T": str(self.fase_t.isChecked()),
            "Neutro": str(self.neutro.isChecked()),
            "Terra": str(self.terra.isChecked()),
            "DR": str(self.dr.isChecked()),
            "Corrente_DR": self.corrente_dr.text(),
        }
