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


def alvos_de_snap(doc, exceto=None, cota=None, limite_arestas=2000):
    """Extrai vértices, pontos médios e segmentos 2D de objetos visíveis do documento.

    Ignora o objeto em inserção (``exceto``), símbolos elétricos já capturados por
    ``posicoes_dos_simbolos``, textos e planilhas. O limite de arestas evita lentidão
    em modelos muito carregados.
    """
    if doc is None or not hasattr(doc, "Objects"):
        return {"vertices": [], "meios": [], "segmentos": []}
    vertices, meios, segmentos = [], [], []
    vistos_v, vistos_m = set(), set()
    arestas_lidas = 0
    for obj in doc.Objects:
        if exceto is not None and getattr(obj, "Name", None) == getattr(exceto, "Name", None):
            continue
        if getattr(getattr(obj, "Proxy", None), "Type", "") in TIPOS_DE_SIMBOLO:
            continue
        tipo_id = getattr(obj, "TypeId", "")
        if tipo_id.startswith("Spreadsheet::") or tipo_id.startswith("App::Annotation"):
            continue
        vo = getattr(obj, "ViewObject", None)
        if vo is not None and getattr(vo, "Visibility", True) is False:
            continue
        shape = getattr(obj, "Shape", None)
        arestas = getattr(shape, "Edges", None) if shape is not None else None
        if not arestas:
            continue
        for aresta in arestas:
            if arestas_lidas >= limite_arestas:
                return {"vertices": vertices, "meios": meios, "segmentos": segmentos}
            verts = getattr(aresta, "Vertexes", None) or ()
            if len(verts) != 2:
                continue
            p1 = getattr(verts[0], "Point", None)
            p2 = getattr(verts[1], "Point", None)
            if p1 is None or p2 is None:
                continue
            x1, y1 = float(p1.x), float(p1.y)
            x2, y2 = float(p2.x), float(p2.y)
            if (x2 - x1) ** 2 + (y2 - y1) ** 2 <= 1.0:
                continue
            arestas_lidas += 1
            for vx, vy in ((x1, y1), (x2, y2)):
                chave = (round(vx), round(vy))
                if chave not in vistos_v:
                    vistos_v.add(chave)
                    vertices.append((vx, vy))
            mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            chave_m = (round(mx), round(my))
            if chave_m not in vistos_m:
                vistos_m.add(chave_m)
                meios.append((mx, my))
            segmentos.append(((x1, y1), (x2, y2)))
    return {"vertices": vertices, "meios": meios, "segmentos": segmentos}
