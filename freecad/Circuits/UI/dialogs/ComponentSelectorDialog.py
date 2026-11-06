"""
Diálogo reutilizável para seleção de componentes FreeCAD.
Permite buscar, visualizar e selecionar arquivos FCStd de uma pasta específica.
"""

import os
import zipfile
from pathlib import Path
from typing import Optional

from freecad.Circuits.qt import QtCore, QtGui, QtWidgets, Qt, Signal, Slot

import FreeCAD as App
import FreeCADGui as Gui


class ComponentSelectorDialog(QtWidgets.QDialog):
    """Diálogo para seleção de componentes com preview de thumbnails e navegação de pastas.
    
    Reutilizável para diferentes pastas de componentes.
    
    Attributes:
        components_path: Caminho da pasta raiz contendo os componentes
        selected_component: Arquivo selecionado (retorna None se cancelado)
    """
    
    # Signal emitido quando um componente é selecionado
    component_selected = Signal(str)  # emite o caminho do arquivo
    
    def __init__(self, components_path: str, title: str = "Selecionador de Componentes", parent=None):
        """Inicializa o diálogo."""
        super().__init__(parent or Gui.getMainWindow())
        
        self.components_path = components_path
        self.current_folder = components_path
        self.selected_component: Optional[str] = None
        
        self.initUI(title)
        self.populate_tree()
        self.load_components(self.current_folder)
        
    def initUI(self, title: str):
        """Cria a interface do diálogo."""
        self.setWindowTitle(title)
        self.resize(1000, 650)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        
        # Estilo Global do Diálogo
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e24;
            }
            QLabel {
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit {
                background-color: #2b2b36;
                color: #ffffff;
                border: 1px solid #454555;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
                background-color: #32323e;
            }
            QScrollArea {
                border: 1px solid #33333d;
                border-radius: 8px;
                background-color: #1a1a1f;
            }
            QWidget#componentsContainer {
                background-color: #1a1a1f;
            }
            QTreeWidget {
                background-color: #1a1a1f;
                border: 1px solid #33333d;
                border-radius: 8px;
                color: #e0e0e0;
                font-size: 13px;
                padding: 5px;
            }
            QTreeWidget::item {
                padding: 6px;
                border-radius: 4px;
                margin: 2px 0px;
            }
            QTreeWidget::item:hover {
                background-color: #2b2b36;
            }
            QTreeWidget::item:selected {
                background-color: #007acc;
                color: white;
            }
            QPushButton {
                background-color: #3a3a4a;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a4a5a;
            }
            QPushButton:pressed {
                background-color: #2a2a3a;
            }
            QPushButton#btnOk {
                background-color: #007acc;
            }
            QPushButton#btnOk:hover {
                background-color: #0098ff;
            }
            QPushButton#btnOk:disabled {
                background-color: #2b2b36;
                color: #666;
            }
            QScrollBar:vertical {
                border: none;
                background: #1e1e24;
                width: 12px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #454555;
                min-height: 20px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #555565;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Layout principal
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header (Título + Busca)
        header_layout = QtWidgets.QHBoxLayout()
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar componentes...")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.search_input)
        main_layout.addLayout(header_layout)
        
        # Corpo: Tree lateral + Grid de cards
        body_layout = QtWidgets.QHBoxLayout()
        body_layout.setSpacing(15)
        
        # Sidebar com pastas
        self.folder_tree = QtWidgets.QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setFixedWidth(220)
        self.folder_tree.setCursor(Qt.PointingHandCursor)
        self.folder_tree.itemClicked.connect(self.on_folder_selected)
        body_layout.addWidget(self.folder_tree)
        
        # Scroll Area com cards dos componentes
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.components_container = QtWidgets.QWidget()
        self.components_container.setObjectName("componentsContainer")
        
        # Usa um grid layout para permitir múltiplas linhas e colunas
        self.components_layout = QtWidgets.QGridLayout(self.components_container)
        self.components_layout.setSpacing(15)
        self.components_layout.setContentsMargins(15, 15, 15, 15)
        self.components_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        scroll.setWidget(self.components_container)
        body_layout.addWidget(scroll)
        
        main_layout.addLayout(body_layout)
        
        # Painel inferior (Info + Botões)
        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.setContentsMargins(0, 5, 0, 0)
        
        info_icon = QtWidgets.QLabel("📌")
        self.info_label = QtWidgets.QLabel("Nenhum componente selecionado")
        self.info_label.setStyleSheet("color: #888; font-style: italic; font-size: 13px;")
        
        bottom_layout.addWidget(info_icon)
        bottom_layout.addWidget(self.info_label)
        bottom_layout.addStretch()
        
        self.btn_cancel = QtWidgets.QPushButton("Cancelar")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QtWidgets.QPushButton("Inserir Componente")
        self.btn_ok.setObjectName("btnOk")
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_ok.setEnabled(False)
        
        bottom_layout.addWidget(self.btn_cancel)
        bottom_layout.addWidget(self.btn_ok)
        main_layout.addLayout(bottom_layout)
        
    def populate_tree(self):
        """Preenche a árvore lateral com a hierarquia de pastas."""
        self.folder_tree.clear()
        
        if not os.path.exists(self.components_path):
            return
            
        root_name = os.path.basename(os.path.normpath(self.components_path))
        if not root_name:
            root_name = "Biblioteca"
            
        root_item = QtWidgets.QTreeWidgetItem(self.folder_tree, [f"📂 {root_name}"])
        root_item.setData(0, Qt.UserRole, self.components_path)
        
        self._add_subfolders(self.components_path, root_item)
        
        root_item.setExpanded(True)
        self.folder_tree.setCurrentItem(root_item)
        
    def _add_subfolders(self, path: str, parent_item: QtWidgets.QTreeWidgetItem):
        """Adiciona subpastas recursivamente à árvore."""
        try:
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    tree_item = QtWidgets.QTreeWidgetItem(parent_item, [f"📁 {item}"])
                    tree_item.setData(0, Qt.UserRole, item_path)
                    self._add_subfolders(item_path, tree_item)
        except PermissionError:
            pass

    def on_folder_selected(self, item, column):
        """Callback quando uma pasta é clicada na árvore."""
        folder_path = item.data(0, Qt.UserRole)
        if folder_path and os.path.exists(folder_path):
            self.current_folder = folder_path
            self.load_components(folder_path)
            
            # Limpa seleção atual
            self.selected_component = None
            self.info_label.setText("Nenhum componente selecionado")
            self.info_label.setStyleSheet("color: #888; font-style: italic; font-size: 13px;")
            self.btn_ok.setEnabled(False)
            
            # Se a busca tiver texto, aplica o filtro na nova pasta
            if self.search_input.text():
                self.on_search_text_changed(self.search_input.text())
        
    def load_components(self, folder_path: str):
        """Carrega os componentes da pasta especificada no layout de grade."""
        # Limpa componentes anteriores
        while self.components_layout.count():
            child = self.components_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.components_cards = {}
        
        if not os.path.exists(folder_path):
            return
        
        # Busca arquivos .FCStd
        files = [
            f for f in os.listdir(folder_path)
            if f.endswith('.FCStd')
        ]
        
        if not files:
            no_files = QtWidgets.QLabel("Nenhum componente encontrado nesta pasta.")
            no_files.setStyleSheet("color: #888; font-size: 14px;")
            no_files.setAlignment(Qt.AlignCenter)
            self.components_layout.addWidget(no_files, 0, 0)
            return
        
        # Popula a grade (4 colunas agora, pois a árvore ocupa espaço)
        max_columns = 4
        row = 0
        col = 0
        
        for filename in sorted(files):
            filepath = os.path.join(folder_path, filename)
            card = ComponentCard(filename, filepath)
            card.clicked.connect(lambda f=filepath: self.on_component_selected(f))
            self.components_cards[filepath] = card
            
            self.components_layout.addWidget(card, row, col)
            
            col += 1
            if col >= max_columns:
                col = 0
                row += 1
        
    def on_component_selected(self, filepath: str):
        """Callback quando um componente é selecionado."""
        for card in self.components_cards.values():
            card.set_selected(False)
        
        self.components_cards[filepath].set_selected(True)
        self.selected_component = filepath
        
        filename = os.path.basename(filepath)
        self.info_label.setText(f"Selecionado: <b>{filename}</b>")
        self.info_label.setStyleSheet("color: #007acc; font-size: 13px;")
        self.btn_ok.setEnabled(True)
        
        self.component_selected.emit(filepath)
        
    def on_search_text_changed(self, text: str):
        """Filtra componentes conforme o usuário digita e reorganiza o grid."""
        text_lower = text.lower()
        
        # Removemos tudo do grid temporariamente
        for i in reversed(range(self.components_layout.count())): 
            self.components_layout.takeAt(i)
            
        # Reposicionamos apenas os visíveis
        max_columns = 4
        row = 0
        col = 0
        
        for filepath, card in self.components_cards.items():
            is_match = text_lower in card.filename.lower()
            card.setVisible(is_match)
            
            if is_match:
                self.components_layout.addWidget(card, row, col)
                col += 1
                if col >= max_columns:
                    col = 0
                    row += 1
    
    def get_selected_component(self) -> Optional[str]:
        """Retorna o caminho do componente selecionado ou None."""
        return self.selected_component


class ComponentCard(QtWidgets.QWidget):
    """Card individual com thumbnail e informações do componente."""
    
    clicked = Signal()
    
    def __init__(self, filename: str, filepath: str, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.filepath = filepath
        self.is_selected = False
        self.setObjectName("card")
        
        self.initUI()
        self.load_thumbnail()
        self._apply_style()
        
    def initUI(self):
        self.setFixedSize(160, 190)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # Container para a imagem com fundo
        img_container = QtWidgets.QWidget()
        img_container.setFixedSize(134, 134)
        img_container.setStyleSheet("background: #22222b; border-radius: 6px;")
        img_layout = QtWidgets.QVBoxLayout(img_container)
        img_layout.setContentsMargins(0, 0, 0, 0)
        
        self.thumbnail_label = QtWidgets.QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        img_layout.addWidget(self.thumbnail_label)
        
        # Label de texto
        name_only = os.path.splitext(self.filename)[0]
        self.name_label = QtWidgets.QLabel(name_only)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet("font-size: 12px; color: #cccccc; font-weight: 500;")
        
        layout.addWidget(img_container, alignment=Qt.AlignCenter)
        layout.addWidget(self.name_label, alignment=Qt.AlignTop)
        
    def load_thumbnail(self):
        """Extrai e carrega o thumbnail do arquivo FCStd."""
        try:
            with zipfile.ZipFile(self.filepath, 'r') as z:
                thumb_names = [n for n in z.namelist() if n.lower() == "thumbnails/thumbnail.png"]
                if thumb_names:
                    data = z.read(thumb_names[0])
                    pixmap = QtGui.QPixmap()
                    if pixmap.loadFromData(data):
                        scaled = pixmap.scaled(
                            120, 120,
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        )
                        self.thumbnail_label.setPixmap(scaled)
                        return
        except Exception:
            pass
        
        # Ícone de fallback caso não tenha thumbnail
        self.thumbnail_label.setText("📦")
        self.thumbnail_label.setStyleSheet("font-size: 64px; color: #555566;")
        
    def _apply_style(self):
        """Atualiza a aparência baseada no estado."""
        if self.is_selected:
            self.setStyleSheet("""
                QWidget#card {
                    background-color: #2b3644;
                    border: 2px solid #007acc;
                    border-radius: 8px;
                }
            """)
            self.name_label.setStyleSheet("font-size: 12px; color: #007acc; font-weight: bold;")
        else:
            self.setStyleSheet("""
                QWidget#card {
                    background-color: #2b2b36;
                    border: 1px solid #3a3a4a;
                    border-radius: 8px;
                }
                QWidget#card:hover {
                    border: 1px solid #5a5a6a;
                    background-color: #32323e;
                }
            """)
            self.name_label.setStyleSheet("font-size: 12px; color: #cccccc; font-weight: 500;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            
    def enterEvent(self, event):
        """Efeito hover via PySide já que QWidget puro as vezes ignora :hover no CSS."""
        if not self.is_selected:
            self.setStyleSheet("""
                QWidget#card {
                    background-color: #32323e;
                    border: 1px solid #5a5a6a;
                    border-radius: 8px;
                }
            """)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        if not self.is_selected:
            self._apply_style()
        super().leaveEvent(event)
            
    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._apply_style()
