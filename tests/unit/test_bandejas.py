"""Bandejas: conexões, suportes, materiais e o serviço com o FreeCAD simulado."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import bandejas as regras
from freecad.Circuits.core import quantitativos

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Spreadsheet")
RECARREGAR = ("freecad.Circuits.services.bandejas", "freecad.Circuits.services.pavimentos")


def caminho(pontos, tipo="eletrocalha_perfurada", largura=200, aba=50, altura=2800.0, tampa=False, nome="B"):
    return {"pontos": pontos, "tipo": tipo, "largura": largura, "aba": aba, "altura": altura, "tampa": tampa,
            "nome": nome}


def pecas(resultado):
    return sorted(c["peca"] for c in resultado["conexoes"])


class TestConexoes(unittest.TestCase):
    def test_reta_tem_dois_terminais(self):
        resultado = regras.analisar([caminho([(0, 0), (6000, 0)])])
        self.assertEqual(pecas(resultado), [regras.TERMINAL, regras.TERMINAL])
        self.assertEqual(len(resultado["trechos"]), 1)

    def test_curvas_de_90_e_45(self):
        l90 = regras.analisar([caminho([(0, 0), (3000, 0), (3000, 3000)])])
        self.assertIn("Curva horizontal 90°", pecas(l90))
        l45 = regras.analisar([caminho([(0, 0), (3000, 0), (5000, 2000)])])
        self.assertIn("Curva horizontal 45°", pecas(l45))
        self.assertEqual(regras.nome_da_curva(30.0), "Curva horizontal 45°")
        self.assertEqual(regras.nome_da_curva(20.0), "Curva horizontal 20°")

    def test_vertices_alinhados_nao_sao_peca(self):
        resultado = regras.analisar([caminho([(0, 0), (2000, 0), (4000, 0)])])
        self.assertEqual(pecas(resultado), [regras.TERMINAL, regras.TERMINAL])

    def test_derivacao_no_meio_vira_te(self):
        resultado = regras.analisar([
            caminho([(0, 0), (6000, 0)], nome="A"),
            caminho([(3000, 20), (3000, 3000)], largura=100, nome="B"),  # ponta a 2 cm da linha
        ])
        self.assertIn(regras.TE, pecas(resultado))
        te = next(c for c in resultado["conexoes"] if c["peca"] == regras.TE)
        self.assertEqual(te["largura"], 200)  # pela bandeja principal
        self.assertEqual(len(resultado["trechos"]), 3)

    def test_cruzeta(self):
        resultado = regras.analisar([
            caminho([(-3000, 0), (3000, 0)]), caminho([(0, -3000), (0, 3000)]),
        ])
        # as duas linhas se cruzam sem vértice no meio: o cruzamento só vira nó se alguém tiver vértice lá
        self.assertNotIn(regras.CRUZETA, pecas(resultado))
        resultado = regras.analisar([
            caminho([(-3000, 0), (0, 0), (3000, 0)]), caminho([(0, -3000), (0, 0), (0, 3000)]),
        ])
        self.assertIn(regras.CRUZETA, pecas(resultado))
        self.assertEqual(pecas(resultado).count(regras.TERMINAL), 4)

    def test_reducao_quando_a_largura_muda(self):
        reta = regras.analisar([caminho([(0, 0), (3000, 0)], largura=300, nome="A"),
                                caminho([(3000, 0), (6000, 0)], largura=200, nome="B")])
        self.assertEqual(pecas(reta), [regras.REDUCAO, regras.TERMINAL, regras.TERMINAL])
        reducao = next(c for c in reta["conexoes"] if c["peca"] == regras.REDUCAO)
        self.assertEqual((reducao["largura"], reducao["para_largura"]), (300, 200))
        # ramal mais estreito num tê: tê da principal e redução para o ramal
        te = regras.analisar([caminho([(0, 0), (6000, 0)], largura=300), caminho([(3000, 0), (3000, 2000)], largura=100)])
        self.assertEqual(pecas(te).count(regras.REDUCAO), 1)
        self.assertIn(regras.TE, pecas(te))

    def test_curvas_verticais_quando_a_altura_muda(self):
        resultado = regras.analisar([caminho([(0, 0), (3000, 0)], altura=2800.0, nome="A"),
                                     caminho([(3000, 0), (3000, 3000)], altura=2300.0, nome="B")])
        nomes = pecas(resultado)
        self.assertIn("Curva horizontal 90°", nomes)
        self.assertIn(regras.CURVA_VERTICAL_EXTERNA, nomes)
        self.assertIn(regras.CURVA_VERTICAL_INTERNA, nomes)
        (vertical,) = resultado["verticais"]
        self.assertEqual((vertical["de"], vertical["ate"], vertical["comprimento"], vertical["sentido"], vertical["nome"]),
                         (2300.0, 2800.0, 500.0, "desce", "B"))
        self.assertEqual(len([s for s in resultado["suportes"] if s.get("vertical")]), 1)
        rotulos = regras.rotulos_por_no(resultado["conexoes"])
        self.assertEqual(rotulos[(3000.0, 0.0)], "C90 + CVE + CVI")
        # diferença pequena (até 1 cm) não é curva vertical
        self.assertEqual(regras.analisar([caminho([(0, 0), (3000, 0)], altura=2800.0),
                                          caminho([(3000, 0), (6000, 0)], altura=2805.0)])["verticais"], [])

    def test_bloco_da_vertical(self):
        blocos = regras.blocos_da_vertical(200, 50, 2300, 2800)
        self.assertEqual(len(blocos), 3)
        self.assertEqual(blocos[1][2] + blocos[1][5], 2800.0)
        self.assertEqual(regras.blocos_da_vertical(200, 50, 2800, 2800), [])

    def test_rotulos(self):
        self.assertEqual(regras.rotulo_da_conexao("Curva horizontal 90°"), "C90")
        self.assertEqual([regras.rotulo_da_conexao(p) for p in (regras.TE, regras.CRUZETA, regras.TERMINAL)],
                         ["T", "X", "TF"])


class TestSuportes(unittest.TestCase):
    def test_suporte_perto_das_pontas_e_vao_maximo(self):
        posicoes = regras._suportes_do_trecho(6000, 1500)
        self.assertEqual(posicoes[0], 500)
        self.assertEqual(posicoes[-1], 5500)
        vaos = [b - a for a, b in zip(posicoes, posicoes[1:])]
        self.assertTrue(all(v <= 1500 + 1e-6 for v in vaos))
        self.assertEqual(len(posicoes), 5)  # 5000 mm em 4 vãos de 1250
        self.assertEqual(regras._suportes_do_trecho(800, 1500), [400])
        self.assertEqual(regras._suportes_do_trecho(0, 1500), [])

    def test_leito_tem_vao_maior(self):
        eletrocalha = regras.analisar([caminho([(0, 0), (9000, 0)])])["suportes"]
        leito = regras.analisar([caminho([(0, 0), (9000, 0)], tipo="leito")])["suportes"]
        self.assertGreater(len(eletrocalha), len(leito))
        self.assertEqual({s["angulo"] for s in eletrocalha}, {0.0})


class TestMateriais(unittest.TestCase):
    def test_metros_conexoes_emendas_e_suportes(self):
        resultado = regras.analisar([caminho([(0, 0), (6000, 0), (6000, 3000)], tampa=True)])
        itens = {(i["grupo"], i["item"], i["especificacao"]): i["quantidade"]
                 for i in regras.materiais(resultado, pe_direito_mm=3000.0)}
        self.assertEqual(itens[("Bandejas e leitos", "Eletrocalha perfurada",
                                "200x50 mm, barras de 3 m (inclui 5% de perdas)")], 9.45)
        self.assertEqual(itens[("Bandejas e leitos", "Tampa de encaixe", "largura 200 mm")], 9.45)
        self.assertEqual(itens[("Bandejas e leitos", "Curva horizontal 90°", "Eletrocalha perfurada 200x50 mm")], 1)
        self.assertEqual(itens[("Bandejas e leitos", "Terminal de fechamento", "Eletrocalha perfurada 200x50 mm")], 2)
        # 1 emenda no meio do trecho de 6 m e 2 nos lados da curva
        self.assertEqual(itens[("Bandejas e leitos", "Emenda (par de talas)", "200x50 mm")], 3)
        suportes = len(resultado["suportes"])
        self.assertEqual(itens[("Suportes", "Suporte suspenso (trapézio)", "para largura 200 mm")], suportes)
        self.assertEqual(itens[("Suportes", "Vergalhão roscado 3/8\"", "tirante até a laje")], round(suportes * 0.4, 2))
        self.assertEqual(itens[("Suportes", "Chumbador 3/8\"", "na laje")], 2 * suportes)

    def test_fixacao_vertical_e_reducao(self):
        resultado = regras.analisar([caminho([(0, 0), (3000, 0)], largura=300, altura=2800.0, nome="A"),
                                     caminho([(3000, 0), (6000, 0)], largura=200, altura=2300.0, nome="B")])
        itens = {(i["grupo"], i["item"], i["especificacao"]): i["quantidade"] for i in regras.materiais(resultado)}
        self.assertEqual(itens[("Bandejas e leitos", "Redução", "Eletrocalha perfurada 300x50 mm para 200 mm")], 1)
        self.assertEqual(itens[("Bandejas e leitos", regras.CURVA_VERTICAL_EXTERNA, "Eletrocalha perfurada 200x50 mm")], 1)
        # 3 m + 0,5 m de vertical na seção 200x50, com 5 % de perdas
        self.assertEqual(itens[("Bandejas e leitos", "Eletrocalha perfurada",
                                "200x50 mm, barras de 3 m (inclui 5% de perdas)")], 3.68)
        emendas = sum(q for (g, i, _), q in itens.items() if i == "Emenda (par de talas)")
        self.assertEqual(emendas, 6)  # redução e as duas curvas verticais, dois lados cada
        self.assertEqual(itens[("Fixação", regras.PARAFUSO, "nas emendas")], 6 * regras.PARAFUSOS_POR_EMENDA)
        self.assertEqual(itens[("Fixação", regras.PARAFUSO, "no terminal de fechamento")], 2 * regras.PARAFUSOS_POR_TERMINAL)
        suspensos = len([s for s in resultado["suportes"] if not s.get("vertical")])
        self.assertEqual(itens[("Fixação", "Grampo de fixação da bandeja no perfilado", "com parafuso e porca")],
                         2 * suspensos)
        self.assertEqual(itens[("Suportes", "Suporte de parede para trecho vertical", "para largura 200 mm")], 1)

    def test_entram_no_quantitativo_em_ordem(self):
        itens = regras.materiais(regras.analisar([caminho([(0, 0), (3000, 0)])]))
        linhas = quantitativos.montar([], [("3/4", 1000.0)], itens)
        grupos = [l["grupo"] for l in linhas]
        self.assertLess(grupos.index("Eletrodutos"), grupos.index("Bandejas e leitos"))
        self.assertLess(grupos.index("Bandejas e leitos"), grupos.index("Suportes"))
        self.assertLess(grupos.index("Suportes"), grupos.index("Fixação"))


class TestBlocos(unittest.TestCase):
    def test_eletrocalha_tem_fundo_e_abas(self):
        blocos = regras.blocos_do_trecho(3000, 200, 50, "eletrocalha_lisa", 100, 0)
        self.assertEqual(len(blocos), 3)
        self.assertEqual(blocos[0], (-100.0, -100.0, 0.0, 3100.0, 200.0, regras.ESPESSURA_MM))

    def test_leito_tem_longarinas_e_travessas(self):
        blocos = regras.blocos_do_trecho(3000, 300, 100, "leito")
        self.assertEqual(len(blocos), 2 + 10)

    def test_suporte_vai_ate_a_laje(self):
        perfil, tirante, _ = regras.blocos_do_suporte(200, 2800, 3000)
        self.assertEqual(perfil[4], 300.0)
        self.assertEqual(tirante[2] + tirante[5], 3000.0)
        self.assertEqual(len(regras.blocos_do_suporte(200, 3000, 3000)), 1)  # encostada na laje: sem tirante


class Objeto:
    def __init__(self, nome, **props):
        self.Name = self.Label = nome
        self.__dict__.update(props)

    def addProperty(self, tipo, nome, grupo="", dica=""):
        setattr(self, nome, None)
        return self


class TestServico(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.servico = importlib.import_module("freecad.Circuits.services.bandejas")

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def linha(self, nome, pontos):
        vetores = [types.SimpleNamespace(x=x, y=y, z=0.0) for x, y in pontos]
        return Objeto(nome, Points=vetores, Placement=types.SimpleNamespace(multVec=lambda p: p),
                      ViewObject=types.SimpleNamespace())

    def test_marcar_e_analisar_por_pavimento(self):
        a, b = self.linha("A", [(0, 0), (3000, 0), (3000, 3000)]), self.linha("B", [(0, 0), (0, 3000)])
        doc = types.SimpleNamespace(Objects=[a, b, Objeto("texto")])
        with mock.patch.object(self.servico.pavimentos, "pavimento_do_objeto", return_value=None), \
                mock.patch.object(self.servico.pavimentos, "arquivar") as arquivar:
            marcadas = self.servico.marcar(doc, [a, Objeto("sem pontos")], tipo="leito", largura=300, aba=100,
                                           altura=2500, tampa=True)
            self.servico.marcar(doc, [b])
        self.assertEqual(marcadas, [a])
        self.assertEqual(arquivar.call_count, 2)
        self.assertEqual((a.TipoBandeja, a.Largura, a.Aba, a.AlturaBandeja, a.Tampa), ("leito", 300.0, 100.0, 2500.0, True))
        self.assertEqual(a.ViewObject.LineColor, self.servico.COR_BANDEJA)
        self.assertEqual(self.servico.listar(doc), [a, b])
        pavs = {"A": "Térreo", "B": "Superior"}
        with mock.patch.object(self.servico, "_nome_pavimento", lambda doc, obj: pavs[obj.Name]):
            resultado = self.servico.analisar(doc)
        self.assertEqual(sorted(resultado), ["Superior", "Térreo"])
        self.assertIn("Curva horizontal 90°", pecas(resultado["Térreo"]))
        self.assertEqual(resultado["Superior"]["trechos"][0]["tipo"], "eletrocalha_perfurada")
