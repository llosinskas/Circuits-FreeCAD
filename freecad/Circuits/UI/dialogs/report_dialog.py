"""Diálogo de opções do relatório PDF."""
from freecad.Circuits.qt import QtWidgets


class ReportDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerar Relatório PDF")
        self.setMinimumWidth(350)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Selecione os itens a incluir no relatório:"))

        self.chk_calculos = self._opcao(layout, "Cálculos (Quadros, Demandas)")
        self.chk_diagramas = self._opcao(layout, "Diagramas Unifilares")
        self.chk_materiais = self._opcao(layout, "Quantitativo de Materiais")
        self.chk_cortes = self._opcao(layout, "Cortes (Vistas 3D)")

        form_layout = QtWidgets.QFormLayout()
        self.edit_projeto = QtWidgets.QLineEdit()
        self.edit_projeto.setPlaceholderText("Ex: Projeto Residencial X")
        form_layout.addRow("Nome do Projeto:", self.edit_projeto)

        self.edit_autor = QtWidgets.QLineEdit()
        self.edit_autor.setPlaceholderText("Seu nome / Engenheiro")
        form_layout.addRow("Autor:", self.edit_autor)
        layout.addLayout(form_layout)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_gerar = QtWidgets.QPushButton("Gerar Relatório PDF...")
        self.btn_gerar.clicked.connect(self.accept)
        self.btn_cancelar = QtWidgets.QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_gerar)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    @staticmethod
    def _opcao(layout, texto):
        caixa = QtWidgets.QCheckBox(texto)
        caixa.setChecked(True)
        layout.addWidget(caixa)
        return caixa

    def get_opcoes(self):
        return {
            "calculos": self.chk_calculos.isChecked(),
            "diagramas": self.chk_diagramas.isChecked(),
            "materiais": self.chk_materiais.isChecked(),
            "cortes": self.chk_cortes.isChecked(),
            "projeto": self.edit_projeto.text(),
            "autor": self.edit_autor.text(),
        }
