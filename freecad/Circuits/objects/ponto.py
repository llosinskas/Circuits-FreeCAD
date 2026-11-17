"""Objeto FeaturePython para pontos elétricos em planta (PontoEletrico).

Um único objeto serve tomadas, pontos de energia e iluminação: a propriedade
``Simbolo`` escolhe o desenho 2D em ``core.simbolos``. Os dados elétricos
(potência, tensão, circuito) são lidos por ``services.circuitos`` para montar
os circuitos do quadro e o diagrama unifilar.

Depois de usado em projetos, o nome deste módulo e das classes fica congelado.
"""
import os

import FreeCAD as App
import Part

from freecad.Circuits.core import simbolos
from freecad.Circuits.core.simbologia import tamanho_efetivo

try:
    import FreeCADGui as Gui  # noqa: F401
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

TAMANHO_PADRAO = 200.0  # mm: cerca de 4 mm impressos em 1:50
TENSOES = ["127V", "220V", "380V"]
PREFERENCIAS = "User parameter:BaseApp/Preferences/Mod/Circuits"


def escala_padrao():
    """Escala dos símbolos novos, gravada pelo comando Escala dos símbolos."""
    return App.ParamGet(PREFERENCIAS).GetFloat("EscalaSimbolos", 1.0) or 1.0


def tamanho_do_ponto(obj):
    """Tamanho do símbolo na planta, em mm, já com a escala."""
    tamanho = obj.Tamanho.Value if hasattr(obj.Tamanho, "Value") else float(obj.Tamanho)
    return tamanho_efetivo(tamanho, getattr(obj, "Escala", 1.0))


def icone_do_simbolo(simbolo):
    from freecad.Circuits import ICON_PATH
    return os.path.join(ICON_PATH, "simbologia", f"{simbolo}.svg")


def _aresta(primitiva):
    tipo = primitiva[0]
    if tipo == "linha":
        _, x1, y1, x2, y2 = primitiva
        return Part.makeLine(App.Vector(x1, y1, 0), App.Vector(x2, y2, 0))
    centro = App.Vector(primitiva[1], primitiva[2], 0)
    eixo = App.Vector(0, 0, 1)
    if tipo == "circulo":
        return Part.makeCircle(primitiva[3], centro, eixo)
    return Part.makeCircle(primitiva[3], centro, eixo, primitiva[4], primitiva[5])


def forma_do_simbolo(simbolo, tamanho, com_vertice=False):
    """Compound com as arestas do símbolo, no plano Z=0.

    Com ``com_vertice``, inclui um vértice no ponto de inserção (a caixa), onde o
    snap do Draft prende o eletroduto ao desenhar.
    """
    formas = [_aresta(p) for p in simbolos.geometria(simbolo, tamanho)]
    if com_vertice:
        formas.append(Part.Vertex(App.Vector(0, 0, 0)))
    return Part.makeCompound(formas)


class PontoEletrico:
    """Ponto elétrico na planta 2D: tomada, ponto de energia ou iluminação."""

    Type = "Ponto"

    def __init__(self, obj, simbolo="tomada_baixa"):
        obj.Proxy = self
        self._add_properties(obj, simbolo)

    def _add_properties(self, obj, simbolo="tomada_baixa"):
        dados = simbolos.CATALOGO[simbolo]

        def nova(tipo, nome, grupo, dica):
            """Cria a propriedade se faltar. Devolve True quando foi criada agora."""
            if hasattr(obj, nome):
                return False
            obj.addProperty(tipo, nome, grupo, dica)
            return True

        # --- Elétrica ---
        if nova("App::PropertyEnumeration", "Simbolo", "Elétrica", "Símbolo desenhado na planta"):
            obj.Simbolo = list(simbolos.CATALOGO)
            obj.Simbolo = simbolo
        if nova("App::PropertyString", "Descricao", "Elétrica", "Descrição do ponto (vai para o quadro de cargas)"):
            obj.Descricao = dados["descricao"]
        if nova("App::PropertyFloat", "Potencia", "Elétrica", "Potência aparente do ponto, em VA"):
            obj.Potencia = float(dados["potencia_va"])
        if nova("App::PropertyFloat", "FatorPotencia", "Elétrica", "Fator de potência (0 a 1)"):
            obj.FatorPotencia = float(dados["fator_potencia"])
        if nova("App::PropertyEnumeration", "Tensao", "Elétrica", "Tensão entre os condutores do ponto"):
            obj.Tensao = TENSOES
            obj.Tensao = f"{dados['tensao']}V"
        if nova("App::PropertyEnumeration", "Ligacao", "Elétrica", "F+N: fase e neutro; F+F: duas fases; 3F: trifásico"):
            obj.Ligacao = list(simbolos.LIGACOES)
            obj.Ligacao = dados["ligacao"]
        if nova("App::PropertyString", "Circuito", "Elétrica", "Número do circuito no quadro"):
            obj.Circuito = "" if dados["categoria"] == simbolos.QUADRO else "1"
        if nova("App::PropertyString", "Quadro", "Elétrica", "Quadro que alimenta o ponto (vazio: qualquer quadro)"):
            obj.Quadro = ""
        if nova("App::PropertyString", "Ambiente", "Elétrica", "Retângulo do luminotécnico que criou o ponto"):
            obj.Ambiente = ""
        if nova("App::PropertyString", "Comando", "Elétrica", "Letra do interruptor que comanda o ponto (iluminação)"):
            obj.Comando = ""  # preenchido pelo comando Ligar interruptor

        if dados["categoria"] == simbolos.QUADRO and nova(
            "App::PropertyString", "Planilha", "Elétrica", "Nome da planilha com os dados deste quadro"
        ):
            obj.Planilha = ""
        if "medidores" in dados and nova("App::PropertyInteger", "Medidores", "Elétrica", "Quantidade de medidores"):
            obj.Medidores = dados["medidores"]

        # --- Símbolo 2D ---
        if nova("App::PropertyDistance", "Tamanho", "Símbolo 2D", "Tamanho do símbolo na planta"):
            obj.Tamanho = TAMANHO_PADRAO
        if nova("App::PropertyFloat", "Escala", "Símbolo 2D", "Multiplica o tamanho do símbolo (2 = dobro)"):
            obj.Escala = 1.0

        # --- Geração 3D ---
        largura, profundidade, altura = dados["caixa_mm"]
        if nova("App::PropertyDistance", "Altura3D", "Caixa 3D", "Altura de montagem em relação ao piso"):
            obj.Altura3D = float(dados["altura_mm"])
        if nova("App::PropertyDistance", "CaixaLargura", "Caixa 3D", "Largura da caixa (eixo X)"):
            obj.CaixaLargura = largura
        if nova("App::PropertyDistance", "CaixaProfundidade", "Caixa 3D", "Profundidade da caixa (eixo Y)"):
            obj.CaixaProfundidade = profundidade
        if nova("App::PropertyDistance", "CaixaAltura", "Caixa 3D", "Altura da caixa (eixo Z)"):
            obj.CaixaAltura = altura

    def execute(self, obj):
        """Gera o símbolo 2D no plano Z=0."""
        tamanho = tamanho_do_ponto(obj)
        if tamanho <= 0:
            return
        obj.Shape = forma_do_simbolo(obj.Simbolo, tamanho, com_vertice=True)

    def onDocumentRestored(self, obj):
        """Acrescenta propriedades criadas em versões mais novas da bancada."""
        self._add_properties(obj, getattr(obj, "Simbolo", "tomada_baixa"))

    def dumps(self):
        return {"Type": self.Type}

    def loads(self, state):
        if state:
            self.Type = state.get("Type", "Ponto")


class ViewProviderPontoEletrico:
    """Provedor visual do PontoEletrico: o ícone acompanha o símbolo."""

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return icone_do_simbolo(getattr(getattr(self, "Object", None), "Simbolo", "tomada_baixa"))

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def updateData(self, fp, prop):
        pass

    def onChanged(self, vp, prop):
        pass

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def dumps(self):
        return None

    def loads(self, state):
        return None


def create_ponto(simbolo, placement=None):
    """Cria um PontoEletrico no documento ativo.

    Args:
        simbolo: chave de ``core.simbolos.CATALOGO``.
        placement: App.Placement opcional.
    Returns:
        O objeto criado, ou None se não houver documento ativo.
    """
    doc = App.activeDocument()
    if not doc:
        return None

    obj = doc.addObject("Part::FeaturePython", "Ponto")
    PontoEletrico(obj, simbolo)
    obj.Label = simbolos.CATALOGO[simbolo]["legenda"]
    obj.Escala = escala_padrao()
    if GUI_AVAILABLE:
        ViewProviderPontoEletrico(obj.ViewObject)
    if placement:
        obj.Placement = placement

    doc.recompute()
    return obj
