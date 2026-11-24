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
        self.assertTrue(any("indireta" in a for a in r["avisos"]))


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
        self.assertEqual(set(custos), {"convencional", "descentralizado", "busway"})
        for orcamento in custos.values():
            self.assertAlmostEqual(orcamento["total"], orcamento["material"] * 1.30)
        segunda = sorted(o["total"] for o in custos.values())[1]
        self.assertAlmostEqual(r["economia"], segunda - custos[r["recomendada"]]["total"])
        texto = c.relatorio(r)
        self.assertIn("Busway", texto)
        self.assertIn("Coluna", texto)

    def test_precos_da_planilha_mudam_a_escolha(self):
        base = c.comparar(predio(), demanda_total_a=600.0)
        caro = {f"busway_m_{n}": 1e6 for n in c.CORRENTES_BUSWAY}
        r = c.comparar(predio(), demanda_total_a=600.0, precos=caro, andares_por_centro=0)
        self.assertEqual(r["recomendada"], "convencional")
        self.assertNotIn("descentralizado", r["custos"])
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

    def test_coluna_detalhada_com_pecas_dentro_das_caixas(self):
        pecas = c.pecas_da_coluna(12, "Coluna simples")
        caixas = {p[0]: p for p in c.coluna_de_medicao(12, "Coluna simples")["caixas"]}
        por_tipo = {}
        for peca in pecas:
            por_tipo.setdefault(peca["tipo"], []).append(peca)
        self.assertEqual(len(por_tipo["medidor"]), 12)
        self.assertEqual(len(por_tipo["tampa"]), 13)  # 12 caixas e a CDPM
        self.assertEqual([p["rotulo"] for p in por_tipo["barra"]], ["Barra R", "Barra S", "Barra T", "Barra N",
                                                                     "Barra PE"])
        self.assertEqual(len(por_tipo["dps"]), c.DPS_POR_CDPM)
        self.assertEqual(len(por_tipo["eletroduto"]), 13)
        entrada = next(p for p in por_tipo["eletroduto"] if p["rotulo"] == "Eletroduto de entrada")
        self.assertEqual(entrada["origem"][2], 0.0)  # desce até o piso
        for peca in pecas:
            if peca["forma"] != "caixa" or peca["tipo"] in ("tampa", "etiqueta"):
                continue
            dono = caixas[peca["rotulo"].split()[0]] if peca["rotulo"].split()[0] in caixas else caixas["CDPM"]
            (x, y, z), (dx, dy, dz) = dono[1], dono[2]
            (px, py, pz), (qx, qy, qz) = peca["origem"], peca["dims"]
            self.assertTrue(x - 1e-6 <= px and px + qx <= x + dx + 1e-6, peca["rotulo"])
            self.assertTrue(y - 1e-6 <= py and py + qy <= y + dy + 1e-6, peca["rotulo"])
            self.assertTrue(z - 1e-6 <= pz and pz + qz <= z + dz + 1e-6, peca["rotulo"])
        medidor, disjuntor = (next(p for p in pecas if p["rotulo"] == f"M01 {n}") for n in ("medidor", "disjuntor"))
        self.assertGreater(medidor["origem"][2], disjuntor["origem"][2])  # medição em cima, proteção embaixo

    def test_materiais_do_busway_e_das_colunas(self):
        itens = {i["item"]: i["quantidade"] for i in c.materiais_do_busway(
            [{"nominal": 630, "horizontal": 10.0, "vertical": 20.0, "cotovelos": 1, "lajes": 6}])}
        self.assertEqual(itens["Busway (barramento blindado)"], 30.0)
        self.assertEqual(itens["Emenda (junção) de busway"], 9 + 1)
        self.assertEqual(itens["Suporte de busway"], 20)
        self.assertEqual(itens["Barreira corta-fogo"], 6)
        self.assertEqual(itens["Fita de advertência"], 2)
        colunas = {(i["item"], i["especificacao"]): i["quantidade"] for i in c.materiais_das_colunas(
            [{"caixas": 30, "cdpms": ["Coluna MAX"]}, {"caixas": 6, "cdpms": ["Coluna simples"]}])}
        self.assertEqual(colunas[("Caixa de medição tipo P", "policarbonato, 260 × 520 × 190 mm")], 36)
        self.assertEqual(colunas[("DPS", "classe II, 3 fases e neutro")], 8)
        self.assertEqual(colunas[("Barramento de cobre", "20x5 mm")], 3.0)
        mec = {(i["item"], i["especificacao"]): i["quantidade"] for i in c.materiais_das_caixas_mec(
            ["MEC IV", "MEC IV", "MEC XII"])}
        self.assertEqual(mec[("Caixa de medição centralizada", "MEC IV")], 2)
        self.assertEqual(mec[("Placa de comunicação", "")], 4)

    def test_emendas_a_cada_3_m_e_suportes_fora_delas(self):
        emendas, suportes = c.emendas_e_suportes(10000)
        self.assertEqual(emendas, [3000, 6000, 9000])
        self.assertTrue(all(abs(s - e) > 150 for s in suportes for e in emendas))
        self.assertTrue(all(b - a <= 1500 + 1e-9 for a, b in zip(suportes, suportes[1:])))



class TestDimensionarColunas(unittest.TestCase):
    def test_30_medidores_em_10_colunas_de_3_com_a_cdpm_no_meio(self):
        d = c.dimensionar_colunas(30, 63.0, 2, demanda_total_a=250.0)
        conjunto, = d["conjuntos"]
        self.assertEqual((d["modelo"], conjunto["caixas"], conjunto["cdpm"]), ("P", 30, "Coluna dupla"))
        self.assertEqual(c.distribuicao(30, 3), (15, 15, 3))
        self.assertAlmostEqual(conjunto["largura_mm"], 10 * 260 + 520)  # 5 colunas de cada lado
        self.assertEqual(conjunto["disjuntor_geral"], 250)
        self.assertEqual(conjunto["barramento"], "25x5 mm")  # Tabela 23 e o mínimo da Tabela 28
        self.assertLessEqual(conjunto["ramal"], 185)
        self.assertEqual(d["disjuntor_unidade"], 63)

    def test_medidores_por_coluna_mudam_a_capacidade(self):
        self.assertEqual([c.capacidade_agrupamento(v) for v in (1, 2, 3)], [12, 24, 30])
        d = c.dimensionar_colunas(30, 63.0, 2, por_coluna=2, demanda_total_a=250.0)
        self.assertEqual([g["caixas"] for g in d["conjuntos"]], [15, 15])
        self.assertTrue(any("abrigado" in a for a in d["avisos"]))
        g = c.coluna_de_medicao(12, "Coluna simples", 2)
        self.assertEqual(g["altura"], 2 * 520)
        self.assertEqual(g["base"], c.ALTURA_BASE_MM[2])

    def test_trifasicas_vao_para_as_caixas_metalicas(self):
        d = c.dimensionar_colunas(20, 40.0, 3)
        self.assertEqual(d["modelo"], "metalica")
        self.assertEqual(sum(g["medicoes"] for g in d["conjuntos"]), 20)
        self.assertTrue(all(g["corrente"] <= c.CORRENTE_MAX_COLETIVA for g in d["conjuntos"]))
        self.assertTrue(all(g["medicoes"] <= c.CAIXAS_METALICAS[g["modelo"]][0] for g in d["conjuntos"]))
        self.assertTrue(any("caixa de barramentos" in a for a in d["avisos"]))
        self.assertEqual([g["modelo"] for g in c.caixas_metalicas(12, 10.0)], ["N"])
        self.assertEqual([g["modelo"] for g in c.caixas_metalicas(16, 10.0)], ["O"])
        self.assertEqual([g["modelo"] for g in c.caixas_metalicas(5, 10.0)], ["H"])
        self.assertEqual([g["modelo"] for g in c.caixas_metalicas(8, 10.0, "L")], ["L", "L"])

    def test_acima_de_100_a_e_indireta(self):
        d = c.dimensionar_colunas(2, 250.0, 3)
        self.assertEqual(d["modelo"], "indireta")
        self.assertEqual([g["modelo"] for g in d["conjuntos"]], ["IND300", "IND300"])  # uma por unidade
        g = d["conjuntos"][0]
        self.assertEqual((g["disjuntor_geral"], g["chave"], g["tc"]), (250, 250, "300/5 A"))
        self.assertIsNone(d["disjuntor_unidade"])
        self.assertTrue(any("chave seccionadora" in a for a in d["avisos"]))
        self.assertTrue(any("101 a 200 A" in a for a in c.dimensionar_colunas(1, 150.0, 3)["avisos"]))

    def test_indireta_de_300_a_600_a_em_caixa_m_com_dois_circuitos(self):
        g, = c.dimensionar_colunas(1, 450.0, 3)["conjuntos"]
        self.assertEqual((g["modelo"], g["paralelos"], g["disjuntor_geral"], g["tc"]), ("IND600", 2, 500, "600/5 A"))
        self.assertLessEqual(g["ramal"], 185)  # nota 8: dois circuitos de até 185 mm²
        d = c.dimensionar_colunas(1, 700.0, 3)
        self.assertEqual(d["conjuntos"], [])
        self.assertIn("cabine de barramentos", d["avisos"][0])

    def test_trifasicas_ate_4_em_caixas_e_com_cdpm(self):
        d = c.dimensionar_colunas(3, 40.0, 3)
        g, = d["conjuntos"]
        self.assertEqual((d["modelo"], g["modelo"], g["medicoes"], g["disjuntor_geral"]), ("E", "E", 3, 125))
        self.assertAlmostEqual(g["largura_mm"], 3 * 350 + 300)
        self.assertLessEqual(g["ramal"], c.SECAO_MAX_RAMAL_E)
        self.assertEqual(c.dimensionar_colunas(6, 30.0, 3)["modelo"], "metalica")  # mais de 4: coletivas
        self.assertEqual(c.dimensionar_colunas(4, 40.0, 3)["modelo"], "metalica")  # 160 A passa da CDPM
        forcado = c.dimensionar_colunas(8, 40.0, 3, modelo="Caixa E")
        self.assertTrue(all(g["corrente"] <= 125 or g["medicoes"] == 1 for g in forcado["conjuntos"]))
        self.assertTrue(any("grupos de caixas E" in a for a in forcado["avisos"]))

    def test_caixa_e_detalhada(self):
        pecas = c.pecas_do_grupo_e(3)
        caixas = [p for p in pecas if p["tipo"] == "corpo" and p["rotulo"] in ("E01", "E02", "E03")]
        self.assertEqual(len(caixas), 3)
        self.assertTrue(all(p["dims"] == (350.0, 250.0 - c.TAMPA_MM, 560.0) for p in caixas))
        self.assertEqual(sum(1 for p in pecas if p["tipo"] == "medidor"), 3)
        self.assertTrue(any(p["rotulo"] == "CDPM" for p in pecas))
        self.assertFalse(any(p["rotulo"] == "CDPM" for p in c.pecas_do_grupo_e(1)))
        medidor = next(p for p in pecas if p["rotulo"] == "E01 medidor")
        self.assertGreater(medidor["origem"][2], 1200 + 560 - 390)  # no compartimento de cima

    def test_indireta_detalhada(self):
        rotulos = [p["rotulo"] for p in c.pecas_da_indireta("IND300")]
        for nome in ("Chave seccionadora sob carga", "Caixa dos TCs", "Proteção geral", "Medidor",
                     "Bloco de aferição", "Eletroduto de entrada"):
            self.assertIn(nome, rotulos)
        self.assertEqual(sum(1 for r in rotulos if r.startswith("Módulo") and "tampa" not in r), 4)
        m = [p["rotulo"] for p in c.pecas_da_indireta("IND600")]
        self.assertEqual(sum(1 for r in m if r.startswith("TC ")), 3)
        self.assertEqual(sum(1 for r in m if r.startswith("Eletroduto de entrada")), 2)

    def test_mec_indireta_no_busway(self):
        self.assertEqual([x["tipo"] for x in c.caixas_mec(1, 150, 150)], ["MEC IV"])
        caixas = c.caixas_mec(2, 500, 250)
        self.assertEqual([x["tipo"] for x in caixas], ["MEC VI", "MEC VI"])
        self.assertTrue(all(x["indireta"] for x in caixas))

    def test_convencional_separa_as_unidades_indiretas(self):
        andares = [c.andar("1º", 3, 4, 63, 2), c.andar("Loja", 0, 1, 250, 3)]
        r = c.convencional(andares, demanda_total_a=400)
        modelos = [g.get("modelo") for g in r["agrupamentos"]]
        self.assertIn("IND300", modelos)
        self.assertIn("P", modelos)
        texto = c.relatorio(c.comparar(andares, demanda_total_a=400))
        self.assertIn("TC 300/5 A", texto)
        self.assertNotIn("barramento None", texto)
        custo = [i["descricao"] for i in c.orcamento(r)["itens"]]
        self.assertIn("Conjunto de medição indireta até 300 A (policarbonato)", custo)

    def test_materiais_de_e_e_indireta(self):
        itens = {(i["item"], i["especificacao"]): i["quantidade"] for i in c.materiais_das_colunas(
            [{"caixas_e": 3, "cdpm_e": 1, "indiretas": ["IND300", "IND600"]}])}
        self.assertEqual(itens[("Caixa de medição tipo E", "350 × 560 × 250 mm")], 3)
        self.assertEqual(itens[("CDPM das caixas E", "300 × 500 × 250 mm, até 125 A")], 1)
        self.assertEqual(itens[("Conjunto de medição indireta", c.INDIRETAS["IND300"][1])], 1)
        self.assertEqual(itens[("Chave seccionadora sob carga sem fusíveis", "antes dos TCs")], 1)

    def test_caixa_p_forcada_em_trifasica_avisa(self):
        d = c.dimensionar_colunas(6, 40.0, 3, modelo="P (policarbonato)")
        self.assertEqual(d["modelo"], "P")
        self.assertTrue(any("mono e bifásicas" in a for a in d["avisos"]))

    def test_barramento_e_ramal(self):
        self.assertEqual(c.barramento(180), "15x3 mm")
        self.assertEqual(c.barramento(180, (20, 5)), "20x5 mm")
        self.assertIsNone(c.barramento(900))
        self.assertGreater(c.ramal_de_distribuicao(300, 30, 220), c.ramal_de_distribuicao(100, 30, 220))

    def test_caixa_metalica_detalhada_dentro_do_corpo(self):
        pecas = c.pecas_da_caixa_metalica("N", 10)
        self.assertEqual(sum(1 for p in pecas if p["tipo"] == "medidor"), 10)
        corpo = next(p for p in pecas if p["rotulo"] == "Caixa N")
        (x, y, z), (dx, dy, dz) = corpo["origem"], corpo["dims"]
        for p in pecas:
            if p["tipo"] == "medidor":
                (px, py, pz), (qx, qy, qz) = p["origem"], p["dims"]
                self.assertTrue(x <= px and px + qx <= x + dx and z <= pz and pz + qz <= z + dz)
        barramentos = next(p for p in pecas if p["rotulo"] == "Barramentos N")
        self.assertAlmostEqual(barramentos["origem"][2] + barramentos["dims"][2], z)  # logo abaixo da caixa
        self.assertFalse(any(p["rotulo"].startswith("Barramentos") for p in c.pecas_da_caixa_metalica("O")))

    def test_conjuntos_lado_a_lado_e_centrados(self):
        d = c.dimensionar_colunas(30, 63.0, 2, por_coluna=2, demanda_total_a=250.0)
        pecas = c.pecas_do_centro(d)
        self.assertEqual({p["conjunto"] for p in pecas}, {1, 2})
        caixas = [p for p in pecas if p["forma"] == "caixa"]
        xs = [p["origem"][0] for p in caixas] + [p["origem"][0] + p["dims"][0] for p in caixas]
        self.assertAlmostEqual(min(xs) + max(xs), 0.0, delta=1e-6)
        fim_1 = max(p["origem"][0] + p["dims"][0] for p in caixas if p["conjunto"] == 1)
        inicio_2 = min(p["origem"][0] for p in caixas if p["conjunto"] == 2)
        self.assertAlmostEqual(inicio_2 - fim_1, c.FOLGA_ENTRE_AGRUPAMENTOS_MM)



class TestDescentralizado(unittest.TestCase):
    def test_um_centro_a_cada_grupo_de_andares(self):
        r = c.descentralizado(predio(), tensao=220.0, distancia_horizontal=15.0, demanda_total_a=600.0,
                              andares_por_centro=4)
        self.assertEqual(len(r["centros"]), 3)
        self.assertEqual([x["andar"] for x in r["centros"]], ["1º", "5º", "9º"])
        self.assertEqual(sum(x["unidades"] for x in r["centros"]), 48)
        self.assertAlmostEqual(sum(x["corrente"] for x in r["centros"]), 600.0)
        primeiro, ultimo = r["centros"][0], r["centros"][-1]
        self.assertAlmostEqual(primeiro["ramal"]["comprimento"], 15.0 + 3.0)
        self.assertGreater(ultimo["ramal"]["secao"], primeiro["ramal"]["secao"])  # mais longe, mais queda
        self.assertTrue(all(x["chave"] in c.CHAVES_VERTICAIS for x in r["centros"]))
        self.assertTrue(all(x["qdc_local"] for x in r["centros"]))  # todos a mais de 15 m: independentes
        # alimentadores só do centro ao andar: o mais longo é de 3 andares acima mais o trecho no andar
        self.assertAlmostEqual(max(a["comprimento"] for a in primeiro["alimentadores"]),
                               9.0 + c.COMPRIMENTO_NO_ANDAR_M)

    def test_centro_perto_da_entrada_nao_e_independente(self):
        r = c.descentralizado([c.andar("Térreo", 0, 8, 40), c.andar("1º", 3, 8, 40)], distancia_horizontal=5.0,
                              demanda_total_a=300.0, andares_por_centro=1)
        self.assertEqual([x["qdc_local"] for x in r["centros"]], [None, None])  # 5 m e 8 m

    def test_menos_cabo_que_o_centro_unico(self):
        conv = c.convencional(predio(), demanda_total_a=600.0)
        desc = c.descentralizado(predio(), demanda_total_a=600.0)
        self.assertLess(desc["cabo_mm2_m"], conv["cabo_mm2_m"])
        itens = [i["descricao"] for i in c.orcamento(desc)["itens"]]
        self.assertIn(c.PRECOS["chave_vertical"][0], itens)
        self.assertTrue(any(d.startswith("QDC 5 no centro") for d in itens))

    def test_comparacao_com_tres_solucoes(self):
        r = c.comparar(predio(), demanda_total_a=600.0)
        self.assertIsNotNone(r["descentralizado"])
        texto = c.relatorio(r)
        self.assertIn("2) Medição descentralizada", texto)
        self.assertIn("3) Busway", texto)
        self.assertIn("chave vertical", texto)
        self.assertIn(("Centros descentralizados", "3"), c.resumo(r))
        poucos = c.comparar(predio(andares=3), demanda_total_a=200.0)
        self.assertIsNone(poucos["descentralizado"])  # cabem num centro só


class TestPlanoDeGeracao(unittest.TestCase):
    ANDARES = [c.andar("Térreo", 0, 0)] + [c.andar(f"{i}º", 3 * i, 4, 63, 2) for i in range(1, 7)] + \
        [c.andar("Loja", 0, 1, 250, 3)]

    def test_centro_unico_com_diretas_e_indireta(self):
        centro, = c.plano_de_geracao(self.ANDARES, "convencional", demanda_total_a=400.0)
        self.assertEqual([o["chave"] for o in centro["objetos"]], ["diretas", "indireta Loja"])
        diretas, indireta = centro["objetos"]
        self.assertEqual((diretas["valores"]["Medidores"], indireta["valores"]["Modelo"]), (24, "Indireta"))
        self.assertAlmostEqual(diretas["valores"]["DemandaTotal"] + 400.0 * 250 / (24 * 63 + 250), 400.0, places=0)
        # lado a lado, centrados, com a folga entre eles
        self.assertAlmostEqual(diretas["x"] - diretas["largura"] / 2 + indireta["x"] + indireta["largura"] / 2, 0.0)
        self.assertAlmostEqual(indireta["x"] - indireta["largura"] / 2 - (diretas["x"] + diretas["largura"] / 2),
                               c.FOLGA_ENTRE_AGRUPAMENTOS_MM)
        ab = centro["abrigo"]
        self.assertAlmostEqual(ab["y0"] + ab["profundidade"], ab["fundo"])  # o fundo das caixas na parede
        self.assertIsNone(centro["ramal"])

    def test_descentralizado_com_ramal_por_centro(self):
        centros = c.plano_de_geracao(self.ANDARES, "descentralizado", demanda_total_a=400.0, andares_por_centro=4)
        self.assertEqual([x["andar"] for x in centros], ["Loja", "4º"])
        self.assertTrue(all(x["ramal"]["secao"] for x in centros))
        self.assertEqual(centros[1]["cota"], 12.0)

    def test_busway_nao_e_desenhado_aqui(self):
        with self.assertRaises(ValueError):
            c.plano_de_geracao(self.ANDARES, "busway")


if __name__ == "__main__":
    unittest.main()
