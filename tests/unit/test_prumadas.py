"""Prumadas verticais (core/prumadas.py): trechos, eletrodutos pela ocupação, esquema, planta e 3D."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import ocupacao
from freecad.Circuits.core import prumadas as p


def predio(andares=6, unidades=4):
    return [p.andar("Térreo", 0, 0)] + [p.andar(f"{i}º Pavimento", 3000 * i, unidades) for i in range(1, andares + 1)]


class TestDimensionar(unittest.TestCase):
    def test_trechos_levam_as_unidades_de_cima(self):
        r = p.dimensionar(predio())
        energia = r["sistemas"]["energia"]
        self.assertEqual([t["dutos"] for t in energia["trechos"]], [24, 20, 16, 12, 8, 4])  # um por unidade
        self.assertEqual(energia["trechos"][0]["cabos"], 24 * 4)
        self.assertEqual(energia["trechos"][0]["comprimento"], 3.0)
        self.assertEqual(len(energia["derivacoes"]), 6)
        # o eletroduto de cada alimentador comporta os 4 cabos de 16 mm² pela taxa de 40 %
        nominal = energia["trechos"][0]["nominal"]
        self.assertTrue(ocupacao.comporta(nominal, [ocupacao.diametro_do_cabo(16)] * 4))

    def test_dados_e_interfone_repartem_em_eletrodutos_do_tamanho_escolhido(self):
        r = p.dimensionar(predio())
        dados = r["sistemas"]["dados"]["trechos"]
        self.assertEqual(dados[0]["cabos"], 48)
        self.assertTrue(all(t["nominal"] == "1 1/2" for t in dados))
        self.assertGreater(dados[0]["dutos"], dados[-1]["dutos"])
        self.assertTrue(all(t["taxa"] <= ocupacao.TAXA_TRES_OU_MAIS + 1e-9 for t in dados))
        interfone = r["sistemas"]["interfone"]["trechos"]
        self.assertEqual(interfone[0]["cabos"], 24)

    def test_emergencia_vai_a_todos_os_andares(self):
        andares = predio(3) + [p.andar("Cobertura", 12000, 0)]
        r = p.dimensionar(andares)
        emergencia = r["sistemas"]["emergencia"]
        self.assertEqual(len(emergencia["trechos"]), 4)  # até a cobertura, mesmo sem unidades
        self.assertEqual(emergencia["trechos"][0]["nominal"], "3/4")
        self.assertEqual(len(r["sistemas"]["energia"]["trechos"]), 3)  # a energia para no último com unidades

    def test_energia_em_eletrocalha(self):
        r = p.dimensionar(predio(), {"forma_energia": "Eletrocalha"})
        larguras = [t["eletrocalha"] for t in r["sistemas"]["energia"]["trechos"]]
        self.assertEqual(larguras, sorted(larguras, reverse=True))
        self.assertTrue(all(t["taxa"] <= p.TAXA_ELETROCALHA + 1e-9 for t in r["sistemas"]["energia"]["trechos"]))
        self.assertIn("Eletrocalha", p.descricao_trecho(r["sistemas"]["energia"]["trechos"][0]))

    def test_sistemas_escolhidos_e_poucos_andares(self):
        r = p.dimensionar(predio(), {"sistemas": ["interfone", "dados"]})
        self.assertEqual(list(r["sistemas"]), ["dados", "interfone"])  # na ordem de ORDEM
        self.assertTrue(p.dimensionar([p.andar("Térreo", 0, 4)])["avisos"])

    def test_materiais(self):
        linhas = p.materiais(p.dimensionar(predio()))
        itens = {(l[0], l[1]): l[3] for l in linhas}
        energia = p.SISTEMAS["energia"][0]
        self.assertAlmostEqual(itens[(energia, 'Eletroduto rígido Ø1"')], (24 + 20 + 16 + 12 + 8 + 4) * 3.0)
        self.assertEqual(itens[(energia, "Caixa de passagem do andar")], 6)
        # cabo: 4 condutores × (altura até o andar + 3 m de folga) × unidades
        esperado = 4 * sum((3.0 * i + 3.0) * 4 for i in range(1, 7))
        self.assertAlmostEqual(itens[(energia, "Cabo 16 mm² 750 V")], esperado)
        self.assertIn((p.SISTEMAS["emergencia"][0], "Cabo 2,5 mm² 750 V"), itens)


class TestDesenhos(unittest.TestCase):
    def test_esquema_vertical(self):
        r = p.dimensionar(predio(3))
        e = p.esquema(r)
        textos = [t[2] for t in e["textos"]]
        self.assertIn("ESQUEMA VERTICAL DAS PRUMADAS", textos)
        for origem in ("Centro de medição", "DG de telecomunicações", "Central de portaria"):
            self.assertIn(origem, textos)
        self.assertIn("+3,00", textos)
        self.assertTrue(any(t.startswith('12 × Ø') for t in textos))  # energia no primeiro trecho
        self.assertEqual(sum(1 for t in textos if t == "4 unid."), 3)  # rótulo de cada andar
        for ap in ("AP1", "AP2", "AP3", "AP4"):  # uma seta por apartamento: 3 sistemas x 3 andares
            self.assertEqual(textos.count(ap), 9)

    def test_textos_do_esquema_nao_se_sobrepoem(self):
        e = p.esquema(p.dimensionar(predio(4)))

        def caixa(t):
            x, y, texto, altura, _ = t
            return x, y, x + len(texto) * altura * p.LARGURA_LETRA, y + altura
        caixas = [caixa(t) for t in e["textos"]]
        for i, (a0, b0, a1, b1) in enumerate(caixas):
            for c0, d0, c1, d1 in caixas[i + 1:]:
                self.assertFalse(a0 < c1 and c0 < a1 and b0 < d1 and d0 < b1, (e["textos"][i],))

    def test_leque_de_setas(self):
        linhas, textos = p.leque_de_setas(0.0, 0.0, 4, 700.0, 80.0)
        self.assertEqual([t[2] for t in textos], ["AP1", "AP2", "AP3", "AP4"])
        ys = [t[1] for t in textos]
        self.assertEqual(len(set(ys)), 4)
        self.assertEqual(len(linhas), 4 * 4)
        self.assertEqual([t[2] for t in p.leque_de_setas(0, 0, 40, 700, 80)[1]], ["AP1 a AP40"])
        self.assertEqual(p.leque_de_setas(0, 0, 0, 700, 80), ([], []))

    def test_simbolo_em_planta_com_apartamentos(self):
        r = p.dimensionar(predio(3))
        andar = p.simbolo_planta(r, 2)
        self.assertEqual([t[2] for t in andar["textos"] if t[2].startswith("AP")], ["AP1", "AP2", "AP3", "AP4"])
        self.assertFalse([t for t in p.simbolo_planta(r, 0)["textos"] if t[2].startswith("AP")])  # origem

    def test_simbolo_em_planta_por_andar(self):
        r = p.dimensionar(predio(3))
        base, meio, topo = (p.simbolo_planta(r, i) for i in (0, 2, 3))
        self.assertEqual(len(base["circulos"]), 4)
        self.assertTrue(any(t[2].endswith("sobe") for t in base["textos"]))
        self.assertTrue(any(t[2].endswith("passa") for t in meio["textos"]))
        self.assertTrue(any(t[2].endswith("chega") for t in topo["textos"]))
        self.assertEqual(p.simbolo_planta(r, 9)["circulos"], [])

    def test_pecas_3d(self):
        r = p.dimensionar(predio(2))
        pecas = p.pecas_3d(r)
        dutos = [x for x in pecas if x["tipo"] == "eletroduto" and x["cor_tipo"] == "energia"]
        self.assertEqual(len(dutos), 8 + 4)
        self.assertTrue(all(x["eixo"] == (0.0, 0.0, 1.0) and x["comprimento"] == 3000.0 for x in dutos))
        caixas = [x for x in pecas if x["tipo"] == "caixa"]
        self.assertEqual(len(caixas), 4 * 2)
        self.assertEqual(caixas[0]["origem"][2], 3000.0 + p.ALTURA_CAIXA_MM)
        xs = sorted({x["origem"][0] for x in caixas})
        self.assertEqual(len(xs), 4)  # um sistema ao lado do outro


if __name__ == "__main__":
    unittest.main()


class TestSimboloGirado(unittest.TestCase):
    def setUp(self):
        from freecad.Circuits.core import prumadas as p
        self.p = p
        andares = [p.andar("Térreo", 0, 0), p.andar("1º", 3000, 4), p.andar("2º", 6000, 4)]
        self.r = p.dimensionar(andares, {})

    def test_sem_rotacao_so_desloca(self):
        base = self.p.simbolo_planta(self.r, 0)
        girado = self.p.simbolo_girado(self.r, 0, 0.0)
        dx, dy = self.p.AFASTAMENTO_SIMBOLO_MM
        self.assertAlmostEqual(girado["circulos"][0][0], base["circulos"][0][0] + dx)
        self.assertAlmostEqual(girado["circulos"][0][1], base["circulos"][0][1] + dy)

    def test_noventa_graus_gira_o_afastamento_e_os_circulos(self):
        girado = self.p.simbolo_girado(self.r, 0, 90.0)
        dx, dy = self.p.AFASTAMENTO_SIMBOLO_MM
        x, y, _ = girado["circulos"][0]
        self.assertAlmostEqual(x, -dy, places=6)
        self.assertAlmostEqual(y, dx, places=6)
        segundo = girado["circulos"][1]
        self.assertAlmostEqual(segundo[0], x, places=6)  # o próximo sistema vai para +y
        self.assertGreater(segundo[1], y)
        self.assertTrue(all(abs(t[4] - 90.0) < 1e-9 for t in girado["textos"]))

    def test_texto_nunca_de_cabeca_para_baixo(self):
        for angulo in (135.0, 180.0, 225.0, -120.0):
            for t in self.p.simbolo_girado(self.r, 0, angulo)["textos"]:
                self.assertTrue(-90.0 <= t[4] <= 90.0, (angulo, t[4]))

    def test_texto_virado_ocupa_o_mesmo_lugar(self):
        desenho = {"linhas": [], "circulos": [], "textos": [(0.0, 0.0, "ABCD", 10.0, 0.0)], "limites": (0, 0, 1, 1)}
        x, y, _, _, angulo = self.p.girar(desenho, 180.0)["textos"][0]
        self.assertAlmostEqual(angulo, 0.0)
        self.assertAlmostEqual(x, -4 * 10.0 * self.p.LARGURA_LETRA)
        self.assertAlmostEqual(y, -10.0)
