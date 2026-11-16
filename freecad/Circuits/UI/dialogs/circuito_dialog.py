"""Diálogo para definir o circuito e o quadro dos pontos selecionados."""
from freecad.Circuits.qt import QtWidgets

QUALQUER_QUADRO = "(qualquer quadro)"
MANTER_QUADRO = "(não alterar)"


class DefinirCircuitoDialog(QtWidgets.QDialog):
    """
    Args:
        quantidade: número de pontos que serão alterados.
        circuitos: circuitos já usados na planta.
        sugestao: circuito que vem preenchido.
        quadros: nomes dos quadros do documento.
    """

    def __init__(self, quantidade, circuitos, sugestao, quadros):
        super().__init__()
        self.setWindowTitle("Definir circuito")
        self.setMinimumWidth(340)

        layout = QtWidgets.QFormLayout()
        layout.addRow(QtWidgets.QLabel(f"{quantidade} ponto(s) selecionado(s)"))

        self.circuito = QtWidgets.QComboBox()
        self.circuito.setEditable(True)
        self.circuito.addItems(list(circuitos))
        self.circuito.setEditText(str(sugestao))
        layout.addRow("Circuito (escolha ou digite um novo):", self.circuito)

        self.quadro = QtWidgets.QComboBox()
        self.quadro.addItems([MANTER_QUADRO, QUALQUER_QUADRO] + list(quadros))
        layout.addRow("Quadro:", self.quadro)

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
        """``circuito`` (texto) e ``quadro``: None não altera, '' vale para qualquer quadro."""
        escolhido = self.quadro.currentText()
        quadro = None if escolhido == MANTER_QUADRO else "" if escolhido == QUALQUER_QUADRO else escolhido
        return {"circuito": self.circuito.currentText().strip(), "quadro": quadro}
