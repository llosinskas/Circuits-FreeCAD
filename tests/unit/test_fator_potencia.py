"""Correção do fator de potência (core/fator_potencia.py).

Q = P·(tg φ1 − tg φ2), FP de referência 0,92; banco em estágios comerciais; cabo e
proteção do banco pela corrente nominal × 1,35. Potências em kW e kvar, tensão em V.
"""
import math
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import fator_potencia


class Base(unittest.TestCase):
    def setUp(self):
        self.f = fator_potencia


class TestPotenciaReativa(Base):
    def test_de_0_80_para_0_92(self):
        self.assertAlmostEqual(self.f.potencia_reativa(500.0, 0.80), 500 * (0.75 - math.tan(math.acos(0.92))))
        self.assertAlmostEqual(self.f.potencia_reativa(500.0, 0.80), 162.0, delta=0.5)

    def test_ja_corrigido_nao_pede_capacitor(self):
        self.assertEqual(self.f.potencia_reativa(500.0, 0.95), 0.0)

    def test_fator_invalido(self):
        for fp in (0.0, 1.2):
            with self.assertRaises(ValueError):
                self.f.potencia_reativa(100.0, fp)


class TestBanco(Base):
    def test_estagios_cobrem_a_potencia_com_o_menor_passo(self):
        banco = self.f.banco(162.0)
        self.assertGreaterEqual(sum(banco["estagios"]), 162.0)
        self.assertTrue(all(e in self.f.ESTAGIOS_KVAR for e in banco["estagios"]))
        self.assertEqual(banco["menor_estagio"], min(banco["estagios"]))
        self.assertLessEqual(sum(banco["estagios"]) - 162.0, max(self.f.ESTAGIOS_KVAR))

    def test_corrente_de_projeto_do_banco(self):
        nominal = 50.0e3 / (math.sqrt(3) * 380.0)
        self.assertAlmostEqual(self.f.corrente_capacitor(50.0, 380.0), nominal)
        self.assertAlmostEqual(self.f.corrente_de_projeto(50.0, 380.0), 1.35 * nominal)

    def test_aviso_de_ressonancia_perto_da_5a_harmonica(self):
        # fr = 60·√(Scc/Q): Scc = 20 MVA e Q = 800 kvar dão 300 Hz, a 5ª harmônica
        self.assertAlmostEqual(self.f.frequencia_ressonancia(20000.0, 800.0), 300.0)
        self.assertTrue(self.f.risco_ressonancia(20000.0, 800.0))
        self.assertFalse(self.f.risco_ressonancia(20000.0, 100.0))  # 849 Hz, longe da 5ª e da 7ª


class TestDimensionar(Base):
    def test_resultado_e_relatorio(self):
        r = self.f.dimensionar(500.0, 0.80, tensao=380.0, potencia_curto_kva=20000.0)
        self.assertEqual(r["banco"]["estagios"], [50, 50, 50, 12.5])
        self.assertAlmostEqual(r["corrente_projeto"], 1.35 * r["corrente_nominal"])
        self.assertFalse(r["risco_ressonancia"])
        self.assertIn("162,5 kvar", self.f.relatorio(r))

    def test_ja_corrigido(self):
        r = self.f.dimensionar(100.0, 0.95)
        self.assertIsNone(r["banco"])
        self.assertIn("não precisa", self.f.relatorio(r))


if __name__ == "__main__":
    unittest.main()
