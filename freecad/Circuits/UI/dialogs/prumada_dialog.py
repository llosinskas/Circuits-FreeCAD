"""Diálogo das prumadas verticais: sistemas, andares e cabos por unidade, com prévia dos trechos."""
from freecad.Circuits.core import ocupacao
from freecad.Circuits.core import prumadas as regras
from freecad.Circuits.qt import QtWidgets

SECOES = ["6", "10", "16", "25", "35", "50", "70", "95", "120"]
SECOES_EMERGENCIA = ["1,5", "2,5", "4"]
PROPRIEDADE_DO_SISTEMA = {"energia": "Energia", "dados": "Dados", "interfone": "Interfone",
                          "emergencia": "IluminacaoEmergencia"}


def _combo(opcoes, atual):
    combo = QtWidgets.QComboBox()
    combo.addItems([str(o) for o in opcoes])
    if str(atual) in [str(o) for o in opcoes]:
        combo.setCurrentText(str(atual))
    return combo


def _numero(texto):
    return float(str(texto).replace(",", "."))


class PrumadaDialog(QtWidgets.QDialog):
    """Devolve em ``get_dados`` as propriedades do objeto ``Prumada`` (``Andares`` como lista de dicionários)."""

    def __init__(self, andares, atual=None, editando=False):
        super().__init__()
        atual = atual or {}
        self.setWindowTitle("Editar prumadas verticais" if editando else "Prumadas verticais")
        self.setMinimumWidth(720)
        raiz = QtWidgets.QVBoxLayout(self)
        texto = QtWidgets.QLabel(
            "Prumadas de energia, dados, interfone e iluminação de emergência pelo shaft, do andar mais baixo "
            "(origem: centro de medição, DG, portaria e central de emergência) aos andares. Depois de confirmar, "
            "clique na planta no ponto do shaft.")
        texto.setWordWrap(True)
        raiz.addWidget(texto)

        linha = QtWidgets.QHBoxLayout()
        self.sistemas = {}
        for chave, propriedade in PROPRIEDADE_DO_SISTEMA.items():
            caixa = QtWidgets.QCheckBox(regras.SISTEMAS[chave][0])
            caixa.setChecked(bool(atual.get(propriedade, True)))
            caixa.toggled.connect(self.atualizar_previa)
            self.sistemas[chave] = caixa
            linha.addWidget(caixa)
        raiz.addLayout(linha)

        corpo = QtWidgets.QHBoxLayout()
        self.tabela = QtWidgets.QTableWidget(len(andares), 3)
        self.tabela.setHorizontalHeaderLabels(["Pavimento", "Cota do piso [m]", "Unidades"])
        for i, a in enumerate(andares):
            self.tabela.setItem(i, 0, QtWidgets.QTableWidgetItem(a["nome"]))
            self.tabela.setItem(i, 1, QtWidgets.QTableWidgetItem(f"{a['cota'] / 1000.0:.2f}".replace(".", ",")))
            self.tabela.setItem(i, 2, QtWidgets.QTableWidgetItem(str(a["unidades"])))
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.itemChanged.connect(self.atualizar_previa)
        corpo.addWidget(self.tabela, 3)

        formulario = QtWidgets.QFormLayout()
        p = regras.PADROES
        self.secao = _combo(SECOES, f"{float(atual.get('SecaoAlimentador', p['secao_alimentador'])):g}")
        formulario.addRow("Alimentador de cada unidade [mm²]:", self.secao)
        self.condutores = QtWidgets.QSpinBox()
        self.condutores.setRange(2, 5)
        self.condutores.setValue(int(atual.get("CondutoresPorUnidade", p["condutores_por_unidade"])))
        self.condutores.setToolTip("2 fases, neutro e PE = 4")
        formulario.addRow("Condutores por unidade:", self.condutores)
        self.forma = _combo(regras.FORMAS_ENERGIA, atual.get("FormaEnergia", p["forma_energia"]))
        formulario.addRow("Energia em:", self.forma)
        self.pontos = QtWidgets.QSpinBox()
        self.pontos.setRange(1, 24)
        self.pontos.setValue(int(atual.get("PontosDados", p["pontos_dados"])))
        formulario.addRow("Cabos UTP por unidade:", self.pontos)
        self.eletroduto_dados = _combo(list(ocupacao.DIAMETROS_INTERNOS), atual.get("EletrodutoDados",
                                                                                     p["eletroduto_dados"]))
        formulario.addRow("Eletroduto de dados:", self.eletroduto_dados)
        self.interfone = QtWidgets.QSpinBox()
        self.interfone.setRange(1, 4)
        self.interfone.setValue(int(atual.get("CabosInterfone", p["cabos_interfone"])))
        formulario.addRow("Cabos de interfone por unidade:", self.interfone)
        self.eletroduto_interfone = _combo(list(ocupacao.DIAMETROS_INTERNOS),
                                           atual.get("EletrodutoInterfone", p["eletroduto_interfone"]))
        formulario.addRow("Eletroduto de interfone:", self.eletroduto_interfone)
        self.circuitos = QtWidgets.QSpinBox()
        self.circuitos.setRange(1, 6)
        self.circuitos.setValue(int(atual.get("CircuitosEmergencia", p["circuitos_emergencia"])))
        formulario.addRow("Circuitos de emergência:", self.circuitos)
        self.secao_emergencia = _combo(SECOES_EMERGENCIA, f"{float(atual.get('SecaoEmergencia', p['secao_emergencia'])):g}"
                                       .replace(".", ","))
        formulario.addRow("Seção da emergência [mm²]:", self.secao_emergencia)
        self.tipo = _combo(("Rígido", "Flexível"), atual.get("TipoEletroduto", p["tipo_eletroduto"]))
        formulario.addRow("Eletrodutos:", self.tipo)
        corpo.addLayout(formulario, 2)
        raiz.addLayout(corpo)
        for widget in (self.secao, self.forma, self.eletroduto_dados, self.eletroduto_interfone,
                       self.secao_emergencia, self.tipo):
            widget.currentIndexChanged.connect(self.atualizar_previa)
        for widget in (self.condutores, self.pontos, self.interfone, self.circuitos):
            widget.valueChanged.connect(self.atualizar_previa)

        raiz.addWidget(QtWidgets.QLabel("Prévia dos trechos:"))
        self.previa = QtWidgets.QTextEdit()
        self.previa.setReadOnly(True)
        self.previa.setMinimumHeight(170)
        raiz.addWidget(self.previa)
        botoes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        botoes.button(QtWidgets.QDialogButtonBox.Ok).setText("Aplicar" if editando else "Posicionar no shaft")
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        raiz.addWidget(botoes)
        self.atualizar_previa()

    def andares(self):
        lista = []
        for i in range(self.tabela.rowCount()):
            try:
                nome = self.tabela.item(i, 0).text().strip()
                cota = _numero(self.tabela.item(i, 1).text()) * 1000.0
                unidades = int(_numero(self.tabela.item(i, 2).text() or 0))
            except (AttributeError, ValueError):
                continue
            if nome:
                lista.append(regras.andar(nome, cota, unidades))
        return lista

    def get_dados(self):
        dados = {PROPRIEDADE_DO_SISTEMA[chave]: caixa.isChecked() for chave, caixa in self.sistemas.items()}
        dados.update({
            "Andares": self.andares(),
            "SecaoAlimentador": _numero(self.secao.currentText()),
            "CondutoresPorUnidade": int(self.condutores.value()),
            "FormaEnergia": self.forma.currentText(),
            "PontosDados": int(self.pontos.value()),
            "EletrodutoDados": self.eletroduto_dados.currentText(),
            "CabosInterfone": int(self.interfone.value()),
            "EletrodutoInterfone": self.eletroduto_interfone.currentText(),
            "CircuitosEmergencia": int(self.circuitos.value()),
            "SecaoEmergencia": _numero(self.secao_emergencia.currentText()),
            "TipoEletroduto": self.tipo.currentText(),
        })
        return dados

    def parametros(self):
        d = self.get_dados()
        return {"sistemas": [c for c, caixa in self.sistemas.items() if caixa.isChecked()],
                "secao_alimentador": d["SecaoAlimentador"], "condutores_por_unidade": d["CondutoresPorUnidade"],
                "forma_energia": d["FormaEnergia"], "pontos_dados": d["PontosDados"],
                "eletroduto_dados": d["EletrodutoDados"], "cabos_interfone": d["CabosInterfone"],
                "eletroduto_interfone": d["EletrodutoInterfone"], "circuitos_emergencia": d["CircuitosEmergencia"],
                "secao_emergencia": d["SecaoEmergencia"], "tipo_eletroduto": d["TipoEletroduto"]}

    def atualizar_previa(self, *_):
        resultado = regras.dimensionar(self.andares(), self.parametros())
        linhas = list(resultado["avisos"])
        for s in resultado["sistemas"].values():
            linhas.append(f"{s['sigla']} - {s['nome']} (origem: {s['origem']})")
            linhas += [f"   {t['de']} → {t['ate']}: {regras.descricao_trecho(t)}" for t in s["trechos"]]
            linhas += [f"   aviso: {a}" for a in s["avisos"]]
        self.previa.setPlainText("\n".join(linhas))
