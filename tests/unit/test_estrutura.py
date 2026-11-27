"""Estrutura de pastas do projeto (core.estrutura)."""
import unittest

from freecad.Circuits.core import estrutura as e


class TestEstrutura(unittest.TestCase):
    def test_pasta_de_cada_objeto(self):
        self.assertEqual(e.pasta_de(["parametros_do_projeto"], "Spreadsheet::Sheet", "Parametros"), "planilhas")
        self.assertEqual(e.pasta_de(["quadro"], "Spreadsheet::Sheet", "QD1"), "planilhas")
        self.assertEqual(e.pasta_de(["quadro_origem"], "App::DocumentObjectGroup", "diagrama"), "diagramas")
        self.assertEqual(e.pasta_de(["multifilar_de"], "App::DocumentObjectGroup", "m"), "diagramas")
        self.assertEqual(e.pasta_de([], "App::DocumentObjectGroup", "Legenda_simbolos"), "documentos")
        self.assertEqual(e.pasta_de(["folha_circuits"], "TechDraw::DrawPage", "Page"), "folhas")
        self.assertIsNone(e.pasta_de([], "Part::Feature", "Box"))  # o que não é da bancada fica onde está
        self.assertIsNone(e.pasta_de(["quadro"], "App::FeaturePython", "X"))  # só planilhas vão para Planilhas
        self.assertIsNone(e.pasta_de([e.MARCA], "App::DocumentObjectGroup", "Planilhas"))  # as próprias pastas

    def test_poucas_pastas_de_saida(self):
        self.assertEqual(e.pastas_iniciais(), ["pavimentos", "planilhas"])
        self.assertEqual(e.pastas_iniciais(niveis_bim=True), ["planilhas"])
        self.assertLessEqual(len(e.PASTAS), 5)

    def test_pavimentos_mantem_o_nome_interno_antigo(self):
        self.assertEqual(e.PASTAS["pavimentos"][0], "Pontos_eletricos")
        self.assertNotIn("Pontos_eletricos", e.PASTAS_ANTIGAS)


if __name__ == "__main__":
    unittest.main()
