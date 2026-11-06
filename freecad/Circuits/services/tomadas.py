"""Tomadas representadas por Sketch com simbologia 2D e propriedades elétricas."""
import Draft
import FreeCAD as App
import FreeCADGui as Gui
import Part
import Sketcher  # noqa: F401  (registra o tipo Sketcher::SketchObject)

from freecad.Circuits.services.documento import create_group

ALTURA_SIMBOLO = 100


def _criar_sketch(doc):
    """Sketch com o símbolo da tomada: triângulo com linha de conexão."""
    sketch = doc.addObject("Sketcher::SketchObject", "Tomada")
    h = ALTURA_SIMBOLO
    sketch.addGeometry(Part.LineSegment(App.Vector(0, 0), App.Vector(h / 3, 0)), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(h / 3, h / 4), App.Vector(h / 3, -h / 4)), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(h / 3, h / 4), App.Vector(h, 0)), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(h / 3, -h / 4), App.Vector(h, 0)), False)
    return sketch


def _adicionar_propriedades(sketch):
    sketch.addProperty("App::PropertyPower", "potencia")
    sketch.addProperty("App::PropertyInteger", "Fase")
    sketch.addProperty("App::PropertyFloat", "Fator_potencia")
    sketch.addProperty("App::PropertyFloat", "altura_piso")
    sketch.addProperty("App::PropertyString", "Descricao")
    sketch.addProperty("App::PropertyInteger", "Circuito")
    sketch.addProperty("App::PropertyElectricPotential", "Tensao")
    sketch.addProperty("App::PropertyString", "tipo")
    sketch.addProperty("App::PropertyBool", "terra")
    sketch.addProperty("App::PropertyBool", "neutro")


def _valores_padrao(sketch, altura_piso):
    sketch.terra = True
    sketch.neutro = True
    sketch.tipo = "tomada"
    sketch.Fase = 2
    sketch.Fator_potencia = 0.9
    sketch.Descricao = "Descrição da tomada"
    sketch.potencia = 100
    sketch.altura_piso = altura_piso
    sketch.Circuito = 1
    sketch.Tensao = "220"


def criar_tomada_simples(doc, ponto):
    """Tomada do comando ComponentEletric (altura do piso 30, sem dados de caixa)."""
    sketch = _criar_sketch(doc)
    sketch.Placement.Base = ponto
    _adicionar_propriedades(sketch)
    _valores_padrao(sketch, altura_piso=30)
    doc.recompute()
    return sketch


def criar_tug(doc):
    """Tomada do comando InsertTugs (altura do piso 300, com dados da caixa 3D)."""
    sketch = _criar_sketch(doc)
    _adicionar_propriedades(sketch)
    sketch.addProperty("App::PropertyFloat", "CaixaAltura", "Caixa 3D", "Altura da caixa 4x2 em mm")
    sketch.addProperty("App::PropertyFloat", "CaixaLargura", "Caixa 3D", "Largura da caixa 4x2 em mm")
    sketch.addProperty("App::PropertyFloat", "CaixaProfundidade", "Caixa 3D", "Profundidade da caixa 4x2 em mm")
    _valores_padrao(sketch, altura_piso=300)
    sketch.CaixaAltura = 100.0
    sketch.CaixaLargura = 60.0
    sketch.CaixaProfundidade = 40.0
    doc.recompute()
    return sketch


def listar_tomadas(doc):
    return [obj for obj in doc.Objects if hasattr(obj, "tipo") and obj.tipo == "tomada"]


def gerar_caixas_tomadas(doc, tomadas):
    """Cria a caixa 3D de cada tomada e esconde o grupo com os símbolos 2D."""
    grupo_caixas = create_group("Equipamentos", doc)
    grupo_tomadas = doc.getObject("Tomadas")
    if grupo_tomadas is None:
        grupo_tomadas = doc.addObject("App::DocumentObjectGroup", "Tomadas")

    for tomada in tomadas:
        caixa = doc.addObject("Part::Box", "tomada")
        caixa.Length = 20
        caixa.Width = 30
        caixa.Height = 30
        Draft.move([caixa], tomada.Placement.Base, copy=False)
        Draft.move([caixa], App.Vector(-15, -10, tomada.altura_piso), copy=False)
        grupo_caixas.addObject(caixa)
        grupo_tomadas.addObject(tomada)

    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, "Tomadas")
    Gui.runCommand("Std_ToggleVisibility", 0)
