"""Etapa 6: quadro de comando e proteção de motores (core/comando.py).

Estrela-triângulo: contatores de rede e de triângulo com 0,58·In, de estrela com
0,33·In, relé térmico ajustado em 0,58·In (ligado nas fases do enrolamento).
Contatores em AC-3 e faixas de disjuntor-motor são listas genéricas de catálogo.
"""
import unittest

from tests.plano._apoio import carregar


class Base(unittest.TestCase):
    def setUp(self):
        self.c = carregar(self, "comando", 6)


class TestPartidaDireta(Base):
    def test_um_contator_e_rele_na_corrente_nominal(self):
        r = self.c.dimensionar_partida(10.0, "direta")
        self.assertEqual(list(r["contatores"]), ["K1"])
        self.assertGreaterEqual(r["contatores"]["K1"], 10.0)
        self.assertIn(r["contatores"]["K1"], self.c.CONTATORES_AC3)
        minimo, maximo = r["rele"]
        self.assertLessEqual(minimo, 10.0)
        self.assertGreaterEqual(maximo, 10.0)
        self.assertEqual(r["ajuste_rele"], 10.0)


class TestEstrelaTriangulo(Base):
    def test_tres_contatores_com_as_correntes_reduzidas(self):
        r = self.c.dimensionar_partida(20.0, "estrela_triangulo")
        self.assertEqual(r["contatores"], {"K1_rede": 12, "K2_triangulo": 12, "K3_estrela": 9})
        self.assertAlmostEqual(r["ajuste_rele"], 11.6)
        minimo, maximo = r["rele"]
        self.assertTrue(minimo <= 11.6 <= maximo)


class TestEletronica(Base):
    def test_soft_starter_e_inversor_pela_corrente(self):
        for partida in ("soft_starter", "inversor"):
            r = self.c.dimensionar_partida(30.0, partida)
            self.assertGreaterEqual(r["dispositivo"], 30.0)
            self.assertNotIn("K3_estrela", r.get("contatores", {}))

    def test_partida_desconhecida(self):
        with self.assertRaises(ValueError):
            self.c.dimensionar_partida(10.0, "compensadora")


class TestDisjuntorMotor(Base):
    def test_faixa_contem_a_corrente(self):
        for corrente in (0.5, 3.2, 8.1, 14.0, 24.0):
            minimo, maximo = self.c.faixa_disjuntor_motor(corrente)
            self.assertTrue(minimo <= corrente <= maximo, corrente)

    def test_corrente_acima_do_catalogo(self):
        with self.assertRaises(ValueError):
            self.c.faixa_disjuntor_motor(5000.0)

    def test_disjuntor_motor_entra_no_resultado(self):
        r = self.c.dimensionar_partida(8.1, "direta")
        self.assertEqual(r["disjuntor_motor"], self.c.faixa_disjuntor_motor(8.1))


class TestMotorPelaPotencia(Base):
    def test_usa_a_corrente_nominal_dos_motores_prediais(self):
        # 5 cv em 380 V com os valores típicos de core.functions.Predial.motores
        from freecad.Circuits.core.functions.Predial import motores
        esperado = motores.corrente_nominal(5, 380)
        r = self.c.dimensionar_motor(5, 380, "direta")
        self.assertAlmostEqual(r["corrente_nominal"], esperado)
        self.assertGreaterEqual(r["contatores"]["K1"], esperado)


if __name__ == "__main__":
    unittest.main()
