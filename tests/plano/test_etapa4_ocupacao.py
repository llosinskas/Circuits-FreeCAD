"""Etapa 4: eletroduto pela taxa de ocupação (core/ocupacao.py).

NBR 5410, 6.2.11.1.6: no máximo 53 % da seção interna com um cabo, 31 % com dois e
40 % com três ou mais. Os diâmetros internos dos eletrodutos vêm do catálogo e são
passados como argumento.
"""
import math
import unittest

from tests.plano._apoio import carregar

INTERNOS = {"1/2": 16.0, "3/4": 21.0, "1": 26.6, "1 1/4": 35.0}


class Base(unittest.TestCase):
    def setUp(self):
        self.o = carregar(self, "ocupacao", 4)


class TestTaxa(Base):
    def test_taxa_pelo_numero_de_cabos(self):
        self.assertEqual([self.o.taxa_maxima(n) for n in (1, 2, 3, 10)], [0.53, 0.31, 0.40, 0.40])

    def test_sem_cabos_e_erro(self):
        with self.assertRaises(ValueError):
            self.o.taxa_maxima(0)


class TestEletroduto(Base):
    def test_area_do_cabo_pelo_diametro_externo(self):
        self.assertAlmostEqual(self.o.area_cabo(5.0), math.pi * 25 / 4)

    def test_menor_eletroduto_que_comporta_os_cabos(self):
        # 10 cabos de 5 mm: 196,3 mm²; com 40 %, precisa de 490,9 mm² internos (d ≥ 25 mm)
        self.assertEqual(self.o.eletroduto_minimo([5.0] * 10, INTERNOS), "1")

    def test_poucos_cabos_cabem_no_menor(self):
        self.assertEqual(self.o.eletroduto_minimo([3.6] * 3, INTERNOS), "1/2")

    def test_dois_cabos_usam_31_por_cento(self):
        # 2 cabos de 8 mm: 100,5 mm²; com 31 %, 324,3 mm² (d ≥ 20,3 mm)
        self.assertEqual(self.o.eletroduto_minimo([8.0, 8.0], INTERNOS), "3/4")

    def test_nenhum_comporta(self):
        self.assertIsNone(self.o.eletroduto_minimo([10.0] * 20, INTERNOS))

    def test_aviso_quando_o_desenhado_e_menor(self):
        self.assertTrue(self.o.eletroduto_pequeno("3/4", [5.0] * 10, INTERNOS))
        self.assertFalse(self.o.eletroduto_pequeno("1 1/4", [5.0] * 10, INTERNOS))


if __name__ == "__main__":
    unittest.main()
