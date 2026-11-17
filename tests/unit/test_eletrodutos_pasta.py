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


    def test_rigido_tambem_faz_a_curva_em_arco_no_3d(self):
        linha = types.SimpleNamespace(Diametro="3/4", Tipo="Rígido", Altura3D=2800.0, Cor="Amarelo", FilletRadius=0.0)
        self.servico._preparar_caminho(linha)
        raio_tubo = self.servico.DIAMETROS_EXTERNOS["3/4"] / 2
        self.assertAlmostEqual(linha.FilletRadius, raio_tubo * self.servico.FATOR_RAIO_CURVA_RIGIDO)
        linha.Tipo = "Flexível"
        self.servico._preparar_caminho(linha)
        self.assertAlmostEqual(linha.FilletRadius, raio_tubo * self.servico.FATOR_RAIO_CURVA_FLEXIVEL)


if __name__ == "__main__":
    unittest.main()
