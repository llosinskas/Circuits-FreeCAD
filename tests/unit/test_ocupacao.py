"""Eletroduto pela taxa de ocupação (core/ocupacao.py) e roteamento dos cabos pela rede (core/rede.py).

NBR 5410, 6.2.11.1.6: no máximo 53 % da seção interna com um cabo, 31 % com dois e
40 % com três ou mais. Os diâmetros internos dos eletrodutos vêm do catálogo e são
passados como argumento.
"""
import math
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import ocupacao, rede

INTERNOS = {"1/2": 16.0, "3/4": 21.0, "1": 26.6, "1 1/4": 35.0}


class Base(unittest.TestCase):
    def setUp(self):
        self.o = ocupacao


class TestTaxa(Base):
    def test_taxa_pelo_numero_de_cabos(self):
        self.assertEqual([self.o.taxa_maxima(n) for n in (1, 2, 3, 10)], [0.53, 0.31, 0.40, 0.40])

    def test_sem_cabos_e_erro(self):
        with self.assertRaises(ValueError):
            self.o.taxa_maxima(0)


class TestEletroduto(Base):
    def test_area_do_cabo_pelo_diametro_externo(self):
        self.assertAlmostEqual(self.o.area_cabo(5.0), math.pi * 25 / 4)

    def test_menor_eletroduto_que_comporta_os_cabos(self):
        # 10 cabos de 5 mm: 196,3 mm²; com 40 %, precisa de 490,9 mm² internos (d ≥ 25 mm)
        self.assertEqual(self.o.eletroduto_minimo([5.0] * 10, INTERNOS), "1")

    def test_poucos_cabos_cabem_no_menor(self):
        self.assertEqual(self.o.eletroduto_minimo([3.6] * 3, INTERNOS), "1/2")

    def test_dois_cabos_usam_31_por_cento(self):
        # 2 cabos de 8 mm: 100,5 mm²; com 31 %, 324,3 mm² (d ≥ 20,3 mm)
        self.assertEqual(self.o.eletroduto_minimo([8.0, 8.0], INTERNOS), "3/4")

    def test_nenhum_comporta(self):
        self.assertIsNone(self.o.eletroduto_minimo([10.0] * 20, INTERNOS))

    def test_aviso_quando_o_desenhado_e_menor(self):
        self.assertTrue(self.o.eletroduto_pequeno("3/4", [5.0] * 10, INTERNOS))
        self.assertFalse(self.o.eletroduto_pequeno("1 1/4", [5.0] * 10, INTERNOS))


def caminho(nome, *pontos, altura=2800.0, diametro="3/4", **extra):
    return dict({"pontos": list(pontos), "altura": altura, "diametro": diametro, "nome": nome}, **extra)


def caixa(id_, x, y, altura=300.0, tipo="ponto", circuito="", comando=""):
    return {"id": id_, "nome": id_, "x": x, "y": y, "altura": altura, "tipo": tipo, "circuito": circuito,
            "comando": comando, "quadro": "", "pavimento": "", "refs": {id_}}


def info(secao=2.5, fases=1):
    return lambda quadro, numero, membros: {"secao": secao, "fases": fases, "neutro": True, "terra": True}


class TestTabelas(Base):
    def test_diametro_do_cabo_pela_secao(self):
        self.assertEqual(self.o.diametro_do_cabo(2.5), 3.6)
        self.assertEqual(self.o.diametro_do_cabo(3.0), self.o.DIAMETRO_CABO[4.0])  # a próxima maior

    def test_flexivel_tem_secao_livre_menor(self):
        flexivel, rigido = self.o.internos_do_tipo("Flexível"), self.o.internos_do_tipo("Rígido")
        self.assertLess(flexivel["3/4"], rigido["3/4"])
        self.assertEqual(flexivel["2"], rigido["2"])  # acima do corrugado, vale o rígido

    def test_nominais_iguais_aos_do_eletroduto_desenhado(self):
        from freecad.Circuits.core.tables.eletrodutos import DIAMETROS_EXTERNOS
        self.assertEqual(set(self.o.DIAMETROS_INTERNOS), set(DIAMETROS_EXTERNOS))


class TestVerificar(Base):
    def trecho(self, n, secao=2.5, comprimento=2.0, circuito="C1"):
        return {"comprimento": comprimento,
                "condutores": [{"secao": secao, "funcao": "fase", "circuito": circuito}] * n}

    def test_trecho_mais_cheio_decide(self):
        r = self.o.verificar_eletroduto("E1", "1/2", "Rígido", [self.trecho(3), self.trecho(12, circuito="C2")])
        self.assertEqual(r["cabos"], 12)
        self.assertTrue(r["pequeno"])
        self.assertEqual(r["minimo"], "3/4")
        self.assertEqual(r["circuitos"], ["C1", "C2"])
        self.assertEqual(r["comprimento"], 4.0)
        self.assertTrue(r["avisos"][0].endswith("use Ø3/4\"."))

    def test_sem_cabos_nao_reprova(self):
        r = self.o.verificar_eletroduto("E1", "3/4", "Flexível", [{"comprimento": 1.0, "condutores": []}])
        self.assertEqual((r["cabos"], r["pequeno"], r["minimo"], r["avisos"]), (0, False, None, []))

    def test_bandeja_so_informa(self):
        r = self.o.verificar_bandeja("B1", 100, 50, [self.trecho(10, secao=16)])
        self.assertAlmostEqual(r["camada_unica"], 75.0)
        self.assertFalse(r["acima_referencia"])
        self.assertTrue(self.o.verificar_bandeja("B1", 50, 25, [self.trecho(20, secao=16)])["acima_referencia"])

    def test_tabela_poe_os_pequenos_primeiro(self):
        ok = self.o.verificar_eletroduto("A", "1", "Rígido", [self.trecho(3)])
        pequeno = self.o.verificar_eletroduto("B", "1/2", "Rígido", [self.trecho(12)])
        linhas = self.o.tabela([ok, pequeno], [self.o.verificar_bandeja("C", 100, 50, [self.trecho(4)])])
        self.assertEqual(linhas[0], self.o.CABECALHO)
        self.assertEqual([l[0] for l in linhas[1:]], ["B", "A", "C"])
        self.assertEqual(linhas[1][-1], "aumentar para 3/4")
        self.assertEqual(linhas[2][-1], "ok")


class TestRoteamento(unittest.TestCase):
    """Os cabos de cada circuito são seguidos pelos eletrodutos e eletrocalhas até o quadro."""

    def test_condutores_por_trecho_e_rota(self):
        caminhos = [caminho("E1", (0, 0), (3000, 0)), caminho("E2", (3000, 0), (3000, 2000)),
                    caminho("E3", (3000, 0), (6000, 0))]
        caixas = [caixa("QD", 0, 0, 1500, tipo="quadro"), caixa("T1", 3000, 2000, circuito="1"),
                  caixa("T2", 6000, 0, circuito="2")]
        r = rede.analisar(caminhos, caixas, info())
        por_dono = ocupacao.agrupar_trechos(r["trechos"])
        e1 = por_dono[("eletroduto", "E1")][0]["condutores"]
        self.assertEqual(len(e1), 6)  # F+N+T de dois circuitos
        self.assertEqual({c["circuito"] for c in e1}, {"C1", "C2"})
        self.assertEqual(len(por_dono[("eletroduto", "E2")][0]["condutores"]), 3)
        rota = next(x for x in r["rotas"] if x["circuito"] == "1")
        self.assertEqual(rota["infraestrutura"], [("E1", "eletroduto"), ("E2", "eletroduto")])
        self.assertEqual(rota["por_ponto"]["T1"], [("E1", "eletroduto"), ("E2", "eletroduto")])

    def test_retornos_entram_no_trecho(self):
        caminhos = [caminho("E1", (0, 0), (2000, 0)), caminho("E2", (2000, 0), (2000, 1500))]
        caixas = [caixa("QD", 0, 0, 1500, tipo="quadro"), caixa("L1", 2000, 0, 2800, circuito="1", comando="a"),
                  caixa("S1", 2000, 1500, 1100, tipo="interruptor", circuito="1", comando="a")]
        r = rede.analisar(caminhos, caixas, info(secao=1.5))
        e2 = ocupacao.agrupar_trechos(r["trechos"])[("eletroduto", "E2")][0]["condutores"]
        self.assertEqual(sorted(c["funcao"] for c in e2), ["fase", "retorno"])

    def test_cabo_passa_pela_eletrocalha(self):
        # o eletroduto do quadro e o do ponto param na borda da eletrocalha (300 mm de largura)
        caminhos = [caminho("E1", (0, 0), (0, 850)),
                    caminho("B1", (-1000, 1000), (6000, 1000), altura=3000, diametro="", largura=300.0),
                    caminho("E2", (5000, 1150), (5000, 3000))]
        caixas = [caixa("QD", 0, 0, 1500, tipo="quadro"), caixa("T1", 5000, 3000, circuito="1")]
        r = rede.analisar(caminhos, caixas, info())
        rota = r["rotas"][0]["infraestrutura"]
        self.assertEqual(rota, [("E1", "eletroduto"), ("B1", "bandeja"), ("E2", "eletroduto")])
        bandeja = ocupacao.agrupar_trechos(r["trechos"])[("bandeja", "B1")]
        self.assertTrue(any(len(t["condutores"]) == 3 for t in bandeja))
        self.assertEqual(r["avisos"], [])

    def test_sem_nome_os_resultados_antigos_nao_mudam(self):
        sem = [{"pontos": [(0, 0), (3000, 0)], "altura": 2800.0, "diametro": "3/4"}]
        com = [caminho("E1", (0, 0), (3000, 0))]
        caixas = [caixa("QD", 0, 0, 1500, tipo="quadro"), caixa("T1", 3000, 0, circuito="1")]
        a, b = rede.analisar(sem, caixas, info()), rede.analisar(com, caixas, info())
        self.assertEqual((a["fios"], a["circuitos"]), (b["fios"], b["circuitos"]))
        self.assertEqual(a["trechos"], [])
        self.assertEqual(a["rotas"][0]["infraestrutura"], [])

    def test_juntar_leva_trechos_e_rotas_com_o_pavimento(self):
        r = rede.analisar([caminho("E1", (0, 0), (3000, 0))],
                          [caixa("QD", 0, 0, 1500, tipo="quadro"), caixa("T1", 3000, 0, circuito="1")], info())
        r["pavimento"] = "Térreo"
        total = rede.juntar([r])
        self.assertEqual(total["trechos"][0]["pavimento"], "Térreo")
        self.assertEqual(total["rotas"][0]["pavimento"], "Térreo")


if __name__ == "__main__":
    unittest.main()
