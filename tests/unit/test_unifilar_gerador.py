"""Diagrama da transferência rede/gerador (core.unifilar.transferencia)."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import unifilar
from freecad.Circuits.core.functions.Predial import gerador

H = 10.0


def _resumo():
    return dict(gerador.resumo(gerador.dimensionar([gerador.carga("QGBT", potencia=100)], comprimento=40)))


class TestTransferencia(unittest.TestCase):
    def setUp(self):
        self.forma = unifilar.transferencia(_resumo(), ["QGBT", "Bombas"], H)
        self.textos = [t for _, _, t, _ in self.forma["textos"]]

    def test_rede_e_gerador_com_disjuntor_e_contator_chegam_na_barra(self):
        # dois disjuntores (4 terminais) e o círculo do gerador
        self.assertEqual(len(self.forma["circulos"]), 5)
        barra = [l for l in self.forma["linhas"] if l[0] == l[2] == 9 * H]
        self.assertEqual(barra, [(9 * H, 0.0, 9 * H, -4 * H)])
        contatos = [l for l in self.forma["linhas"] if l[:2] in ((6 * H, 0.0), (6 * H, -4 * H)) and l[3] != l[1]]
        self.assertEqual(len(contatos), 2)  # K1 e K2 abertos

    def test_textos_do_gerador_qta_cabos_e_cargas(self):
        for esperado in ("Rede 380 V", "QTA 320 A", "K1", "K2", "GMG 180 kVA", "144 kW · 380 V",
                         "Fases: 1 x 150 mm²", "Cargas do gerador", "QGBT", "Bombas"):
            self.assertIn(esperado, self.textos)
        self.assertEqual(self.textos.count("320A"), 2)

    def test_sem_resultado_desenha_so_o_esquema(self):
        textos = [t for _, _, t, _ in unifilar.transferencia({}, [], H)["textos"]]
        self.assertIn("QTA", textos)
        self.assertNotIn("320A", textos)

    def test_lista_de_cargas_e_cortada(self):
        cargas = [f"Q{i}" for i in range(12)]
        textos = [t for _, _, t, _ in unifilar.transferencia({}, cargas, H)["textos"]]
        self.assertIn("e mais 4", textos)
        self.assertNotIn("Q8", textos)


if __name__ == "__main__":
    unittest.main()
