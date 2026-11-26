"""Altura de cada trecho do eletroduto e os lances de mesma altura (core/alturas.py)."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import alturas, pecas_eletroduto, rede

PONTOS = [(0, 0), (3000, 0), (3000, 2000), (6000, 2000)]


class TestAlturas(unittest.TestCase):
    def test_lista_vale_so_com_um_valor_por_trecho(self):
        self.assertEqual(alturas.alturas_dos_trechos(3, 2800, [2800, 300, 300]), [2800, 300, 300])
        self.assertEqual(alturas.alturas_dos_trechos(3, 2800, [1, 2]), [2800.0] * 3)
        self.assertEqual(alturas.alturas_dos_trechos(3, 2800), [2800.0] * 3)

    def test_lances_dividem_no_vertice_da_mudanca(self):
        lances = alturas.lances(PONTOS, [2800, 2800, 300])
        self.assertEqual([(l["pontos"], l["altura"], l["trechos"]) for l in lances], [
            ([(0, 0), (3000, 0), (3000, 2000)], 2800.0, (0, 1)),
            ([(3000, 2000), (6000, 2000)], 300.0, (2, 2)),
        ])
        self.assertEqual(len(alturas.lances(PONTOS, [2800, 2805, 2795])), 1)  # dentro da tolerância
        self.assertFalse(alturas.varias_alturas([2800, 2805]))
        self.assertTrue(alturas.varias_alturas([2800, 300]))

    def test_selecao_de_trechos_e_vertices(self):
        self.assertEqual(alturas.trechos_da_selecao(PONTOS), [0, 1, 2])
        self.assertEqual(alturas.trechos_da_selecao(PONTOS, arestas=[(3010, 1000)]), [1])
        self.assertEqual(alturas.trechos_da_selecao(PONTOS, vertices=[(3000, 2000)]), [2])
        self.assertEqual(alturas.trechos_da_selecao(PONTOS, vertices=[(3000, 2000)], sentido="inicio"), [0, 1])

    def test_trocar_so_o_lance_que_chega_no_no(self):
        novas = alturas.trocar_no_no(PONTOS, [2800, 2800, 300], 3000, 2000, 2800, 3000)
        self.assertEqual(novas, [3000.0, 3000.0, 300.0])
        self.assertEqual(alturas.trocar_no_no(PONTOS, [2800, 2800, 300], 0, 9000, 2800, 3000), [2800, 2800, 300])

    def test_rotulo_como_offset(self):
        self.assertEqual((alturas.rotulo(2800), alturas.rotulo(-50)), ("+2,80", "-0,05"))


class TestSobeNoMeio(unittest.TestCase):
    """O eletroduto que muda de altura num vértice sobe ali, como o offset do Revit."""

    def caminhos(self, alturas_):
        return [{"pontos": l["pontos"], "altura": l["altura"], "diametro": "3/4", "tipo": "Rígido", "nome": "E1"}
                for l in alturas.lances(PONTOS, alturas_)]

    def test_descida_com_duas_curvas_no_vertice(self):
        resultado = pecas_eletroduto.analisar(self.caminhos([2800, 2800, 300]))
        descida, = resultado["descidas"]
        self.assertEqual((descida["x"], descida["y"], descida["de"], descida["ate"]), (3000, 2000, 300.0, 2800.0))
        self.assertEqual(sum(1 for b in descida["bracos"] if b["curva"]), 2)
        self.assertEqual({b["nome"] for b in descida["bracos"]}, {"E1"})

    def test_vertical_nas_transicoes_da_rede(self):
        r = rede.analisar([{k: c[k] for k in ("pontos", "altura", "diametro")} for c in self.caminhos([2800, 2800, 300])],
                          [], lambda *a: None)
        self.assertEqual([(t["x"], t["y"], t["comprimento"]) for t in r["transicoes"]], [(3000, 2000, 2.5)])

    def test_rotulo_leva_a_altura_do_lance(self):
        caminhos = [dict(c, rotulo_altura=alturas.rotulo(c["altura"])) for c in self.caminhos([2800, 2800, 300])]
        textos = [t for *_, t in pecas_eletroduto.rotulos(caminhos)]
        self.assertEqual(textos, ['Ø3/4" +2,80', 'Ø3/4" +0,30'])


if __name__ == "__main__":
    unittest.main()
