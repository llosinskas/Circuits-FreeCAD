"""Aterramento: resistência das hastes e marcação do condutor de cobre nu."""
import importlib
import math
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import formularios
from freecad.Circuits.core.functions.Predial import aterramento

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet")
RECARREGAR = ("freecad.Circuits.services.aterramento", "freecad.Circuits.services.pavimentos",
              "freecad.Circuits.services.estilo")


class TestCalculo(unittest.TestCase):
    def test_uma_haste_pela_formula_de_dwight(self):
        # 100 Ω·m, haste de 2,40 m e 5/8": 100/(2π·2,4)·(ln(4·2,4/0,00795) − 1) ≈ 40,4 Ω
        r = aterramento.resistencia_haste(100, 2.4, 15.9)
        self.assertAlmostEqual(r, 100 / (2 * math.pi * 2.4) * (math.log(4 * 2.4 / 0.00795) - 1), places=6)
        self.assertAlmostEqual(r, 40.4, places=1)

    def test_lambda_reproduz_a_tabela_de_hastes_em_linha(self):
        self.assertEqual(aterramento.fator_lambda(1), 0)
        self.assertAlmostEqual(aterramento.fator_lambda(2), 1.0)
        self.assertAlmostEqual(aterramento.fator_lambda(3), 1.667, places=3)
        self.assertAlmostEqual(aterramento.fator_lambda(4), 2.167, places=3)

    def test_mais_hastes_diminuem_a_resistencia(self):
        valores = [aterramento.resistencia_hastes(100, n, 3.0) for n in range(1, 11)]
        self.assertEqual(valores, sorted(valores, reverse=True))
        self.assertEqual(valores[0], aterramento.resistencia_haste(100))
        # duas hastes ficam acima da metade de uma: elas se influenciam
        self.assertGreater(valores[1], valores[0] / 2)

    def test_dimensionar_acha_o_menor_numero_de_hastes(self):
        r = aterramento.dimensionar(100, 10.0)
        self.assertTrue(r["atende"])
        self.assertLessEqual(r["resistencia"], 10.0)
        self.assertGreater(aterramento.resistencia_hastes(100, r["hastes"] - 1, 3.0), 10.0)
        self.assertEqual(r["cabo_entre_hastes"], (r["hastes"] - 1) * 3.0)
        self.assertIn("atende", aterramento.relatorio(r))

    def test_numero_de_hastes_informado(self):
        r = aterramento.dimensionar(100, 10.0, hastes=2)
        self.assertEqual(r["hastes"], 2)
        self.assertFalse(r["atende"])
        self.assertIn("Seriam necessárias", aterramento.relatorio(r))

    def test_solo_muito_resistivo(self):
        r = aterramento.dimensionar(3000, 1.0)
        self.assertIsNone(r["hastes_necessarias"])
        self.assertIn("malha", aterramento.relatorio(r))

    def test_entradas_invalidas(self):
        with self.assertRaises(ValueError):
            aterramento.resistencia_haste(0)
        with self.assertRaises(ValueError):
            aterramento.dimensionar(100, 0)

    def test_formulario(self):
        valores = formularios.valores_iniciais(formularios.ATERRAMENTO)
        self.assertEqual(valores["resistividade"], 50.0)  # a primeira opção de solo preenche a resistividade
        valores.pop("solo")
        self.assertGreater(aterramento.dimensionar(**valores)["hastes"], 0)


class TestCondutor(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.servico = importlib.import_module("freecad.Circuits.services.aterramento")

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def test_marca_as_linhas_e_ignora_o_resto(self):
        class Linha:
            def __init__(self):
                self.Points, self.ViewObject = [], types.SimpleNamespace(LineColor=(1, 1, 1))

            def addProperty(self, tipo, nome, grupo="", dica=""):
                setattr(self, nome, None)

        linha, texto = Linha(), types.SimpleNamespace(Name="Texto")
        doc = mock.MagicMock()
        nivel = object()  # o pavimento onde os símbolos entram (nível ativo do BIM, selecionado ou ativo)
        with mock.patch.object(self.servico.pavimentos, "pavimento_do_objeto", return_value=None), \
                mock.patch.object(self.servico.pavimentos, "pavimento_para_insercao", return_value=nivel), \
                mock.patch.object(self.servico.pavimentos, "arquivar") as arquivar:
            self.assertEqual(self.servico.marcar_condutores(doc, [linha, texto], "35"), 1)
        self.assertEqual(linha.SecaoAterramento, "35")
        self.assertEqual(linha.ViewObject.LineColor, self.servico.COR_ATERRAMENTO)
        arquivar.assert_called_once_with(doc, linha, nivel)
        self.assertTrue(self.servico.eh_condutor(linha))

    def test_calculo_gravado_e_levantamento_para_o_memorial(self):
        class Planilha:
            def __init__(self):
                self.celulas, self.Label = {}, ""

            def addProperty(self, tipo, nome, grupo="", dica=""):
                setattr(self, nome, "")

            def set(self, celula, valor):
                self.celulas[celula] = valor

            def getContents(self, celula):
                return self.celulas.get(celula, "")

            def get(self, celula):
                return float(self.celulas[celula])

            def setColumnWidth(self, *args):
                pass

        folha = Planilha()
        doc = mock.MagicMock()
        doc.Objects = []
        doc.addObject.return_value = folha
        with mock.patch.object(self.servico.pavimentos, "pavimento_para_insercao", return_value=None):
            self.assertIsNone(self.servico.ler_calculo(doc))
            self.servico.gravar_calculo(doc, {"resistividade": 300, "resistencia_alvo": 10, "hastes": 3,
                                              "espacamento": 3, "comprimento_haste": 2.4, "diametro_haste": 15.9})
        doc.Objects = [folha]
        self.assertEqual(self.servico.ler_calculo(doc),
                         {"resistividade": 300.0, "resistencia_alvo": 10.0, "hastes": 3, "espacamento": 3.0,
                          "comprimento_haste": 2.4, "diametro_haste": 15.9})

        def ponto(simbolo):
            return types.SimpleNamespace(Simbolo=simbolo, Proxy=types.SimpleNamespace(Type="Ponto"))

        cabo = types.SimpleNamespace(Points=[], SecaoAterramento="50", Shape=types.SimpleNamespace(Length=6000.0))
        doc.Objects = [ponto("haste_aterramento"), ponto("haste_aterramento"), ponto("bep"), cabo, cabo]
        self.assertEqual(self.servico.levantamento(doc),
                         {"hastes": 2, "caixas_inspecao": 0, "bep": 1, "condutores": {"50": 12.0}})


if __name__ == "__main__":
    unittest.main(verbosity=2)
