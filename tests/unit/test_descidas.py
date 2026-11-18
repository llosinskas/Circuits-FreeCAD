"""Descidas entre eletrodutos de alturas diferentes (core.pecas_eletroduto)."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import pecas_eletroduto as p


def caminho(nome, pontos, altura, tipo="Rígido", diametro="3/4", instalacao=p.TETO):
    return {"nome": nome, "pontos": pontos, "altura": altura, "tipo": tipo, "material": "PVC",
            "instalacao": instalacao, "diametro": diametro}


class TestDescidas(unittest.TestCase):
    def test_teto_para_piso_faz_descida_com_duas_curvas(self):
        r = p.analisar([caminho("A", [(0, 0), (3000, 0)], 2800),
                        caminho("B", [(3000, 0), (3000, 2000)], -50, instalacao=p.PISO)])
        self.assertEqual(len(r["descidas"]), 1)
        d = r["descidas"][0]
        self.assertEqual((d["x"], d["y"], d["de"], d["ate"]), (3000, 0, -50, 2800))
        self.assertAlmostEqual(d["raio"], p.raio_da_curva("3/4", "Rígido"), places=1)  # 6 × 13,45 mm
        bracos = {b["nome"]: b for b in d["bracos"]}
        self.assertTrue(bracos["A"]["curva"] and bracos["B"]["curva"])
        self.assertEqual((bracos["A"]["ponta"], bracos["B"]["ponta"]), ("fim", "inicio"))
        self.assertAlmostEqual(bracos["A"]["ux"], -1.0)  # A sai do nó para trás (−x)
        self.assertAlmostEqual(bracos["B"]["uy"], 1.0)
        curvas = [x for x in r["pecas"] if x["peca"] == p.CURVA_VERTICAL]
        self.assertEqual(len(curvas), 2)
        self.assertFalse([x for x in r["pecas"] if x["peca"] in (p.LUVA,) or x["peca"].startswith("Curva 90°") and
                          x["peca"] != p.CURVA_VERTICAL])  # nada de luva ou curva horizontal no nó
        self.assertEqual(p.siglas(r), [])  # a descida tem o símbolo próprio, não sigla

    def test_mesma_altura_nao_e_descida(self):
        r = p.analisar([caminho("A", [(0, 0), (3000, 0)], 2800), caminho("B", [(3000, 0), (6000, 0)], 2805)])
        self.assertEqual(r["descidas"], [])

    def test_flexivel_nao_tem_peca_e_tem_raio_maior(self):
        r = p.analisar([caminho("A", [(0, 0), (3000, 0)], 2800, "Flexível"),
                        caminho("B", [(3000, 0), (3000, 3000)], 300, "Flexível")])
        d = r["descidas"][0]
        self.assertGreater(d["raio"], p.raio_da_curva("3/4", "Rígido"))
        self.assertFalse([x for x in r["pecas"] if x["peca"] == p.CURVA_VERTICAL])

    def test_raio_cabe_na_vertical_curta_e_no_trecho(self):
        r = p.analisar([caminho("A", [(0, 0), (3000, 0)], 2800, diametro="2"),
                        caminho("B", [(3000, 0), (3000, 100)], 2700, diametro="2")])
        d = r["descidas"][0]
        self.assertLessEqual(d["raio"], 50.0)  # 100 mm de vertical para duas curvas
        self.assertLessEqual(d["raio"], 0.9 * 100)

    def test_derivacao_sem_curva_no_eletroduto_que_passa(self):
        # A passa pelo nó no teto; B desce dele para o piso
        r = p.analisar([caminho("A", [(0, 0), (3000, 0), (6000, 0)], 2800, instalacao=p.APARENTE),
                        caminho("B", [(3000, 0), (3000, 2000)], -50)])
        d = r["descidas"][0]
        curvas = {b["nome"]: b["curva"] for b in d["bracos"]}
        self.assertEqual(curvas, {"A": False, "B": True})

    def test_caixa_no_no_nao_e_descida(self):
        r = p.analisar([caminho("A", [(0, 0), (3000, 0)], 2800), caminho("B", [(3000, 0), (3000, 2000)], -50)],
                       caixas=[(3000, 0)])
        self.assertEqual(r["descidas"], [])


if __name__ == "__main__":
    unittest.main()
