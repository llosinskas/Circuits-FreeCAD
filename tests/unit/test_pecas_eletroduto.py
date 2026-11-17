"""Eletrodutos com a dinâmica das eletrocalhas: peças nos nós, caixas nas derivações, rótulos e materiais."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import pecas_eletroduto as regras


def eletroduto(pontos, tipo="Rígido", material="PVC", instalacao=regras.TETO, diametro="3/4", nome="E"):
    return {"pontos": pontos, "tipo": tipo, "material": material, "instalacao": instalacao, "diametro": diametro,
            "altura": 2800.0, "nome": nome}


def pecas(resultado):
    return sorted(p["peca"] for p in resultado["pecas"])


class TestPecas(unittest.TestCase):
    def test_rigido_tem_curva_pre_fabricada(self):
        r = regras.analisar([eletroduto([(0, 0), (3000, 0), (3000, 2000)])], caixas=[(0, 0), (3000, 2000)])
        self.assertIn("Curva 90°", pecas(r))
        r45 = regras.analisar([eletroduto([(0, 0), (2000, 0), (3000, 1000)])], caixas=[(0, 0), (3000, 1000)])
        self.assertIn("Curva 45°", pecas(r45))

    def test_flexivel_so_dobra(self):
        r = regras.analisar([eletroduto([(0, 0), (3000, 0), (3000, 2000)], tipo="Flexível")],
                            caixas=[(0, 0), (3000, 2000)])
        self.assertEqual(pecas(r), [])

    def test_bucha_e_arruela_em_cada_entrada_de_caixa_do_rigido(self):
        r = regras.analisar([eletroduto([(0, 0), (2000, 0)]), eletroduto([(2000, 0), (2000, 2000)], nome="F")],
                            caixas=[(0, 0), (2000, 0), (2000, 2000)])
        self.assertEqual(pecas(r).count(regras.BUCHA), 4)  # 2 eletrodutos, 2 pontas cada, todas em caixas

    def test_derivacao_embutida_sem_caixa_pede_caixa_de_passagem(self):
        r = regras.analisar([eletroduto([(0, 0), (6000, 0)]), eletroduto([(3000, 0), (3000, 2000)], nome="F")],
                            caixas=[(0, 0), (6000, 0), (3000, 2000)])
        self.assertEqual(r["caixas_novas"], [{"x": 3000.0, "y": 0.0, "diametro": "3/4"}])
        self.assertNotIn(regras.CONDULETE + " T", pecas(r))

    def test_derivacao_aparente_tem_condulete(self):
        aparente = dict(instalacao=regras.APARENTE)
        r = regras.analisar([eletroduto([(0, 0), (6000, 0)], **aparente),
                             eletroduto([(3000, 0), (3000, 2000)], nome="F", **aparente)],
                            caixas=[(0, 0), (6000, 0), (3000, 2000)])
        self.assertIn(regras.CONDULETE + " T", pecas(r))
        self.assertEqual(r["caixas_novas"], [])

    def test_derivacao_em_cima_de_caixa_nao_pede_nada(self):
        r = regras.analisar([eletroduto([(0, 0), (6000, 0)]), eletroduto([(3000, 0), (3000, 2000)], nome="F")],
                            caixas=[(0, 0), (6000, 0), (3000, 2000), (3000, 0)])
        self.assertEqual(r["caixas_novas"], [])

    def test_ponta_solta_vira_aviso(self):
        r = regras.analisar([eletroduto([(0, 0), (2000, 0)])], caixas=[(0, 0)])
        self.assertEqual(len(r["avisos"]), 1)
        self.assertIn("ponta solta", r["avisos"][0])

    def test_luvas_a_cada_barra_de_3_m_no_rigido(self):
        r = regras.analisar([eletroduto([(0, 0), (7000, 0)])], caixas=[(0, 0), (7000, 0)])
        self.assertEqual(pecas(r).count(regras.LUVA), 2)  # 7 m em 3 barras
        flex = regras.analisar([eletroduto([(0, 0), (7000, 0)], tipo="Flexível")], caixas=[(0, 0), (7000, 0)])
        self.assertEqual(pecas(flex), [])


class TestMateriais(unittest.TestCase):
    def test_pecas_e_abracadeiras_do_aparente(self):
        r = regras.analisar([eletroduto([(0, 0), (3000, 0), (3000, 3000)], instalacao=regras.APARENTE)],
                            caixas=[(0, 0), (3000, 3000)])
        itens = {(i["grupo"], i["item"], i["especificacao"]): i["quantidade"] for i in regras.materiais(r)}
        self.assertEqual(itens[("Eletrodutos", "Curva 90°", 'PVC rígido 3/4"')], 1)
        self.assertEqual(itens[("Eletrodutos", regras.BUCHA, 'PVC rígido 3/4"')], 2)
        # 2 trechos de 3 m: 3 abraçadeiras cada (a cada 1,5 m e uma na ponta)
        self.assertEqual(itens[("Fixação", "Abraçadeira tipo D", '3/4"')], 6)
        self.assertEqual(itens[("Fixação", "Parafuso com bucha de nylon", "para abraçadeira")], 6)

    def test_embutido_nao_tem_abracadeira(self):
        r = regras.analisar([eletroduto([(0, 0), (3000, 0)])], caixas=[(0, 0), (3000, 0)])
        self.assertFalse(any(i["grupo"] == "Fixação" for i in regras.materiais(r)))


class TestPlanta(unittest.TestCase):
    def test_rotulo_do_diametro_no_meio_do_trecho_mais_longo(self):
        (rotulo,) = regras.rotulos([eletroduto([(0, 0), (1000, 0), (1000, 5000)], diametro="1")])
        x, y, angulo, texto = rotulo
        self.assertEqual((texto, round(angulo)), ('Ø1"', 90))
        self.assertEqual(y, 2500.0)
        self.assertNotEqual(x, 1000.0)  # afastado da linha, para não ficar em cima dela

    def test_rotulo_foge_das_pecas_no_meio_do_trecho(self):
        (rotulo,) = regras.rotulos([eletroduto([(0, 0), (4000, 0)])], evitar=[(2000.0, 0.0)])
        self.assertEqual(rotulo[0], 1000.0)  # a 1/4 do trecho, longe do tê no meio

    def test_siglas_so_das_pecas_que_aparecem_na_planta(self):
        r = regras.analisar([eletroduto([(0, 0), (3000, 0), (3000, 2000)])], caixas=[(0, 0), (3000, 2000)])
        self.assertEqual([(round(x), round(y), s) for x, y, s in regras.siglas(r)], [(3000, 0, "C90")])

    def test_piso_e_tracejado(self):
        self.assertTrue(regras.tracejado(regras.PISO))
        self.assertFalse(regras.tracejado(regras.TETO))
        self.assertFalse(regras.tracejado(regras.APARENTE))

    def test_altura_padrao_pela_instalacao(self):
        self.assertEqual([regras.ALTURA_PADRAO[i] for i in (regras.TETO, regras.PISO, regras.APARENTE)],
                         [2800.0, -50.0, 2800.0])


if __name__ == "__main__":
    unittest.main()
