"""Prévia dos pontos automáticos por ambiente: tipo, quantidades da NBR 5410 e o que gerar."""
from freecad.Circuits.core import ambientes as regras
from freecad.Circuits.qt import QtCore, QtWidgets

COLUNAS = ["Gerar", "Ambiente", "Tipo", "Área (m²)", "Perímetro (m)", "Portas", "Tomadas (TUG)", "Potência TUG",
           "Iluminação"]


class PontosAutoDialog(QtWidgets.QDialog):
    """Uma linha por ambiente; mudar o tipo refaz a previsão da linha.

    Args:
        ambientes: [(nome, tipo, área m², perímetro m)].
        prever: função (índice, tipo) -> plano de ``core.ambientes.posicoes``.
    """

    def __init__(self, ambientes, prever):
        super().__init__()
        self.setWindowTitle("Pontos automáticos")
        self.setMinimumWidth(900)
        self._prever = prever
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(
            "Previsão mínima da NBR 5410 (9.5.2). Confira o tipo de cada ambiente: ele define quantas tomadas "
            "e a potência.\nAs tomadas ficam pelo perímetro, fora das portas e dos cantos; o interruptor, ao lado "
            "da porta; a luz, no centro. Os pontos gerados antes para o ambiente são substituídos."))
        self.tabela = QtWidgets.QTableWidget(len(ambientes), len(COLUNAS))
        self.tabela.setHorizontalHeaderLabels(COLUNAS)
        self._linhas = []
        for linha, (nome, tipo, area, perimetro) in enumerate(ambientes):
            marcar = QtWidgets.QCheckBox()
            marcar.setChecked(True)
            self.tabela.setCellWidget(linha, 0, marcar)
            self._texto(linha, 1, nome)
            combo = QtWidgets.QComboBox()
            combo.addItems(list(regras.TIPOS))
            combo.setCurrentIndex(list(regras.TIPOS).index(tipo) if tipo in regras.TIPOS else 0)
            combo.currentIndexChanged.connect(lambda *_, l=linha: self._atualizar(l))
            self.tabela.setCellWidget(linha, 2, combo)
            self._texto(linha, 3, f"{area:.2f}".replace(".", ","))
            self._texto(linha, 4, f"{perimetro:.2f}".replace(".", ","))
            self._linhas.append((marcar, combo))
            self._atualizar(linha)
        self.tabela.resizeColumnsToContents()
        layout.addWidget(self.tabela)
        self.avisos = QtWidgets.QLabel("")
        self.avisos.setWordWrap(True)
        layout.addWidget(self.avisos)
        botoes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        botoes.button(QtWidgets.QDialogButtonBox.Ok).setText("Gerar pontos")
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)
        self.setLayout(layout)
        self._mostrar_avisos()

    def _texto(self, linha, coluna, texto):
        item = QtWidgets.QTableWidgetItem(str(texto))
        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
        self.tabela.setItem(linha, coluna, item)

    def _atualizar(self, linha):
        tipo = self._linhas[linha][1].currentText() if linha < len(self._linhas) else None
        plano = self._prever(linha, tipo)
        previsao = plano["previsao"]
        potencias = previsao["potencias"]
        resumo = ", ".join(f"{potencias.count(p)} × {p:.0f} VA" for p in sorted(set(potencias), reverse=True))
        self._texto(linha, 5, plano["portas"])
        self._texto(linha, 6, previsao["tugs"])
        self._texto(linha, 7, resumo)
        self._texto(linha, 8, f"{previsao['iluminacao_va']:.0f} VA")
        if hasattr(self, "avisos"):
            self._mostrar_avisos()

    def _mostrar_avisos(self):
        textos = []
        for linha in range(self.tabela.rowCount()):
            plano = self._prever(linha, self._linhas[linha][1].currentText())
            textos += [f"{self.tabela.item(linha, 1).text()}: {a}" for a in plano["avisos"]]
        self.avisos.setText("\n".join(textos))

    def get_dados(self):
        """[(índice do ambiente, tipo)] das linhas marcadas."""
        return [(linha, combo.currentText()) for linha, (marcar, combo) in enumerate(self._linhas)
                if marcar.isChecked()]
