"""Centro de medição Enel SP: medição agrupada × busway (core.centro_medicao)."""
import math
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import centro_medicao as c


def predio(andares=12, unidades=4, demanda=63.0, passo=3.0):
    return [c.andar("Térreo", 0.0, 0)] + [c.andar(f"{i}º", passo * i, unidades, demanda) for i in range(1, andares + 1)]


class TestQuedaPelaEnel(unittest.TestCase):
    def test_exemplo_2_da_norma_rede_subterranea(self):
        # 7.22.15, exemplo 2: k = 0,01615; 26 m × 400 A + 3 × 300 + 3 × 200 + 3 × 100, 208 V -> 1,97 V, 0,95 %
        volts = sum(c.queda(0.01615, l, i, 208)[0] for l, i in ((26, 400), (3, 300), (3, 200), (3, 100)))
        self.assertAlmostEqual(volts, 1.9703, places=3)
        self.assertAlmostEqual(100 * volts / 208, 0.947, places=2)

    def test_busway_do_exemplo_2_sai_com_500_a_e_queda_ate_1_por_cento(self):
        # Primeira derivação a 26 m do QDC (20 m horizontais + 5,15 m + 0,85 m do plug-in), andares a cada 3 m.
        andares = [c.andar(f"{i}º", 5.15 + 3 * i, 1, 100.0, 3) for i in range(4)]
        r = c.busway(andares, tensao=208.0, uso=1.0, distancia_horizontal=20.0)
        linha, = r["linhas"]
        self.assertEqual([round(l, 2) for l, _, _ in linha["trechos"]], [26.0, 3.0, 3.0, 3.0])
        self.assertEqual([i for _, i, _ in linha["trechos"]], [400, 300, 200, 100])
        self.assertEqual(linha["nominal"], 500)  # o de 400 A daria 1,5 %
        self.assertAlmostEqual(linha["queda"], 0.947, places=2)

    def test_k_dos_cabos_pela_tabela_42(self):
        # √3/10 × (R cos φ + X sen φ): 185 mm² de cobre, R = 22,5/185 mΩ/m, X = 0,08 mΩ/m, cos φ 0,92
        r, x = 22.5 / 185, 0.08
        esperado = math.sqrt(3) / 10 * (r * 0.92 + x * math.sqrt(1 - 0.92 ** 2))
        self.assertAlmostEqual(c.k_cabo(185), esperado)
        self.assertAlmostEqual(c.k_cabo(185, paralelos=3), esperado / 3)
        self.assertGreater(c.k_cabo(185), 0.02)  # e não 0,0025 como no exemplo 1 da norma


class TestConvencional(unittest.TestCase):
    def test_cdpm_pela_tabela_28(self):
        self.assertEqual(c.tipo_cdpm(12, 200), "Coluna simples")
        self.assertEqual(c.tipo_cdpm(20, 240), "Coluna dupla")
        self.assertEqual(c.tipo_cdpm(20, 280), "Coluna MAX")
        self.assertIsNone(c.tipo_cdpm(31, 100))
        self.assertIsNone(c.tipo_cdpm(10, 320))

    def test_agrupamentos_ate_30_caixas_e_300_a(self):
        grupos = c.agrupamentos(48, 12.5)
        self.assertEqual([g["caixas"] for g in grupos], [24, 24])
        self.assertTrue(all(g["caixas"] <= 30 and g["corrente"] <= 300 for g in grupos))
        grupos = c.agrupamentos(20, 40.0)  # 800 A: a corrente manda
        self.assertEqual(len(grupos), 3)
        self.assertTrue(all(g["corrente"] <= 300 for g in grupos))

    def test_disposicao_3_na_vertical_e_6_colunas_por_lado(self):
        self.assertEqual(c.distribuicao(30), (15, 15, 3))
        self.assertEqual(c.distribuicao(4), (2, 2, 2))
        self.assertEqual(c.distribuicao(1), (1, 0, 1))
        with self.assertRaises(ValueError):
            c.distribuicao(31)

    def test_centro_de_medicao_e_alimentadores(self):
        r = c.convencional(predio(), tensao=220.0, distancia_horizontal=15.0, demanda_total_a=600.0)
        self.assertEqual(r["caixas"], 48)
        self.assertEqual(len(r["agrupamentos"]), 2)
        self.assertTrue(any("abrigado" in a for a in r["avisos"]))
        self.assertGreater(r["abrigo"]["area"], 5)
        primeiro, ultimo = r["alimentadores"][0], r["alimentadores"][-1]
        self.assertAlmostEqual(primeiro["comprimento"], 15 + 3 + c.COMPRIMENTO_NO_ANDAR_M)
        self.assertGreaterEqual(primeiro["secao"], c.SECAO_MIN_UNIDADE)
        self.assertGreaterEqual(ultimo["secao"], primeiro["secao"])  # mais longe, mais queda
        self.assertTrue(all(a["queda"] <= c.QUEDA_ALIMENTADOR_UNIDADE for a in r["alimentadores"]))

    def test_unidade_acima_de_100_a_avisa(self):
        r = c.convencional([c.andar("1º", 3, 2, 120.0)], demanda_total_a=200)
        self.assertTrue(any("caixa P" in a for a in r["avisos"]))


class TestBusway(unittest.TestCase):
    def test_caixas_mec_pela_tabela_30(self):
        self.assertEqual([x["tipo"] for x in c.caixas_mec(4, 200)], ["MEC IV"])
        self.assertEqual([x["tipo"] for x in c.caixas_mec(2, 150)], ["MEC II"])
        self.assertEqual([x["tipo"] for x in c.caixas_mec(8, 350)], ["MEC IX"])
        caixas = c.caixas_mec(16, 600)  # passa de 12 medições e de 400 A: duas caixas
        self.assertEqual(len(caixas), 2)
        self.assertTrue(all(x["corrente"] <= 400 and 63 <= x["disjuntor"] <= 400 for x in caixas))
        self.assertEqual(c.caixas_mec(0, 0), [])

    def test_prumada_de_12_andares(self):
        r = c.busway(predio(), tensao=220.0, uso=2.0, distancia_horizontal=15.0, demanda_total_a=600.0)
        linha, = r["linhas"]
        self.assertGreaterEqual(linha["nominal"], 600)
        self.assertLessEqual(linha["queda"], 2.0)
        self.assertEqual(len(r["andares"]), 12)
        m = r["materiais"]
        self.assertEqual(m["corta_fogo"], 12)
        self.assertEqual(m["plugins"], 12)
        self.assertGreaterEqual(m["suportes"], math.ceil(linha["comprimento"] / 1.5))
        self.assertGreater(r["shaft"]["largura"], 700)

    def test_queda_alta_pede_outra_linha(self):
        r = c.busway(predio(andares=30, unidades=6, demanda=40), tensao=220.0, uso=1.0, distancia_horizontal=40.0,
                     demanda_total_a=2000.0)
        self.assertGreater(len(r["linhas"]), 1)
        self.assertTrue(all(l["queda"] <= 1.0 + 1e-9 for l in r["linhas"]))
        atendidos = [a for l in r["linhas"] for a in l["andares"]]
        self.assertEqual(len(atendidos), 30)  # cada andar numa linha só

    def test_entrada_pela_tabela_32(self):
        self.assertEqual(c.entrada(250)[:2], ("QDC 5", 1))
        self.assertEqual(c.entrada(600)[:2], ("QDC 10", 2))
        self.assertEqual(c.entrada(3000)[0], c.CABINE)


class TestComparacao(unittest.TestCase):
    def test_orcamento_e_recomendacao(self):
        r = c.comparar(predio(), tensao=220.0, uso=2.0, distancia_horizontal=15.0, demanda_total_a=600.0)
        self.assertIn(r["recomendada"], ("convencional", "busway"))
        custos = r["custos"]
        self.assertEqual(set(custos), {"convencional", "busway"})
        for orcamento in custos.values():
            self.assertAlmostEqual(orcamento["total"], orcamento["material"] * 1.30)
        mais_caro = max(custos.values(), key=lambda o: o["total"])["total"]
        self.assertAlmostEqual(r["economia"], mais_caro - custos[r["recomendada"]]["total"])
        texto = c.relatorio(r)
        self.assertIn("Busway", texto)
        self.assertIn("Coluna", texto)

    def test_precos_da_planilha_mudam_a_escolha(self):
        base = c.comparar(predio(), demanda_total_a=600.0)
        caro = {f"busway_m_{n}": 1e6 for n in c.CORRENTES_BUSWAY}
        r = c.comparar(predio(), demanda_total_a=600.0, precos=caro)
        self.assertEqual(r["recomendada"], "convencional")
        self.assertGreater(r["custos"]["busway"]["total"], base["custos"]["busway"]["total"])

    def test_sem_demanda_do_edificio_avisa(self):
        r = c.comparar(predio(andares=3))
        self.assertIn("diversidade", r["convencional"]["avisos"][0])


class TestPlanilhaEGeometria(unittest.TestCase):
    def test_linhas_dos_pavimentos(self):
        linhas = c.linhas_dos_pavimentos([("1º", 3.0), ("Térreo", 0.0), ("2º", 6.0)])
        self.assertEqual([(l["nome"], l["cota"], l["unidades"]) for l in linhas],
                         [("Térreo", 0.0, 0), ("1º", 3.0, 4), ("2º", 6.0, 4)])
        self.assertEqual(len(c.linhas_dos_pavimentos([])), 4)

    def test_andar_da_linha_com_virgula(self):
        a = c.andar_da_linha({"nome": "3º", "cota": "9,5", "unidades": "6", "demanda_a": "50", "fases": ""})
        self.assertEqual((a["cota"], a["unidades"], a["demanda_a"], a["fases"]), (9.5, 6, 50.0, 2))
        with self.assertRaises(ValueError):
            c.andar_da_linha({"nome": "x", "unidades": "dois"})

    def test_coluna_de_30_caixas(self):
        g = c.coluna_de_medicao(30, "Coluna MAX")
        caixas = [p for p in g["caixas"] if p[0] != "CDPM"]
        self.assertEqual(len(caixas), 30)
        self.assertTrue(300 <= g["base"] <= 400)  # 3 na vertical: 0,30 a 0,40 m (Tabela 29)
        self.assertAlmostEqual(g["altura"], 3 * 520)
        self.assertLessEqual(g["base"] + g["altura"], 1900 + 1e-9)  # topo da coluna MAX até 1,90 m
        self.assertAlmostEqual(g["largura"], 10 * 260 + 470)
        # nenhuma caixa se sobrepõe a outra
        for i, (_, (x1, _, z1), (dx1, _, dz1)) in enumerate(g["caixas"]):
            for _, (x2, _, z2), (dx2, _, dz2) in g["caixas"][i + 1:]:
                self.assertFalse(x1 < x2 + dx2 - 1e-6 and x2 < x1 + dx1 - 1e-6
                                 and z1 < z2 + dz2 - 1e-6 and z2 < z1 + dz1 - 1e-6)

    def test_emendas_a_cada_3_m_e_suportes_fora_delas(self):
        emendas, suportes = c.emendas_e_suportes(10000)
        self.assertEqual(emendas, [3000, 6000, 9000])
        self.assertTrue(all(abs(s - e) > 150 for s in suportes for e in emendas))
        self.assertTrue(all(b - a <= 1500 + 1e-9 for a, b in zip(suportes, suportes[1:])))


if __name__ == "__main__":
    unittest.main()
