import os 
import FreeCAD as App
import FreeCADGui as Gui
import zipfile
from freecad.Circuits.qt import QtCore, QtGui, QtWidgets

class PartCard(QtWidgets.QWidget):
    def __init__(self, name, path, parent=None):
        super().__init__(parent)
        self.path = path
        # Layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargin(4,4,4,4)
        layout.setSpacing(4)
        # Thumbnail
        self.thumb = QtWidgets.QLabel()
        self.thumb.setFixedSize(100,100)
        self.thumb.setAlignment(QtCore.Qt.AlignCenter)
        self.thumb.setStyleSheet("background:#2b2b2b; border:1px solid #444; border-radius:4px;")
        self._load_thumbnail()

        # nome
        lbl = QtWidgets.QLabel(os.path.splitext(name)[0])
        lbl.setAlignment(QtCore.Qt.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet('font-size:11px; color:#ddd;')
        layout.addWidget(self.thumb)
        layout.addWidget(lbl)
        #self.setFixedWidth(115)
        self.setCursor(QtCore.Qt.PointingHandCursor)
    def _load_thumbnail(self):
        """Extrai o thumbnail do ZIP sem abrir o documento"""
        try:
            with zipfile.ZipFile(self.path, 'r') as  z:
                if "thumbnails/Thumbnail.png" in z.namelist():
                    data = z.read("thumbnails/Thumbnail.png")
                    pixmap = QtGui.QPixmap()
                    pixmap.loadFromData(data)
                    self.thumb.setPixmap(
                        pixmap.scaled(96, 96, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    )
                    return 
        except Exception:
            pass
        self.thumb.setText("📦 - Sem Imagem")
        self.thumb.setStyleSheet(
            self.thumb.styleSheet()+"font-size:36px;"
        )