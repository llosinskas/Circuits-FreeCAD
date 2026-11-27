"""Símbolos das prumadas acompanham o objeto.

Ao mover ou girar um objeto ``Prumada`` (``Placement``) ou mudar os andares, os símbolos em planta
de cada pavimento são refeitos (``services.prumadas.desenhar_2d``) um segundo depois da última
mudança. Durante a inserção com o mouse nada é refeito: o comando desenha ao fixar.

Desligue pela preferência booleana ``AtualizarPrumadas`` em ``BaseApp/Preferences/Mod/Circuits``.
"""
import time

import FreeCAD as App

from freecad.Circuits.qt import QtCore
from freecad.Circuits.services import prumadas

PREFERENCIAS = "User parameter:BaseApp/Preferences/Mod/Circuits"
PREFERENCIA = "AtualizarPrumadas"
PROPRIEDADES = {"Placement"}
ESPERA_MS = 1000

_observador = None


def ligado():
    try:
        return App.ParamGet(PREFERENCIAS).GetBool(PREFERENCIA, True)
    except Exception:
        return True


def _sendo_inserido(obj):
    try:
        from freecad.Circuits.UI.dialogs.ComponentInserter import ComponentInsertionMode
        modo = ComponentInsertionMode._active_instance
        return modo is not None and getattr(modo, "obj", None) is obj and getattr(modo, "is_active", True)
    except Exception:
        return False


class ObservadorPrumadas:
    """Agenda o redesenho dos símbolos das prumadas movidas ou giradas."""

    def __init__(self):
        self.pendentes = {}  # (documento, objeto) -> instante da mudança
        self.temporizador = QtCore.QTimer()
        self.temporizador.setSingleShot(True)
        self.temporizador.timeout.connect(self.atualizar)

    def slotChangedObject(self, obj, prop):
        if prop not in PROPRIEDADES or not ligado():
            return
        try:
            if "Restore" in obj.State or not prumadas.eh_prumada(obj) or _sendo_inserido(obj):
                return
            chave = (obj.Document.Name, obj.Name)
        except Exception:
            return
        self.pendentes[chave] = time.monotonic()
        self.temporizador.start(ESPERA_MS)

    def atualizar(self):
        pendentes, self.pendentes = self.pendentes, {}
        for (documento, nome), mudou_em in pendentes.items():
            if prumadas.ULTIMO_DESENHO >= mudou_em:
                continue  # o comando já redesenhou depois da mudança
            try:
                doc = App.getDocument(documento)
                obj = doc.getObject(nome)
            except Exception:
                continue
            if obj is None or _sendo_inserido(obj):
                continue
            try:
                prumadas.desenhar_2d(doc, obj)
            except Exception as erro:
                App.Console.PrintWarning(f"Circuits: símbolos das prumadas não atualizados: {erro}\n")


def instalar():
    """Liga o observador uma vez por sessão do FreeCAD."""
    global _observador
    if _observador is None:
        _observador = ObservadorPrumadas()
        App.addDocumentObserver(_observador)
    return _observador
