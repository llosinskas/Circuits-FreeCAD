"""Diálogo para escolher, criar ou ajustar o pavimento ativo."""
from freecad.Circuits.qt import QtWidgets

MM_POR_M = 1000.0


class DefinirPavimentoDialog(QtWidgets.QDialog):
    """
    Args:
        pavimentos: lista de dicionários com ``nome``, ``elevacao_mm``, ``altura_mm``, ``ativo`` e ``bim``
            (níveis do BIM têm cota e altura só para leitura).
        sugestao: dicionário com ``nome``, ``elevacao_mm`` e ``altura_mm`` do próximo pavimento.
        titulo: título da janela.
        selecionar_sugestao: abre com o pavimento novo sugerido, em vez do ativo.
    """

    def __init__(self, pavimentos, sugestao, titulo="Pavimento", selecionar_sugestao=False):
        super().__init__()
        self.setWindowTitle(titulo)
        self.setMinimumWidth(380)
        self._valores = {p["nome"]: p for p in pavimentos}
        self._valores.setdefault(sugestao["nome"], sugestao)

        layout = QtWidgets.QFormLayout()
        aviso = QtWidgets.QLabel(
            "Os próximos símbolos entram neste pavimento.\n"
            "Escolha um existente ou digite um nome novo."
        )
        layout.addRow(aviso)

        self.nota = QtWidgets.QLabel("Nível do BIM: a cota e a altura vêm do BIM e não mudam aqui.")
        self.nota.setVisible(False)
        layout.addRow(self.nota)

        self.nome = QtWidgets.QComboBox()
        self.nome.setEditable(True)
        self.nome.addItems(list(self._valores))
        layout.addRow("Pavimento:", self.nome)

        self.elevacao = QtWidgets.QDoubleSpinBox()
        self.elevacao.setRange(-500.0, 5000.0)
        self.elevacao.setDecimals(2)
        self.elevacao.setSuffix(" m")
        self.elevacao.setToolTip("Cota do piso, a partir do térreo. Soma-se à altura de montagem nas caixas 3D.")
        layout.addRow("Cota do piso:", self.elevacao)

        self.altura = QtWidgets.QDoubleSpinBox()
        self.altura.setRange(1.0, 20.0)
        self.altura.setDecimals(2)
        self.altura.setSuffix(" m")
        self.altura.setToolTip("Distância de um piso ao seguinte. Serve para sugerir a cota do próximo pavimento.")
        layout.addRow("Altura de piso a piso:", self.altura)

        botoes = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("Usar este pavimento")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept)
        btn_cancelar = QtWidgets.QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancelar)
        layout.addRow(botoes)
        self.setLayout(layout)

        ativo = next((p["nome"] for p in pavimentos if p["ativo"]), sugestao["nome"])
        if selecionar_sugestao:
            ativo = sugestao["nome"]
        self.nome.setCurrentIndex(max(0, self.nome.findText(ativo)))
        self._preencher(ativo)
        self.nome.currentTextChanged.connect(self._preencher)

    def _preencher(self, nome):
        """Escolher um pavimento da lista traz a cota e a altura dele; um nome novo mantém os valores."""
        dados = self._valores.get(nome)
        if dados is not None:
            self.elevacao.setValue(dados["elevacao_mm"] / MM_POR_M)
            self.altura.setValue(dados["altura_mm"] / MM_POR_M)
        bim = bool(dados and dados.get("bim"))
        self.elevacao.setEnabled(not bim)
        self.altura.setEnabled(not bim)
        self.nota.setVisible(bim)

    def get_dados(self):
        return {
            "nome": self.nome.currentText().strip(),
            "elevacao_mm": self.elevacao.value() * MM_POR_M,
            "altura_mm": self.altura.value() * MM_POR_M,
        }
