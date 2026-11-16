"""Alinhamento de símbolos: travas, atração automática, alinhar e distribuir."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import alinhamento


class TestTravas(unittest.TestCase):
    def test_mais_proximo(self):
        self.assertIsNone(alinhamento.mais_proximo((0, 0), []))
        self.assertEqual(alinhamento.mais_proximo((90, 10), [(0, 0), (100, 0)]), (100, 0))

    def test_primeira_trava_e_a_do_eixo_mais_perto(self):
        # O cursor está quase na mesma vertical do vizinho: trava X primeiro, depois Y.
        self.assertEqual(alinhamento.travas_possiveis((1010, 500), [(1000, 0)]), [("x", 1000), ("y", 0)])
        # Quase na mesma horizontal: trava Y primeiro.
        self.assertEqual(alinhamento.travas_possiveis((500, 20), [(1000, 0)]), [("y", 0), ("x", 1000)])

    def test_sem_vizinhos_nao_ha_trava(self):
        self.assertEqual(alinhamento.travas_possiveis((0, 0), []), [])

    def test_aplicar_trava(self):
        self.assertEqual(alinhamento.aplicar_trava((12, 34), None), (12, 34))
        self.assertEqual(alinhamento.aplicar_trava((12, 34), ("x", 100)), (100, 34))
        self.assertEqual(alinhamento.aplicar_trava((12, 34), ("y", 100)), (12, 100))


class TestAtrair(unittest.TestCase):
    def test_dentro_da_tolerancia_alinha(self):
        self.assertEqual(alinhamento.atrair((1008, 500), [(1000, 0)], 10), (1000, 500, True, False))

    def test_fora_da_tolerancia_nao_mexe(self):
        self.assertEqual(alinhamento.atrair((1020, 500), [(1000, 0)], 10), (1020, 500, False, False))

    def test_cada_eixo_pode_alinhar_com_um_vizinho_diferente(self):
        vizinhos = [(1000, 0), (0, 2000)]
        self.assertEqual(alinhamento.atrair((995, 2004), vizinhos, 10), (1000, 2000, True, True))

    def test_sem_vizinhos_ou_sem_tolerancia(self):
        self.assertEqual(alinhamento.atrair((5, 5), [], 10), (5, 5, False, False))
        self.assertEqual(alinhamento.atrair((5, 5), [(0, 0)], 0), (5, 5, False, False))


class TestAlinharEDistribuir(unittest.TestCase):
    def test_fileira_horizontal_alinha_no_y_do_primeiro(self):
        pontos = [(0, 100), (1000, 130), (2000, 80)]
        self.assertEqual(alinhamento.alinhar(pontos), [(0, 100), (1000, 100), (2000, 100)])

    def test_fileira_vertical_alinha_no_x_do_primeiro(self):
        pontos = [(50, 0), (70, 1000), (20, 2500)]
        self.assertEqual(alinhamento.alinhar(pontos), [(50, 0), (50, 1000), (50, 2500)])

    def test_um_ponto_so_nao_muda(self):
        self.assertEqual(alinhamento.alinhar([(3, 4)]), [(3, 4)])

    def test_distribuir_mantem_os_extremos_e_a_ordem_da_lista(self):
        pontos = [(3000, 10), (0, 20), (500, 30), (900, 40)]
        self.assertEqual(alinhamento.distribuir(pontos), [(3000, 10), (0, 20), (1000, 30), (2000, 40)])

    def test_distribuir_na_vertical(self):
        self.assertEqual(alinhamento.distribuir([(0, 0), (5, 100), (9, 1000)]), [(0, 0), (5, 500), (9, 1000)])

    def test_distribuir_precisa_de_tres_pontos(self):
        self.assertEqual(alinhamento.distribuir([(0, 0), (10, 0)]), [(0, 0), (10, 0)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
