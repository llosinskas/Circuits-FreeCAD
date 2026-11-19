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


class TestPecaDeSaida3D(unittest.TestCase):
    def test_horizontal_flange_na_aba_e_luva_para_fora(self):
        s = p.saidas([eletroduto("E", [(2000, 150), (2000, 3000)], 2650)], [BANDEJA])[0]
        self.assertEqual((s["normal"], s["z"]), ((-0.0, 1.0), 2650.0))
        placa, luva, anel = p.solidos_da_saida(s)
        self.assertEqual(placa[0], "placa")
        self.assertAlmostEqual(placa[1][1], 150 + p.ESPESSURA_FLANGE_MM / 2)  # do lado de fora da aba
        self.assertEqual(placa[2], (-0.0, 1.0, 0.0))
        self.assertAlmostEqual(placa[3], 26.9 + 2 * p.ABA_FLANGE_MM)  # 3/4": 26,9 mm externo
        self.assertEqual((luva[0], luva[2]), ("cilindro", (-0.0, 1.0, 0.0)))
        self.assertAlmostEqual(luva[3], 26.9 / 2 + p.FOLGA_LUVA_MM)
        self.assertAlmostEqual(anel[1][1] + anel[4], luva[1][1] + luva[4])  # o anel fecha a ponta da luva
        self.assertGreater(anel[3], luva[3])

    def test_vertical_embaixo_do_fundo_para_baixo(self):
        s = p.saidas([eletroduto("E", [(3000, 3000), (3000, 40)], 300)], [BANDEJA])[0]
        self.assertEqual((s["z"], s["sentido"]), (2600.0, -1.0))
        placa, luva, _ = p.solidos_da_saida(s)
        self.assertEqual(placa[2], (0.0, 0.0, -1.0))
        self.assertAlmostEqual(placa[1][2], 2600 - p.ESPESSURA_FLANGE_MM / 2)
        self.assertEqual(luva[1][:2], (3000.0, 40.0))

    def test_vertical_de_cima_sobre_a_aba(self):
        s = p.saidas([eletroduto("E", [(3000, 3000), (3000, 0)], 3000)], [BANDEJA])[0]
        self.assertEqual((s["z"], s["sentido"]), (2700.0, 1.0))
        self.assertEqual(p.solidos_da_saida(s)[1][2], (0.0, 0.0, 1.0))


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
