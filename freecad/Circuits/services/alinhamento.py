"""Posições dos símbolos da planta e alinhamento de objetos selecionados."""
import FreeCAD as App

from freecad.Circuits.core import alinhamento
from freecad.Circuits.services.tomadas import listar_tomadas

TIPOS_DE_SIMBOLO = ("Ponto", "Switch", "Lighting", "Outlet")


def listar_simbolos(doc):
    """Símbolos elétricos da planta: pontos, interruptores e tomadas em Sketch."""
    simbolos = [
        obj for obj in doc.Objects
        if getattr(getattr(obj, "Proxy", None), "Type", "") in TIPOS_DE_SIMBOLO
    ]
    return simbolos + [obj for obj in listar_tomadas(doc) if obj not in simbolos]


def posicoes_dos_simbolos(doc, exceto=None):
    """(x, y) de cada símbolo da planta, menos o objeto ``exceto`` (o que está sendo inserido)."""
    return [
        (obj.Placement.Base.x, obj.Placement.Base.y)
        for obj in listar_simbolos(doc)
        if exceto is None or obj.Name != exceto.Name
    ]


def _mover(doc, objetos, calcular, nome):
    """Aplica ``calcular`` às posições dos objetos, em uma única operação de desfazer."""
    objetos = [obj for obj in objetos if hasattr(obj, "Placement")]
    posicoes = [(obj.Placement.Base.x, obj.Placement.Base.y) for obj in objetos]
    novas = calcular(posicoes)
    movidos = 0
    doc.openTransaction(nome)
    try:
        for obj, antiga, nova in zip(objetos, posicoes, novas):
            if antiga == nova:
                continue
            posicao = obj.Placement
            posicao.Base = App.Vector(nova[0], nova[1], posicao.Base.z)
            obj.Placement = posicao
            movidos += 1
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    return movidos


def alinhar_objetos(doc, objetos):
    """Coloca os objetos em linha com o primeiro. Devolve quantos se moveram."""
    return _mover(doc, objetos, alinhamento.alinhar, "Alinhar símbolos")


def distribuir_objetos(doc, objetos):
    """Espaça os objetos igualmente entre os extremos. Devolve quantos se moveram."""
    return _mover(doc, objetos, alinhamento.distribuir, "Distribuir símbolos")
