import os 
import FreeCAD as App
import FreeCADGui as Gui
import zipfile
from freecad.Circuits.qt import QtCore, QtGui, QtWidgets
from .Cards import PartCard
from freecad.Circuits import LIBRARY_PATH

class PartsBrowserDialog(QtWidgets.QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent or Gui.getMainWindow())

        self.setWindowTitle(r"{title}")
        self.setWindowMinimumSize(600,400)
        self.selected_path = None
        self._build_ui()
        self._scan_library(LIBRARY_PATH)

        #layout = QtWidgets.QVBoxLayout(self)
        #self.scroll = QtWidgets.QScrollArea()
        #self.scroll.setWidgetResizable(True)
        #self.container = QtWidgets.QWidget()
        #self.grid = QtWidgets.QGridLayout(self.container)
        #self.grid.setContentsMargin(8,8,8,8)
        #self.grid.setSpacing(8)
        #self.scroll.setWidget(self.container)
        #layout.addWidget(self.scroll)

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentMargin(8,8,8,8)
        
        top = QtWidgets.QHBoxLayout()
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Buscar por componente...")
        self.search.textChanged.connect(self._filter)
        btn_open = QtWidgets.QPushButton("Abrir pasta")
        btn_open.setTooTip("Selecionar outra pasta da biblioteca")
        btn_open.clicked.connect(self._choose_folder)
        top.addWidget(self.search)
        top.addWidget(btn_open)
        root.addLayout(top)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        #Grade de cards com scroll 
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.grid_widget = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(self.grid_widget)
        self.grid.setSpacing(8)
        scroll.setWidget(self.grid_widget)
        splitter.addWidget(scroll)
        # Painel de detalhes
        detail = QtWidgets.QWidget()
        detail.setMinimumWidth(200)
        detail_layout = QtWidgets.QVBoxLayout(detail)
        self.big_preview = QtWidgets.QLabel("Selecione uma peça")
        self.big_preview.setFixedSize(200, 200)
        self.big_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.big_preview.setStyleSheet(
            "background:#1e1e1e; border:1px solid #555; border-radius:6px; color:#888;"
        )
        self.detail_name  = QtWidgets.QLabel("")
        self.detail_name.setStyleSheet("font-weight:bold; font-size:13px;")
        self.detail_name.setWordWrap(True)
        self.detail_size  = QtWidgets.QLabel("")
        self.detail_size.setStyleSheet("color:#888; font-size:11px;")
        self.detail_path_lbl = QtWidgets.QLabel("")
        self.detail_path_lbl.setStyleSheet("color:#666; font-size:10px;")
        self.detail_path_lbl.setWordWrap(True)

        self.btn_add = QtWidgets.QPushButton("➕  Adicionar ao Projeto")
        self.btn_add.setEnabled(False)
        self.btn_add.setStyleSheet(
            "QPushButton { background:#0a84ff; color:white; padding:8px; "
            "border-radius:5px; font-weight:bold; }"
            "QPushButton:disabled { background:#333; color:#666; }"
            "QPushButton:hover { background:#339dff; }"
        )
        self.btn_add.clicked.connect(self._insert_part)

        detail_layout.addWidget(self.big_preview)
        detail_layout.addWidget(self.detail_name)
        detail_layout.addWidget(self.detail_size)
        detail_layout.addWidget(self.detail_path_lbl)
        detail_layout.addStretch()
        detail_layout.addWidget(self.btn_add)
        splitter.addWidget(detail)
        splitter.setSizes([450, 210])

        root.addWidget(splitter)

        # status bar
        self.status = QtWidgets.QLabel("Nenhuma peça carregada")
        self.status.setStyleSheet("color:#888; font-size:11px;")
        root.addWidget(self.status)

    # ── Leitura da biblioteca ────────────────────────────────────────────
    def _scan_library(self, folder):
        if not os.path.isdir(folder):
            self.status.setText(f"Pasta não encontrada: {folder}")
            return
        self.all_parts = []
        for root_dir, _, files in os.walk(folder):
            for f in sorted(files):
                if f.lower().endswith(".fcstd"):
                    self.all_parts.append({
                        "name": f,
                        "path": os.path.join(root_dir, f),
                        "rel":  os.path.relpath(
                            os.path.join(root_dir, f), folder
                        ),
                    })
        self._populate(self.all_parts)

    def _populate(self, parts):
        # limpa grade
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()

        cols = 3
        for i, p in enumerate(parts):
            card = PartCard(p["name"], p["path"])
            card.mousePressEvent = lambda e, pp=p: self._select(pp)
            self.grid.addWidget(card, i // cols, i % cols)

        spacer = QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.grid.addItem(spacer, len(parts) // cols + 1, 0)
        self.status.setText(f"{len(parts)} peça(s) encontrada(s)")

    # ── Selecionar peça ──────────────────────────────────────────────────
    def _select(self, part):
        self.selected_path = part["path"]
        self.detail_name.setText(os.path.splitext(part["name"])[0])
        size_kb = os.path.getsize(part["path"]) / 1024
        self.detail_size.setText(f"{size_kb:.1f} KB")
        self.detail_path_lbl.setText(part["rel"])
        self.btn_add.setEnabled(True)

        # preview grande
        try:
            with zipfile.ZipFile(part["path"], "r") as z:
                if "thumbnails/Thumbnail.png" in z.namelist():
                    data = z.read("thumbnails/Thumbnail.png")
                    pix = QtGui.QPixmap()
                    pix.loadFromData(data)
                    self.big_preview.setPixmap(
                        pix.scaled(196, 196, QtCore.Qt.KeepAspectRatio,
                                   QtCore.Qt.SmoothTransformation)
                    )
                    return
        except Exception:
            pass
        self.big_preview.setText("Sem preview disponível")

    # ── Filtro de busca ──────────────────────────────────────────────────
    def _filter(self, text):
        filtered = [
            p for p in self.all_parts
            if text.lower() in p["name"].lower()
        ]
        self._populate(filtered)

    # ── Selecionar outra pasta ───────────────────────────────────────────
    def _choose_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Selecionar Pasta da Biblioteca", LIBRARY_PATH
        )
        if folder:
            self.selected_path = None
            self.btn_add.setEnabled(False)
            self._scan_library(folder)

    # ── Inserir peça no documento ────────────────────────────────────────
    def _insert_part(self):
        if not self.selected_path:
            return
        doc = App.ActiveDocument
        if not doc:
            QtWidgets.QMessageBox.warning(
                self, "Atenção", "Nenhum documento ativo no FreeCAD."
            )
            return
        try:
            Gui.ActiveDocument.mergeProject(self.selected_path)
            doc.recompute()
            self.status.setText(
                f"✅  '{self.detail_name.text()}' adicionado com sucesso!"
            )
        except Exception as ex:
            QtWidgets.QMessageBox.critical(self, "Erro ao inserir peça", str(ex))