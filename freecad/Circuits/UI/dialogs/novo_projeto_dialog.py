"""Diálogo do botão Novo projeto: identificação, edificação e pavimentos, fornecimento, condutores e proteção."""
from freecad.Circuits.core import novo_projeto as regras
from freecad.Circuits.core import parametros as campos
from freecad.Circuits.qt import QtCore, QtWidgets

CARIMBO = (("projeto", "Nome do projeto"), ("obra", "Obra / endereço"), ("cliente", "Cliente"),
           ("responsavel", "Responsável técnico"), ("registro", "CREA / CFT"), ("desenhista", "Desenhista"))


def _numero(texto, padrao=0.0):
    try:
        return float(str(texto).replace(",", ".").strip())
    except ValueError:
        return padrao


def _metros(mm):
    return f"{float(mm) / 1000.0:.2f}".replace(".", ",")


def _combo(opcoes, atual=None):
    combo = QtWidgets.QComboBox()
    combo.addItems([str(o) for o in opcoes])
    if atual is not None and str(atual) in [str(o) for o in opcoes]:
        combo.setCurrentText(str(atual))
    return combo


def _duplo(valor, minimo, maximo, decimais=2, sufixo=""):
    campo = QtWidgets.QDoubleSpinBox()
    campo.setRange(minimo, maximo)
    campo.setDecimals(decimais)
    campo.setValue(float(valor))
    if sufixo:
        campo.setSuffix(sufixo)
    return campo


class NovoProjetoDialog(QtWidgets.QDialog):
    """Devolve em ``get_dados`` o dicionário de ``core.novo_projeto`` (pavimentos em mm)."""

    def __init__(self, dados, bim_disponivel=True, editando=False):
        super().__init__()
        self.dados = dict(dados)
        self.setWindowTitle("Editar projeto elétrico" if editando else "Novo projeto elétrico")
        self.setMinimumSize(760, 560)
        raiz = QtWidgets.QVBoxLayout(self)
        aviso = QtWidgets.QLabel(
            "Preencha o que já sabe: tudo pode ser mudado depois (Parâmetros, Pavimento, ou abrindo este botão de "
            "novo). Os dados vão para o carimbo das folhas, o dimensionamento pela NBR 5410 e o memorial.")
        aviso.setWordWrap(True)
        raiz.addWidget(aviso)
        abas = QtWidgets.QTabWidget()
        abas.addTab(self._aba_identificacao(), "Identificação")
        abas.addTab(self._aba_pavimentos(bim_disponivel, editando), "Edificação e pavimentos")
        abas.addTab(self._aba_fornecimento(), "Fornecimento de energia")
        abas.addTab(self._aba_condutores(), "Condutores e proteção")
        raiz.addWidget(abas)
        self.resumo = QtWidgets.QLabel()
        self.resumo.setWordWrap(True)
        raiz.addWidget(self.resumo)
        botoes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        botoes.button(QtWidgets.QDialogButtonBox.Ok).setText("Aplicar" if editando else "Criar projeto")
        botoes.accepted.connect(self._aceitar)
        botoes.rejected.connect(self.reject)
        raiz.addWidget(botoes)
        self._preencher_tabela(self.dados.get("pavimentos") or [])
        self.atualizar_resumo()

    # --- abas -------------------------------------------------------------------------------------

    def _aba_identificacao(self):
        aba = QtWidgets.QWidget()
        formulario = QtWidgets.QFormLayout(aba)
        self.textos = {}
        for chave, rotulo in CARIMBO:
            campo = QtWidgets.QLineEdit(str(self.dados.get(chave, "") or ""))
            campo.setToolTip(campos.CAMPOS[chave][2])
            self.textos[chave] = campo
            formulario.addRow(rotulo + ":", campo)
        self.tipo = _combo(regras.TIPOS_EDIFICACAO, self.dados.get("tipo_edificacao"))
        self.tipo.setToolTip("Ao trocar, sugere pavimentos, tensões, fornecimento e curto na entrada")
        formulario.addRow("Tipo de edificação:", self.tipo)
        return aba

    def _aba_pavimentos(self, bim_disponivel, editando):
        aba = QtWidgets.QWidget()
        caixa = QtWidgets.QVBoxLayout(aba)
        grade = QtWidgets.QGridLayout()
        lista = self.dados.get("pavimentos") or []
        sugestao = regras.SUGESTOES.get(self.tipo.currentText(), regras.SUGESTOES[regras.TIPOS_EDIFICACAO[0]])
        acima = [p for p in lista if p["nome"] not in (regras.TERREO, regras.COBERTURA)
                 and not p["nome"].startswith("Subsolo")]
        self.subsolos = QtWidgets.QSpinBox()
        self.subsolos.setRange(0, regras.MAXIMO_SUBSOLOS)
        self.subsolos.setValue(sum(1 for p in lista if p["nome"].startswith("Subsolo")))
        self.andares = QtWidgets.QSpinBox()
        self.andares.setRange(0, regras.MAXIMO_ANDARES)
        self.andares.setValue(len(acima))
        self.andares.setToolTip("Andares acima do térreo: 1º Pavimento, 2º Pavimento...")
        self.cobertura = QtWidgets.QCheckBox("Cobertura (casa de máquinas, barrilete)")
        self.cobertura.setChecked(any(p["nome"] == regras.COBERTURA for p in lista))
        terreo = next((p for p in lista if p["nome"] == regras.TERREO), None)
        self.altura_terreo = _duplo((terreo["altura"] if terreo else sugestao["altura_terreo"]) / 1000.0,
                                    2.0, 20.0, sufixo=" m")
        self.piso_a_piso = _duplo((acima[0]["altura"] if acima else sugestao["piso_a_piso"]) / 1000.0,
                                  2.0, 20.0, sufixo=" m")
        self.cota_terreo = _duplo((terreo["cota"] if terreo else 0.0) / 1000.0, -50.0, 500.0, sufixo=" m")
        self.unidades = QtWidgets.QSpinBox()
        self.unidades.setRange(0, 200)
        self.unidades.setValue(max([int(p.get("unidades") or 0) for p in acima] or
                                   [int((terreo or {}).get("unidades") or 0) if not acima else 0] or [0]))
        self.unidades.setToolTip("Apartamentos ou salas de cada andar acima do térreo (com o térreo só, nele). "
                                 "Vão para as prumadas (uma seta por apartamento) e para o centro de medição.")
        for linha, (rotulo, campo) in enumerate((("Subsolos:", self.subsolos), ("Andares acima do térreo:", self.andares),
                                                  ("Piso a piso do térreo:", self.altura_terreo),
                                                  ("Piso a piso dos andares:", self.piso_a_piso),
                                                  ("Cota do piso do térreo:", self.cota_terreo),
                                                  ("Unidades por andar:", self.unidades))):
            grade.addWidget(QtWidgets.QLabel(rotulo), linha // 2, (linha % 2) * 2)
            grade.addWidget(campo, linha // 2, (linha % 2) * 2 + 1)
        grade.addWidget(self.cobertura, 3, 0, 1, 4)
        caixa.addLayout(grade)
        gerar = QtWidgets.QPushButton("Gerar a lista de pavimentos")
        gerar.setToolTip("Refaz a tabela com os números acima (os nomes e cotas editados à mão se perdem)")
        gerar.clicked.connect(self.gerar_pavimentos)
        caixa.addWidget(gerar)
        self.tabela = QtWidgets.QTableWidget(0, 4)
        self.tabela.setHorizontalHeaderLabels(["Pavimento", "Cota do piso [m]", "Piso a piso [m]", "Unidades"])
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        cabecalho.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.tabela.itemChanged.connect(self.atualizar_resumo)
        caixa.addWidget(self.tabela)
        self.niveis_bim = QtWidgets.QCheckBox("Pavimentos como níveis da bancada BIM (como o botão Nível do BIM; "
                                              "andares no IFC)")
        self.niveis_bim.setChecked(bool(self.dados.get("niveis_bim")) and bim_disponivel)
        self.niveis_bim.setEnabled(bim_disponivel)
        self.niveis_bim.setToolTip("Marcado (o padrão), cada pavimento é um nível do BIM dentro do edifício do projeto, "
                                   "com as pastas de Tomadas, Iluminação, Quadros... dentro dele. Num projeto com "
                                   "pavimentos em pasta, marcar converte cada um em nível, levando o que está dentro. "
                                   "Níveis do BIM existentes mantêm a cota e a altura deles. Sem marcar, cada pavimento "
                                   "é uma pasta da bancada.")
        caixa.addWidget(self.niveis_bim)
        if editando:
            nota = QtWidgets.QLabel("Pavimentos que saírem da lista não são apagados.")
            caixa.addWidget(nota)
        for campo in (self.subsolos, self.andares, self.unidades):
            campo.valueChanged.connect(self.gerar_pavimentos)
        self.cobertura.toggled.connect(self.gerar_pavimentos)
        for campo in (self.altura_terreo, self.piso_a_piso, self.cota_terreo):
            campo.editingFinished.connect(self.gerar_pavimentos)
        self.tipo.currentTextChanged.connect(self.aplicar_sugestao)
        return aba

    def _aba_fornecimento(self):
        aba = QtWidgets.QWidget()
        formulario = QtWidgets.QFormLayout(aba)
        self.concessionaria = QtWidgets.QLineEdit(str(self.dados.get("concessionaria", "") or ""))
        self.concessionaria.setPlaceholderText("Ex.: Enel SP, Copel, Cemig, Light")
        formulario.addRow("Concessionária:", self.concessionaria)
        self.sistema = _combo(regras.SISTEMAS, self.dados.get("sistema"))
        self.sistema.setToolTip("Tensões fase-neutro / fase-fase da rede")
        formulario.addRow("Sistema de tensões:", self.sistema)
        self.fornecimento = _combo(regras.FORNECIMENTOS, self.dados.get("fornecimento"))
        formulario.addRow("Fornecimento:", self.fornecimento)
        self.icc = _duplo(self.dados.get("icc_entrada_ka") or 5.0, 0.5, 100.0, 1, " kA")
        self.icc.setToolTip(campos.CAMPOS["icc_entrada_ka"][2])
        formulario.addRow("Curto-circuito na entrada:", self.icc)
        self.esquema = _combo(campos.ESQUEMAS, self.dados.get("esquema"))
        self.esquema.setToolTip(campos.CAMPOS["esquema"][2])
        formulario.addRow("Esquema de aterramento:", self.esquema)
        self.terra = _duplo(self.dados.get("resistencia_terra") or 10.0, 0.1, 1000.0, 1, " Ω")
        self.terra.setToolTip(campos.CAMPOS["resistencia_terra"][2])
        formulario.addRow("Resistência de aterramento:", self.terra)
        for sinal in (self.sistema.currentTextChanged, self.fornecimento.currentTextChanged,
                      self.esquema.currentTextChanged):
            sinal.connect(self.atualizar_resumo)
        return aba

    def _aba_condutores(self):
        aba = QtWidgets.QWidget()
        formulario = QtWidgets.QFormLayout(aba)
        self.material = _combo(campos.MATERIAIS, self.dados.get("material"))
        formulario.addRow("Material dos condutores:", self.material)
        self.isolacao = _combo(campos.ISOLACOES, self.dados.get("isolacao"))
        formulario.addRow("Isolação:", self.isolacao)
        self.temperatura = _duplo(self.dados.get("temperatura_ambiente") or 30.0, 10.0, 60.0, 0, " °C")
        formulario.addRow("Temperatura ambiente:", self.temperatura)
        self.curva_iluminacao = _combo(("B", "C", "D"), self.dados.get("curva_iluminacao") or "B")
        formulario.addRow("Curva dos disjuntores de iluminação:", self.curva_iluminacao)
        self.curva_tomadas = _combo(("B", "C", "D"), self.dados.get("curva_tomadas") or "C")
        formulario.addRow("Curva dos disjuntores de tomadas:", self.curva_tomadas)
        self.dr = _combo(("30", "100", "300", "500"), f"{float(self.dados.get('sensibilidade_dr') or 30):g}")
        formulario.addRow("Sensibilidade do DR [mA]:", self.dr)
        return aba

    # --- comportamento ----------------------------------------------------------------------------

    def aplicar_sugestao(self, tipo):
        sugestao = regras.SUGESTOES.get(tipo)
        if not sugestao:
            return
        for campo, valor in ((self.subsolos, sugestao["subsolos"]), (self.andares, sugestao["andares"]),
                             (self.unidades, sugestao.get("unidades", 0))):
            campo.blockSignals(True)
            campo.setValue(valor)
            campo.blockSignals(False)
        self.cobertura.blockSignals(True)
        self.cobertura.setChecked(sugestao["cobertura"])
        self.cobertura.blockSignals(False)
        self.altura_terreo.setValue(sugestao["altura_terreo"] / 1000.0)
        self.piso_a_piso.setValue(sugestao["piso_a_piso"] / 1000.0)
        self.sistema.setCurrentText(sugestao["sistema"])
        self.fornecimento.setCurrentText(sugestao["fornecimento"])
        self.esquema.setCurrentText(sugestao["esquema"])
        self.icc.setValue(sugestao["icc_entrada_ka"])
        self.gerar_pavimentos()

    def gerar_pavimentos(self, *_):
        lista = regras.pavimentos(self.subsolos.value(), self.andares.value(), self.cobertura.isChecked(),
                                  self.piso_a_piso.value() * 1000.0, self.altura_terreo.value() * 1000.0,
                                  self.cota_terreo.value() * 1000.0, unidades_por_andar=self.unidades.value())
        self._preencher_tabela(lista)
        self.atualizar_resumo()

    def _preencher_tabela(self, lista):
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(len(lista))
        for i, pav in enumerate(lista):
            valores = (pav["nome"], _metros(pav["cota"]), _metros(pav["altura"]), str(int(pav.get("unidades") or 0)))
            for coluna, valor in enumerate(valores):
                item = QtWidgets.QTableWidgetItem(valor)
                if pav.get("bim") and coluna in (1, 2):
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                    item.setToolTip("Nível da bancada BIM: cota e altura são editadas no próprio nível")
                self.tabela.setItem(i, coluna, item)
        self.tabela.blockSignals(False)

    def pavimentos(self):
        lista = []
        for i in range(self.tabela.rowCount()):
            celulas = [self.tabela.item(i, c) for c in range(4)]
            if any(c is None for c in celulas[:3]):
                continue
            unidades = int(_numero(celulas[3].text() if celulas[3] is not None else 0, 0.0))
            lista.append({"nome": celulas[0].text().strip(), "cota": _numero(celulas[1].text()) * 1000.0,
                          "altura": _numero(celulas[2].text()) * 1000.0, "unidades": unidades})
        return lista

    def get_dados(self):
        dados = {chave: campo.text().strip() for chave, campo in self.textos.items()}
        dados.update({
            "tipo_edificacao": self.tipo.currentText(),
            "pavimentos": self.pavimentos(),
            "niveis_bim": self.niveis_bim.isChecked(),
            "concessionaria": self.concessionaria.text().strip(),
            "sistema": self.sistema.currentText(),
            "fornecimento": self.fornecimento.currentText(),
            "icc_entrada_ka": float(self.icc.value()),
            "esquema": self.esquema.currentText(),
            "resistencia_terra": float(self.terra.value()),
            "material": self.material.currentText(),
            "isolacao": self.isolacao.currentText(),
            "temperatura_ambiente": float(self.temperatura.value()),
            "curva_iluminacao": self.curva_iluminacao.currentText(),
            "curva_tomadas": self.curva_tomadas.currentText(),
            "sensibilidade_dr": float(self.dr.currentText()),
        })
        return dados

    def atualizar_resumo(self, *_):
        dados = self.get_dados()
        erros = regras.validar(dados)
        texto = "Será criado: " + regras.resumo(dados) + "."
        if erros:
            texto = "<span style='color:#c5221f'>" + " ".join(erros) + "</span>"
        self.resumo.setText(texto)

    def _aceitar(self):
        erros = regras.validar(self.get_dados())
        if erros:
            QtWidgets.QMessageBox.warning(self, "Projeto", "\n".join(erros))
            return
        self.accept()
