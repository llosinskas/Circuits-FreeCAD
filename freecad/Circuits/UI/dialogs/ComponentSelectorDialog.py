"""Biblioteca de componentes: categorias, busca, miniaturas, detalhes e o modo de inserção.

Mostra os exemplos paramétricos da bancada e os arquivos .FCStd da pasta (e das
subpastas). Devolve o caminho escolhido (``exemplo:<chave>`` nos exemplos) e o
modo (link ou cópia) por ``get_selected_component`` e ``get_modo``.
"""
import os
from typing import Optional

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits import ICON_PATH
from freecad.Circuits.core import biblioteca as regras
from freecad.Circuits.qt import QtCore, QtGui, QtWidgets
from freecad.Circuits.services import biblioteca

TODOS = "Todos"
ICONE_DA_CATEGORIA = {
    "Tomadas": "tomadas.svg", "Interruptores": "interruptor.svg", "Iluminação": "lampada.svg",
    "Quadros e proteção": "quadro_novo.svg", "Caixas": "conectar_caixas.svg", "Equipamentos": "equipamentos.svg",
    "Outros": "Componentes.svg",
}
TAMANHO_PREVIA = 220
CAMINHO = QtCore.Qt.UserRole
PREFS_GRUPO = "User parameter:BaseApp/Preferences/Mod/Circuits"
ORIGENS = [
    ("todos", "Todos"),
    ("exemplos", "Exemplos paramétricos"),
    ("arquivos", "Arquivos (.FCStd)"),
    ("recentes", "Recentes"),
]
TAMANHOS_ICONE = [("Pequeno", 64), ("Médio", 96), ("Grande", 128)]


class ComponentSelectorDialog(QtWidgets.QDialog):
    """Escolha de um componente da biblioteca.

    Args:
        components_path: pasta dos arquivos .FCStd.
        title: título da janela.
        com_exemplos: inclui os exemplos paramétricos da bancada.
    """

    def __init__(self, components_path: str, title: str = "Biblioteca de componentes", parent=None,
                 com_exemplos: bool = True):
        if parent is None and hasattr(Gui, "getMainWindow"):
            try:
                parent = Gui.getMainWindow()
            except Exception:
                parent = None
        super().__init__(parent)
        self.components_path = components_path
        self.com_exemplos = com_exemplos
        self.selected_component: Optional[str] = None
        self._itens = biblioteca.listar_itens(components_path, com_exemplos)
        self._por_caminho = {item["caminho"]: item for item in self._itens}
        self._icones = {}
        self._recentes, self._modo_salvo = self._carregar_preferencias()
        self.setWindowTitle(title)
        self.resize(1120, 700)
        self._montar()
        self._preencher_categorias()
        self._filtrar()
        self.busca.setFocus()

    # --- preferências --------------------------------------------------------------

    @staticmethod
    def _carregar_preferencias():
        try:
            prefs = App.ParamGet(PREFS_GRUPO)
            bruto = prefs.GetString("BibliotecaRecentes", "")
            recentes = [c for c in bruto.split("|") if c]
            modo = prefs.GetString("BibliotecaModo", biblioteca.LINK)
            return recentes, modo
        except Exception:
            return [], biblioteca.LINK

    def _salvar_preferencias(self):
        try:
            prefs = App.ParamGet(PREFS_GRUPO)
            prefs.SetString("BibliotecaModo", self.get_modo())
            if self.selected_component:
                recentes = [self.selected_component] + [c for c in self._recentes if c != self.selected_component]
                prefs.SetString("BibliotecaRecentes", "|".join(recentes[:10]))
        except Exception:
            pass

    # --- montagem -----------------------------------------------------------------

    def _montar(self):
        layout = QtWidgets.QVBoxLayout(self)

        barra = QtWidgets.QHBoxLayout()
        self.busca = QtWidgets.QLineEdit()
        self.busca.setPlaceholderText("Buscar: tomada 220, disjuntor, motor, quadro...")
        self.busca.setClearButtonEnabled(True)
        self.busca.textChanged.connect(self._filtrar)
        self.busca.returnPressed.connect(lambda: self.accept() if self.selected_component else None)
        barra.addWidget(self.busca, 1)

        self.filtro_origem = QtWidgets.QComboBox()
        for chave, rotulo in ORIGENS:
            self.filtro_origem.addItem(rotulo, chave)
        self.filtro_origem.currentIndexChanged.connect(self._filtrar)
        barra.addWidget(self.filtro_origem)

        self.modo_visualizacao = QtWidgets.QComboBox()
        self.modo_visualizacao.addItems(["Grade", "Lista"])
        self.modo_visualizacao.currentIndexChanged.connect(self._atualizar_visualizacao)
        barra.addWidget(self.modo_visualizacao)

        self.tamanho_icone = QtWidgets.QComboBox()
        for rotulo, px in TAMANHOS_ICONE:
            self.tamanho_icone.addItem(rotulo, px)
        self.tamanho_icone.setCurrentIndex(1)
        self.tamanho_icone.currentIndexChanged.connect(self._atualizar_visualizacao)
        barra.addWidget(self.tamanho_icone)

        btn_atualizar = QtWidgets.QPushButton("Atualizar")
        btn_atualizar.setToolTip("Recarregar arquivos da pasta da biblioteca")
        btn_atualizar.clicked.connect(self._recarregar)
        barra.addWidget(btn_atualizar)

        btn_pasta = QtWidgets.QPushButton("Abrir pasta")
        btn_pasta.setToolTip("Abrir a pasta da biblioteca no explorador de arquivos")
        btn_pasta.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(self.components_path)))
        barra.addWidget(btn_pasta)
        layout.addLayout(barra)

        divisao = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.categorias = QtWidgets.QListWidget()
        self.categorias.setMaximumWidth(210)
        self.categorias.currentRowChanged.connect(lambda *_: self._filtrar())
        divisao.addWidget(self.categorias)

        centro = QtWidgets.QWidget()
        centro_layout = QtWidgets.QVBoxLayout(centro)
        centro_layout.setContentsMargins(0, 0, 0, 0)
        self.contador = QtWidgets.QLabel()
        centro_layout.addWidget(self.contador)

        self.lista = QtWidgets.QListWidget()
        self.lista.setResizeMode(QtWidgets.QListView.Adjust)
        self.lista.setMovement(QtWidgets.QListView.Static)
        self.lista.setWordWrap(True)
        self.lista.setSpacing(6)
        self.lista.currentItemChanged.connect(self._mostrar_detalhes)
        self.lista.itemDoubleClicked.connect(lambda *_: self.accept())
        centro_layout.addWidget(self.lista, 1)
        divisao.addWidget(centro)

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
        if self._modo_salvo == biblioteca.COPIA:
            self.modo_copia.setChecked(True)
        else:
            self.modo_link.setChecked(True)
        modos.addWidget(self.modo_link)
        modos.addWidget(self.modo_copia)
        detalhes.addWidget(caixa_modo)
        self.caixa_modo = caixa_modo

        self.repetir = QtWidgets.QCheckBox("Inserir em sequência (repetir até ESC)")
        self.repetir.setToolTip("Permite clicar várias vezes na planta para inserir múltiplos itens iguais")
        detalhes.addWidget(self.repetir)

        detalhes.addWidget(QtWidgets.QLabel(
            "Entra em <pavimento> > Equipamentos.\n"
            "Atalhos ao posicionar: R gira 90° | Espaço alinha | S snap | O orienta na parede"))
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

        self._aplicar_estilo_lista()

    def _aplicar_estilo_lista(self):
        px = int(self.tamanho_icone.currentData() or 96)
        em_lista = self.modo_visualizacao.currentText() == "Lista"
        if em_lista:
            self.lista.setViewMode(QtWidgets.QListView.ListMode)
            lado = max(32, px // 2)
            self.lista.setIconSize(QtCore.QSize(lado, lado))
            self.lista.setGridSize(QtCore.QSize())
        else:
            self.lista.setViewMode(QtWidgets.QListView.IconMode)
            self.lista.setIconSize(QtCore.QSize(px, px))
            self.lista.setGridSize(QtCore.QSize(px + 64, px + 56))

    def _atualizar_visualizacao(self, *_):
        self._icones.clear()
        self._aplicar_estilo_lista()
        self._filtrar()

    def _recarregar(self):
        self._itens = biblioteca.listar_itens(self.components_path, self.com_exemplos)
        self._por_caminho = {item["caminho"]: item for item in self._itens}
        self._icones.clear()
        self._preencher_categorias()
        self._filtrar()

    def _preencher_categorias(self):
        self.categorias.blockSignals(True)
        self.categorias.clear()
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
        self.categorias.blockSignals(False)

    # --- ícones e miniaturas ------------------------------------------------------------

    @staticmethod
    def _icone_da_categoria(nome):
        return QtGui.QIcon(os.path.join(ICON_PATH, ICONE_DA_CATEGORIA.get(nome, "Componentes.svg")))

    def _desenhar_previa_exemplo(self, chave, tamanho):
        dados = regras.EXEMPLOS.get(chave)
        if not dados:
            return None
        try:
            pixmap = QtGui.QPixmap(tamanho, tamanho)
            pixmap.fill(QtGui.QColor("#F7F8FA"))
            painter = QtGui.QPainter(pixmap)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)

            caixas_2d = []
            for primitiva in dados["primitivas"]:
                if primitiva[0] == "caixa":
                    (x, y, _), (dx, dy, _) = primitiva[1], primitiva[2]
                    caixas_2d.append(("rect", x, y, dx, dy))
                else:
                    (cx, cy, _), raio, comp, eixo = primitiva[1], primitiva[2], primitiva[3], primitiva[4]
                    if abs(eixo[2]) >= abs(eixo[0]) and abs(eixo[2]) >= abs(eixo[1]):
                        caixas_2d.append(("circ", cx - raio, cy - raio, 2 * raio, 2 * raio))
                    elif abs(eixo[0]) >= abs(eixo[1]):
                        sinal = 1.0 if eixo[0] >= 0 else -1.0
                        x0 = cx if sinal > 0 else cx - comp
                        caixas_2d.append(("rect", x0, cy - raio, comp, 2 * raio))
                    else:
                        sinal = 1.0 if eixo[1] >= 0 else -1.0
                        y0 = cy if sinal > 0 else cy - comp
                        caixas_2d.append(("rect", cx - raio, y0, 2 * raio, comp))

            xs = [c[1] for c in caixas_2d] + [c[1] + c[3] for c in caixas_2d]
            ys = [c[2] for c in caixas_2d] + [c[2] + c[4] for c in caixas_2d]
            largura = max(max(xs) - min(xs), 1.0)
            prof = max(max(ys) - min(ys), 1.0)
            margem = max(14, int(tamanho * 0.14))
            area = max(tamanho - 2 * margem, 10)
            escala = min(area / largura, area / prof)
            ox = (tamanho - largura * escala) / 2.0 - min(xs) * escala
            oy = (tamanho - prof * escala) / 2.0 - min(ys) * escala

            r, g, b = dados.get("cor", (0.7, 0.75, 0.8))
            cor = QtGui.QColor.fromRgbF(r, g, b)
            painter.setPen(QtGui.QPen(QtGui.QColor("#334155"), 1.5))
            painter.setBrush(QtGui.QBrush(cor))
            for tipo, x, y, dx, dy in caixas_2d:
                rx = ox + x * escala
                ry = tamanho - (oy + (y + dy) * escala)
                rw, rh = max(dx * escala, 2.0), max(dy * escala, 2.0)
                if tipo == "circ":
                    painter.drawEllipse(QtCore.QRectF(rx, ry, rw, rh))
                else:
                    painter.drawRect(QtCore.QRectF(rx, ry, rw, rh))

            # Cruz da origem de inserção
            px0, py0 = ox, tamanho - oy
            painter.setPen(QtGui.QPen(QtGui.QColor("#DC2626"), 1.2))
            painter.drawLine(int(px0 - 5), int(py0), int(px0 + 5), int(py0))
            painter.drawLine(int(px0), int(py0 - 5), int(px0), int(py0 + 5))

            if tamanho >= 160:
                dims = regras.dimensoes_do_exemplo(chave)
                painter.setPen(QtGui.QColor("#475569"))
                painter.drawText(6, tamanho - 8, f"{dims[0]:g} × {dims[1]:g} × {dims[2]:g} mm")
            painter.end()
            return pixmap
        except Exception:
            return None

    def _pixmap(self, item, tamanho):
        if item["exemplo"]:
            chave = regras.chave_do_exemplo(item["caminho"])
            previa = self._desenhar_previa_exemplo(chave, tamanho)
            if previa is not None:
                return previa
        else:
            dados = biblioteca.miniatura(item["caminho"])
            if dados:
                imagem = QtGui.QPixmap()
                if imagem.loadFromData(dados):
                    return imagem.scaled(tamanho, tamanho, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        return self._icone_da_categoria(item["categoria"]).pixmap(tamanho, tamanho)

    def _icone(self, item):
        if item["caminho"] not in self._icones:
            px = int(self.tamanho_icone.currentData() or 96)
            self._icones[item["caminho"]] = QtGui.QIcon(self._pixmap(item, px))
        return self._icones[item["caminho"]]

    # --- lista e detalhes -----------------------------------------------------------------

    def _filtrar(self, *_):
        atual = self.categorias.currentItem()
        escolhida = atual.data(CAMINHO) if atual else None
        origem = self.filtro_origem.currentData()
        self.lista.clear()
        filtrados = regras.filtrar(self._itens, self.busca.text(), escolhida, origem=origem, recentes=self._recentes)
        for item in filtrados:
            linha = QtWidgets.QListWidgetItem(self._icone(item), item["nome"])
            linha.setData(CAMINHO, item["caminho"])
            linha.setToolTip(item["descricao"])
            self.lista.addItem(linha)
        self.contador.setText(f"{len(filtrados)} componente(s) exibido(s)")
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
            self.info.setText("Mude a busca, a origem ou a categoria.")
            self.previa.clear()
            return
        self.titulo.setText(item["nome"])
        self.previa.setPixmap(self._pixmap(item, TAMANHO_PREVIA))
        if item["exemplo"]:
            chave = regras.chave_do_exemplo(item["caminho"])
            dados = regras.EXEMPLOS[chave]
            dims = regras.dimensoes_do_exemplo(chave)
            extras = [
                item["descricao"],
                f"Dimensões: {dims[0]:g} × {dims[1]:g} × {dims[2]:g} mm",
                f"Altura de montagem: {dados.get('altura_mm', 0) / 1000:.2f} m".replace(".", ","),
            ]
            if dados.get("potencia_va"):
                extras.append(f"Potência: {dados['potencia_va']:.0f} VA")
            self.info.setText(f"{item['categoria']} · exemplo paramétrico\n\n" + "\n".join(extras))
        else:
            tamanho = os.path.getsize(item["caminho"]) / 1024 if os.path.exists(item["caminho"]) else 0
            pasta = os.path.relpath(os.path.dirname(item["caminho"]), self.components_path)
            self.info.setText(f"{item['categoria']}\n\nArquivo: {os.path.basename(item['caminho'])}"
                              f"{'' if pasta == '.' else f' (em {pasta})'}\n{tamanho:.0f} kB")
        self.caixa_modo.setEnabled(not item["exemplo"])

    def accept(self):
        self._salvar_preferencias()
        super().accept()

    # --- resultado --------------------------------------------------------------------

    def get_selected_component(self) -> Optional[str]:
        """Caminho do arquivo escolhido, ou ``exemplo:<chave>``; None se nada foi escolhido."""
        return self.selected_component

    def get_modo(self) -> str:
        """'link' ou 'copia' (``services.biblioteca``)."""
        return biblioteca.COPIA if self.modo_copia.isChecked() else biblioteca.LINK

    def get_repetir(self) -> bool:
        """True quando o usuário pediu inserção em sequência até ESC."""
        return self.repetir.isChecked()
