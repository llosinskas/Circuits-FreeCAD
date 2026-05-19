"""
Objeto FeaturePython para Tomada (Outlet).
Desenha o símbolo 2D na planta (semicírculo - padrão NBR 5444)
e armazena propriedades para geração posterior da caixa 3D.
"""

import FreeCAD as App
import Part
import math

try:
    import FreeCADGui as Gui
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


class Outlet:
    """FeaturePython customizado para representar uma Tomada na planta 2D."""

    Type = "Outlet"

    def __init__(self, obj):
        obj.Proxy = self
        self._add_properties(obj)

    def _add_properties(self, obj):
        # --- Identificação ---
        if not hasattr(obj, "Circuito"):
            obj.addProperty(
                "App::PropertyString", "Circuito", "Tomada",
                "Número do circuito no quadro"
            ).Circuito = "1"

        if not hasattr(obj, "Potencia"):
            obj.addProperty(
                "App::PropertyString", "Potencia", "Tomada",
                "Potência da tomada (ex: 600VA, 100VA)"
            ).Potencia = "600VA"

        if not hasattr(obj, "Tensao"):
            obj.addProperty(
                "App::PropertyEnumeration", "Tensao", "Tomada",
                "Tensão nominal da tomada"
            )
            obj.Tensao = ["127V", "220V", "Bifásica"]
            obj.Tensao = "127V"

        if not hasattr(obj, "TipoTomada"):
            obj.addProperty(
                "App::PropertyEnumeration", "TipoTomada", "Tomada",
                "Tipo da tomada"
            )
            obj.TipoTomada = ["Baixa", "Média", "Alta"]
            obj.TipoTomada = "Baixa"

        if not hasattr(obj, "QtdPontos"):
            obj.addProperty(
                "App::PropertyInteger", "QtdPontos", "Tomada",
                "Quantidade de pontos de tomada na caixa"
            ).QtdPontos = 1

        # --- Geometria 2D ---
        if not hasattr(obj, "RaioSimbolo"):
            obj.addProperty(
                "App::PropertyDistance", "RaioSimbolo", "Símbolo 2D",
                "Raio do semicírculo do símbolo na planta"
            ).RaioSimbolo = 20.0

        # --- Geração 3D ---
        if not hasattr(obj, "Altura3D"):
            obj.addProperty(
                "App::PropertyDistance", "Altura3D", "Caixa 3D",
                "Altura (elevação Z) onde a caixa será posicionada"
            ).Altura3D = 300.0  # Tomada baixa padrão: 30cm

        if not hasattr(obj, "CaixaAltura"):
            obj.addProperty(
                "App::PropertyDistance", "CaixaAltura", "Caixa 3D",
                "Altura da caixa 4x2 (eixo Z)"
            ).CaixaAltura = 100.0

        if not hasattr(obj, "CaixaLargura"):
            obj.addProperty(
                "App::PropertyDistance", "CaixaLargura", "Caixa 3D",
                "Largura da caixa 4x2 (eixo X)"
            ).CaixaLargura = 60.0

        if not hasattr(obj, "CaixaProfundidade"):
            obj.addProperty(
                "App::PropertyDistance", "CaixaProfundidade", "Caixa 3D",
                "Profundidade da caixa 4x2 (eixo Y)"
            ).CaixaProfundidade = 40.0

    def execute(self, obj):
        """Gera o símbolo 2D: semicírculo + linha base (padrão NBR 5444), no plano Z=0."""
        raio = obj.RaioSimbolo.Value if hasattr(obj.RaioSimbolo, "Value") else float(obj.RaioSimbolo)

        if raio <= 0:
            return

        edges = []

        # Semicírculo superior (arco de 0° a 180°)
        center = App.Vector(0, 0, 0)
        arc = Part.makeCircle(raio, center, App.Vector(0, 0, 1), 0, 180)
        edges.append(arc)

        # Linha base horizontal (fecha o semicírculo)
        p_left = App.Vector(-raio, 0, 0)
        p_right = App.Vector(raio, 0, 0)
        base_line = Part.makeLine(p_left, p_right)
        edges.append(base_line)

        # Indicador de quantidade de pontos (tracinhos verticais dentro)
        qtd = obj.QtdPontos if hasattr(obj, "QtdPontos") else 1
        if qtd > 1:
            spacing = (2 * raio) / (qtd + 1)
            for i in range(1, qtd + 1):
                x_pos = -raio + spacing * i
                tick_bottom = App.Vector(x_pos, 0, 0)
                tick_top = App.Vector(x_pos, raio * 0.5, 0)
                edges.append(Part.makeLine(tick_bottom, tick_top))

        compound = Part.makeCompound(edges)
        obj.Shape = compound

    def onChanged(self, fp, prop):
        """Reexecuta quando propriedades visuais mudam."""
        if prop in ["RaioSimbolo", "QtdPontos"]:
            pass  # FreeCAD chama execute() automaticamente

    def dumps(self):
        return {"Type": self.Type}

    def loads(self, state):
        if state:
            self.Type = state.get("Type", "Outlet")


class ViewProviderOutlet:
    """Provedor visual para o Outlet."""

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        import os
        from freecad.Circuits import ICON_PATH
        return os.path.join(ICON_PATH, "tomadas.svg")

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


def create_outlet(name="Tomada", placement=None):
    """Função utilitária para criar uma Tomada no documento ativo.
    
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
    Outlet(obj)

    if GUI_AVAILABLE:
        ViewProviderOutlet(obj.ViewObject)

    if placement:
        obj.Placement = placement

    doc.recompute()
    return obj
