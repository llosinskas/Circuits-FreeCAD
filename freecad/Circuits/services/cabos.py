"""Simbologia 2D de cabos (fase, neutro e terra) em Sketches."""
import FreeCAD as App
import Part

from freecad.Circuits.core.simbologia import posicoes_fase
from freecad.Circuits.services.documento import create_group

ALTURA_SIMBOLO = 100
DESLOCAMENTO = App.Vector(50, 50, 0)


def _linha(sketch, x1, y1, x2, y2):
    sketch.addGeometry(Part.LineSegment(App.Vector(x1, y1), App.Vector(x2, y2)), False)


def _novo_sketch(doc, posicao):
    sketch = doc.addObject("Sketcher::SketchObject", "Cabo")
    sketch.Placement = App.Placement(posicao + DESLOCAMENTO, App.Rotation(0, 0, 0))
    return sketch


def _desenhar_fases(sketch, fases, neutro, terra, h):
    for x in posicoes_fase(fases, neutro, terra, h):
        _linha(sketch, x, -h / 2, x, h / 2)


def desenhar_cabo_planta(doc, equipamento, grupo):
    """Símbolo do cabo de um equipamento na planta."""
    h = ALTURA_SIMBOLO
    terra = equipamento.terra
    neutro = equipamento.neutro
    sketch = _novo_sketch(doc, equipamento.Placement.Base)
    if terra:
        _linha(sketch, 0, 0, 0, h / 2)
        _linha(sketch, -h / 5, h / 2, 0, h / 2)
    if neutro:
        if terra:
            _linha(sketch, h / 2, 0, h / 2, h / 2)
            _linha(sketch, h / 2 - h / 5, h / 2, h / 2 + h / 5, h / 2)
        else:
            _linha(sketch, 0, 0, 0, h / 2)
            _linha(sketch, -h / 5, h / 2, h / 5, h / 2)
    _desenhar_fases(sketch, equipamento.Fase, neutro, terra, h)
    grupo.addObject(sketch)


def desenhar_cabos_planta(doc, equipamentos):
    grupo = create_group("Cabos", doc)
    for equipamento in equipamentos:
        desenhar_cabo_planta(doc, equipamento, grupo)


def desenhar_cabo_unifilar(doc, fases, terra, neutro, h, posicao, grupo):
    """Símbolo do cabo no diagrama unifilar (traços de neutro e terra diferem da planta)."""
    sketch = _novo_sketch(doc, posicao)
    if terra:
        _linha(sketch, 0, 0, 0, h / 2)
        _linha(sketch, -h / 5, h / 2, h / 5, h / 2)
    if neutro:
        if terra:
            _linha(sketch, h / 2, -h / 2, h / 2, h / 2)
            _linha(sketch, -h / 5 + h / 2, h / 2, h / 2, h / 2)
        else:
            _linha(sketch, 0, -h / 2, 0, h / 2)
            _linha(sketch, -h / 5, h / 2, 0, h / 2)
    _desenhar_fases(sketch, fases, neutro, terra, h)
    grupo.addObject(sketch)
