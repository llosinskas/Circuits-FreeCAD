"""Modelo 3D completo num botão só (services/modelo_3d.py), com o FreeCAD simulado."""
import importlib
import sys
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)

MODULOS = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Spreadsheet", "Sketcher")


class TestModelo3D(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.dict(sys.modules, {n: mock.MagicMock(name=n) for n in MODULOS})
        self.patch.start()
        for nome in [n for n in sys.modules if n.startswith("freecad.Circuits.services")]:
            sys.modules.pop(nome, None)
        self.servico = importlib.import_module("freecad.Circuits.services.modelo_3d")

    def tearDown(self):
        for nome in [n for n in sys.modules if n.startswith("freecad.Circuits.services")]:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def test_gera_tudo_e_conta(self):
        s = self.servico
        conduite, tug = object(), object()
        with mock.patch.object(s.caixas_3d, "listar_alvos", return_value=(["p1", "p2"], [tug])), \
                mock.patch.object(s.caixas_3d, "gerar_caixas", return_value=2) as caixas, \
                mock.patch.object(s.rede, "listar_eletrodutos", return_value=[conduite]), \
                mock.patch.object(s.eletrodutos, "gerar_tubos", return_value=1) as tubos, \
                mock.patch.object(s.bandejas, "listar", return_value=["b"]), \
                mock.patch.object(s.bandejas, "gerar_3d", return_value=1) as bandejas_3d, \
                mock.patch.object(s.bandejas, "gerar_suportes", return_value={"Térreo": 4}) as suportes:
            feito = s.gerar_tudo("doc")
        self.assertEqual(feito, {"caixas": 2, "eletrodutos": 1, "bandejas": 1, "suportes": 4})
        caixas.assert_called_once_with("doc", ["p1", "p2"], [tug])  # a TUG em Sketch já tem caixa aqui
        tubos.assert_called_once_with("doc", [conduite])  # também as linhas marcadas, não só ConduitPath
        bandejas_3d.assert_called_once_with("doc")
        suportes.assert_called_once_with("doc")

    def test_sem_nada_nao_chama_os_geradores(self):
        s = self.servico
        with mock.patch.object(s.caixas_3d, "listar_alvos", return_value=([], [])), \
                mock.patch.object(s.caixas_3d, "gerar_caixas") as caixas, \
                mock.patch.object(s.rede, "listar_eletrodutos", return_value=[]), \
                mock.patch.object(s.eletrodutos, "gerar_tubos") as tubos, \
                mock.patch.object(s.bandejas, "listar", return_value=[]), \
                mock.patch.object(s.bandejas, "gerar_3d") as bandejas_3d:
            self.assertEqual(sum(s.gerar_tudo("doc").values()), 0)
        caixas.assert_not_called()
        tubos.assert_not_called()
        bandejas_3d.assert_not_called()


if __name__ == "__main__":
    unittest.main()
