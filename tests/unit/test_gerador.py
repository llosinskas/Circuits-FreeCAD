"""Pré-dimensionamento do gerador diesel (core.functions.Predial.gerador)."""
import math
import unittest

from freecad.Circuits.core.functions.Predial import gerador as g

MOTOR = "Motor (bomba, ventilador, compressor)"


def _quadro(kw, fd=1.0, fp=1.0):
    return g.carga("QD", "Quadro (cargas mistas)", 1, kw, "kW", fp, fd)


class TestCarga(unittest.TestCase):
    def test_campos_em_branco_valem_os_padroes_do_tipo(self):
        c = g.carga("Luz", "Iluminação e tomadas", "", 10, "", "", "")
        self.assertEqual((c["quantidade"], c["fator_demanda"], c["fator_potencia"]), (1.0, 1.0, 0.92))
        self.assertAlmostEqual(c["kva"], 10 / 0.92)
        self.assertFalse(c["motor"])
        self.assertEqual(c["partida"], "")

    def test_motor_em_cv_usa_rendimento_e_partida_direta(self):
        c = g.carga("Bomba", MOTOR, 1, 10, "cv")
        self.assertAlmostEqual(c["kw"], 10 * 0.7355 / 0.85)
        self.assertTrue(c["motor"])
        self.assertEqual(c["partida"], "Direta")

    def test_kva_vira_kw_pelo_fator_de_potencia(self):
        self.assertAlmostEqual(g.carga("UPS", "Nobreak (UPS)", 1, 20, "kVA")["kw"], 18.0)

    def test_inversor_torna_o_motor_nao_linear(self):
        c = g.carga("Elevador", "Elevador", 1, 15, "cv", partida="Inversor de frequência")
        self.assertTrue(c["nao_linear"])

    def test_aceita_virgula_decimal_e_no_gerador_n(self):
        c = g.carga("X", "Resistiva (chuveiro, aquecedor, forno)", "2", "5,5", "kW", "1", "0,5", "", "N")
        self.assertAlmostEqual(c["kw"], 5.5)
        self.assertAlmostEqual(c["fator_demanda"], 0.5)
        self.assertFalse(c["no_gerador"])

    def test_valores_invalidos(self):
        with self.assertRaises(ValueError):
            g.carga("X", "Desconhecido", 1, 1)
        with self.assertRaises(ValueError):
            g.carga("X", unidade="HP", potencia=1)
        with self.assertRaises(ValueError):
            g.carga("X", potencia=1, fator_demanda=1.5)
        with self.assertRaises(ValueError):
            g.carga("X", MOTOR, 1, 1, "cv", partida="Mágica")


class TestDimensionar(unittest.TestCase):
    def test_demanda_dividida_pela_diversidade(self):
        r = g.dimensionar([_quadro(100, 0.8), _quadro(50, 0.6)], fator_diversidade=1.25)
        self.assertAlmostEqual(r["instalada_kw"], 150)
        self.assertAlmostEqual(r["soma_demandas_kw"], 110)
        self.assertAlmostEqual(r["demanda_kw"], 88)

    def test_carga_resistiva_decidida_pelos_kw_com_carregamento(self):
        r = g.dimensionar([_quadro(64)], carregamento=0.8)
        self.assertAlmostEqual(r["criterios"]["demanda_kw"], 64 / 0.8 / 0.8)  # 100 kVA
        self.assertEqual(r["criterio"], "demanda_kw")
        self.assertEqual(r["gerador_kva"], 100)

    def test_regime_prime_pede_gerador_maior(self):
        emergencia = g.dimensionar([_quadro(64)], carregamento=g.REGIMES["Emergência (standby)"])
        prime = g.dimensionar([_quadro(64)], carregamento=g.REGIMES["Prime (horário de ponta, sem rede)"])
        self.assertGreater(prime["gerador_kva"], emergencia["gerador_kva"])

    def test_cargas_nao_lineares_contam_mais(self):
        linear = g.dimensionar([g.carga("A", "Iluminação e tomadas", 1, 20, "kVA", 0.9)])
        ups = g.dimensionar([g.carga("A", "Nobreak (UPS)", 1, 20, "kVA", 0.9)])
        self.assertAlmostEqual(ups["criterios"]["demanda_kva"], linear["criterios"]["demanda_kva"] * 1.5)

    def test_partida_direta_do_maior_motor_decide(self):
        r = g.dimensionar([g.carga("Bomba", MOTOR, 1, 50, "cv")], afundamento=20, reatancia=0.15)
        kva = 50 * 0.7355 / 0.85 / 0.85
        self.assertAlmostEqual(r["partida_kva"], 6 * kva)
        self.assertAlmostEqual(r["criterios"]["partida_motor"], 0.15 * 6 * kva * 0.8 / 0.2)
        self.assertEqual(r["criterio"], "partida_motor")
        self.assertLessEqual(r["afundamento"], 20.0)

    def test_soft_starter_reduz_o_gerador(self):
        direta = g.dimensionar([g.carga("B", MOTOR, 1, 50, "cv", partida="Direta")])
        suave = g.dimensionar([g.carga("B", MOTOR, 1, 50, "cv", partida="Soft-starter")])
        self.assertLess(suave["gerador_kva"], direta["gerador_kva"])

    def test_cargas_fora_do_gerador_nao_entram(self):
        fora = g.carga("Chuveiros", "Resistiva (chuveiro, aquecedor, forno)", 10, 7.5, no_gerador=False)
        r = g.dimensionar([_quadro(40), fora])
        self.assertAlmostEqual(r["instalada_kw"], 40)

    def test_altitude_e_temperatura_reduzem_a_potencia(self):
        self.assertAlmostEqual(g.reducao(2000, 45), 1 - 0.10 - 0.05)
        normal = g.dimensionar([_quadro(64)])
        alto = g.dimensionar([_quadro(64)], altitude=2500)
        self.assertGreater(alto["gerador_kva"], normal["gerador_kva"])

    def test_corrente_disjuntor_e_cabo(self):
        r = g.dimensionar([_quadro(100)], tensao=380, comprimento=20)  # 156 kVA → 180 kVA
        self.assertEqual(r["gerador_kva"], 180)
        self.assertAlmostEqual(r["corrente"], 180000 / (math.sqrt(3) * 380))
        self.assertEqual(r["disjuntor"], 320)
        self.assertGreaterEqual(r["cabo"]["iz"], r["disjuntor"])
        self.assertEqual(r["neutro"], r["cabo"]["secao"])

    def test_cabos_em_paralelo_acima_de_300(self):
        r = g.dimensionar([_quadro(400)], comprimento=30)  # 625 kVA, 950 A
        self.assertGreater(r["cabo"]["paralelos"], 1)
        self.assertGreaterEqual(r["cabo"]["iz"], r["disjuntor"])

    def test_cabo_longo_aumenta_pela_queda(self):
        curto = g.cabo(100, 90, 10, 380)
        longo = g.cabo(100, 90, 400, 380)
        self.assertEqual(curto["criterio"], "capacidade")
        self.assertEqual(longo["criterio"], "queda_tensao")
        self.assertGreater(longo["secao"], curto["secao"])
        self.assertLessEqual(longo["queda"], g.QUEDA_MAXIMA)

    def test_condutor_de_protecao_tabela_58(self):
        self.assertEqual(g.condutor_protecao(16), 16)
        self.assertEqual(g.condutor_protecao(35), 16)
        self.assertEqual(g.condutor_protecao(120), 70)
        self.assertEqual(g.condutor_protecao(150), 95)

    def test_tanque_pela_autonomia(self):
        r = g.dimensionar([_quadro(100)], autonomia=10, consumo_especifico=0.25)
        self.assertAlmostEqual(r["consumo_lh"], 25.0)
        self.assertEqual(r["tanque_l"], 280)  # 25 × 10 × 1,1 = 275, arredondado para cima

    def test_erros(self):
        with self.assertRaises(ValueError):
            g.dimensionar([])
        with self.assertRaises(ValueError):
            g.dimensionar([_quadro(10)], fator_diversidade=0.8)
        with self.assertRaises(ValueError):
            g.dimensionar([_quadro(5000)])

    def test_relatorio(self):
        r = g.dimensionar([_quadro(100, 0.7), g.carga("Bomba", MOTOR, 2, 10, "cv")], fator_diversidade=1.1)
        texto = g.relatorio(r)
        for trecho in ("GERADOR:", "DISJUNTOR DO GERADOR", "fases:", "neutro:", "proteção (PE)", "tanque",
                       "← decide", "partida direta", "diversidade 1,10"):
            self.assertIn(trecho, texto)


class TestPlanilha(unittest.TestCase):
    def test_linha_da_planilha_vira_carga(self):
        c = g.carga_da_linha({"descricao": "Bomba", "tipo": MOTOR, "quantidade": "2", "potencia": "5",
                              "unidade": "cv", "fator_demanda": "0,5", "no_gerador": "S"})
        self.assertEqual((c["quantidade"], c["fator_demanda"], c["partida"]), (2.0, 0.5, "Direta"))

    def test_exemplos_sao_cargas_validas(self):
        r = g.dimensionar([g.carga_da_linha(e) for e in g.EXEMPLOS])
        self.assertTrue(r["maior_motor"])

    def test_um_quadro_por_linha_com_o_fator_de_demanda_calculado(self):
        linhas = g.linhas_dos_quadros([("QGBT", 80.0, 56.0), ("QD2", 12.5, None), ("Vazio", 0.0, None)])
        self.assertEqual([l["descricao"] for l in linhas], ["QGBT", "QD2"])
        self.assertEqual((linhas[0]["potencia"], linhas[0]["fator_demanda"]), ("80", "0,70"))
        self.assertEqual(linhas[1]["fator_demanda"], "1,00")
        self.assertAlmostEqual(g.carga_da_linha(linhas[0])["fator_demanda"], 0.7)

    def test_resumo(self):
        rotulos = dict(g.resumo(g.dimensionar([_quadro(100)])))
        self.assertEqual(rotulos["Gerador [kVA]"], "180")
        self.assertIn("mm²", rotulos["Cabos por fase"])


if __name__ == "__main__":
    unittest.main()
