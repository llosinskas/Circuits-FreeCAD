"""Diálogo genérico de cálculo: poucas perguntas, opções prontas e resultado na hora."""
import FreeCAD as App

from freecad.Circuits.core import formularios
from freecad.Circuits.qt import QtWidgets

PREFERENCIAS = "User parameter:BaseApp/Preferences/Mod/Circuits/Formularios"


class CalculoDialog(QtWidgets.QDialog):
    """Monta o formulário a partir de uma lista de campos e mostra o resultado.

    O resultado é recalculado a cada mudança, sem precisar de botão. Os campos
    marcados como avançados ficam em um grupo fechado no início. Os valores
    usados ficam guardados e voltam na próxima vez que o formulário abrir.

    Args:
        titulo: título da janela.
        campos: lista de campos, no formato descrito em ``core.formularios``.
        calcular: função que recebe o dicionário de valores e devolve
            (resultado, texto). Pode lançar ``ValueError`` com a mensagem ao usuário.
        texto_aceitar: rótulo do botão que fecha o diálogo aceitando o resultado;
            vazio esconde o botão.
        chave: nome sob o qual os valores são guardados; vazio não guarda nada.
    """

    def __init__(self, titulo, campos, calcular, texto_aceitar="", chave=""):
        super().__init__()
        self.setWindowTitle(titulo)
        self.setMinimumWidth(560)
        self._campos = list(campos)
        self._calcular = calcular
        self._chave = chave
        self._entradas = {}
        self._carregando = True
        self.resultado = None

        layout = QtWidgets.QVBoxLayout()
        basico = QtWidgets.QFormLayout()
        avancado = QtWidgets.QFormLayout()
        for campo in self._campos:
            entrada = self._criar_entrada(campo)
            self._entradas[campo["chave"]] = entrada
            rotulo = QtWidgets.QLabel(campo["rotulo"])
            if campo.get("dica"):
                rotulo.setToolTip(campo["dica"])
                entrada.setToolTip(campo["dica"])
            (avancado if campo.get("avancado") else basico).addRow(rotulo, entrada)
        layout.addLayout(basico)

        self.grupo_avancado = QtWidgets.QGroupBox("Opções avançadas")
        self.grupo_avancado.setCheckable(True)
        self.grupo_avancado.setChecked(False)
        self._conteudo_avancado = QtWidgets.QWidget()
        self._conteudo_avancado.setLayout(avancado)
        self._conteudo_avancado.setVisible(False)
        caixa = QtWidgets.QVBoxLayout()
        caixa.addWidget(self._conteudo_avancado)
        self.grupo_avancado.setLayout(caixa)
        self.grupo_avancado.toggled.connect(self._conteudo_avancado.setVisible)
        self.grupo_avancado.setVisible(avancado.rowCount() > 0)
        layout.addWidget(self.grupo_avancado)

        self.saida = QtWidgets.QPlainTextEdit()
        self.saida.setReadOnly(True)
        self.saida.setMinimumHeight(230)
        layout.addWidget(self.saida)

        botoes = QtWidgets.QHBoxLayout()
        self.btn_aceitar = QtWidgets.QPushButton(texto_aceitar)
        self.btn_aceitar.setDefault(True)
        self.btn_aceitar.setEnabled(False)
        self.btn_aceitar.setVisible(bool(texto_aceitar))
        self.btn_aceitar.clicked.connect(self.accept)
        botoes.addWidget(self.btn_aceitar)

        btn_padroes = QtWidgets.QPushButton("Restaurar padrões")
        btn_padroes.setToolTip("Volta todos os campos aos valores iniciais")
        btn_padroes.clicked.connect(self.restaurar_padroes)
        botoes.addWidget(btn_padroes)

        btn_fechar = QtWidgets.QPushButton("Fechar")
        btn_fechar.clicked.connect(self.reject)
        botoes.addWidget(btn_fechar)
        layout.addLayout(botoes)
        self.setLayout(layout)

        self._definir_valores(formularios.valores_iniciais(self._campos))
        self._definir_valores(self._valores_guardados())
        self._carregando = False
        self.calcular()

    # --- entradas ---------------------------------------------------------

    def _criar_entrada(self, campo):
        valor = campo["valor"]
        if isinstance(valor, (list, tuple)):
            entrada = QtWidgets.QComboBox()
            entrada.addItems([str(item) for item in valor])
            entrada.currentIndexChanged.connect(lambda *_, c=campo: self._alterado(c))
            return entrada
        if isinstance(valor, int):
            entrada = QtWidgets.QSpinBox()
        else:
            entrada = QtWidgets.QDoubleSpinBox()
            entrada.setDecimals(campo.get("decimais", 2))
        entrada.setRange(campo.get("minimo", 0), campo.get("maximo", 1000000))
        entrada.setValue(valor)
        if campo.get("sufixo"):
            entrada.setSuffix(" " + campo["sufixo"])
        entrada.valueChanged.connect(lambda *_, c=campo: self._alterado(c))
        return entrada

    def _definir_valor(self, chave, valor):
        entrada = self._entradas.get(chave)
        if entrada is None or valor is None:
            return
        if isinstance(entrada, QtWidgets.QComboBox):
            indice = entrada.findText(str(valor))
            if indice >= 0:
                entrada.setCurrentIndex(indice)
        else:
            entrada.setValue(valor)

    def _definir_valores(self, valores):
        for chave, valor in valores.items():
            self._definir_valor(chave, valor)

    def _alterado(self, campo):
        """Uma entrada mudou: aplica a predefinição, se for o caso, e recalcula."""
        if self._carregando:
            return
        preenchimento = {}
        if "preenche" in campo:
            preenchimento = campo["preenche"].get(self._entradas[campo["chave"]].currentText(), {})
        if preenchimento:
            self._carregando = True
            self._definir_valores(preenchimento)
            self._carregando = False
        self.calcular()

    def get_dados(self):
        """Valores do formulário, por chave do campo."""
        return {
            chave: entrada.currentText() if isinstance(entrada, QtWidgets.QComboBox) else entrada.value()
            for chave, entrada in self._entradas.items()
        }

    # --- cálculo ----------------------------------------------------------

    def calcular(self):
        try:
            self.resultado, texto = self._calcular(self.get_dados())
        except ValueError as erro:
            self.resultado = None
            texto = f"Não foi possível calcular: {erro}"
        self.saida.setPlainText(texto)
        self.btn_aceitar.setEnabled(self.resultado is not None)

    def restaurar_padroes(self):
        self._carregando = True
        self._definir_valores(formularios.valores_iniciais(self._campos))
        self._carregando = False
        self.calcular()

    # --- valores guardados --------------------------------------------------

    def _parametros(self):
        return App.ParamGet(f"{PREFERENCIAS}/{self._chave}")

    def _valores_guardados(self):
        """Valores da última vez em que o formulário foi usado, já validados."""
        if not self._chave:
            return {}
        try:
            parametros = self._parametros()
            guardados = {}
            for campo in self._campos:
                texto = parametros.GetString(campo["chave"], "")
                if texto:
                    guardados[campo["chave"]] = formularios.converter(campo, texto)
            return guardados
        except Exception:
            return {}

    def _guardar_valores(self):
        if not self._chave:
            return
        try:
            parametros = self._parametros()
            for chave, valor in self.get_dados().items():
                parametros.SetString(chave, str(valor))
        except Exception:
            pass  # guardar é conveniência: nunca impede o fechamento

    def done(self, codigo):
        self._guardar_valores()
        super().done(codigo)
