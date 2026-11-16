"""Cálculos prediais: motores, demanda, pressurização de escada e bomba de recalque."""
import math
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import circuitos
from freecad.Circuits.core.functions.Predial import demanda, motores, pressurizacao, recalque
from freecad.Circuits.core.simbolos import ILUM, TUE, TUG


class TestMotores(unittest.TestCase):
    def test_motor_comercial_e_o_primeiro_que_atende(self):
        self.assertEqual(motores.motor_comercial(0.7), 1)  # 1 cv = 0,7355 kW
        self.assertEqual(motores.motor_comercial(0.7355), 1)
        self.assertEqual(motores.motor_comercial(0.74), 1.5)
        self.assertEqual(motores.motor_comercial(5.84), 10)  # 7,5 cv = 5,52 kW não atende

    def test_potencia_acima_da_lista(self):
        with self.assertRaises(ValueError):
            motores.motor_comercial(500)

    def test_corrente_trifasica_e_monofasica(self):
        # 1 cv: 0,7355 / 0,85 = 0,865 kW; / 0,85 = 1,018 kVA
        self.assertAlmostEqual(motores.corrente_nominal(1, 380), 1018 / (math.sqrt(3) * 380), places=2)
        self.assertAlmostEqual(motores.corrente_nominal(1, 220, fases=1), 1018 / 220, places=2)

    def test_dados_motor(self):
        dados = motores.dados_motor(1.0, 220)
        self.assertEqual(dados["motor_cv"], 1.5)
        self.assertAlmostEqual(dados["potencia_aparente_kva"], 1.5 * 0.7355 / 0.85 / 0.85, places=4)
        self.assertEqual((dados["tensao"], dados["fases"]), (220, 3))


class TestDemanda(unittest.TestCase):
    def test_faixas_de_iluminacao_e_tug(self):
        self.assertEqual(demanda.fator_ilum_tug(1000), 0.86)
        self.assertEqual(demanda.fator_ilum_tug(1001), 0.75)
        self.assertEqual(demanda.fator_ilum_tug(6000), 0.45)
        self.assertEqual(demanda.fator_ilum_tug(10000), 0.27)
        self.assertEqual(demanda.fator_ilum_tug(25000), 0.24)

    def test_fator_tue_pelo_numero_de_circuitos(self):
        self.assertEqual([demanda.fator_tue(n) for n in (0, 1, 2, 3, 4, 10, 25, 40)],
                         [1.0, 1.0, 1.0, 0.84, 0.76, 0.52, 0.38, 0.38])

    def test_fatores_nunca_aumentam_com_a_carga(self):
        ilum = [fator for _, fator in demanda.FATORES_ILUM_TUG] + [demanda.FATOR_ILUM_TUG_ACIMA]
        tue = [demanda.FATORES_TUE[n] for n in sorted(demanda.FATORES_TUE)]
        self.assertEqual(ilum, sorted(ilum, reverse=True))
        self.assertEqual(tue, sorted(tue, reverse=True))

    def test_demanda_residencial(self):
        r = demanda.demanda_residencial(6000, [5500, 1500, 1000])
        self.assertAlmostEqual(r["demanda_ilum_tug_w"], 2700)
        self.assertAlmostEqual(r["demanda_tue_w"], 6720)
        self.assertAlmostEqual(r["demanda_w"], 9420)
        self.assertAlmostEqual(r["fator_global"], 9420 / 14000)
        self.assertIn("9.42 kW", demanda.relatorio(r))

    def test_quadro_vazio(self):
        r = demanda.demanda_residencial(0, [])
        self.assertEqual((r["demanda_w"], r["fator_global"]), (0, 0.0))

    def test_demanda_de_circuitos_separa_por_tipo(self):
        def ponto(numero, potencia, tipo):
            return {"circuito": numero, "potencia_va": potencia, "fator_potencia": 1.0, "tensao": 220,
                    "ligacao": "F+N", "tipo_circuito": tipo, "descricao": ""}
        grupo = circuitos.agrupar([ponto("1", 800, ILUM), ponto("2", 1200, TUG), ponto("3", 5500, TUE)])
        r = demanda.demanda_de_circuitos(grupo)
        self.assertEqual((r["instalada_ilum_tug_w"], r["circuitos_tue"], r["instalada_tue_w"]), (2000, 1, 5500))
        self.assertAlmostEqual(r["demanda_w"], 2000 * 0.75 + 5500)


class TestPressurizacao(unittest.TestCase):
    def test_vazao_por_frestas(self):
        # 12 portas x 0,01 m² a 50 Pa: 0,827 x 0,12 x raiz(50)
        self.assertAlmostEqual(pressurizacao.vazao_frestas(0.12), 0.827 * 0.12 * math.sqrt(50), places=6)
        self.assertEqual(pressurizacao.vazao_frestas(0), 0)

    def test_vazao_portas_abertas(self):
        self.assertAlmostEqual(pressurizacao.vazao_portas_abertas(2, 0.9, 2.1), 3.78)

    def test_dimensionamento_de_uma_escada_de_12_portas(self):
        r = pressurizacao.dimensionar(12)
        self.assertAlmostEqual(r["vazao_portas_fechadas"], 0.7017, places=3)
        self.assertAlmostEqual(r["vazao_portas_abertas"], 3.78 + 0.827 * 0.10 * math.sqrt(50), places=4)
        self.assertEqual(r["condicao"], "portas abertas")
        self.assertAlmostEqual(r["vazao_ventilador"], r["vazao_portas_abertas"] * 1.25 * 1.15, places=6)
        self.assertAlmostEqual(r["potencia_eixo_kw"], r["vazao_ventilador"] * 500 / (0.65 * 0.95) / 1000, places=6)
        self.assertEqual(r["motor"]["motor_cv"], 10)
        self.assertIn("10 cv", pressurizacao.relatorio(r))

    def test_sem_porta_aberta_valem_as_frestas(self):
        r = pressurizacao.dimensionar(20, portas_abertas=0, tipo_porta="Dupla", duto="Alvenaria")
        self.assertEqual(r["condicao"], "portas fechadas")
        self.assertAlmostEqual(r["vazao_ventilador"], 0.827 * 0.6 * math.sqrt(50) * 1.25 * 1.25, places=6)

    def test_entradas_invalidas(self):
        with self.assertRaises(ValueError):
            pressurizacao.dimensionar(0)
        with self.assertRaises(ValueError):
            pressurizacao.dimensionar(3, portas_abertas=4)


class TestRecalque(unittest.TestCase):
    def test_vazao(self):
        self.assertEqual(recalque.consumo_diario(80), 16000)
        self.assertAlmostEqual(recalque.vazao_recalque(16000, 5), 16.0 / 18000, places=9)
        with self.assertRaises(ValueError):
            recalque.vazao_recalque(16000, 0)

    def test_diametro(self):
        vazao = 16.0 / 18000
        self.assertAlmostEqual(recalque.diametro_forchheimer(vazao, 5), 1300 * (5 / 24) ** 0.25 * math.sqrt(vazao))
        self.assertEqual(recalque.diametro_comercial(26.2), (32, 27.8))
        self.assertEqual(recalque.diametro_comercial(27.8), (32, 27.8))
        with self.assertRaises(ValueError):
            recalque.diametro_comercial(500)

    def test_perda_de_carga_cresce_com_a_vazao_e_cai_com_o_diametro(self):
        base = recalque.perda_carga_unitaria(0.001, 27.8)
        self.assertGreater(recalque.perda_carga_unitaria(0.002, 27.8), base)
        self.assertLess(recalque.perda_carga_unitaria(0.001, 44.0), base)
        # Hazen-Williams, C = 140, D = 27,8 mm, Q = 1 L/s
        self.assertAlmostEqual(base, 10.643 * 0.001 ** 1.852 / (140 ** 1.852 * 0.0278 ** 4.87), places=9)

    def test_folga_do_motor(self):
        self.assertEqual([recalque.folga_motor(cv) for cv in (1, 2, 3, 8, 15, 30)], [0.5, 0.5, 0.3, 0.2, 0.15, 0.1])

    def test_edificio_de_80_pessoas(self):
        r = recalque.dimensionar(80, 40, 60)
        self.assertAlmostEqual(r["vazao_m3h"], 3.2, places=6)
        self.assertEqual(r["diametro_nominal_mm"], 32)
        self.assertTrue(0.5 < r["velocidade"] < 3.0)
        self.assertAlmostEqual(r["altura_manometrica"], 40 + r["perda_carga"])
        self.assertAlmostEqual(r["potencia_eixo_kw"], 9810 * r["vazao"] * r["altura_manometrica"] / 0.5 / 1000)
        self.assertEqual(r["motor"]["motor_cv"], 2)  # 1,13 cv no eixo + 50 % de folga
        self.assertIn("DN 32", recalque.relatorio(r))

    def test_motor_monofasico(self):
        r = recalque.dimensionar(20, 15, 30, tensao=220, fases=1)
        self.assertEqual(r["motor"]["fases"], 1)
        self.assertIn("monofásico 220 V", recalque.relatorio(r))

    def test_entradas_invalidas(self):
        with self.assertRaises(ValueError):
            recalque.dimensionar(0, 40, 60)
        with self.assertRaises(ValueError):
            recalque.dimensionar(80, 40, 60, rendimento=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
