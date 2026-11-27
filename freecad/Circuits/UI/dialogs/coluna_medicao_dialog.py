"""Diálogo de criação e edição das colunas de medição com prévia em tempo real."""
from freecad.Circuits.core import centro_medicao as regras
from freecad.Circuits.qt import QtWidgets


class ColunaMedicaoDialog(QtWidgets.QDialog):
    """Configura dimensionamento e layout das colunas de medição (padrão Enel SP + ajustes)."""

    def __init__(self, atual=None, editando=False):
        super().__init__()
        atual = atual or {}
        self.setWindowTitle("Editar coluna de medição" if editando else "Inserir coluna de medição")
        self.setMinimumWidth(680)

        raiz = QtWidgets.QVBoxLayout()
        abas = QtWidgets.QTabWidget()

        # --- Aba 1: Dimensionamento (Enel SP) ---
        aba_dim = QtWidgets.QWidget()
        form_dim = QtWidgets.QFormLayout(aba_dim)

        self.medidores = QtWidgets.QSpinBox()
        self.medidores.setRange(1, 2000)
        self.medidores.setValue(int(atual.get("Medidores", 12) or 12))
        form_dim.addRow("Medidores (unidades):", self.medidores)

        self.por_coluna = QtWidgets.QSpinBox()
        self.por_coluna.setRange(1, 3)
        self.por_coluna.setValue(int(atual.get("MedidoresPorColuna", 3) or 3))
        self.por_coluna.setToolTip("Caixas P sobrepostas por coluna (1 a 3, Tabela 29)")
        form_dim.addRow("Caixas por coluna (P):", self.por_coluna)

        self.demanda_unidade = QtWidgets.QDoubleSpinBox()
        self.demanda_unidade.setRange(1.0, 600.0)
        self.demanda_unidade.setDecimals(1)
        self.demanda_unidade.setSuffix(" A")
        self.demanda_unidade.setValue(float(atual.get("DemandaPorMedidor", 63.0) or 63.0))
        form_dim.addRow("Demanda por medidor:", self.demanda_unidade)

        self.demanda_total = QtWidgets.QDoubleSpinBox()
        self.demanda_total.setRange(0.0, 5000.0)
        self.demanda_total.setDecimals(1)
        self.demanda_total.setSuffix(" A")
        self.demanda_total.setSpecialValueText("Automático (soma unidades)")
        self.demanda_total.setValue(float(atual.get("DemandaTotal", 0.0) or 0.0))
        self.demanda_total.setToolTip("Demanda total diversificada [A]; 0 soma todas as unidades")
        form_dim.addRow("Demanda total:", self.demanda_total)

        self.fases = QtWidgets.QComboBox()
        self.fases.addItems(["1", "2", "3"])
        fases_atual = str(int(atual.get("Fases", 2) or 2))
        if fases_atual in ("1", "2", "3"):
            self.fases.setCurrentText(fases_atual)
        form_dim.addRow("Fases por unidade:", self.fases)

        self.modelo = QtWidgets.QComboBox()
        self.modelo.addItems(list(regras.MODELOS))
        modelo_atual = str(atual.get("Modelo", "Automático") or "Automático")
        if modelo_atual in regras.MODELOS:
            self.modelo.setCurrentText(modelo_atual)
        form_dim.addRow("Modelo de caixa:", self.modelo)

        self.cdpm = QtWidgets.QComboBox()
        opcoes_cdpm = ["Automático"] + list(regras.CDPM)
        self.cdpm.addItems(opcoes_cdpm)
        cdpm_atual = str(atual.get("CDPM", "Automático") or "Automático")
        if cdpm_atual in opcoes_cdpm:
            self.cdpm.setCurrentText(cdpm_atual)
        form_dim.addRow("CDPM (caixas P):", self.cdpm)

        self.tensao = QtWidgets.QDoubleSpinBox()
        self.tensao.setRange(110.0, 690.0)
        self.tensao.setDecimals(0)
        self.tensao.setSuffix(" V")
        self.tensao.setValue(float(atual.get("Tensao", 220.0) or 220.0))
        form_dim.addRow("Tensão entre fases:", self.tensao)

        self.comprimento_ramal = QtWidgets.QDoubleSpinBox()
        self.comprimento_ramal.setRange(1.0, 500.0)
        self.comprimento_ramal.setDecimals(1)
        self.comprimento_ramal.setSuffix(" m")
        self.comprimento_ramal.setValue(float(atual.get("ComprimentoRamal", 10.0) or 10.0))
        self.comprimento_ramal.setToolTip("Comprimento do ramal de distribuição entre QDC e medição")
        form_dim.addRow("Comprimento do ramal:", self.comprimento_ramal)

        abas.addTab(aba_dim, "Dimensionamento (Enel SP)")

        # --- Aba 2: Layout e Dimensões ---
        aba_layout = QtWidgets.QWidget()
        form_layout = QtWidgets.QFormLayout(aba_layout)

        self.posicao_cdpm = QtWidgets.QComboBox()
        self.posicao_cdpm.addItems(list(regras.POSICOES_CDPM))
        pos_atual = str(atual.get("PosicaoCDPM", "Centro") or "Centro")
        if pos_atual in regras.POSICOES_CDPM:
            self.posicao_cdpm.setCurrentText(pos_atual)
        form_layout.addRow("Posição da CDPM:", self.posicao_cdpm)

        self.saida_eletroduto = QtWidgets.QComboBox()
        self.saida_eletroduto.addItems(list(regras.SAIDAS_ELETRODUTO))
        saida_atual = str(atual.get("SaidaEletroduto", "Fundo") or "Fundo")
        if saida_atual in regras.SAIDAS_ELETRODUTO:
            self.saida_eletroduto.setCurrentText(saida_atual)
        form_layout.addRow("Saída dos eletrodutos:", self.saida_eletroduto)

        self.altura_base = QtWidgets.QDoubleSpinBox()
        self.altura_base.setRange(0.0, 2000.0)
        self.altura_base.setDecimals(0)
        self.altura_base.setSingleStep(50.0)
        self.altura_base.setSuffix(" mm")
        self.altura_base.setSpecialValueText("Automático (Enel SP)")
        self.altura_base.setValue(float(atual.get("AlturaBase", 0.0) or 0.0))
        form_layout.addRow("Altura da base:", self.altura_base)

        def _dim_spin(chave, dica):
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(0.0, 2000.0)
            spin.setDecimals(0)
            spin.setSingleStep(10.0)
            spin.setSuffix(" mm")
            spin.setSpecialValueText("Automático (padrão Enel)")
            spin.setValue(float(atual.get(chave, 0.0) or 0.0))
            spin.setToolTip(dica)
            return spin

        self.largura_p = _dim_spin("LarguraCaixaP", "Largura da caixa P em mm (0 usa 260 mm)")
        form_layout.addRow("Largura da caixa P:", self.largura_p)

        self.profundidade_p = _dim_spin("ProfundidadeCaixaP", "Profundidade da caixa P em mm (0 usa 190 mm)")
        form_layout.addRow("Profundidade da caixa P:", self.profundidade_p)

        self.altura_p = _dim_spin("AlturaCaixaP", "Altura da caixa P em mm (0 usa 520 mm)")
        form_layout.addRow("Altura da caixa P:", self.altura_p)

        self.folga_conjuntos = _dim_spin("FolgaConjuntos", "Espaço entre agrupamentos em mm (0 usa 100 mm)")
        form_layout.addRow("Folga entre conjuntos:", self.folga_conjuntos)

        self.com_suporte = QtWidgets.QCheckBox("Estrutura de sustentação / pedestal até o piso")
        self.com_suporte.setChecked(bool(atual.get("ComSuporte", True)))
        form_layout.addRow(self.com_suporte)

        abas.addTab(aba_layout, "Layout e Dimensões")
        raiz.addWidget(abas)

        # --- Prévia em tempo real ---
        raiz.addWidget(QtWidgets.QLabel("Prévia do dimensionamento e das dimensões:"))
        self.previa = QtWidgets.QTextEdit()
        self.previa.setReadOnly(True)
        self.previa.setMinimumHeight(180)
        raiz.addWidget(self.previa)

        botoes = QtWidgets.QHBoxLayout()
        self.btn_ok = QtWidgets.QPushButton("Aplicar alterações" if editando else "Inserir na planta")
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self.accept)
        btn_cancelar = QtWidgets.QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(self.btn_ok)
        botoes.addWidget(btn_cancelar)
        raiz.addLayout(botoes)
        self.setLayout(raiz)

        for widget in (
            self.medidores, self.por_coluna, self.demanda_unidade, self.demanda_total,
            self.tensao, self.comprimento_ramal, self.altura_base,
            self.largura_p, self.profundidade_p, self.altura_p, self.folga_conjuntos,
        ):
            widget.valueChanged.connect(self.atualizar_previa)
        for combo in (self.fases, self.modelo, self.cdpm, self.posicao_cdpm, self.saida_eletroduto):
            combo.currentIndexChanged.connect(self.atualizar_previa)
        self.com_suporte.toggled.connect(self.atualizar_previa)

        self.atualizar_previa()

    def get_dados(self):
        """Retorna dict com os nomes exatos das propriedades de ``ColunaMedicao``."""
        return {
            "Medidores": int(self.medidores.value()),
            "MedidoresPorColuna": int(self.por_coluna.value()),
            "DemandaPorMedidor": float(self.demanda_unidade.value()),
            "DemandaTotal": float(self.demanda_total.value()),
            "Fases": int(self.fases.currentText()),
            "Modelo": self.modelo.currentText(),
            "CDPM": self.cdpm.currentText(),
            "Tensao": float(self.tensao.value()),
            "ComprimentoRamal": float(self.comprimento_ramal.value()),
            "PosicaoCDPM": self.posicao_cdpm.currentText(),
            "SaidaEletroduto": self.saida_eletroduto.currentText(),
            "AlturaBase": float(self.altura_base.value()),
            "LarguraCaixaP": float(self.largura_p.value()),
            "ProfundidadeCaixaP": float(self.profundidade_p.value()),
            "AlturaCaixaP": float(self.altura_p.value()),
            "FolgaConjuntos": float(self.folga_conjuntos.value()),
            "ComSuporte": self.com_suporte.isChecked(),
        }

    def atualizar_previa(self):
        dados = self.get_dados()
        cdpm = None if dados["CDPM"] == "Automático" else dados["CDPM"]
        caixa_p = (dados["LarguraCaixaP"], dados["ProfundidadeCaixaP"], dados["AlturaCaixaP"])
        try:
            dim = regras.dimensionar_colunas(
                dados["Medidores"], dados["DemandaPorMedidor"], dados["Fases"],
                dados["MedidoresPorColuna"], dados["Modelo"], cdpm,
                dados["DemandaTotal"], dados["Tensao"], dados["ComprimentoRamal"],
            )
            pecas = regras.pecas_do_centro(
                dim, posicao_cdpm=dados["PosicaoCDPM"], altura_base_mm=dados["AlturaBase"],
                caixa_p_mm=caixa_p if any(v > 0 for v in caixa_p) else None,
                saida_eletroduto=dados["SaidaEletroduto"],
                folga_conjuntos_mm=dados["FolgaConjuntos"],
                com_suporte=dados["ComSuporte"],
            )
            avisos_layout = regras.avisos_layout_enel(
                dim, pecas, posicao_cdpm=dados["PosicaoCDPM"], altura_base_mm=dados["AlturaBase"],
            )
            self.previa.setPlainText(regras.resumo_coluna(dim, pecas, avisos_extras=avisos_layout))
        except ValueError as erro:
            self.previa.setPlainText(f"Configuração inválida:\n{erro}")
