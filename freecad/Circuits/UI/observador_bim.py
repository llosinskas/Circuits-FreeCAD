"""Propriedades BIM (IFC) sempre em dia.

Quando um objeto é criado ou muda (ponto, interruptor, eletroduto, eletrocalha, colunas, prumadas,
o 3D de cada um...), ``services.bim.aplicar_com_3d`` regrava ``IfcType``, os atributos IFC e
``IfcProperties`` dele, até um segundo depois da mudança (as do mesmo segundo vão juntas). Objetos que estão sendo posicionados
com o mouse esperam o clique.

Desligue pela preferência booleana ``PropriedadesBIM`` em ``BaseApp/Preferences/Mod/Circuits``.
"""
import FreeCAD as App

from freecad.Circuits.qt import QtCore
from freecad.Circuits.services import bim

PREFERENCIAS = "User parameter:BaseApp/Preferences/Mod/Circuits"
PREFERENCIA = "PropriedadesBIM"
IGNORADAS = {"IfcType", "IfcProperties", "PredefinedType", "ObjectType", "Tag", bim.MARCA, "Visibility",
             "Label2", "ExpressionEngine", "Proxy", "Placement", "Shape", "SnapPoints", "TiposDasPecas"}
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


class ObservadorBim:
    """Agenda a gravação das propriedades BIM dos objetos criados ou alterados."""

    def __init__(self):
        self.pendentes = set()  # (documento, objeto)
        self.temporizador = QtCore.QTimer()
        self.temporizador.setSingleShot(True)
        self.temporizador.timeout.connect(self.atualizar)

    def _agendar(self, obj):
        if not ligado():
            return
        try:
            if "Restore" in obj.State:
                return
            self.pendentes.add((obj.Document.Name, obj.Name))
        except Exception:
            return
        if not self.temporizador.isActive():  # junta as mudanças do próximo segundo, sem adiar sem fim
            self.temporizador.start(ESPERA_MS)

    def slotCreatedObject(self, obj):
        self._agendar(obj)

    def slotChangedObject(self, obj, prop):
        if prop not in IGNORADAS:
            self._agendar(obj)

    def atualizar(self):
        pendentes, self.pendentes = self.pendentes, set()
        adiados = set()
        for documento, nome in pendentes:
            try:
                doc = App.getDocument(documento)
                obj = doc.getObject(nome)
            except Exception:
                continue
            if obj is None:
                continue
            if _sendo_inserido(obj):
                adiados.add((documento, nome))
                continue
            try:
                bim.aplicar_com_3d(doc, obj)
            except Exception as erro:
                App.Console.PrintWarning(f"Circuits: propriedades BIM não atualizadas: {erro}\n")
        if adiados:
            self.pendentes |= adiados
            self.temporizador.start(ESPERA_MS)


def instalar():
    """Liga o observador uma vez por sessão do FreeCAD."""
    global _observador
    if _observador is None:
        _observador = ObservadorBim()
        App.addDocumentObserver(_observador)
    return _observador
