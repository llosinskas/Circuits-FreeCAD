"""Etapa 2: parâmetros do projeto num lugar só (core/parametros.py).

A planilha "Parâmetros do projeto" é lida como {nome: texto}; ``ler`` completa com
os padrões e converte os tipos.
"""
import unittest

from tests.plano._apoio import carregar


class Base(unittest.TestCase):
    def setUp(self):
        self.p = carregar(self, "parametros", 2)


class TestPadroes(Base):
    def test_sem_planilha_vale_o_padrao_residencial(self):
        p = self.p.ler({})
        self.assertEqual((p["tensao_fn"], p["tensao_ff"]), (127.0, 220.0))
        self.assertEqual((p["esquema"], p["material"], p["isolacao"]), ("TN-S", "cobre", "PVC"))
        self.assertEqual(p["temperatura_ambiente"], 30.0)
        self.assertEqual((p["queda_terminal"], p["queda_total"]), (4.0, 7.0))
        self.assertEqual(p["sensibilidade_dr"], 30.0)
        self.assertIn("icc_entrada_ka", p)


class TestLeitura(Base):
    def test_converte_numeros_com_virgula(self):
        p = self.p.ler({"tensao_fn": "220", "queda_terminal": "3,5"})
        self.assertEqual((p["tensao_fn"], p["queda_terminal"]), (220.0, 3.5))

    def test_valor_invalido_volta_ao_padrao(self):
        p = self.p.ler({"temperatura_ambiente": "quente", "esquema": "XYZ", "isolacao": "borracha"})
        self.assertEqual((p["temperatura_ambiente"], p["esquema"], p["isolacao"]), (30.0, "TN-S", "PVC"))

    def test_aceita_os_esquemas_e_isolacoes_da_norma(self):
        for esquema in ("TN-S", "TN-C-S", "TT"):
            self.assertEqual(self.p.ler({"esquema": esquema})["esquema"], esquema)
        self.assertEqual(self.p.ler({"isolacao": "EPR"})["isolacao"], "EPR")
        self.assertEqual(self.p.ler({"isolacao": "XLPE"})["isolacao"], "XLPE")

    def test_campo_desconhecido_e_ignorado(self):
        self.assertNotIn("cor_do_quadro", self.p.ler({"cor_do_quadro": "cinza"}))

    def test_nao_altera_os_padroes_entre_leituras(self):
        self.p.ler({"tensao_fn": "220"})
        self.assertEqual(self.p.ler({})["tensao_fn"], 127.0)


class TestTensaoDoCircuito(Base):
    def test_monofasico_fase_neutro_e_os_outros_fase_fase(self):
        p = self.p.ler({})
        self.assertEqual([self.p.tensao_do_circuito(p, n) for n in (1, 2, 3)], [127.0, 220.0, 220.0])


if __name__ == "__main__":
    unittest.main()
