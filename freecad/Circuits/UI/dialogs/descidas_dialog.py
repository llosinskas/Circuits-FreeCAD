"""Tabela das subidas e descidas entre eletrodutos de alturas diferentes, para editar."""
from freecad.Circuits.qt import QtCore, QtWidgets

CURVAS = "Curvas de 90°"
CAIXA = "Caixa de passagem"
FORMAS = [CURVAS, CAIXA]
NA_CAIXA = "Até a caixa de"
COLUNAS = ["Pavimento", "Posição (m)", "Eletrodutos", "Ø", "Altura de cima (mm)", "Altura de baixo (mm)", "Ligação"]


class DescidasDialog(QtWidgets.QDialog):
    """Uma linha por descida: as alturas de cima e de baixo e a forma de ligação.

    Args:
        descidas: [(nome do pavimento, descida de ``core.pecas_eletroduto``)].
        ao_escolher: função chamada com o índice da linha clicada (seleciona os eletrodutos).
    """

    def __init__(self, descidas, ao_escolher=None):
        super().__init__()
        self.setWindowTitle("Subidas e descidas dos eletrodutos")
        self.setMinimumWidth(820)
        self._descidas = list(descidas)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(
            "Altura medida do piso do pavimento. Mudar a altura muda o eletroduto inteiro que chega nela.\n"
            "Curvas: o eletroduto de cima e o de baixo fazem curva de 90° na vertical. "
            "Caixa de passagem: cria uma caixa no ponto e os eletrodutos descem até ela.\n"
            "Até a caixa: o eletroduto desce (ou sobe) até a caixa do símbolo; mude a altura do eletroduto."))
        self.tabela = QtWidgets.QTableWidget(len(self._descidas), len(COLUNAS))
        self.tabela.setHorizontalHeaderLabels(COLUNAS)
        self._entradas = []
        for linha, (pav, d) in enumerate(self._descidas):
            textos = [pav or "-", f"{d['x'] / 1000:.2f}; {d['y'] / 1000:.2f}",
                      ", ".join(b["nome"] for b in d["bracos"]), f'{d["diametro"]}"']
            for coluna, texto in enumerate(textos):
                item = QtWidgets.QTableWidgetItem(texto)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)  # só leitura
                self.tabela.setItem(linha, coluna, item)
            cima, baixo = self._altura(d["ate"]), self._altura(d["de"])
            forma = QtWidgets.QComboBox()
            if d.get("caixa"):  # interligação com a caixa do símbolo: só a altura do eletroduto muda
                forma.addItems([f"{NA_CAIXA} {d['caixa']}"])
                forma.setEnabled(False)
                (baixo if d.get("lado") == "cima" else cima).setEnabled(False)
            else:
                forma.addItems(FORMAS)
            self.tabela.setCellWidget(linha, 4, cima)
            self.tabela.setCellWidget(linha, 5, baixo)
            self.tabela.setCellWidget(linha, 6, forma)
            self._entradas.append((cima, baixo, forma))
        self.tabela.resizeColumnsToContents()
        if ao_escolher is not None:
            self.tabela.cellClicked.connect(lambda linha, _: ao_escolher(linha))
        layout.addWidget(self.tabela)

        botoes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        botoes.button(QtWidgets.QDialogButtonBox.Ok).setText("Aplicar")
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)
        self.setLayout(layout)

    @staticmethod
    def _altura(valor):
        caixa = QtWidgets.QDoubleSpinBox()
        caixa.setRange(-2000.0, 20000.0)
        caixa.setDecimals(0)
        caixa.setSingleStep(50.0)
        caixa.setValue(float(valor))
        return caixa

    def get_dados(self):
        """[{indice, de, ate, forma}] só das linhas que mudaram."""
        mudancas = []
        for indice, ((_, d), (cima, baixo, forma)) in enumerate(zip(self._descidas, self._entradas)):
            de, ate, escolha = baixo.value(), cima.value(), forma.currentText()
            if d.get("caixa"):
                escolha = CURVAS  # a ligação com a caixa não muda
            if abs(de - d["de"]) > 0.5 or abs(ate - d["ate"]) > 0.5 or escolha != CURVAS:
                mudancas.append({"indice": indice, "de": de, "ate": ate, "forma": escolha})
        return mudancas
