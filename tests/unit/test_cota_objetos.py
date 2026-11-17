"""Os pontos e interruptores acompanham a cota: Z = CotaPiso + Altura3D."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet")
RECARREGAR = ("freecad.Circuits.objects.ponto", "freecad.Circuits.objects.switch")


def simbolo(z=0.0, cota_piso=3000.0, altura=2000.0, estado=(), criando=False):
    return types.SimpleNamespace(
        CotaPiso=cota_piso, Altura3D=altura, State=list(estado), Proxy=types.SimpleNamespace(_criando=criando),
        Placement=types.SimpleNamespace(Base=types.SimpleNamespace(x=10.0, y=20.0, z=z)),
    )


class TestAcompanharCota(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        falsos["FreeCAD"].Vector = lambda x, y, z: types.SimpleNamespace(x=x, y=y, z=z)
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.ponto = importlib.import_module("freecad.Circuits.objects.ponto")
        self.switch = importlib.import_module("freecad.Circuits.objects.switch")

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def test_mudar_a_altura_move_o_simbolo(self):
        fp = simbolo()
        self.ponto.acompanhar_cota(fp, "Altura3D")
        self.assertEqual((fp.Placement.Base.x, fp.Placement.Base.y, fp.Placement.Base.z), (10.0, 20.0, 5000.0))

    def test_mudar_a_cota_do_piso_move_o_simbolo(self):
        fp = simbolo(cota_piso=6000.0, altura=300.0)
        self.ponto.acompanhar_cota(fp, "CotaPiso")
        self.assertEqual(fp.Placement.Base.z, 6300.0)

    def test_outras_propriedades_nao_movem(self):
        fp = simbolo()
        self.ponto.acompanhar_cota(fp, "Potencia")
        self.assertEqual(fp.Placement.Base.z, 0.0)

    def test_nao_move_ao_abrir_o_arquivo_nem_ao_criar_propriedades(self):
        for fp in (simbolo(estado=["Restore"]), simbolo(criando=True)):
            self.ponto.acompanhar_cota(fp, "Altura3D")
            self.assertEqual(fp.Placement.Base.z, 0.0)

    def test_switch_usa_a_mesma_regra(self):
        fp = simbolo(cota_piso=3000.0, altura=1200.0)
        self.switch.Switch.onChanged(None, fp, "Altura3D")
        self.assertEqual(fp.Placement.Base.z, 4200.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
