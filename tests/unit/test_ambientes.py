"""Ambientes e previsão automática de pontos pela NBR 5410 (core.ambientes)."""
import math
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import ambientes as a

SALA_4X3 = [(0, 0), (4000, 0), (4000, 3000), (0, 3000)]  # 12 m², 14 m


class TestPrevisaoNBR5410(unittest.TestCase):
    def test_tipo_pelo_nome_do_espaco(self):
        self.assertEqual([a.tipo_pelo_nome(n) for n in ("Cozinha 01", "WC social", "Suíte master", "Sala de estar",
                                                         "A.S.", "Depósito")],
                         ["Cozinha", "Banheiro", "Dormitório", "Sala", "Área de serviço", "Outro"])

    def test_iluminacao_100_va_mais_60_a_cada_4_m2_inteiros(self):
        self.assertEqual([a.iluminacao_va(x) for x in (5, 6, 9.9, 10, 14, 18)], [100, 100, 100, 160, 220, 280])

    def test_quantidade_de_tugs(self):
        self.assertEqual(a.quantidade_de_tugs("Sala", 12, 14), 3)  # 1 a cada 5 m ou fração
        self.assertEqual(a.quantidade_de_tugs("Cozinha", 9, 12), 4)  # 1 a cada 3,5 m ou fração
        self.assertEqual(a.quantidade_de_tugs("Banheiro", 4, 8), 1)
        self.assertEqual(a.quantidade_de_tugs("Varanda", 10, 13), 1)
        self.assertEqual(a.quantidade_de_tugs("Corredor", 5, 11), 1)  # até 6 m²
        self.assertEqual(a.quantidade_de_tugs("Corredor", 8, 12), 3)

    def test_potencia_das_areas_molhadas(self):
        self.assertEqual(a.potencias_das_tugs("Cozinha", 4), [600, 600, 600, 100])
        self.assertEqual(a.potencias_das_tugs("Cozinha", 7), [600, 600] + [100] * 5)  # mais de 6 pontos
        self.assertEqual(a.potencias_das_tugs("Sala", 3), [100, 100, 100])
        self.assertEqual(a.simbolo_da_tomada("Cozinha", 600), "tomada_media")
        self.assertEqual(a.simbolo_da_tomada("Cozinha", 100), "tomada_baixa")

    def test_area_e_perimetro_em_qualquer_sentido(self):
        self.assertAlmostEqual(a.area_m2(SALA_4X3[::-1]), 12.0)
        self.assertAlmostEqual(a.perimetro_m(SALA_4X3 + [SALA_4X3[0]]), 14.0)  # fechado com o ponto repetido


class TestPosicoes(unittest.TestCase):
    def test_interruptor_ao_lado_da_porta_virado_para_dentro(self):
        r = a.posicoes(SALA_4X3, "Sala", portas=[(2000, -70, 800)])  # porta no meio da parede de baixo
        i = r["interruptor"]
        self.assertAlmostEqual(i["x"], 2000 + 400 + a.DISTANCIA_INTERRUPTOR_MM)
        self.assertAlmostEqual(i["y"], 0.0)
        self.assertAlmostEqual(i["angulo"], 90.0)  # +y: para dentro da sala
        self.assertEqual((r["portas"], r["avisos"]), (1, []))

    def test_tomadas_pelo_perimetro_fora_da_porta_do_interruptor_e_dos_cantos(self):
        r = a.posicoes(SALA_4X3, "Sala", portas=[(2000, 0, 800)])
        self.assertEqual(len(r["tomadas"]), 3)
        for t in r["tomadas"]:
            if abs(t["y"]) < 1e-6:  # na parede da porta
                self.assertFalse(1400 <= t["x"] <= 2600)
            self.assertGreater(math.dist((t["x"], t["y"]), (r["interruptor"]["x"], r["interruptor"]["y"])), 299)
            cantos = min(math.dist((t["x"], t["y"]), c) for c in SALA_4X3)
            self.assertGreaterEqual(cantos, a.FOLGA_CANTO_MM - 1e-6)
            self.assertTrue(any(abs(t[k] - v) < 1e-6 for k, v in (("x", 0), ("x", 4000), ("y", 0), ("y", 3000))))
            normal = (math.cos(math.radians(t["angulo"])), math.sin(math.radians(t["angulo"])))
            self.assertTrue(a.dentro((t["x"] + normal[0] * 100, t["y"] + normal[1] * 100), SALA_4X3))

    def test_luz_no_centro_com_a_potencia_da_norma(self):
        r = a.posicoes(SALA_4X3, "Sala")
        self.assertEqual((round(r["luz"]["x"]), round(r["luz"]["y"]), r["luz"]["potencia"]), (2000, 1500, 160))
        self.assertTrue(r["avisos"])  # sem porta

    def test_luz_dentro_de_um_ambiente_em_u(self):
        u = [(0, 0), (6000, 0), (6000, 4000), (5000, 4000), (5000, 1000), (1000, 1000), (1000, 4000), (0, 4000)]
        r = a.posicoes(u, "Corredor")
        self.assertTrue(a.dentro((r["luz"]["x"], r["luz"]["y"]), u))

    def test_cozinha_com_tomadas_medias_de_600_va(self):
        cozinha = [(0, 0), (3000, 0), (3000, 3000), (0, 3000)]
        r = a.posicoes(cozinha, "Cozinha", portas=[(1500, 3000, 800)])
        self.assertEqual([(t["simbolo"], t["potencia"]) for t in r["tomadas"]],
                         [("tomada_media", 600)] * 3 + [("tomada_baixa", 100)])

    def test_porta_longe_nao_e_do_ambiente(self):
        self.assertEqual(a.posicoes(SALA_4X3, "Sala", portas=[(9000, 9000, 800)])["portas"], 0)


if __name__ == "__main__":
    unittest.main()
