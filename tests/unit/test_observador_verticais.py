"""Atualização automática das subidas e descidas ao editar um eletroduto (UI/observador_verticais.py)."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)

MODULOS = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Spreadsheet", "Sketcher")


class Temporizador:
    def __init__(self):
        self.iniciado, self.funcao = 0, None
        self.timeout = types.SimpleNamespace(connect=lambda f: setattr(self, "funcao", f))

    def setSingleShot(self, valor):
        pass

    def start(self, ms):
        self.iniciado += 1


class TestObservador(unittest.TestCase):
    def setUp(self):
        falsos = {n: mock.MagicMock(name=n) for n in MODULOS}
        falsos["FreeCAD"].ParamGet.return_value.GetBool.return_value = True
        qt = types.SimpleNamespace(QtCore=types.SimpleNamespace(QTimer=Temporizador), QtWidgets=mock.MagicMock())
        falsos["freecad.Circuits.qt"] = qt
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in ("freecad.Circuits.UI.observador_verticais",):
            sys.modules.pop(nome, None)
        self.m = importlib.import_module("freecad.Circuits.UI.observador_verticais")
        self.planta = types.SimpleNamespace(ATUALIZANDO=False, ULTIMA_ATUALIZACAO=0.0,
                                            atualizar_depois_de_editar=mock.Mock())
        self.m.eletrodutos_planta = self.planta
        self.m.rede = types.SimpleNamespace(eh_eletroduto=lambda obj: getattr(obj, "eletroduto", False))
        self.obs = self.m.ObservadorVerticais()
        self.eletroduto = types.SimpleNamespace(State=[], eletroduto=True, Document=types.SimpleNamespace(Name="D"))

    def tearDown(self):
        sys.modules.pop("freecad.Circuits.UI.observador_verticais", None)
        self.patch.stop()

    def test_altura_mudada_agenda_e_atualiza(self):
        self.obs.slotChangedObject(self.eletroduto, "AlturasTrechos")
        self.assertEqual(self.obs.temporizador.iniciado, 1)
        self.obs.temporizador.funcao()
        self.planta.atualizar_depois_de_editar.assert_called_once()

    def test_ignora_o_que_nao_interessa(self):
        self.obs.slotChangedObject(self.eletroduto, "Label")
        self.obs.slotChangedObject(types.SimpleNamespace(State=[], eletroduto=False), "Altura3D")
        self.obs.slotChangedObject(types.SimpleNamespace(State=["Restore"], eletroduto=True), "Altura3D")
        self.planta.ATUALIZANDO = True
        self.obs.slotChangedObject(self.eletroduto, "Altura3D")
        self.assertEqual(self.obs.temporizador.iniciado, 0)

    def test_nao_repete_o_que_o_comando_ja_atualizou(self):
        self.obs.slotChangedObject(self.eletroduto, "Points")
        self.planta.ULTIMA_ATUALIZACAO = self.obs.mudou_em + 1
        self.obs.temporizador.funcao()
        self.planta.atualizar_depois_de_editar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
