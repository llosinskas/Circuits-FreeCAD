"""Luminotécnico: método dos lúmens, malha de luminárias e distribuição no retângulo."""
import importlib
import math
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core.functions.Predial import luminotecnico as lum

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet")
RECARREGAR = ("freecad.Circuits.services.luminotecnico", "freecad.Circuits.services.identificacao",
              "freecad.Circuits.services.pavimentos",
              "freecad.Circuits.services.alinhamento", "freecad.Circuits.services.tomadas",
              "freecad.Circuits.services.documento", "freecad.Circuits.objects.ponto")


class TestCalculo(unittest.TestCase):
    def test_indice_do_local(self):
        self.assertAlmostEqual(lum.indice_do_local(5, 4, 1.95), 20 / (1.95 * 9))
        with self.assertRaises(ValueError):
            lum.indice_do_local(5, 4, 0)
        with self.assertRaises(ValueError):
            lum.indice_do_local(0, 4, 2)

    def test_fator_de_utilizacao_interpola_e_satura(self):
        self.assertEqual(lum.fator_utilizacao(0.2), 0.32)
        self.assertEqual(lum.fator_utilizacao(1.0), 0.45)
        self.assertAlmostEqual(lum.fator_utilizacao(1.125), 0.48)
        self.assertEqual(lum.fator_utilizacao(9), 0.75)
        fatores = [lum.fator_utilizacao(k / 10) for k in range(1, 70)]
        self.assertEqual(fatores, sorted(fatores))

    def test_malha_regular(self):
        self.assertEqual(lum.malha(1, 5, 4), (1, 1))
        self.assertEqual(lum.malha(4, 5, 4), (2, 2))
        self.assertEqual(lum.malha(7, 5, 4), (4, 2))   # e não uma fileira de 7
        self.assertEqual(lum.malha(18, 10, 6), (6, 3))
        self.assertEqual(lum.malha(3, 9, 2), (3, 1))   # corredor: uma fileira
        self.assertEqual(lum.malha(3, 2, 9), (1, 3))

    def test_malha_nunca_tem_menos_que_o_pedido(self):
        for quantidade in range(1, 60):
            nx, ny = lum.malha(quantidade, 7.3, 4.1)
            self.assertGreaterEqual(nx * ny, quantidade)
            self.assertLessEqual(nx * ny, math.ceil(quantidade * 1.25))

    def test_posicoes_com_meio_espacamento_ate_as_paredes(self):
        self.assertEqual(lum.posicoes(2, 2, 5, 4), [(1.25, 1.0), (3.75, 1.0), (1.25, 3.0), (3.75, 3.0)])

    def test_sala_de_5_por_4(self):
        r = lum.dimensionar(5, 4, 150, 2000)
        # K = 1,14 -> U = 0,484; N = 150 x 20 / (2000 x 0,484 x 0,8) = 3,9 -> 4
        self.assertAlmostEqual(r["quantidade_calculada"], 150 * 20 / (2000 * r["fator_utilizacao"] * 0.8))
        self.assertEqual((r["nx"], r["ny"], r["quantidade"]), (2, 2, 4))
        self.assertGreaterEqual(r["iluminancia_resultante"], 150)
        self.assertEqual(len(r["posicoes"]), 4)
        self.assertIn("2 x 2 = 4 luminárias", lum.relatorio(r))

    def test_fator_do_catalogo_substitui_a_estimativa(self):
        r = lum.dimensionar(5, 4, 150, 2000, fator_utilizacao_informado=0.9)
        self.assertEqual(r["fator_utilizacao"], 0.9)
        self.assertLess(r["quantidade_calculada"], 3)

    def test_entradas_invalidas(self):
        for argumentos in ((5, 4, 0, 2000), (5, 4, 150, 0)):
            with self.assertRaises(ValueError):
                lum.dimensionar(*argumentos)
        with self.assertRaises(ValueError):
            lum.dimensionar(5, 4, 150, 2000, pe_direito=0.7)
        with self.assertRaises(ValueError):
            lum.dimensionar(5, 4, 150, 2000, fator_manutencao=0)

    def test_lista_de_ambientes(self):
        self.assertIsNone(lum.ILUMINANCIAS[lum.PERSONALIZADO])
        self.assertTrue(all(valor > 0 for nome, valor in lum.ILUMINANCIAS.items() if nome != lum.PERSONALIZADO))


def caixa(xmin, ymin, comprimento, largura):
    return types.SimpleNamespace(XMin=xmin, YMin=ymin, XLength=comprimento, YLength=largura)


def forma(xmin, ymin, comprimento, largura):
    return types.SimpleNamespace(isNull=lambda: False, BoundBox=caixa(xmin, ymin, comprimento, largura))


class TestServico(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        falsos["FreeCAD"].Vector = lambda x, y, z: (x, y, z)
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.servico = importlib.import_module("freecad.Circuits.services.luminotecnico")

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def test_ambiente_e_o_primeiro_objeto_com_forma_que_nao_e_simbolo(self):
        simbolo = types.SimpleNamespace(Name="P", Proxy=types.SimpleNamespace(Type="Ponto"), Shape=forma(0, 0, 200, 200))
        pequeno = types.SimpleNamespace(Name="L", Shape=forma(0, 0, 5000, 0))
        retangulo = types.SimpleNamespace(Name="Rectangle", Shape=forma(1000, 2000, 5000, 4000))
        achado = self.servico.ambiente_selecionado([simbolo, pequeno, retangulo])
        self.assertEqual(achado, (retangulo, 1000, 2000, 5.0, 4.0))
        self.assertIsNone(self.servico.ambiente_selecionado([simbolo, pequeno]))

    def test_distribui_e_substitui_as_luminarias_anteriores(self):
        retangulo = types.SimpleNamespace(Name="Rectangle")
        antiga = types.SimpleNamespace(Name="Ponto007", Ambiente="Rectangle")
        de_outro = types.SimpleNamespace(Name="Ponto008", Ambiente="Rectangle001")
        doc = mock.MagicMock()
        doc.Objects = [antiga, de_outro]
        doc.getObject.return_value = None
        novos = [types.SimpleNamespace(Placement=types.SimpleNamespace(Base=None)) for _ in range(4)]
        pavimento = types.SimpleNamespace(Label="1º Pavimento")
        with mock.patch.object(self.servico, "create_ponto", side_effect=novos) as criar, \
                mock.patch.object(self.servico.pavimentos, "garantir_ativo", return_value=pavimento), \
                mock.patch.object(self.servico.pavimentos, "elevacao", return_value=3000.0), \
                mock.patch.object(self.servico.pavimentos, "arquivar") as arquivar:
            criados = self.servico.distribuir(
                doc, retangulo, 1000, 2000, lum.posicoes(2, 2, 5, 4), "luz_teto", 20, 3,
            )
        self.assertEqual([chamada.args[1:] for chamada in arquivar.call_args_list], [(p, pavimento) for p in novos])
        doc.removeObject.assert_called_once_with("Ponto007")
        self.assertEqual(criar.call_count, 4)
        self.assertEqual([p.Placement.Base for p in criados],
                         [(2250.0, 3000.0, 3000.0), (4750.0, 3000.0, 3000.0),
                          (2250.0, 5000.0, 3000.0), (4750.0, 5000.0, 3000.0)])  # na cota do pavimento
        self.assertEqual({(p.Potencia, p.Circuito, p.Ambiente) for p in criados}, {(20.0, "3", "Rectangle")})
        doc.commitTransaction.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
