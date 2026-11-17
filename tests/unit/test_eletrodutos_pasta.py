"""Eletrodutos 3D: as linhas entram na pasta Eletrodutos do pavimento antes de gerar o tubo."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)

MODULOS = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Spreadsheet", "Sketcher")
RECARREGAR = ("freecad.Circuits.services.eletrodutos", "freecad.Circuits.services.pavimentos",
              "freecad.Circuits.services.tomadas", "freecad.Circuits.services.documento")


class TestGerarTubos(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.dict(sys.modules, {n: mock.MagicMock(name=n) for n in MODULOS})
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.servico = importlib.import_module("freecad.Circuits.services.eletrodutos")

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def test_linha_solta_vai_para_o_pavimento_de_insercao(self):
        solta = types.SimpleNamespace(Name="Wire", Points=[], Proxy=types.SimpleNamespace(Type="Wire"))
        guardada = types.SimpleNamespace(Name="Wire001", Points=[], Proxy=types.SimpleNamespace(Type="Wire"))
        doc, nivel = mock.MagicMock(), object()
        with mock.patch.object(self.servico, "_preparar_caminho"), \
                mock.patch.object(self.servico, "_gerar_tubo", return_value=True), \
                mock.patch.object(self.servico, "listar_tomadas", return_value=[]), \
                mock.patch.object(self.servico.pavimentos, "pavimento_do_objeto",
                                  side_effect=lambda d, o: None if o is solta else object()), \
                mock.patch.object(self.servico.pavimentos, "pavimento_para_insercao", return_value=nivel), \
                mock.patch.object(self.servico.pavimentos, "arquivar") as arquivar:
            self.assertEqual(self.servico.gerar_tubos(doc, [solta, guardada]), 2)
        arquivar.assert_called_once_with(doc, solta, nivel)


if __name__ == "__main__":
    unittest.main()
