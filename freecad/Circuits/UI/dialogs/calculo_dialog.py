"""Diálogo genérico de cálculo: formulário, botão Calcular e resultado em texto."""
from freecad.Circuits.qt import QtWidgets


class CalculoDialog(QtWidgets.QDialog):
    """Monta o formulário a partir de uma lista de campos e mostra o resultado.

    Args:
        titulo: título da janela.
        campos: lista de dicionários com ``chave``, ``rotulo`` e ``valor``.
            ``valor`` inteiro vira caixa de número inteiro, decimal vira caixa
            de número decimal e lista vira caixa de escolha. Opcionais:
            ``minimo``, ``maximo``, ``decimais`` e ``sufixo``.
        calcular: função que recebe o dicionário de valores e devolve
            (resultado, texto). Pode lançar ``ValueError`` com a mensagem ao usuário.
        texto_aceitar: rótulo do botão que fecha o diálogo aceitando o resultado;
            vazio esconde o botão.
    """

    def __init__(self, titulo, campos, calcular, texto_aceitar=""):
        super().__init__()
        self.setWindowTitle(titulo)
        self.setMinimumWidth(520)
        self._calcular = calcular
        self._entradas = {}
        self.resultado = None

        layout = QtWidgets.QVBoxLayout()
        formulario = QtWidgets.QFormLayout()
        for campo in campos:
            entrada = self._criar_entrada(campo)
            self._entradas[campo["chave"]] = entrada
            formulario.addRow(campo["rotulo"], entrada)
        layout.addLayout(formulario)

        self.saida = QtWidgets.QPlainTextEdit()
        self.saida.setReadOnly(True)
        self.saida.setMinimumHeight(230)
        self.saida.setPlaceholderText("Preencha os dados e clique em Calcular.")
        layout.addWidget(self.saida)

        botoes = QtWidgets.QHBoxLayout()
        self.btn_calcular = QtWidgets.QPushButton("Calcular")
        self.btn_calcular.setDefault(True)
        self.btn_calcular.clicked.connect(self.calcular)
        botoes.addWidget(self.btn_calcular)

        self.btn_aceitar = QtWidgets.QPushButton(texto_aceitar)
        self.btn_aceitar.setEnabled(False)
        self.btn_aceitar.setVisible(bool(texto_aceitar))
        self.btn_aceitar.clicked.connect(self.accept)
        botoes.addWidget(self.btn_aceitar)

        btn_fechar = QtWidgets.QPushButton("Fechar")
        btn_fechar.clicked.connect(self.reject)
        botoes.addWidget(btn_fechar)
        layout.addLayout(botoes)
        self.setLayout(layout)

    @staticmethod
    def _criar_entrada(campo):
        valor = campo["valor"]
        if isinstance(valor, (list, tuple)):
            entrada = QtWidgets.QComboBox()
            entrada.addItems([str(item) for item in valor])
            return entrada
        if isinstance(valor, int):
            entrada = QtWidgets.QSpinBox()
        else:
            entrada = QtWidgets.QDoubleSpinBox()
            entrada.setDecimals(campo.get("decimais", 2))
        entrada.setRange(campo.get("minimo", 0), campo.get("maximo", 1000000))
        entrada.setValue(valor)
        if campo.get("sufixo"):
            entrada.setSuffix(" " + campo["sufixo"])
        return entrada

    def get_dados(self):
        """Valores do formulário, por chave do campo."""
        return {
            chave: entrada.currentText() if isinstance(entrada, QtWidgets.QComboBox) else entrada.value()
            for chave, entrada in self._entradas.items()
        }

    def calcular(self):
        try:
            self.resultado, texto = self._calcular(self.get_dados())
        except ValueError as erro:
            self.resultado = None
            texto = f"Não foi possível calcular: {erro}"
        self.saida.setPlainText(texto)
        self.btn_aceitar.setEnabled(self.resultado is not None)
