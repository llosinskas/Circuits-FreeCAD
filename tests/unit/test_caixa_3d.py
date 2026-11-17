"""Volume 3D da caixa em relação ao ponto de inserção do símbolo (core/simbolos.py)."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import simbolos


class TestPosicaoDaCaixa(unittest.TestCase):
    def test_tomadas_de_parede_ficam_atras_do_ponto(self):
        for simbolo in ("tomada_baixa", "tomada_media", "tomada_alta"):
            self.assertEqual(simbolos.posicao_da_caixa(simbolo), "parede", simbolo)

    def test_tomada_de_piso_fica_embaixo_e_os_outros_centrados(self):
        self.assertEqual(simbolos.posicao_da_caixa("tomada_piso"), "piso")
        self.assertEqual(simbolos.posicao_da_caixa("luz_teto"), "centro")
        self.assertEqual(simbolos.posicao_da_caixa("nao_existe"), "centro")


class TestCaixaLocal(unittest.TestCase):
    """(x, y, z do canto, comprimento em x, em y, em z) no sistema do símbolo, com z a partir da cota da caixa."""

    def test_parede_entra_no_sentido_contrario_ao_triangulo(self):
        # o triângulo aponta para +x (o ambiente); a caixa vai de -profundidade a 0 em x
        self.assertEqual(simbolos.caixa_local("parede", 60, 40, 100), (-40.0, -30.0, -50.0, 40.0, 60.0, 100.0))

    def test_piso_tem_o_topo_no_piso(self):
        self.assertEqual(simbolos.caixa_local("piso", 100, 100, 50), (-50.0, -50.0, -50.0, 100.0, 100.0, 50.0))

    def test_centro_como_antes(self):
        self.assertEqual(simbolos.caixa_local("centro", 60, 40, 100), (-30.0, -20.0, -50.0, 60.0, 40.0, 100.0))


if __name__ == "__main__":
    unittest.main()


import importlib  # noqa: E402
import sys  # noqa: E402
import types  # noqa: E402
from unittest import mock  # noqa: E402

MODULOS = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Spreadsheet", "Sketcher")
RECARREGAR = ("freecad.Circuits.services.caixas_3d", "freecad.Circuits.services.pavimentos",
              "freecad.Circuits.services.tomadas", "freecad.Circuits.services.documento")


class TestServico(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.dict(sys.modules, {n: mock.MagicMock(name=n) for n in MODULOS})
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        fc = sys.modules["FreeCAD"]
        fc.Vector = lambda x=0.0, y=0.0, z=0.0: (x, y, z)
        fc.Placement = lambda base, rotacao: ("placement", base, rotacao)
        self.servico = importlib.import_module("freecad.Circuits.services.caixas_3d")

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def ponto(self, simbolo, rotacao="girada 90°"):
        return types.SimpleNamespace(
            Name="T1", Label="T1", Simbolo=simbolo, Proxy=types.SimpleNamespace(Type="Ponto"),
            CaixaLargura=60.0, CaixaProfundidade=40.0, CaixaAltura=100.0,
            Placement=types.SimpleNamespace(Base=types.SimpleNamespace(x=1000.0, y=2000.0, z=0.0), Rotation=rotacao))

    def gerar(self, obj):
        doc = mock.MagicMock()
        doc.getObject.return_value = None
        with mock.patch.object(self.servico.pavimentos, "cota_3d", return_value=300.0), \
                mock.patch.object(self.servico.pavimentos, "guardar_3d"):
            self.servico.gerar_caixas(doc, [obj], [])
        return doc.addObject.return_value

    def test_tomada_de_parede_atras_do_ponto_e_girada_com_o_simbolo(self):
        part = sys.modules["Part"]
        caixa = self.gerar(self.ponto("tomada_baixa"))
        part.makeBox.assert_called_once_with(40.0, 60.0, 100.0, (-40.0, -30.0, -50.0))
        self.assertEqual(caixa.Placement, ("placement", (1000.0, 2000.0, 300.0), "girada 90°"))

    def test_luz_continua_centrada(self):
        part = sys.modules["Part"]
        self.gerar(self.ponto("luz_teto"))
        part.makeBox.assert_called_once_with(60.0, 40.0, 100.0, (-30.0, -20.0, -50.0))
