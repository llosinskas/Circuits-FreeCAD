"""Estudo de curto-circuito pela IEC 60909 (core/curto.py).

Impedâncias em mΩ, referidas à baixa tensão; correntes em kA; tensões de linha em V.
Valores de referência: rede de 500 MVA, transformador de 1000 kVA com uk = 5 % e
10,5 kW de perdas no cobre, 380 V no secundário.
"""
import math
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import curto

U = 380.0


class Base(unittest.TestCase):
    def setUp(self):
        self.c = curto

    def assertProximo(self, valor, esperado, tolerancia=0.01):
        self.assertAlmostEqual(valor, esperado, delta=abs(esperado) * tolerancia)


class TestImpedancias(Base):
    def test_rede_pela_potencia_de_curto(self):
        r, x = self.c.impedancia_rede(500.0, U)  # Scc em MVA, c = 1,1
        self.assertProximo(x, 0.3161)
        self.assertProximo(r, 0.1 * x)

    def test_transformador_com_correcao_kt(self):
        r, x = self.c.impedancia_transformador(1000.0, U, 5.0, perdas_cobre_w=10500.0)
        # sem KT: R = 1,516 e X = 7,059 mΩ; KT = 0,95 x 1,05 / (1 + 0,6 x 0,0489) = 0,969
        self.assertProximo(r, 1.4693)
        self.assertProximo(x, 6.8407)

    def test_cabo_em_paralelo(self):
        r, x = self.c.impedancia_cabo(240.0, 50.0, paralelos=2)  # cobre a 20 °C, 0,08 mΩ/m
        self.assertProximo(r, 1.929)
        self.assertProximo(x, 2.0)

    def test_cabo_quente_tem_mais_resistencia(self):
        frio, _ = self.c.impedancia_cabo(4.0, 40.0)
        quente, _ = self.c.impedancia_cabo(4.0, 40.0, temperatura=80.0)
        self.assertProximo(quente / frio, 1 + 0.004 * 60, tolerancia=0.02)


class TestCorrentes(Base):
    def test_trifasico_e_pico_no_qgbt(self):
        rr, xr = self.c.impedancia_rede(500.0, U)
        rt, xt = self.c.impedancia_transformador(1000.0, U, 5.0, perdas_cobre_w=10500.0)
        r, x = rr + rt, xr + xt
        ik = self.c.curto_trifasico(r, x, U)  # cmáx = 1,05
        self.assertProximo(ik, 31.50)
        self.assertProximo(self.c.fator_pico(r, x), 1.5424)
        self.assertProximo(self.c.corrente_pico(ik, r, x), 68.72)

    def test_fator_pico_entre_1_02_e_2(self):
        self.assertProximo(self.c.fator_pico(1.0, 0.0001), 1.02, tolerancia=0.001)
        self.assertLess(self.c.fator_pico(0.0, 1.0), 2.0 + 1e-9)

    def test_fase_terra_minimo_pelo_laco(self):
        # 220 V entre fase e terra, laço de 100 mΩ resistivo, cmín = 0,95
        self.assertProximo(self.c.curto_minimo_fase_terra(60.0, 0.0, 40.0, 0.0, 220.0), 0.95 * 220 / 100)

    def test_capacidade_de_interrupcao_comercial(self):
        self.assertEqual(self.c.capacidade_interrupcao(4.0), 4.5)
        self.assertEqual(self.c.capacidade_interrupcao(31.5), 36)
        self.assertGreaterEqual(self.c.capacidade_interrupcao(0.5), 3)
        with self.assertRaises(ValueError):
            self.c.capacidade_interrupcao(500.0)


class TestEstudo(Base):
    def test_cada_barra_soma_as_impedancias_de_cima(self):
        barras = [
            {"nome": "QGBT", "origem": "", "rede_mva": 500.0,
             "transformador": {"potencia_kva": 1000.0, "uk": 5.0, "perdas_cobre_w": 10500.0}},
            {"nome": "CCM1", "origem": "QGBT", "cabo": {"secao": 240.0, "comprimento": 50.0, "paralelos": 2}},
            {"nome": "QDL", "origem": "CCM1", "cabo": {"secao": 16.0, "comprimento": 30.0}},
        ]
        resultado = self.c.estudo(barras, U)
        self.assertProximo(resultado["QGBT"]["ik3"], 31.50)
        self.assertProximo(resultado["CCM1"]["ik3"], 23.56)
        self.assertLess(resultado["QDL"]["ik3"], resultado["CCM1"]["ik3"])
        for barra in resultado.values():
            self.assertIn("ip", barra)
            self.assertIn("icu_minimo", barra)
            self.assertGreaterEqual(barra["icu_minimo"], barra["ik3"])

    def test_origem_que_nao_existe(self):
        with self.assertRaises(ValueError):
            self.c.estudo([{"nome": "QD1", "origem": "QGBT", "cabo": {"secao": 10.0, "comprimento": 5.0}}], U)


class TestPlanilha(Base):
    def test_entrada_e_uma_barra_por_quadro(self):
        linhas = self.c.linhas_dos_quadros([("QGBT", "", "240"), ("QD1", "QGBT", "16"), ("QD2", "Medidor", "")])
        self.assertEqual([(l["nome"], l.get("origem", "")) for l in linhas],
                         [("Entrada", ""), ("QGBT", "Entrada"), ("QD1", "QGBT"), ("QD2", "Entrada")])
        self.assertEqual(linhas[3]["secao"], "10")  # sem cabo de entrada no quadro, um palpite

    def test_barras_das_linhas_com_virgula_e_erros_com_a_linha(self):
        linhas = [(3, {"nome": "Entrada", "rede_mva": "500", "trafo_kva": "1000", "uk": "5", "perdas_cobre_w": ""}),
                  (4, {"nome": "QD1", "origem": "Entrada", "secao": "16", "comprimento": "12,5", "material": "Alumínio"}),
                  (5, {"nome": ""})]
        entrada, qd1 = self.c.barras_das_linhas(linhas)
        self.assertEqual(entrada["transformador"], {"potencia_kva": 1000.0, "uk": 5.0, "perdas_cobre_w": 0.0})
        self.assertEqual(qd1["cabo"], {"secao": 16.0, "comprimento": 12.5, "paralelos": 1, "material": "aluminio"})
        with self.assertRaisesRegex(ValueError, "Linha 7"):
            self.c.barras_das_linhas([(7, {"nome": "QD", "origem": "X", "secao": "16", "comprimento": "dez"})])
        with self.assertRaisesRegex(ValueError, "Linha 3.*origem"):
            self.c.barras_das_linhas([(3, {"nome": "Solta"})])

    def test_estudo_da_planilha_e_relatorio(self):
        barras = self.c.barras_das_linhas([
            (3, {"nome": "Entrada", "rede_mva": "500", "trafo_kva": "1000", "uk": "5", "perdas_cobre_w": "10500"}),
            (4, {"nome": "QD1", "origem": "Entrada", "secao": "16", "comprimento": "30"})])
        resultado = self.c.estudo(barras, U)
        self.assertLess(resultado["QD1"]["ik1_min"], resultado["QD1"]["ik3"])
        self.assertIn("QD1:", self.c.relatorio(resultado))


if __name__ == "__main__":
    unittest.main()
