"""Escala dos símbolos da planta."""
import FreeCAD as App

from freecad.Circuits.objects.ponto import PREFERENCIAS
from freecad.Circuits.services import tomadas
from freecad.Circuits.services.alinhamento import listar_simbolos
from freecad.Circuits.services.identificacao import atualizar_anotacao


def definir_escala_padrao(escala):
    """Escala com que os próximos pontos serão criados."""
    App.ParamGet(PREFERENCIAS).SetFloat("EscalaSimbolos", float(escala))


def _aplicar(obj, escala):
    """Grava a escala no símbolo. Devolve False se o tipo do objeto não tem escala."""
    tipo = getattr(getattr(obj, "Proxy", None), "Type", "")
    if tipo in ("Ponto", "Switch"):
        if not hasattr(obj, "Escala"):  # objeto criado antes de a propriedade existir
            obj.Proxy._add_properties(obj)
        obj.Escala = escala
        return True
    if getattr(obj, "tipo", "") == "tomada":
        tomadas.aplicar_escala(obj, escala)
        return True
    return False


def aplicar_escala(doc, objetos, escala):
    """Aplica a escala aos símbolos dados, ou a todos os da planta se a lista for vazia.

    Returns:
        (símbolos alterados, símbolos sem suporte a escala).
    Raises:
        ValueError: se a escala não for positiva.
    """
    if escala <= 0:
        raise ValueError("A escala precisa ser maior que zero.")
    alvos = list(objetos) or listar_simbolos(doc)
    alterados = ignorados = 0
    doc.openTransaction("Escala dos símbolos")
    try:
        for obj in alvos:
            if _aplicar(obj, float(escala)):
                alterados += 1
            else:
                ignorados += 1
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    atualizar_anotacao(doc)
    return alterados, ignorados
