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
                self.assertGreaterEqual(xmin, -0.85)
                self.assertLessEqual(xmax, 1.2)
                self.assertLessEqual(ymax - ymin, 1.2)

    def test_dados_eletricos_sao_validos(self):
        for chave, dados in simbolos.CATALOGO.items():
            with self.subTest(chave):
                if dados["categoria"] == simbolos.QUADRO:  # quadro não é carga de circuito
                    self.assertEqual((dados["potencia_va"], dados["tipo_circuito"]), (0, None))
                    continue
                self.assertGreater(dados["potencia_va"], 0)
                self.assertTrue(0 < dados["fator_potencia"] <= 1)
                self.assertIn(dados["tensao"], (127, 220, 380))
                self.assertIn(dados["ligacao"], simbolos.LIGACOES)
                self.assertIn(dados["tipo_circuito"], (simbolos.ILUM, simbolos.TUG, simbolos.TUE))
                self.assertIn(dados["categoria"], (simbolos.TOMADA, simbolos.ENERGIA, simbolos.ILUMINACAO))

    def test_quadros_tem_sigla_e_medidores(self):
        siglas = {chave: dados["descricao"] for chave, dados in simbolos.CATALOGO.items()
                  if dados["categoria"] == simbolos.QUADRO}
        self.assertEqual(siglas, {"quadro_distribuicao": "QD", "quadro_comando": "QC",
                                  "quadro_medicao": "QM", "medicao_agrupada": "CM"})
        self.assertEqual(simbolos.CATALOGO["quadro_medicao"]["medidores"], 1)
        self.assertGreater(simbolos.CATALOGO["medicao_agrupada"]["medidores"], 1)
        self.assertNotIn("medidores", simbolos.CATALOGO["quadro_distribuicao"])

    def test_geometria_escala_com_o_tamanho(self):
        self.assertEqual(simbolos.geometria("luz_teto", 200)[0], ("circulo", 0, 0, 100.0))
        # Os ângulos do arco não mudam com a escala.
        self.assertEqual(simbolos.geometria("arandela", 200)[0], ("arco", 0, 0, 100.0, 0, 180))

    def test_tomadas_se_distinguem_pela_hachura(self):
        baixa, media, alta = (len(simbolos.geometria(f"tomada_{t}")) for t in ("baixa", "media", "alta"))
        self.assertEqual(baixa, 4)
        self.assertGreater(media, baixa)
        self.assertGreater(alta, baixa)

    def test_interruptores_tem_o_desenho_do_objeto_switch(self):
        simples = simbolos.geometria_interruptor("Simples", 200)
        self.assertEqual(simples, [("circulo", 0, 0, 80.0), ("linha", 80.0, 0, 120.0, 0)])  # raio 80, linha de 40
        self.assertEqual(len(simbolos.geometria_interruptor("Paralelo", 200)), 3)
        self.assertEqual(len(simbolos.geometria_interruptor("Intermediário", 200)), 4)
        self.assertEqual(simbolos.limites_de(simples), (-80.0, -80.0, 120.0, 80.0))
        self.assertEqual(set(simbolos.INTERRUPTORES), {"Simples", "Paralelo", "Intermediário"})

    def test_simbolo_desconhecido(self):
        with self.assertRaises(KeyError):
            simbolos.geometria("nao_existe")

    def test_todo_simbolo_tem_icone(self):
        pasta = os.path.join(ROOT, "freecad", "Circuits", "Resources", "Icons", "simbologia")
        for chave in simbolos.CATALOGO:
            self.assertTrue(os.path.exists(os.path.join(pasta, f"{chave}.svg")), chave)


if __name__ == "__main__":
    unittest.main(verbosity=2)
