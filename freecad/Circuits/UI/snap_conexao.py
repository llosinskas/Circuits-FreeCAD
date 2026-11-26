"""Snap especial de ligação: o eletroduto prende no ponto da caixa dos símbolos e na borda das eletrocalhas.

Como o conector de um dispositivo no Revit: ao desenhar uma linha do Draft (eletroduto,
eletrocalha) com o cursor sobre uma tomada, luminária, interruptor, quadro ou caixa de
passagem, o ponto vai direto para a caixa do símbolo (``SnapPoints``, o ponto de
inserção), com o marcador do snap especial, em vez do ponto mais próximo da linha do
desenho, que o snap "Próximo" do Draft escolheria. Sobre uma eletrocalha ou leito (a linha
de centro ou o contorno em linha dupla), o ponto vai para a borda dela, do lado do cursor,
na perpendicular (``core.bandejas.ponto_na_borda``): onde a ponta do eletroduto vira uma
saída de eletrocalha.

O Draft já oferece os ``SnapPoints`` no snap especial, mas como mais um candidato, e o
mais perto do cursor ganha. Este módulo envolve o ``snapToObject`` do snapper (conferido
no FreeCAD 1.0.2) e dá prioridade ao ponto de ligação. Qualquer erro cai no snap normal.

Desligue pela preferência booleana ``SnapConexao`` em ``BaseApp/Preferences/Mod/Circuits``.
"""
import math

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.core import bandejas as regras_bandejas
from freecad.Circuits.services import bandejas

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


def ponto_na_eletrocalha(obj, cursor):
    """Ponto da borda da eletrocalha sob o cursor, ou None se o objeto não é eletrocalha nem o
    contorno dela. No contorno (um objeto por pavimento), vale a eletrocalha mais perto."""
    if bandejas.eh_bandeja(obj):
        candidatas = [obj]
    elif hasattr(obj, "contorno_bandejas_de"):
        candidatas = bandejas.listar(obj.Document)
    else:
        return None
    caminhos = []
    for bandeja in candidatas:
        try:
            caminhos.append(dict(bandejas._caminho(bandeja), objeto=bandeja))
        except Exception:
            continue
    # sobre a própria linha da eletrocalha, sempre ela; sobre o contorno, só perto de uma
    folga = math.inf if bandejas.eh_bandeja(obj) else regras_bandejas.FOLGA_SNAP_MM
    achado = regras_bandejas.bandeja_sob_o_cursor(caminhos, (cursor.x, cursor.y), folga=folga)
    if achado is None:
        return None
    caminho, (x, y) = achado
    objeto = caminho["objeto"]
    z = objeto.Placement.multVec(objeto.Points[0]).z if objeto.Points else cursor.z
    return App.Vector(x, y, z)


def ponto_de_ligacao(obj, cursor):
    """Onde a linha prende: a caixa do símbolo mais perto do cursor ou a borda da eletrocalha."""
    pontos = pontos_de_ligacao(obj)
    if pontos:
        return mais_perto(pontos, cursor)
    return ponto_na_eletrocalha(obj, cursor)


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
                info = snapper.snapInfo
                cursor = App.Vector(info["x"], info["y"], info["z"])
                ponto = ponto_de_ligacao(obj, cursor) if obj is not None else None
                if ponto is not None:
                    snapper.lastSnappedObject = obj
                    return _prender(snapper, ponto, lastpoint, constrain)
            except Exception as erro:
                App.Console.PrintLog(f"Circuits: snap de ligação ignorado: {erro}\n")
        return original(lastpoint, active, constrain, eline, point)

    snapper.snapToObject = snap_to_object
    _instalado = snapper
    return True
