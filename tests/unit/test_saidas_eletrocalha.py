"""Saídas de eletroduto nas eletrocalhas (core.pecas_eletroduto)."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import pecas_eletroduto as p

# eletrocalha de 300 mm ao longo de x, de 0 a 6 m, com a base a 2,60 m e aba de 100 mm
BANDEJA = {"nome": "B", "pontos": [(0, 0), (6000, 0)], "largura": 300.0, "aba": 100.0, "altura": 2600.0}


def eletroduto(nome, pontos, altura, tipo="Rígido"):
    return {"nome": nome, "pontos": pontos, "altura": altura, "tipo": tipo, "material": "PVC",
            "instalacao": p.TETO, "diametro": "3/4"}


class TestSaidas(unittest.TestCase):
    def test_na_altura_da_eletrocalha_sai_pela_lateral(self):
        s = p.saidas([eletroduto("E", [(2000, 150), (2000, 3000)], 2650)], [BANDEJA])
        self.assertEqual(len(s), 1)
        self.assertEqual((s[0]["tipo"], s[0]["x"], s[0]["y"], s[0]["bandeja"]), ("horizontal", 2000, 150, "B"))
        self.assertNotIn("descida", s[0])

    def test_abaixo_sai_pelo_fundo_com_descida(self):
        s = p.saidas([eletroduto("E", [(3000, 3000), (3000, 40)], 300)], [BANDEJA])
        self.assertEqual(s[0]["tipo"], "vertical")
        d = s[0]["descida"]
        self.assertEqual((d["x"], d["y"], d["de"], d["ate"]), (3000.0, 40.0, 300.0, 2600.0))
        self.assertTrue(d["bracos"][0]["curva"])
        self.assertAlmostEqual(d["bracos"][0]["uy"], 1.0)  # o eletroduto sai da ponta para +y

    def test_acima_desce_ate_o_topo_da_aba(self):
        d = p.saidas([eletroduto("E", [(3000, 3000), (3000, 0)], 3000)], [BANDEJA])[0]["descida"]
        self.assertEqual((d["de"], d["ate"]), (2700.0, 3000.0))

    def test_longe_da_eletrocalha_nao_e_saida(self):
        self.assertEqual(p.saidas([eletroduto("E", [(2000, 400), (2000, 3000)], 2650)], [BANDEJA]), [])

    def test_analisar_tira_o_aviso_e_conta_as_pecas(self):
        caminhos = [eletroduto("E", [(2000, 150), (2000, 3000)], 2650),
                    eletroduto("F", [(4000, 3000), (4000, 0)], 300)]
        r = p.analisar(caminhos, caixas=[(2000, 3000), (4000, 3000)], eletrocalhas=[BANDEJA])
        self.assertEqual(r["avisos"], [])
        self.assertEqual(r["pontas_soltas"], [])
        self.assertEqual(len(r["saidas"]), 2)
        self.assertEqual(len(r["descidas"]), 1)  # só a saída vertical
        itens = {(m["grupo"], m["item"]): m["quantidade"] for m in p.materiais(r)}
        self.assertEqual(itens[(p.GRUPO_BANDEJAS, p.SAIDA_HORIZONTAL)], 1)
        self.assertEqual(itens[(p.GRUPO_BANDEJAS, p.SAIDA_VERTICAL)], 1)
        self.assertEqual(itens[(p.GRUPO, p.CURVA_VERTICAL)], 1)
        self.assertEqual(sorted(t for _, _, t in p.marcas_de_saida(r)), ['SH Ø3/4"', 'SV Ø3/4"'])
        self.assertEqual(p.siglas(r), [])

    def test_sem_eletrocalha_a_ponta_continua_solta(self):
        r = p.analisar([eletroduto("E", [(2000, 150), (2000, 3000)], 2650)], caixas=[(2000, 3000)])
        self.assertEqual(len(r["avisos"]), 1)


class TestEncaixeNaEletrocalha(unittest.TestCase):
    def test_ponta_perto_vai_para_a_borda_ou_para_o_centro(self):
        caminhos = [eletroduto("E", [(2000, 3000), (2000, 300)], 2650),  # na altura: vai à borda (y = 150)
                    eletroduto("F", [(3000, 3000), (3000, 350)], 300),  # abaixo e fora: vai ao centro
                    eletroduto("G", [(4000, 3000), (4000, 100)], 300),  # abaixo e já sobre a eletrocalha: fica
                    eletroduto("H", [(5000, 3000), (5000, 900)], 2650)]  # longe: fica
        novos, movidas = p.encaixar_nas_bandejas(caminhos, [BANDEJA])
        self.assertEqual(movidas, 2)
        self.assertEqual([n[-1] for n in novos], [(2000, 150), (3000, 0), (4000, 100), (5000, 900)])


if __name__ == "__main__":
    unittest.main()
