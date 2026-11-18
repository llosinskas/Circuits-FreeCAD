"""Prumadas: eletrodutos e eletrocalhas que passam pelo teto ou pelo piso para outro pavimento (core/verticais.py)."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import bandejas, pecas_eletroduto, verticais

PAVIMENTOS = {"Térreo": 0.0, "1º Pavimento": 3000.0, "2º Pavimento": 6000.0}


def ponta(pavimento, x=1000.0, y=2000.0, altura=2800.0, tipo="eletroduto", nome="E", **mais):
    dados = {"tipo": tipo, "x": x, "y": y, "pavimento": pavimento, "altura": altura, "nome": nome, "diametro": "1"}
    if tipo == "eletrocalha":
        dados.update(largura=200.0, aba=50.0, tipo_bandeja="eletrocalha_perfurada", angulo=0.0)
    dados.update(mais)
    return dados


def por_pavimento(itens):
    return {(i["pavimento"], i["nivel"]): i for i in itens}


class TestLigacao(unittest.TestCase):
    def test_pontas_empilhadas_viram_prumada_pelo_teto_e_pelo_piso(self):
        itens = verticais.ligacoes_entre_pavimentos(
            [ponta("Térreo", altura=2800.0), ponta("1º Pavimento", x=1040.0, altura=-50.0, nome="F")], PAVIMENTOS)
        p = por_pavimento(itens)
        terreo, primeiro = p[("Térreo", "teto")], p[("1º Pavimento", "piso")]
        self.assertEqual((terreo["sentido"], terreo["de"], terreo["ate"], terreo["destino"]), ("sobe", 2800.0, 2950.0,
                                                                                               "1º Pavimento"))
        self.assertEqual((primeiro["sentido"], primeiro["de"], primeiro["ate"], primeiro["destino"]),
                         ("desce", -200.0, -50.0, "Térreo"))
        self.assertEqual(len(itens), 2)

    def test_pavimento_do_meio_tem_passagem(self):
        itens = verticais.ligacoes_entre_pavimentos(
            [ponta("Térreo", altura=2800.0), ponta("2º Pavimento", altura=300.0, nome="F")], PAVIMENTOS)
        passa = por_pavimento(itens)[("1º Pavimento", "passa")]
        self.assertEqual((passa["sentido"], passa["de"], passa["ate"]), ("sobe_desce", -200.0, 3300.0))
        self.assertEqual((passa["origem"], passa["destino"]), ("Térreo", "2º Pavimento"))

    def test_pontas_longe_ou_no_mesmo_pavimento_nao_ligam(self):
        longe = [ponta("Térreo"), ponta("1º Pavimento", x=1500.0)]
        mesmo = [ponta("Térreo"), ponta("Térreo", x=1010.0)]
        self.assertEqual(verticais.ligacoes_entre_pavimentos(longe, PAVIMENTOS), [])
        self.assertEqual(verticais.ligacoes_entre_pavimentos(mesmo, PAVIMENTOS), [])

    def test_eletroduto_nao_liga_com_eletrocalha(self):
        pontas = [ponta("Térreo"), ponta("1º Pavimento", tipo="eletrocalha")]
        self.assertEqual(verticais.ligacoes_entre_pavimentos(pontas, PAVIMENTOS), [])

    def test_eletrocalha_entre_pavimentos(self):
        itens = verticais.ligacoes_entre_pavimentos(
            [ponta("Térreo", tipo="eletrocalha"), ponta("1º Pavimento", tipo="eletrocalha", altura=2800.0)], PAVIMENTOS)
        terreo = por_pavimento(itens)[("Térreo", "teto")]
        self.assertEqual((terreo["tipo"], terreo["largura"], terreo["ate"] - terreo["de"]), ("eletrocalha", 200.0, 3000.0))


class TestTextosESimbolos(unittest.TestCase):
    def setUp(self):
        itens = verticais.ligacoes_entre_pavimentos(
            [ponta("Térreo", altura=2800.0), ponta("2º Pavimento", altura=300.0, nome="F")], PAVIMENTOS)
        self.p = por_pavimento(itens)

    def test_textos_dizem_para_onde_vai(self):
        self.assertEqual(verticais.texto(self.p[("Térreo", "teto")]), 'Ø1" sobe ao 2º Pavimento 3,50 m')
        self.assertEqual(verticais.texto(self.p[("2º Pavimento", "piso")]), 'Ø1" desce ao Térreo 3,50 m')
        self.assertEqual(verticais.texto(self.p[("1º Pavimento", "passa")]), 'Ø1" passa (Térreo → 2º Pavimento)')

    def test_prumada_de_eletroduto_tem_circulo_duplo(self):
        no_pavimento = verticais.itens_de_eletroduto([], [{"x": 0, "y": 0, "de": 0.0, "ate": 2800.0, "diametro": "1"}])[0]
        self.assertEqual(len(verticais.simbolo(no_pavimento, 300)["circulos"]), 1)
        self.assertEqual(len(verticais.simbolo(self.p[("Térreo", "teto")], 300)["circulos"]), 2)

    def test_passagem_atravessa_o_circulo(self):
        s = verticais.simbolo(self.p[("1º Pavimento", "passa")], 300)
        maior = max(s["linhas"], key=lambda l: abs(l[2] - l[0]))
        self.assertLess(min(maior[0], maior[2]), 0)  # a linha começa do outro lado do círculo
        self.assertGreater(max(maior[0], maior[2]), 0)

    def test_prumada_de_eletrocalha_tem_x(self):
        itens = verticais.ligacoes_entre_pavimentos(
            [ponta("Térreo", tipo="eletrocalha"), ponta("1º Pavimento", tipo="eletrocalha")], PAVIMENTOS)
        s = verticais.simbolo(por_pavimento(itens)[("Térreo", "teto")], 300)
        diagonais = [l for l in s["linhas"][4:6]]
        # as duas diagonais da seção (X): uma sai da esquerda, a outra da direita, e cruzam a largura toda
        self.assertEqual(sorted(round(l[0]) for l in diagonais), [-25, 25])
        self.assertTrue(all({round(l[1]), round(l[3])} == {-100, 100} for l in diagonais))


class TestLegenda(unittest.TestCase):
    def test_um_item_por_tipo_usado_na_ordem_fixa(self):
        itens = verticais.ligacoes_entre_pavimentos(
            [ponta("Térreo", altura=2800.0), ponta("2º Pavimento", altura=300.0, nome="F")], PAVIMENTOS)
        itens += verticais.itens_de_eletroduto([], [{"x": 0, "y": 0, "de": 0.0, "ate": 2800.0, "diametro": "1"}])
        legenda = verticais.itens_de_legenda(itens + itens, 300)  # repetidos não duplicam
        self.assertEqual([chave for chave, _, _ in legenda],
                         ["vertical_eletroduto_pavimento_sobe_desce", "vertical_eletroduto_teto",
                          "vertical_eletroduto_piso", "vertical_eletroduto_passa"])
        chave, primitivas, texto = legenda[1]
        self.assertTrue(all(p[0] in ("linha", "circulo") for p in primitivas))
        self.assertIn("pavimento de cima", texto)


class TestDetalheEQuantidade(unittest.TestCase):
    def setUp(self):
        self.itens = verticais.ligacoes_entre_pavimentos(
            [ponta("Térreo", altura=2800.0), ponta("1º Pavimento", altura=300.0, nome="F")], PAVIMENTOS)

    def test_prumada_vira_um_detalhe_so(self):
        (detalhe,) = verticais.detalhes(self.itens)
        self.assertEqual((detalhe["nivel"], detalhe["pavimento"]), ("teto", "Térreo"))

    def test_detalhe_da_prumada_mostra_os_dois_pisos(self):
        (detalhe,) = verticais.detalhes(self.itens)
        g = verticais.geometria_detalhe(detalhe, pe_direito=3000.0)
        textos = [t[2] for t in g["textos"]]
        self.assertIn("piso Térreo", textos)
        self.assertIn("piso 1º Pavimento", textos)
        self.assertIn("+3,30", textos)  # 3000 + 300 a partir do piso de baixo

    def test_detalhe_mostra_o_piso_atravessado_e_o_titulo_acima_de_tudo(self):
        itens = verticais.ligacoes_entre_pavimentos(
            [ponta("Térreo", altura=2800.0), ponta("2º Pavimento", altura=300.0, nome="F")], PAVIMENTOS)
        (detalhe,) = verticais.detalhes(itens)
        g = verticais.geometria_detalhe(detalhe, pe_direito=3000.0)
        textos = {t[2]: t for t in g["textos"]}
        self.assertIn("piso 1º Pavimento", textos)  # o pavimento do meio, que a prumada atravessa
        self.assertIn(3000.0, [l[1] for l in g["linhas"] if l[1] == l[3] and abs(l[2] - l[0]) >= 1500])
        titulo = next(t for t in g["textos"] if t[2].startswith("V1"))
        self.assertGreater(titulo[1], 6300.0)  # acima do trecho que chega a +6,30

    def test_quantidade_conta_cada_prumada_uma_vez(self):
        eletrodutos_v, componentes = verticais.materiais_prumadas(self.itens)
        self.assertEqual(len(eletrodutos_v), 1)
        self.assertAlmostEqual(eletrodutos_v[0]["comprimento"], 0.5)  # de +2,80 a +3,30
        self.assertEqual((eletrodutos_v[0]["diametro"], eletrodutos_v[0]["pavimento"]), ("1", "Térreo"))
        self.assertEqual(componentes, [])

    def test_quantidade_da_prumada_de_eletrocalha(self):
        itens = verticais.ligacoes_entre_pavimentos(
            [ponta("Térreo", tipo="eletrocalha"), ponta("1º Pavimento", tipo="eletrocalha")], PAVIMENTOS)
        eletrodutos_v, componentes = verticais.materiais_prumadas(itens)
        nomes = {(c["item"], c["quantidade"]) for c in componentes}
        self.assertEqual(eletrodutos_v, [])
        self.assertIn((bandejas.CURVA_VERTICAL_INTERNA, 1), nomes)
        self.assertIn((bandejas.CURVA_VERTICAL_EXTERNA, 1), nomes)
        metros = next(c for c in componentes if c["unidade"] == "m")
        self.assertAlmostEqual(metros["quantidade"], 3.0 * (1 + bandejas.PERDA_BANDEJA), places=2)


class TestPontasSoltas(unittest.TestCase):
    def test_eletroduto_informa_as_pontas_soltas(self):
        r = pecas_eletroduto.analisar([{"pontos": [(0, 0), (2000, 0)], "tipo": "Rígido", "material": "PVC",
                                        "instalacao": pecas_eletroduto.TETO, "diametro": "3/4", "altura": 2800.0,
                                        "nome": "E"}], caixas=[(0, 0)])
        self.assertEqual(r["pontas_soltas"], [{"x": 2000.0, "y": 0.0, "diametro": "3/4", "altura": 2800.0,
                                               "nome": "E"}])

    def test_terminal_que_vira_prumada_nao_conta_como_terminal(self):
        r = bandejas.analisar([{"pontos": [(0, 0), (3000, 0)], "tipo": "eletrocalha_perfurada", "largura": 200,
                                "aba": 50, "altura": 2800.0, "tampa": False, "nome": "B"}])
        sem = {i["item"]: i["quantidade"] for i in bandejas.materiais(r, sem_terminal=[(3000.0, 0.0)])}
        com = {i["item"]: i["quantidade"] for i in bandejas.materiais(r)}
        self.assertEqual((com[bandejas.TERMINAL], sem[bandejas.TERMINAL]), (2, 1))


if __name__ == "__main__":
    unittest.main()
