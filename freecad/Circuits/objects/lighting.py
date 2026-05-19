"""
Objeto FeaturePython para Ponto de Iluminação (Lighting).
Desenha o símbolo 2D na planta (círculo com cruz interna)
e armazena propriedades para geração posterior do modelo 3D.
"""

import FreeCAD as App
import Part
import math

try:
    import FreeCADGui as Gui
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


class Lighting:
    """FeaturePython customizado para representar um Ponto de Iluminação na planta 2D."""

    Type = "Lighting"

    def __init__(self, obj):
        obj.Proxy = self
        self._add_properties(obj)

    def _add_properties(self, obj):
        # --- Identificação ---
        if not hasattr(obj, "Circuito"):
            obj.addProperty(
                "App::PropertyString", "Circuito", "Iluminação",
                "Número do circuito no quadro"
            ).Circuito = "1"

        if not hasattr(obj, "Comando"):
            obj.addProperty(
                "App::PropertyString", "Comando", "Iluminação",
                "Letra do comando que aciona este ponto (a, b, c, ...)"
            ).Comando = "a"

        if not hasattr(obj, "Potencia"):
            obj.addProperty(
                "App::PropertyString", "Potencia", "Iluminação",
                "Potência da lâmpada/luminária (ex: 100W)"
            ).Potencia = "100W"

        if not hasattr(obj, "TipoLuminaria"):
            obj.addProperty(
                "App::PropertyEnumeration", "TipoLuminaria", "Iluminação",
                "Tipo da luminária"
            )
            obj.TipoLuminaria = ["Plafon", "Pendente", "Spot", "Embutida", "Arandela"]
            obj.TipoLuminaria = "Plafon"

        # --- Geometria 2D ---
        if not hasattr(obj, "RaioSimbolo"):
            obj.addProperty(
                "App::PropertyDistance", "RaioSimbolo", "Símbolo 2D",
                "Raio do círculo do símbolo na planta"
            ).RaioSimbolo = 30.0

        # --- Geração 3D ---
        if not hasattr(obj, "Altura3D"):
            obj.addProperty(
                "App::PropertyDistance", "Altura3D", "Caixa 3D",
                "Altura (elevação Z) onde a luminária será posicionada"
            ).Altura3D = 2800.0

        if not hasattr(obj, "CaixaAltura"):
            obj.addProperty(
                "App::PropertyDistance", "CaixaAltura", "Caixa 3D",
                "Altura da caixa da luminária (eixo Z)"
            ).CaixaAltura = 50.0

        if not hasattr(obj, "CaixaLargura"):
            obj.addProperty(
                "App::PropertyDistance", "CaixaLargura", "Caixa 3D",
                "Largura da caixa da luminária (eixo X)"
            ).CaixaLargura = 100.0

        if not hasattr(obj, "CaixaProfundidade"):
            obj.addProperty(
                "App::PropertyDistance", "CaixaProfundidade", "Caixa 3D",
                "Profundidade da caixa da luminária (eixo Y)"
            ).CaixaProfundidade = 100.0

    def execute(self, obj):
        """Gera o símbolo 2D: círculo com cruz interna, no plano Z=0."""
        raio = obj.RaioSimbolo.Value if hasattr(obj.RaioSimbolo, "Value") else float(obj.RaioSimbolo)

        if raio <= 0:
            return

        edges = []

        # Círculo no plano XY (Z=0), centrado na origem local do objeto
        circle = Part.makeCircle(raio, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
        edges.append(circle)

        # Cruz interna (linhas verticais e horizontais dentro do círculo)
        # Linha vertical
        edges.append(Part.makeLine(
            App.Vector(0, -raio, 0),
            App.Vector(0, raio, 0)
        ))
        # Linha horizontal
        edges.append(Part.makeLine(
            App.Vector(-raio, 0, 0),
            App.Vector(raio, 0, 0)
        ))

        compound = Part.makeCompound(edges)
        obj.Shape = compound

    def onChanged(self, fp, prop):
        """Reexecuta quando propriedades visuais mudam."""
        if prop in ["RaioSimbolo"]:
            pass  # FreeCAD chama execute() automaticamente

    def dumps(self):
        return {"Type": self.Type}

    def loads(self, state):
        if state:
            self.Type = state.get("Type", "Lighting")


class ViewProviderLighting:
    """Provedor visual para o Lighting."""

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        import os
        from freecad.Circuits import ICON_PATH
        return os.path.join(ICON_PATH, "iluminacao.svg")

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


def create_lighting(name="PontoIluminacao", placement=None):
    """Função utilitária para criar um Ponto de Iluminação no documento ativo.
    
    Args:
        name: Nome interno do objeto.
        placement: App.Placement opcional para posicionar na planta.
        
    Returns:
        O objeto FreeCAD criado, ou None se não houver documento ativo.
    """
    doc = App.activeDocument()
    if not doc:
        return None

    obj = doc.addObject("Part::FeaturePython", name)
    Lighting(obj)

    if GUI_AVAILABLE:
        ViewProviderLighting(obj.ViewObject)

    if placement:
        obj.Placement = placement

    doc.recompute()
    return obj
