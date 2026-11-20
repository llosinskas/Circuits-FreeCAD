"""Pontos automáticos por ambiente: tipo, perguntas do ambiente (porta, pia, chuveiro...), luminotécnico e prévia."""
from freecad.Circuits.core import ambientes as regras
from freecad.Circuits.core import formularios
from freecad.Circuits.qt import QtCore, QtWidgets

COLUNAS = ["Gerar", "Ambiente", "Tipo", "Área (m²)", "Portas", "Tomadas (TUG)", "Iluminação", "Equipamentos"]
SEM_AR = "Sem ar-condicionado"
NAO_INFORMADA = "Não informar"
LAMPADAS = {nome: dados for nome, dados in formularios.LAMPADAS.items() if dados}


def _numero(valor, casas=0):
    return f"{valor:.{casas}f}".replace(".", ",")


class PontosAutoDialog(QtWidgets.QDialog):
    """Uma linha por ambiente e, à direita, as perguntas do ambiente selecionado.

    Args:
        ambientes: [{'nome', 'tipo', 'area', 'perimetro', 'paredes' (rótulos), 'portas_projeto'}].
        prever: função (índice, tipo, opções) -> plano de ``core.ambientes.posicoes``.
    """

    def __init__(self, ambientes, prever):
        super().__init__()
        self.setWindowTitle("Pontos automáticos")
        self.resize(1180, 620)
        self._ambientes = ambientes
        self._prever = prever
        self._opcoes = [{"porta": None, "posicao_porta": 0.5, "bancada": None, "chuveiro": 0.0,
                         "ar_condicionado": 0.0} for _ in ambientes]
        self._atual = -1
        self._carregando = False

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(
            "Previsão mínima da NBR 5410 (9.5.2). Confira o tipo de cada ambiente e responda, à direita, onde ficam a "
            "porta, a pia ou o lavatório e os equipamentos.\nAs tomadas de 600 VA ficam acima da bancada; as outras, "
            "pelo perímetro, fora das portas e dos cantos; o interruptor, ao lado da porta. Os pontos gerados antes "
            "para o ambiente são substituídos."))
        divisao = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.tabela = QtWidgets.QTableWidget(len(ambientes), len(COLUNAS))
        self.tabela.setHorizontalHeaderLabels(COLUNAS)
        self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tabela.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._linhas = []
        for linha, dados in enumerate(ambientes):
            marcar = QtWidgets.QCheckBox()
            marcar.setChecked(True)
            self.tabela.setCellWidget(linha, 0, marcar)
            self._texto(linha, 1, dados["nome"])
            combo = QtWidgets.QComboBox()
            combo.addItems(list(regras.TIPOS))
            combo.setCurrentIndex(list(regras.TIPOS).index(dados["tipo"]) if dados["tipo"] in regras.TIPOS else 0)
            combo.currentIndexChanged.connect(lambda *_, l=linha: self._tipo_mudou(l))
            self.tabela.setCellWidget(linha, 2, combo)
            self._texto(linha, 3, _numero(dados["area"], 2))
            self._linhas.append((marcar, combo))
        divisao.addWidget(self.tabela)
        divisao.addWidget(self._montar_painel())
        divisao.setStretchFactor(0, 3)
        divisao.setStretchFactor(1, 2)
        layout.addWidget(divisao, 1)
        layout.addWidget(self._montar_iluminacao())

        self.avisos = QtWidgets.QLabel("")
        self.avisos.setWordWrap(True)
        layout.addWidget(self.avisos)
        botoes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        botoes.button(QtWidgets.QDialogButtonBox.Ok).setText("Gerar pontos")
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

        self.tabela.currentCellChanged.connect(lambda linha, *_: self._mostrar(linha))
        self._atualizar_todas()
        self.tabela.resizeColumnsToContents()
        if ambientes:
            self.tabela.selectRow(0)
            self._mostrar(0)

    # --- montagem -----------------------------------------------------------------

    def _montar_painel(self):
        self.painel = QtWidgets.QGroupBox("Itens do ambiente")
        form = QtWidgets.QFormLayout(self.painel)
        self.porta = QtWidgets.QComboBox()
        self.porta.setToolTip("Parede da porta de entrada: o interruptor fica ao lado dela e as tomadas fogem dela.")
        form.addRow("Porta", self.porta)
        self.posicao_porta = QtWidgets.QSpinBox()
        self.posicao_porta.setRange(0, 100)
        self.posicao_porta.setSuffix(" % da parede")
        self.posicao_porta.setToolTip("Onde fica o meio da porta, do começo (0 %) ao fim (100 %) da parede, "
                                      "andando no sentido anti-horário do ambiente.")
        form.addRow("Posição da porta", self.posicao_porta)
        self.rotulo_bancada = QtWidgets.QLabel("Pia / bancada")
        self.bancada = QtWidgets.QComboBox()
        self.bancada.setToolTip("As tomadas de 600 VA (a 1,30 m) ficam acima da bancada: no mínimo duas na cozinha, "
                                "copa, área de serviço e lavanderia; no banheiro, a tomada junto ao lavatório.")
        form.addRow(self.rotulo_bancada, self.bancada)
        self.chuveiro = QtWidgets.QCheckBox("Chuveiro elétrico")
        self.potencia_chuveiro = QtWidgets.QSpinBox()
        self.potencia_chuveiro.setRange(2000, 9000)
        self.potencia_chuveiro.setSingleStep(100)
        self.potencia_chuveiro.setValue(int(regras.CHUVEIRO_W))
        self.potencia_chuveiro.setSuffix(" W")
        form.addRow(self.chuveiro, self.potencia_chuveiro)
        self.rotulo_ar = QtWidgets.QLabel("Ar-condicionado")
        self.ar = QtWidgets.QComboBox()
        self.ar.addItems([SEM_AR] + list(regras.AR_CONDICIONADO))
        self.ar.setToolTip("Ponto de ar-condicionado (circuito exclusivo) na parede mais comprida sem porta.")
        form.addRow(self.rotulo_ar, self.ar)
        self.resumo = QtWidgets.QLabel("")
        self.resumo.setWordWrap(True)
        self.resumo.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        form.addRow(self.resumo)
        for sinal in (self.porta.currentIndexChanged, self.posicao_porta.valueChanged,
                      self.bancada.currentIndexChanged, self.chuveiro.toggled, self.potencia_chuveiro.valueChanged,
                      self.ar.currentIndexChanged):
            sinal.connect(lambda *_: self._ler_painel())
        return self.painel

    def _montar_iluminacao(self):
        caixa = QtWidgets.QGroupBox("Iluminação")
        linha = QtWidgets.QHBoxLayout(caixa)
        rotulo = QtWidgets.QLabel("Luminárias pelo luminotécnico (método dos lúmens):")
        rotulo.setToolTip("Quantidade pela iluminância do tipo de ambiente (NBR ISO/CIE 8995-1, antiga "
                          "NBR 5413), em malha dentro do ambiente.")
        linha.addWidget(rotulo)
        self.lampada = QtWidgets.QComboBox()
        self.lampada.addItems(list(LAMPADAS))
        self.lampada.setCurrentIndex(1 if len(LAMPADAS) > 1 else 0)
        linha.addWidget(self.lampada, 1)
        linha.addWidget(QtWidgets.QLabel("Pé-direito"))
        self.pe_direito = QtWidgets.QDoubleSpinBox()
        self.pe_direito.setRange(2.2, 10.0)
        self.pe_direito.setSingleStep(0.05)
        self.pe_direito.setValue(2.7)
        self.pe_direito.setSuffix(" m")
        linha.addWidget(self.pe_direito)
        for sinal in (self.lampada.currentIndexChanged, self.pe_direito.valueChanged):
            sinal.connect(lambda *_: self._atualizar_todas())
        return caixa

    # --- painel do ambiente -----------------------------------------------------------

    def _mostrar(self, linha):
        if not 0 <= linha < len(self._ambientes):
            return
        self._atual = linha
        dados, opcoes = self._ambientes[linha], self._opcoes[linha]
        tipo = self._linhas[linha][1].currentText()
        self._carregando = True
        self.painel.setTitle(f"Itens do ambiente: {dados['nome']}")
        self.porta.clear()
        self.porta.addItem(f"Portas do projeto ({dados['portas_projeto']} encontrada(s))", None)
        for indice, rotulo in enumerate(dados["paredes"]):
            self.porta.addItem(rotulo, indice)
        self.porta.addItem("Sem porta", regras.SEM_PORTA)
        self.porta.setCurrentIndex(max(0, self.porta.findData(opcoes["porta"])) if opcoes["porta"] is not None else 0)
        self.posicao_porta.setValue(round(opcoes["posicao_porta"] * 100))
        self.posicao_porta.setEnabled(isinstance(opcoes["porta"], int))

        pergunta = regras.pergunta_bancada(tipo)
        self.bancada.clear()
        self.bancada.addItem(NAO_INFORMADA, None)
        for indice, rotulo in enumerate(dados["paredes"]):
            self.bancada.addItem(rotulo, indice)
        self.bancada.setCurrentIndex(0 if opcoes["bancada"] is None else self.bancada.findData(opcoes["bancada"]))
        self.rotulo_bancada.setText("Lavatório" if pergunta == "lavatório" else "Pia / bancada")
        for widget in (self.rotulo_bancada, self.bancada):
            widget.setVisible(pergunta is not None)

        self.chuveiro.setChecked(opcoes["chuveiro"] > 0)
        if opcoes["chuveiro"] > 0:
            self.potencia_chuveiro.setValue(int(opcoes["chuveiro"]))
        for widget in (self.chuveiro, self.potencia_chuveiro):
            widget.setVisible(regras.tem_chuveiro(tipo))
        ar = next((nome for nome, va in regras.AR_CONDICIONADO.items() if va == opcoes["ar_condicionado"]), SEM_AR)
        self.ar.setCurrentText(ar)
        for widget in (self.rotulo_ar, self.ar):
            widget.setVisible(regras.tem_ar_condicionado(tipo))
        self._carregando = False
        self._mostrar_resumo(linha)

    def _ler_painel(self):
        if self._carregando or self._atual < 0:
            return
        opcoes = self._opcoes[self._atual]
        opcoes["porta"] = self.porta.currentData()
        opcoes["posicao_porta"] = self.posicao_porta.value() / 100.0
        self.posicao_porta.setEnabled(isinstance(opcoes["porta"], int))
        tipo = self._linhas[self._atual][1].currentText()
        opcoes["bancada"] = self.bancada.currentData() if regras.pergunta_bancada(tipo) else None
        opcoes["chuveiro"] = float(self.potencia_chuveiro.value()) if self.chuveiro.isChecked() else 0.0
        opcoes["ar_condicionado"] = regras.AR_CONDICIONADO.get(self.ar.currentText(), 0.0)
        self._atualizar(self._atual)
        self._mostrar_avisos()

    def _tipo_mudou(self, linha):
        tipo = self._linhas[linha][1].currentText()
        opcoes = self._opcoes[linha]
        if not regras.pergunta_bancada(tipo):
            opcoes["bancada"] = None
        if not regras.tem_chuveiro(tipo):
            opcoes["chuveiro"] = 0.0
        if not regras.tem_ar_condicionado(tipo):
            opcoes["ar_condicionado"] = 0.0
        self._atualizar(linha)
        self._mostrar_avisos()
        if linha == self._atual:
            self._mostrar(linha)

    # --- prévia ---------------------------------------------------------------------

    def _luminotecnico(self):
        lampada = LAMPADAS[self.lampada.currentText()]
        return {"fluxo": lampada["fluxo_luminaria"], "potencia": lampada["potencia"],
                "simbolo": formularios.SIMBOLOS_ILUMINACAO.get(lampada.get("simbolo"), "luz_teto"),
                "pe_direito": self.pe_direito.value()}

    def opcoes(self, linha):
        """Opções do ambiente para ``core.ambientes.posicoes``."""
        return dict(self._opcoes[linha], luminotecnico=self._luminotecnico())

    def _plano(self, linha):
        return self._prever(linha, self._linhas[linha][1].currentText(), self.opcoes(linha))

    def _texto(self, linha, coluna, texto):
        item = QtWidgets.QTableWidgetItem(str(texto))
        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
        self.tabela.setItem(linha, coluna, item)

    def _atualizar(self, linha):
        plano = self._plano(linha)
        previsao = plano["previsao"]
        potencias = previsao["potencias"]
        self._texto(linha, 4, plano["portas"])
        self._texto(linha, 5, f"{previsao['tugs']}: " + ", ".join(
            f"{potencias.count(p)} × {p:.0f} VA" for p in sorted(set(potencias), reverse=True)))
        calculo = plano["luminotecnico"]
        self._texto(linha, 6, f"{calculo['quantidade']} × {calculo['potencia_ponto']:.0f} VA · "
                              f"{calculo['iluminancia_resultante']:.0f} lx")
        self._texto(linha, 7, ", ".join(f"{e['simbolo'].replace('_', ' ')} {e['potencia']:.0f}"
                                        for e in plano["equipamentos"]) or "–")
        if linha == self._atual:
            self._mostrar_resumo(linha, plano)

    def _mostrar_resumo(self, linha, plano=None):
        plano = plano or self._plano(linha)
        previsao, calculo = plano["previsao"], plano["luminotecnico"]
        texto = [f"NBR 5410: {previsao['tugs']} TUG, {previsao['total_tug_va']:.0f} VA; "
                 f"iluminação mínima {previsao['iluminacao_va']:.0f} VA."]
        if calculo:
            texto.append(
                f"Luminotécnico: {calculo['iluminancia']:.0f} lx mantidos no plano a "
                f"{_numero(calculo['plano_trabalho'], 2)} m; "
                f"K = {_numero(calculo['indice_local'], 2)}, U = {_numero(calculo['fator_utilizacao'], 2)}, "
                f"Fm = {_numero(calculo['fator_manutencao'], 2)}; calculadas {_numero(calculo['quantidade_calculada'], 1)}"
                f" → {calculo['quantidade']} luminária(s), {calculo['iluminancia_resultante']:.0f} lx; espaçamento até "
                f"{_numero(calculo['espacamento_maximo'], 2)} m. Cada ponto entra com "
                f"{calculo['potencia_ponto']:.0f} VA (o maior entre a luminária e a parte dela nos "
                f"{calculo['carga_nbr']:.0f} VA da NBR 5410).")
        self.resumo.setText("\n\n".join(texto))

    def _atualizar_todas(self):
        for linha in range(len(self._ambientes)):
            self._atualizar(linha)
        self._mostrar_avisos()

    def _mostrar_avisos(self):
        textos = []
        for linha in range(len(self._ambientes)):
            textos += [f"{self._ambientes[linha]['nome']}: {a}" for a in self._plano(linha)["avisos"]]
        self.avisos.setText("\n".join(textos[:12]))

    def get_dados(self):
        """[(índice do ambiente, tipo, opções)] das linhas marcadas."""
        return [(linha, combo.currentText(), self.opcoes(linha)) for linha, (marcar, combo) in enumerate(self._linhas)
                if marcar.isChecked()]
