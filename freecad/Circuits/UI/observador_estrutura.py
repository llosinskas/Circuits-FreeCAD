"""Estrutura de pastas sempre arrumada.

Num projeto com a estrutura nova (pastas marcadas com ``pasta_projeto``), o que os comandos criam na
raiz do documento (planilhas, diagramas sem símbolo, legenda, notas, folhas) vai para a pasta certa
(``services.estrutura.organizar``) até 1,5 s depois de criado.

Desligue pela preferência booleana ``OrganizarPastas`` em ``BaseApp/Preferences/Mod/Circuits``.
"""
import FreeCAD as App

from freecad.Circuits.qt import QtCore
from freecad.Circuits.services import estrutura

PREFERENCIAS = "User parameter:BaseApp/Preferences/Mod/Circuits"
PREFERENCIA = "OrganizarPastas"
ESPERA_MS = 1500

_observador = None


def ligado():
    try:
        return App.ParamGet(PREFERENCIAS).GetBool(PREFERENCIA, True)
    except Exception:
        return True


class ObservadorEstrutura:
    def __init__(self):
        self.documentos = set()
        self.temporizador = QtCore.QTimer()
        self.temporizador.setSingleShot(True)
        self.temporizador.timeout.connect(self.atualizar)

    def slotCreatedObject(self, obj):
        if not ligado():
            return
        try:
            if "Restore" in obj.State:
                return
            self.documentos.add(obj.Document.Name)
        except Exception:
            return
        if not self.temporizador.isActive():
            self.temporizador.start(ESPERA_MS)

    def atualizar(self):
        documentos, self.documentos = self.documentos, set()
        for nome in documentos:
            try:
                doc = App.getDocument(nome)
            except Exception:
                continue
            try:
                if estrutura.ativa(doc):
                    estrutura.organizar(doc)
            except Exception as erro:
                App.Console.PrintWarning(f"Circuits: pastas não organizadas: {erro}\n")


def instalar():
    """Liga o observador uma vez por sessão do FreeCAD."""
    global _observador
    if _observador is None:
        _observador = ObservadorEstrutura()
        App.addDocumentObserver(_observador)
    return _observador
