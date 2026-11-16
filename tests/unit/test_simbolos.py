"""Catálogo e geometria dos símbolos de pontos elétricos."""
import os
import unittest

from tests import ROOT
from freecad.Circuits.core import simbolos


class TestCatalogo(unittest.TestCase):
    def test_todo_simbolo_tem_geometria_dentro_de_limites_razoaveis(self):
        for chave in simbolos.CATALOGO:
            with self.subTest(chave):
                self.assertTrue(simbolos.geometria(chave))
                xmin, ymin, xmax, ymax = simbolos.limites(chave)
                self.assertGreaterEqual(xmin, -0.7)
                self.assertLessEqual(xmax, 1.2)
                self.assertLessEqual(ymax - ymin, 1.2)

    def test_dados_eletricos_sao_validos(self):
        for chave, dados in simbolos.CATALOGO.items():
            with self.subTest(chave):
                self.assertGreater(dados["potencia_va"], 0)
                self.assertTrue(0 < dados["fator_potencia"] <= 1)
                self.assertIn(dados["tensao"], (127, 220, 380))
                self.assertIn(dados["ligacao"], simbolos.LIGACOES)
                self.assertIn(dados["tipo_circuito"], (simbolos.ILUM, simbolos.TUG, simbolos.TUE))
                self.assertIn(dados["categoria"], (simbolos.TOMADA, simbolos.ENERGIA, simbolos.ILUMINACAO))

    def test_geometria_escala_com_o_tamanho(self):
        self.assertEqual(simbolos.geometria("luz_teto", 200)[0], ("circulo", 0, 0, 100.0))
        # Os ângulos do arco não mudam com a escala.
        self.assertEqual(simbolos.geometria("arandela", 200)[0], ("arco", 0, 0, 100.0, 0, 180))

    def test_tomadas_se_distinguem_pela_hachura(self):
        baixa, media, alta = (len(simbolos.geometria(f"tomada_{t}")) for t in ("baixa", "media", "alta"))
        self.assertEqual(baixa, 4)
        self.assertGreater(media, baixa)
        self.assertGreater(alta, baixa)

    def test_simbolo_desconhecido(self):
        with self.assertRaises(KeyError):
            simbolos.geometria("nao_existe")

    def test_todo_simbolo_tem_icone(self):
        pasta = os.path.join(ROOT, "freecad", "Circuits", "Resources", "Icons", "simbologia")
        for chave in simbolos.CATALOGO:
            self.assertTrue(os.path.exists(os.path.join(pasta, f"{chave}.svg")), chave)


if __name__ == "__main__":
    unittest.main(verbosity=2)
