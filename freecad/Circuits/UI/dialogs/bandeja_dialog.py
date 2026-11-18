"""Diálogos de configuração das bandejas (eletrocalhas e leitos) e de seus suportes."""
from freecad.Circuits.core import bandejas as regras
from freecad.Circuits.qt import QtWidgets


class BandejaDialog(QtWidgets.QDialog):
    """
    Args:
        quantidade: número de linhas selecionadas.
        atual: valores que vêm preenchidos (``tipo``, ``largura``, ``aba``, ``altura`` em mm, ``tampa``).
    """

    def __init__(self, quantidade, atual=None):
        super().__init__()
        atual = atual or {}
        self.setWindowTitle("Bandeja ou leito")
        self.setMinimumWidth(360)
        layout = QtWidgets.QFormLayout()
        layout.addRow(QtWidgets.QLabel(f"{quantidade} linha(s) selecionada(s)"))

        self.tipo = QtWidgets.QComboBox()
        self._tipos = list(regras.TIPOS)
        self.tipo.addItems([regras.TIPOS[t] for t in self._tipos])
        self.tipo.setCurrentIndex(self._tipos.index(atual.get("tipo", regras.TIPO_PADRAO)))
        layout.addRow("Tipo:", self.tipo)

        self.largura = QtWidgets.QComboBox()
        self.largura.addItems([str(v) for v in regras.LARGURAS_MM])
        self.largura.setEditable(True)
        self.largura.setEditText(f"{float(atual.get('largura', regras.LARGURA_PADRAO_MM)):g}")
        self.largura.setToolTip("Largura interna da bandeja, em mm")
        layout.addRow("Largura [mm]:", self.largura)

        self.aba = QtWidgets.QComboBox()
        self.aba.addItems([str(v) for v in regras.ABAS_MM])
        self.aba.setEditable(True)
        self.aba.setEditText(f"{float(atual.get('aba', regras.ABA_PADRAO_MM)):g}")
        self.aba.setToolTip("Altura da lateral (aba), em mm")
        layout.addRow("Aba [mm]:", self.aba)

        self.altura = QtWidgets.QDoubleSpinBox()
        self.altura.setRange(0.0, 20.0)
        self.altura.setDecimals(2)
        self.altura.setSingleStep(0.1)
        self.altura.setValue(float(atual.get("altura", regras.ALTURA_PADRAO_MM)) / 1000.0)
        self.altura.setToolTip("Do piso do pavimento à base da bandeja, em metros")
        layout.addRow("Altura de instalação [m]:", self.altura)

        self.tampa = QtWidgets.QCheckBox("Com tampa")
        self.tampa.setChecked(bool(atual.get("tampa", False)))
        layout.addRow(self.tampa)

        botoes = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("Aplicar")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept)
        btn_cancelar = QtWidgets.QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancelar)
        layout.addRow(botoes)
        self.setLayout(layout)

    @staticmethod
    def _numero(texto, padrao):
        try:
            valor = float(str(texto).replace(",", "."))
        except ValueError:
            return float(padrao)
        return valor if valor > 0 else float(padrao)

    def get_dados(self):
        """``tipo`` (chave de ``core.bandejas.TIPOS``), ``largura``, ``aba`` e ``altura`` em mm, ``tampa``."""
        return {
            "tipo": self._tipos[self.tipo.currentIndex()],
            "largura": self._numero(self.largura.currentText(), regras.LARGURA_PADRAO_MM),
            "aba": self._numero(self.aba.currentText(), regras.ABA_PADRAO_MM),
            "altura": round(self.altura.value() * 1000.0, 1),
            "tampa": self.tampa.isChecked(),
        }


class SuportesDialog(QtWidgets.QDialog):
    """Diálogo de ajuste dos suportes das eletrocalhas e leitos (espaçamento, pendentes, tipo e folga)."""

    def __init__(self, quantidade=0, atual=None):
        super().__init__()
        atual = atual or {}
        self.setWindowTitle("Ajustes dos Suportes de Eletrocalha / Leito")
        self.setMinimumWidth(420)
        layout = QtWidgets.QFormLayout()

        esc = f"{quantidade} bandeja(s) selecionada(s)" if quantidade else "Todas as bandejas do projeto"
        layout.addRow(QtWidgets.QLabel(f"Aplicar em: {esc}"))

        self.tipo_suporte = QtWidgets.QComboBox()
        self._tipos_suporte = list(regras.TIPOS_SUPORTE)
        self.tipo_suporte.addItems([regras.TIPOS_SUPORTE[t] for t in self._tipos_suporte])
        tipo_atual = atual.get("tipo_suporte", regras.TIPO_SUPORTE_PADRAO)
        if tipo_atual in self._tipos_suporte:
            self.tipo_suporte.setCurrentIndex(self._tipos_suporte.index(tipo_atual))
        self.tipo_suporte.setToolTip(
            "Trapézio (perfilado + 2 tirantes), Pendural central (1 tirante) ou Mão francesa (fixada na parede)"
        )
        layout.addRow("Tipo de suporte:", self.tipo_suporte)

        self.vao = QtWidgets.QDoubleSpinBox()
        self.vao.setRange(0.30, 6.00)
        self.vao.setDecimals(2)
        self.vao.setSingleStep(0.25)
        self.vao.setSuffix(" m")
        vao_padrao_mm = float(atual.get("vao_suporte") or regras.VAO_SUPORTE[regras.TIPO_PADRAO])
        self.vao.setValue(vao_padrao_mm / 1000.0)
        self.vao.setToolTip("Espaçamento máximo (vão) entre suportes consecutivos ao longo do trecho")
        layout.addRow("Espaçamento máximo (vão) [m]:", self.vao)

        self.distancia_no = QtWidgets.QDoubleSpinBox()
        self.distancia_no.setRange(0.10, 2.00)
        self.distancia_no.setDecimals(2)
        self.distancia_no.setSingleStep(0.10)
        self.distancia_no.setSuffix(" m")
        dist_mm = float(atual.get("distancia_no") if atual.get("distancia_no") is not None else regras.DISTANCIA_SUPORTE_CONEXAO)
        self.distancia_no.setValue(dist_mm / 1000.0)
        self.distancia_no.setToolTip("Distância do primeiro e do último suporte até as conexões (curvas, tês, pontas)")
        layout.addRow("Distância às conexões/pontas [m]:", self.distancia_no)

        self.pendente = QtWidgets.QDoubleSpinBox()
        self.pendente.setRange(0.00, 20.00)
        self.pendente.setDecimals(2)
        self.pendente.setSingleStep(0.10)
        self.pendente.setSuffix(" m")
        self.pendente.setSpecialValueText("Automático (até a laje)")
        pendente_mm = float(atual.get("pendente") or 0.0)
        self.pendente.setValue(pendente_mm / 1000.0)
        self.pendente.setToolTip(
            "Comprimento dos pendentes/tirantes roscados. Em 0,00 m vai automaticamente da bandeja até a laje do pavimento"
        )
        layout.addRow("Comprimento dos pendentes [m]:", self.pendente)

        self.folga_perfilado = QtWidgets.QSpinBox()
        self.folga_perfilado.setRange(0, 500)
        self.folga_perfilado.setSingleStep(10)
        self.folga_perfilado.setSuffix(" mm")
        folga_mm = int(round(float(atual.get("folga_perfilado") if atual.get("folga_perfilado") is not None else regras.FOLGA_PERFILADO_MM)))
        self.folga_perfilado.setValue(folga_mm)
        self.folga_perfilado.setToolTip("Sobra lateral total do perfilado 38x38 mm além da largura da eletrocalha (ex: 100 mm = 5 cm de cada lado)")
        layout.addRow("Folga lateral do perfilado [mm]:", self.folga_perfilado)

        botoes = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("Gerar suportes")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept)
        btn_cancelar = QtWidgets.QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancelar)
        layout.addRow(botoes)
        self.setLayout(layout)

    def get_dados(self):
        return {
            "tipo_suporte": self._tipos_suporte[self.tipo_suporte.currentIndex()],
            "vao_suporte": round(self.vao.value() * 1000.0, 1),
            "distancia_no": round(self.distancia_no.value() * 1000.0, 1),
            "pendente": round(self.pendente.value() * 1000.0, 1),
            "folga_perfilado": float(self.folga_perfilado.value()),
        }
