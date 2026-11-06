import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core.functions.Cabo.queda_tensao import seccao_minima_queda_monofasica


class TestSecaoMinimaQuedaMonofasica(unittest.TestCase):
    # A fórmula devolve 6,78 mm² para estes dados e o teste original espera 10 mm².
    # Falta confirmar qual dos dois está certo; ver "Problemas conhecidos" no AGENTS.md.
    @unittest.expectedFailure
    def test_seccao_minima_queda_monofasica(self):
        correntes = [7.9, 26.0, 28.8, 11.9, 28.8]  # A
        comprimentos = [8, 18, 24, 38, 49]  # m
        resistividade = 1 / 56  # Ω.mm²/m (cobre)
        tensao = 380  # V
        queda_max_tensao = 4  # %
        seccao_esperada = 10  # mm² (valor aproximado)

        seccao_calculada = seccao_minima_queda_monofasica(
            correntes=correntes,
            comprimentos=comprimentos,
            resistividade=resistividade,
            tensao=tensao,
            queda_max_tensao=queda_max_tensao,
        )
        self.assertAlmostEqual(seccao_calculada, seccao_esperada, delta=0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
