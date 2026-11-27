"""Janela do botão Apoiar: o QR code do LivePix para escanear com o celular e o link para o navegador."""
import os

from freecad.Circuits import ICON_PATH, URL_APOIO
from freecad.Circuits.qt import QtCore, QtGui, QtWidgets

QR_CODE = os.path.join(ICON_PATH, "apoiar_qrcode.png")


class ApoiarDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apoiar o projeto")
        raiz = QtWidgets.QVBoxLayout(self)
        titulo = QtWidgets.QLabel("<h3>Gostou da bancada Circuits?</h3>")
        titulo.setAlignment(QtCore.Qt.AlignCenter)
        raiz.addWidget(titulo)
        texto = QtWidgets.QLabel(
            "Ela é gratuita e de código aberto. Se ela ajuda nos seus projetos, você pode apoiar o "
            "desenvolvimento com um Pix de qualquer valor pelo LivePix: escaneie o QR code com o app do "
            "banco ou do celular, ou abra a página no navegador.")
        texto.setWordWrap(True)
        texto.setAlignment(QtCore.Qt.AlignCenter)
        raiz.addWidget(texto)
        imagem = QtWidgets.QLabel()
        imagem.setAlignment(QtCore.Qt.AlignCenter)
        pixmap = QtGui.QPixmap(QR_CODE)
        if not pixmap.isNull():
            imagem.setPixmap(pixmap)  # no tamanho da imagem: módulos inteiros, o celular lê sem erro
        imagem.setToolTip(URL_APOIO)
        raiz.addWidget(imagem)
        link = QtWidgets.QLabel(f'<a href="{URL_APOIO}">{URL_APOIO}</a>')
        link.setOpenExternalLinks(True)
        link.setAlignment(QtCore.Qt.AlignCenter)
        link.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        raiz.addWidget(link)
        botoes = QtWidgets.QHBoxLayout()
        abrir = QtWidgets.QPushButton("Abrir no navegador")
        abrir.setDefault(True)
        abrir.clicked.connect(self.abrir)
        copiar = QtWidgets.QPushButton("Copiar link")
        copiar.clicked.connect(self.copiar)
        fechar = QtWidgets.QPushButton("Fechar")
        fechar.clicked.connect(self.accept)
        for botao in (abrir, copiar, fechar):
            botoes.addWidget(botao)
        raiz.addLayout(botoes)

    def abrir(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(URL_APOIO))

    def copiar(self):
        QtWidgets.QApplication.clipboard().setText(URL_APOIO)
