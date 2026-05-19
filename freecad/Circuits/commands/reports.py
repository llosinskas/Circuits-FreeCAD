import os 
import FreeCADGui as Gui
import FreeCAD as App
try:
    from PySide2 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError:
        from PySide import QtCore, QtGui
        QtWidgets = QtGui
import freecad.Circuits as WB

class ReportDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerar Relatório PDF")
        self.setMinimumWidth(350)
        
        layout = QtWidgets.QVBoxLayout()
        
        title = QtWidgets.QLabel("Selecione os itens a incluir no relatório:")
        layout.addWidget(title)
        
        self.chk_calculos = QtWidgets.QCheckBox("Cálculos (Quadros, Demandas)")
        self.chk_calculos.setChecked(True)
        layout.addWidget(self.chk_calculos)
        
        self.chk_diagramas = QtWidgets.QCheckBox("Diagramas Unifilares")
        self.chk_diagramas.setChecked(True)
        layout.addWidget(self.chk_diagramas)
        
        self.chk_materiais = QtWidgets.QCheckBox("Quantitativo de Materiais")
        self.chk_materiais.setChecked(True)
        layout.addWidget(self.chk_materiais)
        
        self.chk_cortes = QtWidgets.QCheckBox("Cortes (Vistas 3D)")
        self.chk_cortes.setChecked(True)
        layout.addWidget(self.chk_cortes)
        
        # Autor / Projeto
        form_layout = QtWidgets.QFormLayout()
        self.edit_projeto = QtWidgets.QLineEdit()
        self.edit_projeto.setPlaceholderText("Ex: Projeto Residencial X")
        form_layout.addRow("Nome do Projeto:", self.edit_projeto)
        
        self.edit_autor = QtWidgets.QLineEdit()
        self.edit_autor.setPlaceholderText("Seu nome / Engenheiro")
        form_layout.addRow("Autor:", self.edit_autor)
        layout.addLayout(form_layout)
        
        # Botões
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_gerar = QtWidgets.QPushButton("Gerar Relatório PDF...")
        self.btn_gerar.clicked.connect(self.accept)
        self.btn_cancelar = QtWidgets.QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_gerar)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
    def get_opcoes(self):
        return {
            "calculos": self.chk_calculos.isChecked(),
            "diagramas": self.chk_diagramas.isChecked(),
            "materiais": self.chk_materiais.isChecked(),
            "cortes": self.chk_cortes.isChecked(),
            "projeto": self.edit_projeto.text(),
            "autor": self.edit_autor.text()
        }


class GenerateReport:
    def Activated(self):
        # Verifica dependência do reportlab
        try:
            import reportlab
        except ImportError:
            QtWidgets.QMessageBox.critical(
                None, 
                "Dependência não encontrada", 
                "A biblioteca 'reportlab' é necessária para gerar relatórios em PDF.\n"
                "Por favor, instale-a rodando:\n\npip install reportlab\n\n"
                "No seu console do FreeCAD ou no ambiente Python configurado."
            )
            return

        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento aberto.")
            return
            
        dialog = ReportDialog()
        if dialog.exec_():
            opcoes = dialog.get_opcoes()
            
            # Pergunta onde salvar o arquivo
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                None, "Salvar Relatório PDF", "Relatorio_Projeto.pdf", "PDF Files (*.pdf)"
            )
            
            if file_path:
                # Importa o gerador e passa as opções
                from freecad.Circuits.core.pdf_generator import PDFGenerator
                generator = PDFGenerator(doc, file_path, opcoes)
                try:
                    generator.generate()
                    QtWidgets.QMessageBox.information(None, "Sucesso", f"Relatório gerado em:\n{file_path}")
                except Exception as e:
                    QtWidgets.QMessageBox.critical(None, "Erro", f"Ocorreu um erro ao gerar o PDF:\n{e}")

    def IsActive(self):
        return True

    def GetResources(self):
        return {
            'Pixmap': os.path.join(WB.ICON_PATH, 'gerarPDF.svg'), 
            'MenuText': 'Gerar Relatório PDF...', 
            'ToolTip': 'Configurar e exportar relatório técnico do projeto em PDF'
        }

Gui.addCommand("GenerateReport", GenerateReport())