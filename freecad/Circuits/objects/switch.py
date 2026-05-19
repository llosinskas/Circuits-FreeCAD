"""
Objeto FeaturePython para Interruptor (Switch).
Desenha o símbolo 2D na planta (círculo R=20mm + linha de 10mm na borda)
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


class Switch:
    """FeaturePython customizado para representar um Interruptor na planta 2D."""

    Type = "Switch"

    def __init__(self, obj):
        obj.Proxy = self
        self._add_properties(obj)

    def _add_properties(self, obj):
        # --- Identificação ---
        if not hasattr(obj, "Circuito"):
            obj.addProperty(
                "App::PropertyString", "Circuito", "Interruptor",
                "Número do circuito no quadro"
            ).Circuito = "1"

        if not hasattr(obj, "Comando"):
            obj.addProperty(
                "App::PropertyString", "Comando", "Interruptor",
                "Letra do comando (a, b, c, ...)"
            ).Comando = "a"

        if not hasattr(obj, "Tipo"):
            obj.addProperty(
                "App::PropertyEnumeration", "Tipo", "Interruptor",
                "Tipo do interruptor"
            )
            obj.Tipo = ["Simples", "Paralelo", "Intermediário"]
            obj.Tipo = "Simples"

        # --- Geometria 2D ---
        if not hasattr(obj, "RaioSimbolo"):
            obj.addProperty(
                "App::PropertyDistance", "RaioSimbolo", "Símbolo 2D",
                "Raio do círculo do símbolo na planta"
            ).RaioSimbolo = 20.0

        if not hasattr(obj, "LinhaComprimento"):
            obj.addProperty(
                "App::PropertyDistance", "LinhaComprimento", "Símbolo 2D",
                "Comprimento da linha que sai da borda do círculo"
            ).LinhaComprimento = 10.0

        # --- Geração 3D ---
        if not hasattr(obj, "Altura3D"):
            obj.addProperty(
                "App::PropertyDistance", "Altura3D", "Caixa 3D",
                "Altura (elevação Z) onde a caixa será posicionada"
            ).Altura3D = 1200.0

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
        """Gera o símbolo 2D: círculo + linha saindo da borda, no plano Z=0."""
        raio = obj.RaioSimbolo.Value if hasattr(obj.RaioSimbolo, "Value") else float(obj.RaioSimbolo)
        linha = obj.LinhaComprimento.Value if hasattr(obj.LinhaComprimento, "Value") else float(obj.LinhaComprimento)

        if raio <= 0:
            return

        edges = []

        # Círculo no plano XY (Z=0), centrado na origem local do objeto
        circle = Part.makeCircle(raio, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
        edges.append(circle)

        # Linha horizontal saindo da borda direita do círculo
        if linha > 0:
            p_start = App.Vector(raio, 0, 0)
            p_end = App.Vector(raio + linha, 0, 0)
            line = Part.makeLine(p_start, p_end)
            edges.append(line)

        # Adiciona linhas extras baseado no tipo
        tipo = obj.Tipo if hasattr(obj, "Tipo") else "Simples"
        if tipo == "Paralelo":
            # Segunda linha paralela (deslocada 4mm para cima)
            p_start2 = App.Vector(raio, 4, 0)
            p_end2 = App.Vector(raio + linha, 4, 0)
            edges.append(Part.makeLine(p_start2, p_end2))
        elif tipo == "Intermediário":
            # Duas linhas extras (paralelas acima e abaixo)
            for dy in [4, -4]:
                p_s = App.Vector(raio, dy, 0)
                p_e = App.Vector(raio + linha, dy, 0)
                edges.append(Part.makeLine(p_s, p_e))

        compound = Part.makeCompound(edges)
        obj.Shape = compound

    def onChanged(self, fp, prop):
        """Reexecuta quando propriedades visuais mudam."""
        if prop in ["RaioSimbolo", "LinhaComprimento", "Tipo"]:
            pass  # FreeCAD chama execute() automaticamente

    def dumps(self):
        return {"Type": self.Type}

    def loads(self, state):
        if state:
            self.Type = state.get("Type", "Switch")


class ViewProviderSwitch:
    """Provedor visual para o Switch."""

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        import os
        from freecad.Circuits import ICON_PATH
        return os.path.join(ICON_PATH, "interruptor.svg")

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


def create_switch(name="Interruptor", placement=None):
    """Função utilitária para criar um Switch no documento ativo.
    
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
    Switch(obj)

    if GUI_AVAILABLE:
        ViewProviderSwitch(obj.ViewObject)

    if placement:
        obj.Placement = placement

    doc.recompute()
    return obj
