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
        r = a.posicoes(SALA_4X3, "Sala", opcoes={"luminotecnico": None})
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



COZINHA_3X3 = [(0, 0), (3000, 0), (3000, 3000), (0, 3000)]
LUMINARIA_12W = {"fluxo": 1000.0, "potencia": 12.0, "pe_direito": 2.7}


class TestOpcoesDoAmbiente(unittest.TestCase):
    def test_paredes_com_o_lado_na_planta(self):
        rotulos = [p["rotulo"] for p in a.paredes(SALA_4X3)]
        self.assertEqual(rotulos, ["Parede 1 – de baixo, 4,00 m", "Parede 2 – da direita, 3,00 m",
                                   "Parede 3 – de cima, 4,00 m", "Parede 4 – da esquerda, 3,00 m"])
        self.assertEqual([p["rotulo"] for p in a.paredes(SALA_4X3[::-1])], rotulos)  # sentido não importa

    def test_porta_informada_numa_parede(self):
        r = a.posicoes(SALA_4X3, "Sala", opcoes={"porta": 2, "posicao_porta": 0.25})  # de cima, a 1 m da direita
        self.assertEqual((r["portas"], r["avisos"]), (1, []))
        self.assertAlmostEqual(r["interruptor"]["y"], 3000.0)
        self.assertAlmostEqual(r["interruptor"]["angulo"], -90.0)
        self.assertIn(round(r["interruptor"]["x"]), (3000 - 550, 3000 + 550))

    def test_sem_porta_nao_avisa_nem_usa_as_do_projeto(self):
        r = a.posicoes(SALA_4X3, "Sala", portas=[(2000, 0, 800)], opcoes={"porta": a.SEM_PORTA})
        self.assertEqual((r["portas"], r["avisos"]), (0, []))

    def test_tomadas_de_600_va_acima_da_bancada_da_pia(self):
        r = a.posicoes(COZINHA_3X3, "Cozinha", opcoes={"porta": 2, "bancada": 1})  # pia na parede da direita
        bancada = [t for t in r["tomadas"] if abs(t["x"] - 3000) < 1e-6]
        self.assertEqual([(t["simbolo"], t["potencia"]) for t in bancada], [("tomada_media", 600)] * 3)
        self.assertTrue(all(a.FOLGA_CANTO_MM - 1e-6 <= t["y"] <= 3000 - a.FOLGA_CANTO_MM + 1e-6 for t in bancada))
        self.assertTrue(all(abs(t["angulo"] - 180.0) < 1e-6 for t in bancada))
        outras = [t for t in r["tomadas"] if t not in bancada]
        self.assertEqual([t["potencia"] for t in outras], [100])

    def test_cozinha_pequena_tem_duas_tomadas_na_bancada(self):
        copa = [(0, 0), (1500, 0), (1500, 1000), (0, 1000)]  # 5 m de perímetro: 2 TUG pela regra, 2 na bancada
        r = a.posicoes(copa, "Copa", opcoes={"porta": a.SEM_PORTA, "bancada": 0})
        self.assertGreaterEqual(sum(1 for t in r["tomadas"] if abs(t["y"]) < 1e-6), 2)
        estreita = [(0, 0), (1000, 0), (1000, 700), (0, 700)]  # 3,4 m: a regra dá 1, a bancada pede 2
        r = a.posicoes(estreita, "Cozinha", opcoes={"porta": a.SEM_PORTA, "bancada": 0})
        self.assertEqual((r["previsao"]["tugs"], len(r["tomadas"])), (2, 2))

    def test_lavatorio_e_chuveiro_no_banheiro(self):
        banheiro = [(0, 0), (2000, 0), (2000, 1500), (0, 1500)]
        r = a.posicoes(banheiro, "Banheiro", opcoes={"porta": 0, "posicao_porta": 0.3, "bancada": 2, "chuveiro": 6800})
        self.assertEqual([(t["simbolo"], t["potencia"], round(t["y"])) for t in r["tomadas"]],
                         [("tomada_media", 600, 1500)])
        chuveiro, = r["equipamentos"]
        self.assertEqual((chuveiro["simbolo"], chuveiro["potencia"]), ("chuveiro", 6800))
        self.assertGreater(chuveiro["x"], 1000)  # no canto longe da porta
        self.assertTrue(a.dentro((chuveiro["x"], chuveiro["y"]), banheiro))

    def test_ar_condicionado_na_parede_mais_comprida_sem_porta(self):
        r = a.posicoes(SALA_4X3, "Dormitório", opcoes={"porta": 0, "ar_condicionado": 1300})
        ar, = r["equipamentos"]
        self.assertEqual((ar["simbolo"], ar["potencia"], round(ar["x"]), round(ar["y"])),
                         ("ar_condicionado", 1300, 2000, 3000))
        self.assertEqual(a.posicoes(SALA_4X3, "Cozinha", opcoes={"ar_condicionado": 1300})["equipamentos"], [])

    def test_perguntas_conforme_o_tipo(self):
        self.assertEqual([a.pergunta_bancada(t) for t in ("Cozinha", "Lavanderia", "Banheiro", "Sala")],
                         ["pia", "pia", "lavatório", None])
        self.assertTrue(a.tem_chuveiro("Banheiro") and not a.tem_chuveiro("Cozinha"))
        self.assertTrue(a.tem_ar_condicionado("Dormitório") and not a.tem_ar_condicionado("Banheiro"))


class TestLuminotecnicoNoAmbiente(unittest.TestCase):
    def test_sala_4x3_pelo_metodo_dos_lumens(self):
        r = a.posicoes(SALA_4X3, "Sala", opcoes={"porta": 0, "luminotecnico": LUMINARIA_12W})
        calc = r["luminotecnico"]
        # K = 2 x 12 / (1,95 x 14) = 0,88 -> U = 0,41; N = 150 x 12 / (1000 x 0,41 x 0,8) = 5,5 -> 6
        self.assertAlmostEqual(calc["indice_local"], 24 / (1.95 * 14))
        self.assertEqual(calc["quantidade"], len(r["luzes"]))
        self.assertGreaterEqual(calc["quantidade"], math.ceil(calc["quantidade_calculada"]))
        self.assertGreaterEqual(calc["iluminancia_resultante"], 150)
        # 160 VA da NBR divididos pelos pontos dão menos que 12 W? Não: 160 / 6 = 27 VA por ponto.
        self.assertEqual(r["luzes"][0]["potencia"], math.ceil(160 / calc["quantidade"]))
        self.assertGreaterEqual(sum(l["potencia"] for l in r["luzes"]), 160)
        self.assertTrue(all(a.dentro((l["x"], l["y"]), SALA_4X3) for l in r["luzes"]))

    def test_potencia_da_luminaria_quando_passa_da_norma(self):
        r = a.posicoes(SALA_4X3, "Sala", opcoes={"luminotecnico": {"fluxo": 3600.0, "potencia": 40.0}})
        self.assertTrue(all(l["potencia"] == 40.0 for l in r["luzes"]))

    def test_iluminancia_e_plano_pelo_tipo(self):
        corredor = [(0, 0), (8000, 0), (8000, 1200), (0, 1200)]
        r = a.luminarias(corredor, "Corredor", 800, 9)
        self.assertEqual((r["iluminancia"], r["altura_util"]), (100.0, 2.7))  # no piso
        self.assertEqual(r["ny"], 1)
        self.assertLessEqual(r["espacamento_x"], r["espacamento_maximo"])
        self.assertEqual(a.luminarias(SALA_4X3, "Escritório", 3600, 40)["iluminancia"], 500.0)

    def test_ambiente_em_l_so_com_luminarias_dentro(self):
        l = [(0, 0), (6000, 0), (6000, 3000), (3000, 3000), (3000, 6000), (0, 6000)]
        r = a.luminarias(l, "Sala", 1000, 12)
        self.assertTrue(all(a.dentro(p, l) for p in r["posicoes"]))
        self.assertGreaterEqual(r["quantidade"], math.ceil(r["quantidade_calculada"]))
        self.assertGreaterEqual(r["iluminancia_resultante"], 150)

    def test_luminotecnico_e_o_padrao(self):
        r = a.posicoes(SALA_4X3, "Sala")
        self.assertIsNotNone(r["luminotecnico"])
        self.assertEqual(r["luminotecnico"]["fluxo_luminaria"], a.LUMINOTECNICO_PADRAO["fluxo"])
        self.assertEqual(len(r["luzes"]), r["luminotecnico"]["quantidade"])
        self.assertGreaterEqual(r["luminotecnico"]["iluminancia_resultante"], 150)
        # a lâmpada escolhida sem o pé-direito usa o pé-direito padrão
        r = a.posicoes(SALA_4X3, "Sala", opcoes={"luminotecnico": {"fluxo": 3600.0, "potencia": 40.0}})
        self.assertAlmostEqual(r["luminotecnico"]["altura_util"], 1.95)

    def test_sem_luminotecnico_so_se_pedir(self):
        r = a.posicoes(SALA_4X3, "Sala", opcoes={"luminotecnico": None})
        self.assertEqual((len(r["luzes"]), r["luminotecnico"]), (1, None))


if __name__ == "__main__":
    unittest.main()
