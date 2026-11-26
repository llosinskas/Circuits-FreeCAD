"""Aparência dos desenhos da bancada."""
COR_SKETCH = (0.0, 0.0, 0.0)  # preto: o branco padrão do FreeCAD some sobre o fundo claro
TIPO_SKETCH = "Sketcher::SketchObject"


def pintar_sketch(sketch):
    """Pinta de preto as linhas e os pontos de um Sketch, de forma que a cor fique gravada no arquivo.

    Returns:
        False se o Sketch não tem vista (FreeCAD sem janela); True nos demais casos.
    """
    vista = getattr(sketch, "ViewObject", None)
    if vista is None:
        return False
    if hasattr(vista, "AutoColor"):
        # FreeCAD 1.0: com AutoColor (padrão), a cor volta à das preferências (branco) ao abrir o arquivo
        vista.AutoColor = False
    for nome in ("LineColor", "PointColor"):
        if hasattr(vista, nome):
            setattr(vista, nome, COR_SKETCH)
    return True


def pintar_linha(obj, cor):
    """Pinta a linha de um objeto (Draft Wire, por exemplo). Devolve False sem vista."""
    vista = getattr(obj, "ViewObject", None)
    if vista is None or not hasattr(vista, "LineColor"):
        return False
    vista.LineColor = cor
    return True


def pintar_todos(doc):
    """Pinta de preto todos os Sketches do documento. Devolve quantos foram pintados."""
    return sum(1 for obj in doc.Objects if getattr(obj, "TypeId", "") == TIPO_SKETCH and pintar_sketch(obj))
