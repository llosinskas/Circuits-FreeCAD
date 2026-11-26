"""Snap especial de ligação: a linha do Draft prende na caixa do símbolo (UI/snap_conexao.py)."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)


class Vetor:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z

    def __eq__(self, outro):
        return (self.x, self.y, self.z) == (outro.x, outro.y, outro.z)


class Colocacao:
    def __init__(self, x, y):
        self.Base = Vetor(x, y)

    def multVec(self, p):
        return Vetor(self.Base.x + p.x, self.Base.y + p.y, p.z)


class Snapper:
    def __init__(self, documento):
        self.snapInfo, self.tracker, self.trackLine, self.selectMode = None, mock.Mock(), None, False
        self.mk = {"special": "marca especial"}
        self.cursor, self.spoint, self.running, self.lastSnappedObject = None, None, True, None
        self.chamadas_originais = 0
        self.documento = documento

    def snapToObject(self, lastpoint, active, constrain, eline, point):
        self.chamadas_originais += 1
        return "ponto do Draft"

    def toWP(self, p):
        return p

    def cstr(self, lastpoint, constrain, p):
        return p

    def setCursor(self, nome):
        self.cursor = nome

    def setArchDims(self, a, b):
        pass


class TestSnapConexao(unittest.TestCase):
    def setUp(self):
        self.app = mock.MagicMock(name="FreeCAD")
        self.app.Vector = Vetor
        self.app.ParamGet.return_value.GetBool.return_value = True
        self.patch = mock.patch.dict(sys.modules, {"FreeCAD": self.app, "FreeCADGui": mock.MagicMock()})
        self.patch.start()
        sys.modules.pop("freecad.Circuits.UI.snap_conexao", None)
        self.m = importlib.import_module("freecad.Circuits.UI.snap_conexao")
        self.tomada = types.SimpleNamespace(Name="T1", Proxy=types.SimpleNamespace(Type="Ponto"),
                                            SnapPoints=[Vetor()], Placement=Colocacao(1000, 2000))
        self.linha = types.SimpleNamespace(Name="Wire", Proxy=types.SimpleNamespace(Type="Wire"),
                                           Placement=Colocacao(0, 0))
        objetos = {"T1": self.tomada, "Wire": self.linha}
        self.app.ActiveDocument.getObject.side_effect = objetos.get
        self.snapper = Snapper(None)
        self.assertTrue(self.m.instalar(self.snapper))

    def tearDown(self):
        sys.modules.pop("freecad.Circuits.UI.snap_conexao", None)
        self.patch.stop()

    def cursor_sobre(self, nome, x, y):
        self.snapper.snapInfo = {"Object": nome, "x": x, "y": y, "z": 0.0, "Component": "Edge3"}

    def test_cursor_na_borda_da_tomada_prende_na_caixa(self):
        self.cursor_sobre("T1", 1120, 2080)
        ponto = self.snapper.snapToObject(None, True, False, None, None)
        self.assertEqual(ponto, Vetor(1000, 2000, 0))
        self.assertEqual((self.snapper.cursor, self.snapper.chamadas_originais), ("special", 0))
        self.snapper.tracker.setMarker.assert_called_once_with("marca especial")
        self.assertIs(self.snapper.lastSnappedObject, self.tomada)

    def test_outros_objetos_e_snap_passivo_seguem_o_draft(self):
        self.cursor_sobre("Wire", 10, 0)
        self.assertEqual(self.snapper.snapToObject(None, True, False, None, None), "ponto do Draft")
        self.cursor_sobre("T1", 1120, 2080)
        self.assertEqual(self.snapper.snapToObject(None, False, False, None, None), "ponto do Draft")

    def test_preferencia_desliga(self):
        self.app.ParamGet.return_value.GetBool.return_value = False
        self.cursor_sobre("T1", 1120, 2080)
        self.assertEqual(self.snapper.snapToObject(None, True, False, None, None), "ponto do Draft")

    def test_tomada_antiga_em_sketch_e_instalar_uma_vez(self):
        sketch = types.SimpleNamespace(tipo="tomada", Placement=Colocacao(5, 6))
        self.assertEqual(self.m.pontos_de_ligacao(sketch), [Vetor(5, 6)])
        self.assertFalse(self.m.instalar(self.snapper))  # já instalado


if __name__ == "__main__":
    unittest.main()
