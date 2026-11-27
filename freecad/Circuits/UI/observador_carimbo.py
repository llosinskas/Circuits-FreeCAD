"""Carimbo paramétrico das folhas: atualiza sozinho quando as fontes mudam.

- Mudou a planilha *Parâmetros do projeto* (projeto, obra, cliente, desenho, responsável,
  registro), o nome do documento, uma propriedade ``Carimbo…`` de uma folha, ou uma folha
  foi criada ou apagada: ``folhas.atualizar_carimbos`` reescreve os carimbos de todas.
- O usuário editou o carimbo na própria folha (dois cliques no campo): ``folhas.sincronizar_do_carimbo``
  leva o texto para a fonte, e ele aparece em todas as folhas.

Espera ``ESPERA_MS`` depois da última mudança. Desligue pela preferência booleana
``CarimboParametrico`` em ``BaseApp/Preferences/Mod/Circuits``.
"""
import FreeCAD as App

from freecad.Circuits.core import folhas as regras
from freecad.Circuits.qt import QtCore
from freecad.Circuits.services import folhas

PREFERENCIAS = "User parameter:BaseApp/Preferences/Mod/Circuits"
PREFERENCIA = "CarimboParametrico"
ESPERA_MS = 400

_observador = None


def ligado():
    try:
        return App.ParamGet(PREFERENCIAS).GetBool(PREFERENCIA, True)
    except Exception:
        return True


def _restaurando(obj):
    try:
        return "Restore" in obj.State or "Restoring" in getattr(obj.Document, "State", ())
    except Exception:
        return True


class ObservadorCarimbo:
    """Agenda a atualização dos carimbos das folhas da bancada."""

    def __init__(self):
        self.pendentes = {}  # documento -> nomes das folhas editadas à mão (ou vazio: só atualizar)
        self.temporizador = QtCore.QTimer()
        self.temporizador.setSingleShot(True)
        self.temporizador.timeout.connect(self.atualizar)

    def _agendar(self, obj, editada=None):
        try:
            documento = obj.Document.Name
        except Exception:
            return
        self.pendentes.setdefault(documento, set())
        if editada is not None:
            self.pendentes[documento].add(editada)
        self.temporizador.start(ESPERA_MS)

    def slotChangedObject(self, obj, prop):
        if folhas.ATUALIZANDO_CARIMBOS or not ligado() or _restaurando(obj):
            return
        try:
            if hasattr(obj, "parametros_do_projeto"):
                self._agendar(obj)
            elif hasattr(obj, folhas.MARCA_FOLHA) and prop in set(regras.CARIMBO_DA_FOLHA.values()) | {"Template"}:
                self._agendar(obj)
            elif prop == "EditableTexts" and getattr(obj, "TypeId", "") == "TechDraw::DrawSVGTemplate":
                folha = next((f for f in obj.InList if hasattr(f, folhas.MARCA_FOLHA)), None)
                if folha is not None:
                    self._agendar(obj, folha.Name)
        except Exception:
            return

    def slotCreatedObject(self, obj):
        if not folhas.ATUALIZANDO_CARIMBOS and ligado() and getattr(obj, "TypeId", "") == "TechDraw::DrawPage":
            self._agendar(obj)

    def slotDeletedObject(self, obj):
        if ligado() and hasattr(obj, folhas.MARCA_FOLHA):
            self._agendar(obj)

    def slotChangedDocument(self, doc, prop):
        if prop == "Label" and ligado() and not folhas.ATUALIZANDO_CARIMBOS:
            self.pendentes.setdefault(doc.Name, set())
            self.temporizador.start(ESPERA_MS)

    def atualizar(self):
        pendentes, self.pendentes = self.pendentes, {}
        for documento, editadas in pendentes.items():
            try:
                doc = App.getDocument(documento)
            except Exception:
                continue
            try:
                for nome in editadas:
                    folha = doc.getObject(nome)
                    if folha is not None:
                        folhas.sincronizar_do_carimbo(doc, folha)
                if folhas.atualizar_carimbos(doc):
                    doc.recompute()
            except Exception as erro:
                App.Console.PrintWarning(f"Circuits: carimbo das folhas não atualizado: {erro}\n")


def instalar():
    """Liga o observador uma vez por sessão do FreeCAD."""
    global _observador
    if _observador is None:
        _observador = ObservadorCarimbo()
        App.addDocumentObserver(_observador)
    return _observador
