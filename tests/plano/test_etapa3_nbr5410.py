"""Etapa 3: dimensionamento completo pela NBR 5410 (core/nbr5410.py).

Valores das tabelas conferidos com a NBR 5410:2004 (cobre): tabela 36 (PVC) e 37
(EPR/XLPE), tabela 40 (temperatura ambiente), tabela 42 (agrupamento em feixe ou em
conduto fechado), tabela 47 (seção mínima). k da tabela 30: 115 (PVC) e 143 (EPR/XLPE).
"""
import math
import unittest

from tests.plano._apoio import carregar
from freecad.Circuits.core import rede


class Base(unittest.TestCase):
    def setUp(self):
        self.n = carregar(self, "nbr5410", 3)


class TestCapacidade(Base):
    def test_b1_pvc_dois_e_tres_condutores_carregados(self):
        self.assertEqual([self.n.capacidade(s, "B1", 2) for s in (1.5, 2.5, 4, 6, 10)], [17.5, 24, 32, 41, 57])
        self.assertEqual([self.n.capacidade(s, "B1", 3) for s in (1.5, 2.5, 4, 6, 10)], [15.5, 21, 28, 36, 50])

    def test_metodo_c_pvc(self):
        self.assertEqual([self.n.capacidade(s, "C", 2) for s in (1.5, 2.5, 4, 6, 10)], [19.5, 27, 36, 46, 63])

    def test_b1_epr(self):
        self.assertEqual([self.n.capacidade(s, "B1", 2, "EPR") for s in (1.5, 2.5, 4)], [23, 31, 42])

    def test_secao_fora_da_tabela(self):
        with self.assertRaises(ValueError):
            self.n.capacidade(3.0, "B1", 2)


class TestFatores(Base):
    def test_temperatura_pvc_inclui_30_graus(self):
        self.assertEqual([self.n.fct(t) for t in (25, 30, 35, 40, 50)], [1.06, 1.00, 0.94, 0.87, 0.71])

    def test_temperatura_epr_40_graus(self):
        # a tabela atual em core/tables tem 0,96 em 40 °C para EPR; o certo é 0,91
        self.assertEqual(self.n.fct(40, "EPR"), 0.91)

    def test_temperatura_intermediaria_usa_a_faixa_de_cima(self):
        self.assertEqual(self.n.fct(32), 0.94)

    def test_agrupamento_em_conduto_fechado(self):
        valores = {1: 1.00, 2: 0.80, 3: 0.70, 4: 0.65, 5: 0.60, 6: 0.57, 7: 0.54, 8: 0.52, 10: 0.50, 13: 0.45,
                   17: 0.41, 25: 0.38}
        self.assertEqual({n: self.n.fca(n) for n in valores}, valores)


class TestMetodoPeloTrajeto(Base):
    def test_qualquer_eletroduto_no_caminho_define_b1(self):
        self.assertEqual(self.n.metodo_do_trajeto(["leito", "eletroduto"]), "B1")

    def test_bandeja_aberta_com_cabos_unipolares_e_f_e_com_multipolar_e_e(self):
        self.assertEqual(self.n.metodo_do_trajeto(["eletrocalha_perfurada", "leito"]), "F")
        self.assertEqual(self.n.metodo_do_trajeto(["leito"], multipolar=True), "E")

    def test_eletrocalha_lisa_conta_como_conduto_fechado(self):
        self.assertEqual(self.n.metodo_do_trajeto(["eletrocalha_lisa"]), "B1")

    def test_sem_trajeto_vale_b1(self):
        self.assertEqual(self.n.metodo_do_trajeto([]), "B1")

    def test_bandeja_aberta_exige_cabo_e_nao_condutor_isolado(self):
        # NBR 5410: condutor isolado só em conduto fechado; em bandeja aberta e leito, cabos
        # unipolares ou multipolares (0,6/1 kV)
        self.assertTrue(self.n.exige_cabo(["eletroduto", "leito"]))
        self.assertFalse(self.n.exige_cabo(["eletroduto", "eletrocalha_lisa"]))


class TestQuedaDeTensao(Base):
    def test_monofasico(self):
        # 2 · L · I / (56 · S) = 2 · 30 · 10 / (56 · 2,5) = 4,286 V em 127 V
        self.assertAlmostEqual(self.n.queda_tensao(10, 30, 2.5, 127), 3.375, places=3)

    def test_trifasico(self):
        # √3 · 50 · 20 / (56 · 4) = 7,732 V em 380 V
        self.assertAlmostEqual(self.n.queda_tensao(20, 50, 4, 380, n_fases=3), 2.035, places=3)

    def test_queda_total_do_alimentador_mais_o_circuito(self):
        self.assertTrue(self.n.queda_total_ok(2.5, 4.0))
        self.assertFalse(self.n.queda_total_ok(3.5, 4.0))
        self.assertTrue(self.n.queda_total_ok(3.5, 4.0, limite=8.0))


class TestCurtoCircuito(Base):
    def test_secao_minima_pela_integral_de_joule(self):
        # S ≥ I·√t / k = 3000 · √0,1 / 115
        self.assertAlmostEqual(self.n.secao_curto(3000, 0.1), 3000 * math.sqrt(0.1) / 115, places=3)
        self.assertAlmostEqual(self.n.secao_curto(3000, 0.1, "EPR"), 3000 * math.sqrt(0.1) / 143, places=3)

    def test_secao_comercial_logo_acima(self):
        self.assertEqual([self.n.secao_comercial(v) for v in (1.0, 2.5, 8.25, 26)], [1.5, 2.5, 10, 35])


class TestDimensionarCircuito(Base):
    def dimensionar(self, **dados):
        padrao = {"corrente": 10.0, "tipo": "TUG", "comprimento": 10.0, "tensao": 127.0, "n_fases": 1,
                  "metodo": "B1", "agrupados": 1, "temperatura": 30.0, "isolacao": "PVC", "queda_max": 4.0}
        padrao.update(dados)
        return self.n.dimensionar_circuito(**padrao)

    def test_circuito_curto_fica_na_secao_minima(self):
        r = self.dimensionar()
        self.assertEqual((r["disjuntor"], r["secao"], r["criterio"]), (10, 2.5, "secao_minima"))

    def test_iluminacao_aceita_1_5(self):
        self.assertEqual(self.dimensionar(tipo="ILUM", corrente=5.0)["secao"], 1.5)

    def test_agrupamento_aumenta_a_secao(self):
        # In 20 A; Iz = capacidade · 0,65: 2,5 → 15,6 A; 4 → 20,8 A
        r = self.dimensionar(corrente=18.0, agrupados=4)
        self.assertEqual((r["disjuntor"], r["secao"], r["criterio"]), (20, 4, "capacidade"))
        self.assertAlmostEqual(r["fator"], 0.65)

    def test_circuito_longo_cresce_pela_queda(self):
        # 60 m, 10 A, 127 V: 2,5 → 6,75 %; 4 → 4,22 %; 6 → 2,81 %
        r = self.dimensionar(comprimento=60.0)
        self.assertEqual((r["secao"], r["criterio"]), (6, "queda_tensao"))
        self.assertAlmostEqual(r["queda"], 2.81, places=2)

    def test_temperatura_alta_reduz_a_capacidade(self):
        # 45 °C, PVC: 0,79; In 25 A: 4 → 25,3 A
        r = self.dimensionar(corrente=22.0, temperatura=45.0)
        self.assertEqual((r["disjuntor"], r["secao"]), (25, 4))

    def test_corrente_acima_da_tabela(self):
        with self.assertRaises(ValueError):
            self.dimensionar(corrente=1000.0)


class TestComprimentoNaRede(unittest.TestCase):
    """A queda de tensão precisa do comprimento com as descidas, não só do trecho horizontal."""

    def test_circuito_tem_comprimento_com_as_verticais(self):
        caixas = [
            {"id": "Q", "nome": "QD1", "x": 0.0, "y": 0.0, "tipo": "quadro", "altura": 1500.0, "pavimento": "",
             "circuito": "", "quadro": "QD1", "descricao": "QD1"},
            {"id": "T", "nome": "T1", "x": 10000.0, "y": 0.0, "tipo": "ponto", "altura": 300.0, "pavimento": "",
             "circuito": "1", "quadro": "", "ligacao": "F+N", "comando": ""},
        ]
        caminhos = [{"pontos": [(0.0, 0.0), (10000.0, 0.0)], "altura": 2800.0, "diametro": "3/4"}]
        info = lambda quadro, numero, membros: {"secao": 2.5, "fases": 1, "neutro": True, "terra": True}  # noqa: E731
        (circuito,) = rede.analisar(caminhos, caixas, info)["circuitos"]
        self.assertIn("comprimento", circuito, "Etapa 3: core.rede ainda não informa o comprimento com as descidas")
        # 10 m na horizontal + 1,3 m até o quadro (2,8 − 1,5) + 2,5 m até a tomada (2,8 − 0,3)
        self.assertAlmostEqual(circuito["comprimento"], 13.8, places=2)


if __name__ == "__main__":
    unittest.main()
