"""Biblioteca de componentes: categorias, busca, miniaturas, detalhes e o modo de inserção.

Mostra os exemplos paramétricos da bancada e os arquivos .FCStd da pasta (e das
subpastas). Devolve o caminho escolhido (``exemplo:<chave>`` nos exemplos) e o
modo (link ou cópia) por ``get_selected_component`` e ``get_modo``.
"""
import os
from typing import Optional

from freecad.Circuits import ICON_PATH
from freecad.Circuits.core import biblioteca as regras
from freecad.Circuits.qt import QtCore, QtGui, QtWidgets
from freecad.Circuits.services import biblioteca

import FreeCADGui as Gui

TODOS = "Todos"
ICONE_DA_CATEGORIA = {
    "Tomadas": "tomadas.svg", "Interruptores": "interruptor.svg", "Iluminação": "lampada.svg",
    "Quadros e proteção": "quadro_novo.svg", "Caixas": "conectar_caixas.svg", "Equipamentos": "equipamentos.svg",
    "Outros": "Componentes.svg",
}
TAMANHO_ICONE = 96
TAMANHO_PREVIA = 220
CAMINHO = QtCore.Qt.UserRole


class ComponentSelectorDialog(QtWidgets.QDialog):
    """Escolha de um componente da biblioteca.

    Args:
        components_path: pasta dos arquivos .FCStd.
        title: título da janela.
        com_exemplos: inclui os exemplos paramétricos da bancada.
    """

    def __init__(self, components_path: str, title: str = "Biblioteca de componentes", parent=None,
                 com_exemplos: bool = True):
        super().__init__(parent or Gui.getMainWindow())
        self.components_path = components_path
        self.selected_component: Optional[str] = None
        self._itens = biblioteca.listar_itens(components_path, com_exemplos)
        self._por_caminho = {item["caminho"]: item for item in self._itens}
        self._icones = {}
        self.setWindowTitle(title)
        self.resize(1080, 680)
        self._montar()
        self._preencher_categorias()
        self._filtrar()

    # --- montagem -----------------------------------------------------------------

    def _montar(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.busca = QtWidgets.QLineEdit()
        self.busca.setPlaceholderText("Buscar: tomada 220, disjuntor, motor, quadro...")
        self.busca.setClearButtonEnabled(True)
        self.busca.textChanged.connect(self._filtrar)
        layout.addWidget(self.busca)

        divisao = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.categorias = QtWidgets.QListWidget()
        self.categorias.setMaximumWidth(210)
        self.categorias.currentRowChanged.connect(lambda *_: self._filtrar())
        divisao.addWidget(self.categorias)

        self.lista = QtWidgets.QListWidget()
        self.lista.setViewMode(QtWidgets.QListView.IconMode)
        self.lista.setResizeMode(QtWidgets.QListView.Adjust)
        self.lista.setMovement(QtWidgets.QListView.Static)
        self.lista.setIconSize(QtCore.QSize(TAMANHO_ICONE, TAMANHO_ICONE))
        self.lista.setGridSize(QtCore.QSize(TAMANHO_ICONE + 60, TAMANHO_ICONE + 56))
        self.lista.setWordWrap(True)
        self.lista.setSpacing(6)
        self.lista.currentItemChanged.connect(self._mostrar_detalhes)
        self.lista.itemDoubleClicked.connect(lambda *_: self.accept())
        divisao.addWidget(self.lista)

        painel = QtWidgets.QWidget()
        detalhes = QtWidgets.QVBoxLayout(painel)
        self.previa = QtWidgets.QLabel()
        self.previa.setAlignment(QtCore.Qt.AlignCenter)
        self.previa.setMinimumSize(TAMANHO_PREVIA, TAMANHO_PREVIA)
        self.previa.setFrameShape(QtWidgets.QFrame.StyledPanel)
        detalhes.addWidget(self.previa)
        self.titulo = QtWidgets.QLabel()
        self.titulo.setWordWrap(True)
        fonte = self.titulo.font()
        fonte.setBold(True)
        fonte.setPointSize(fonte.pointSize() + 1)
        self.titulo.setFont(fonte)
        detalhes.addWidget(self.titulo)
        self.info = QtWidgets.QLabel()
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        detalhes.addWidget(self.info)

        caixa_modo = QtWidgets.QGroupBox("Inserir como")
        modos = QtWidgets.QVBoxLayout(caixa_modo)
        self.modo_link = QtWidgets.QRadioButton("Link (referência que acompanha a biblioteca)")
        self.modo_copia = QtWidgets.QRadioButton("Cópia (independente da biblioteca)")
        self.modo_link.setChecked(True)
        modos.addWidget(self.modo_link)
        modos.addWidget(self.modo_copia)
        detalhes.addWidget(caixa_modo)
        self.caixa_modo = caixa_modo
        detalhes.addWidget(QtWidgets.QLabel(
            "Entra numa pasta própria em <pavimento> > Equipamentos, no piso do pavimento ativo.\n"
            "Depois clique na planta para posicionar (R gira 90°)."))
        detalhes.addStretch(1)
        divisao.addWidget(painel)
        divisao.setStretchFactor(1, 1)
        layout.addWidget(divisao, 1)

        botoes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.btn_ok = botoes.button(QtWidgets.QDialogButtonBox.Ok)
        self.btn_ok.setText("Inserir")
        self.btn_ok.setEnabled(False)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def _preencher_categorias(self):
        contagem = {c: 0 for c in regras.CATEGORIAS}
        for item in self._itens:
            contagem[item["categoria"]] = contagem.get(item["categoria"], 0) + 1
        self.categorias.addItem(f"{TODOS} ({len(self._itens)})")
        self.categorias.item(0).setData(CAMINHO, None)
        for nome in regras.CATEGORIAS:
            if contagem.get(nome):
                linha = QtWidgets.QListWidgetItem(self._icone_da_categoria(nome), f"{nome} ({contagem[nome]})")
                linha.setData(CAMINHO, nome)
                self.categorias.addItem(linha)
        self.categorias.setCurrentRow(0)

    # --- ícones e miniaturas ------------------------------------------------------------

    @staticmethod
    def _icone_da_categoria(nome):
        return QtGui.QIcon(os.path.join(ICON_PATH, ICONE_DA_CATEGORIA.get(nome, "Componentes.svg")))

    def _pixmap(self, item, tamanho):
        dados = None if item["exemplo"] else biblioteca.miniatura(item["caminho"])
        if dados:
            imagem = QtGui.QPixmap()
            if imagem.loadFromData(dados):
                return imagem.scaled(tamanho, tamanho, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        return self._icone_da_categoria(item["categoria"]).pixmap(tamanho, tamanho)

    def _icone(self, item):
        if item["caminho"] not in self._icones:
            self._icones[item["caminho"]] = QtGui.QIcon(self._pixmap(item, TAMANHO_ICONE))
        return self._icones[item["caminho"]]

    # --- lista e detalhes -----------------------------------------------------------------

    def _filtrar(self, *_):
        atual = self.categorias.currentItem()
        escolhida = atual.data(CAMINHO) if atual else None
        self.lista.clear()
        for item in regras.filtrar(self._itens, self.busca.text(), escolhida):
            linha = QtWidgets.QListWidgetItem(self._icone(item), item["nome"])
            linha.setData(CAMINHO, item["caminho"])
            linha.setToolTip(item["descricao"])
            self.lista.addItem(linha)
        if self.lista.count():
            self.lista.setCurrentRow(0)
        else:
            self._mostrar_detalhes(None)

    def _mostrar_detalhes(self, linha, *_):
        item = self._por_caminho.get(linha.data(CAMINHO)) if linha else None
        self.selected_component = item["caminho"] if item else None
        self.btn_ok.setEnabled(item is not None)
        if item is None:
            self.titulo.setText("Nenhum componente")
            self.info.setText("Mude a busca ou a categoria.")
            self.previa.clear()
            return
        self.titulo.setText(item["nome"])
        self.previa.setPixmap(self._pixmap(item, TAMANHO_PREVIA))
        if item["exemplo"]:
            dados = regras.EXEMPLOS[regras.chave_do_exemplo(item["caminho"])]
            extras = [item["descricao"], f"Altura de montagem: {dados.get('altura_mm', 0) / 1000:.2f} m".replace(
                ".", ",")]
            if dados.get("potencia_va"):
                extras.append(f"Potência: {dados['potencia_va']:.0f} VA")
            self.info.setText(f"{item['categoria']} · exemplo da bancada (desenhado, sem arquivo)\n\n"
                              + "\n".join(extras))
        else:
            tamanho = os.path.getsize(item["caminho"]) / 1024 if os.path.exists(item["caminho"]) else 0
            pasta = os.path.relpath(os.path.dirname(item["caminho"]), self.components_path)
            self.info.setText(f"{item['categoria']}\n\nArquivo: {os.path.basename(item['caminho'])}"
                              f"{'' if pasta == '.' else f' (em {pasta})'}\n{tamanho:.0f} kB")
        self.caixa_modo.setEnabled(not item["exemplo"])

    # --- resultado --------------------------------------------------------------------

    def get_selected_component(self) -> Optional[str]:
        """Caminho do arquivo escolhido, ou ``exemplo:<chave>``; None se nada foi escolhido."""
        return self.selected_component

    def get_modo(self) -> str:
        """'link' ou 'copia' (``services.biblioteca``)."""
        return biblioteca.COPIA if self.modo_copia.isChecked() else biblioteca.LINK
