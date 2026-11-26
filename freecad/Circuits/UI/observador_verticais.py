"""Atualização automática das subidas e descidas, como no Revit.

Ao mudar a altura (``Altura3D``, ``AlturasTrechos``), os pontos ou o diâmetro de um
eletroduto, os símbolos de subida e descida, os rótulos e o 3D que já existem no
documento são refeitos sozinhos (``eletrodutos_planta.atualizar_depois_de_editar``),
um segundo depois da última mudança, para não refazer a cada passo de uma edição.

Desligue pela preferência booleana ``AtualizarVerticais`` em
``BaseApp/Preferences/Mod/Circuits``.
"""
import time

import FreeCAD as App

from freecad.Circuits.qt import QtCore
from freecad.Circuits.services import eletrodutos_planta, rede

PREFERENCIAS = "User parameter:BaseApp/Preferences/Mod/Circuits"
PREFERENCIA = "AtualizarVerticais"
PROPRIEDADES = {"Altura3D", "AlturasTrechos", "Points", "Diametro", "Tipo", "Placement"}
ESPERA_MS = 1000

_observador = None


def ligado():
    try:
        return App.ParamGet(PREFERENCIAS).GetBool(PREFERENCIA, True)
    except Exception:
        return True


class ObservadorVerticais:
    """Observa os eletrodutos e agenda a atualização do que depende da altura deles."""

    def __init__(self):
        self.documento = None
        self.mudou_em = 0.0
        self.temporizador = QtCore.QTimer()
        self.temporizador.setSingleShot(True)
        self.temporizador.timeout.connect(self.atualizar)

    def slotChangedObject(self, obj, prop):
        if prop not in PROPRIEDADES or eletrodutos_planta.ATUALIZANDO or not ligado():
            return
        try:
            if "Restore" in obj.State or not rede.eh_eletroduto(obj):
                return
            self.documento = obj.Document.Name
        except Exception:
            return
        self.mudou_em = time.monotonic()
        self.temporizador.start(ESPERA_MS)

    def atualizar(self):
        if eletrodutos_planta.ULTIMA_ATUALIZACAO >= self.mudou_em:
            return  # o comando que mudou o eletroduto já atualizou
        try:
            doc = App.getDocument(self.documento)
        except Exception:
            return
        try:
            eletrodutos_planta.atualizar_depois_de_editar(doc)  # só o que já existe: símbolos, rótulos, 3D
        except Exception as erro:
            App.Console.PrintWarning(f"Circuits: subidas e descidas não atualizadas: {erro}\n")


def instalar():
    """Liga o observador uma vez por sessão do FreeCAD."""
    global _observador
    if _observador is None:
        _observador = ObservadorVerticais()
        App.addDocumentObserver(_observador)
    return _observador
