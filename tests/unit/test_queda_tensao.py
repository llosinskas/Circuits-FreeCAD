import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import nbr5410
from freecad.Circuits.core.functions.Cabo.queda_tensao import seccao_minima_queda_monofasica


class TestSecaoMinimaQuedaMonofasica(unittest.TestCase):
    # S = 2·ρ·Σ(I·L) / ΔV = 200·ρ·Σ(I·L) / (V·ΔV%) = 7,25 mm²; o "10 mm²" do teste original é a
    # seção comercial logo acima, não o resultado da fórmula.
    def test_seccao_minima_queda_monofasica(self):
        correntes = [7.9, 26.0, 28.8, 11.9, 28.8]  # A
        comprimentos = [8, 18, 24, 38, 49]  # m
        resistividade = 1 / 56  # Ω.mm²/m (cobre)
        tensao = 380  # V
        queda_max_tensao = 4  # %
        soma = sum(i * l for i, l in zip(correntes, comprimentos))
        seccao_esperada = 200 * resistividade * soma / (tensao * queda_max_tensao)  # 7,25 mm²

        seccao_calculada = seccao_minima_queda_monofasica(
            correntes=correntes,
            comprimentos=comprimentos,
            resistividade=resistividade,
            tensao=tensao,
            queda_max_tensao=queda_max_tensao,
        )
        self.assertAlmostEqual(seccao_calculada, seccao_esperada, places=6)
        self.assertAlmostEqual(seccao_calculada, 7.25, places=2)
        self.assertEqual(nbr5410.secao_comercial(seccao_calculada), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
