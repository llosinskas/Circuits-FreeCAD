"""Aparência dos desenhos da bancada."""
COR_SKETCH = (0.0, 0.0, 0.0)  # preto: o branco padrão do FreeCAD some sobre o fundo claro
TIPO_SKETCH = "Sketcher::SketchObject"


def pintar_sketch(sketch):
    """Pinta de preto as linhas e os pontos de um Sketch.

    Returns:
        False se o Sketch não tem vista (FreeCAD sem janela); True nos demais casos.
    """
    vista = getattr(sketch, "ViewObject", None)
    if vista is None:
        return False
    for nome in ("LineColor", "PointColor"):
        if hasattr(vista, nome):
            setattr(vista, nome, COR_SKETCH)
    return True


def pintar_todos(doc):
    """Pinta de preto todos os Sketches do documento. Devolve quantos foram pintados."""
    return sum(1 for obj in doc.Objects if getattr(obj, "TypeId", "") == TIPO_SKETCH and pintar_sketch(obj))
