"""Snap especial de ligação: o eletroduto prende no ponto da caixa dos símbolos da bancada.

Como o conector de um dispositivo no Revit: ao desenhar uma linha do Draft (eletroduto,
eletrocalha) com o cursor sobre uma tomada, luminária, interruptor, quadro ou caixa de
passagem, o ponto vai direto para a caixa do símbolo (``SnapPoints``, o ponto de
inserção), com o marcador do snap especial, em vez do ponto mais próximo da linha do
desenho, que o snap "Próximo" do Draft escolheria.

O Draft já oferece os ``SnapPoints`` no snap especial, mas como mais um candidato, e o
mais perto do cursor ganha. Este módulo envolve o ``snapToObject`` do snapper (conferido
no FreeCAD 1.0.2) e dá prioridade ao ponto de ligação. Qualquer erro cai no snap normal.

Desligue pela preferência booleana ``SnapConexao`` em ``BaseApp/Preferences/Mod/Circuits``.
"""
import math

import FreeCAD as App
import FreeCADGui as Gui

PREFERENCIAS = "User parameter:BaseApp/Preferences/Mod/Circuits"
PREFERENCIA = "SnapConexao"
TIPOS = ("Ponto", "Switch", "Outlet", "Lighting")

_instalado = None


def ligado():
    try:
        return App.ParamGet(PREFERENCIAS).GetBool(PREFERENCIA, True)
    except Exception:
        return True


def pontos_de_ligacao(obj):
    """Pontos de ligação do símbolo, em coordenadas globais; [] se não é um símbolo da bancada."""
    tipo = getattr(getattr(obj, "Proxy", None), "Type", "")
    if tipo in TIPOS:
        locais = list(getattr(obj, "SnapPoints", [])) or [App.Vector(0, 0, 0)]
        return [obj.Placement.multVec(p) for p in locais]
    if getattr(obj, "tipo", "") == "tomada":  # tomada TUG antiga, em Sketch
        return [obj.Placement.Base]
    return []


def mais_perto(pontos, alvo):
    return min(pontos, key=lambda p: math.hypot(p.x - alvo.x, p.y - alvo.y))


def _objeto_sob_o_cursor(snapper):
    info = snapper.snapInfo or {}
    pai = info.get("ParentObject")
    if pai is not None:
        return pai.getSubObject(info.get("SubName", ""), retType=1)
    return App.ActiveDocument.getObject(info.get("Object", "")) if App.ActiveDocument else None


def _prender(snapper, ponto, lastpoint, constrain):
    """Faz o que o snapper faz com o ponto vencedor (marcador, linha de rastro, cursor)."""
    alvo = snapper.toWP(ponto)
    if snapper.tracker and not snapper.selectMode:
        snapper.tracker.setCoords(alvo)
        snapper.tracker.setMarker(snapper.mk["special"])
        snapper.tracker.on()
    fp = snapper.cstr(lastpoint, constrain, alvo)
    if snapper.trackLine and lastpoint:
        snapper.trackLine.p2(fp)
        snapper.trackLine.setColor()
        snapper.trackLine.on()
    snapper.setCursor("special")
    if lastpoint:
        snapper.setArchDims(lastpoint, fp)
    snapper.spoint = fp
    snapper.running = False
    return fp


def instalar(snapper=None):
    """Envolve o ``snapToObject`` do snapper do Draft (uma vez por sessão). Devolve True se instalou."""
    global _instalado
    snapper = snapper or getattr(Gui, "Snapper", None)
    if snapper is None or _instalado is snapper or not hasattr(snapper, "snapToObject"):
        return False
    original = snapper.snapToObject

    def snap_to_object(lastpoint, active, constrain, eline, point):
        if active and ligado():
            try:
                obj = _objeto_sob_o_cursor(snapper)
                pontos = pontos_de_ligacao(obj) if obj is not None else []
                if pontos:
                    info = snapper.snapInfo
                    cursor = App.Vector(info["x"], info["y"], info["z"])
                    snapper.lastSnappedObject = obj
                    return _prender(snapper, mais_perto(pontos, cursor), lastpoint, constrain)
            except Exception as erro:
                App.Console.PrintLog(f"Circuits: snap de ligação ignorado: {erro}\n")
        return original(lastpoint, active, constrain, eline, point)

    snapper.snapToObject = snap_to_object
    _instalado = snapper
    return True
