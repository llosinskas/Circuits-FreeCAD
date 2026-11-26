"""Subidas e descidas: símbolos na planta e detalhes em elevação (core/verticais.py, core/rede.py)."""
import math
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import rede, verticais


def info(quadro, numero, membros):
    return {"secao": 2.5, "fases": 1, "neutro": True, "terra": True}


def caixa(id_, x, y, altura, tipo="ponto", circuito="1"):
    return {"id": id_, "nome": id_, "x": x, "y": y, "tipo": tipo, "altura": altura, "pavimento": "",
            "circuito": circuito if tipo != "quadro" else "", "quadro": "", "ligacao": "F+N", "comando": "",
            "descricao": id_}


class TestRede(unittest.TestCase):
    def test_descida_para_a_caixa_tem_a_posicao(self):
        r = rede.analisar([{"pontos": [(0, 0), (4000, 0)], "altura": 2800.0, "diametro": "3/4"}],
                          [caixa("QD1", 0, 0, 1500.0, "quadro"), caixa("T1", 4000, 0, 300.0)], info)
        t1 = next(v for v in r["verticais"] if v["caixa"] == "T1")
        self.assertEqual((t1["x"], t1["y"], t1["sentido"]), (4000, 0, "descida"))

    def test_eletrodutos_de_alturas_diferentes_no_mesmo_ponto(self):
        caminhos = [{"pontos": [(0, 0), (4000, 0)], "altura": 2800.0, "diametro": "3/4"},   # no teto
                    {"pontos": [(4000, 0), (4000, 3000)], "altura": -100.0, "diametro": "1"}]  # no piso
        r = rede.analisar(caminhos, [], info)
        self.assertEqual(r["transicoes"], [{"x": 4000.0, "y": 0.0, "de": -100.0, "ate": 2800.0,
                                            "comprimento": 2.9, "diametro": "1", "sentido": "desce"}])
        mesma = rede.analisar([caminhos[0], dict(caminhos[1], altura=2800.0)], [], info)
        self.assertEqual(mesma["transicoes"], [])

    def test_sentido_de_quem_vem_do_quadro(self):
        caminhos = [{"pontos": [(0, 0), (4000, 0)], "altura": 2800.0, "diametro": "3/4"},
                    {"pontos": [(4000, 0), (4000, 3000)], "altura": -100.0, "diametro": "3/4"}]
        # quadro na ponta do teto: o cabo chega pelo teto e desce
        r = rede.analisar(caminhos, [caixa("QD1", 0, 0, 1500.0, "quadro")], info)
        self.assertEqual(r["transicoes"][0]["sentido"], "desce")
        # quadro na ponta do piso: o cabo chega pelo piso e sobe, mesmo desenhado depois
        r = rede.analisar(caminhos, [caixa("QD1", 4000, 3000, 1500.0, "quadro")], info)
        self.assertEqual(r["transicoes"][0]["sentido"], "sobe")

    def test_sem_quadro_vale_a_ordem_do_desenho(self):
        caminhos = [{"pontos": [(4000, 0), (4000, 3000)], "altura": -100.0, "diametro": "3/4"},
                    {"pontos": [(0, 0), (4000, 0)], "altura": 2800.0, "diametro": "3/4"}]
        self.assertEqual(rede.analisar(caminhos, [], info)["transicoes"][0]["sentido"], "sobe")

    def test_sobe_e_desce_no_mesmo_ponto(self):
        caminhos = [{"pontos": [(0, 0), (4000, 0)], "altura": 1500.0, "diametro": "3/4"},
                    {"pontos": [(4000, 0), (4000, 3000)], "altura": 2800.0, "diametro": "3/4"},
                    {"pontos": [(4000, 0), (8000, 0)], "altura": -100.0, "diametro": "3/4"}]
        self.assertEqual(rede.analisar(caminhos, [], info)["transicoes"][0]["sentido"], "sobe_desce")

    def test_juntar_soma_as_transicoes(self):
        um = {"fios": {}, "circuitos": [], "verticais": [], "avisos": [], "transicoes": [{"x": 0}]}
        self.assertEqual(len(rede.juntar([um, dict(um, transicoes=[{"x": 1}])])["transicoes"]), 2)


DESCIDA = {"caixa": "T1", "circuito": "1", "x": 4000.0, "y": 0.0, "altura_eletroduto": 2800.0, "altura_caixa": 300.0,
           "comprimento": 2.5, "sentido": "descida", "diametro": "3/4", "pavimento": "Térreo"}
TRANSICAO = {"x": 4000.0, "y": 0.0, "de": -100.0, "ate": 2800.0, "comprimento": 2.9, "diametro": "1",
             "pavimento": "Térreo"}
BANDEJA = {"x": 6000.0, "y": 0.0, "tipo": "eletrocalha_perfurada", "largura": 200, "aba": 50, "de": 2300.0,
           "ate": 2800.0, "comprimento": 500.0, "angulo": 90.0, "nome": "Wire001", "sentido": "desce",
           "pavimento": "Térreo"}


class TestItens(unittest.TestCase):
    def test_itens_de_eletroduto(self):
        d, t = verticais.itens_de_eletroduto([DESCIDA], [TRANSICAO])
        self.assertEqual((d["tipo"], d["sentido"], d["de"], d["ate"], d["local"]), ("eletroduto", "desce", 300.0,
                                                                                    2800.0, "T1"))
        self.assertEqual((t["sentido"], t["de"], t["ate"], t["diametro"]), ("sobe_desce", -100.0, 2800.0, "1"))
        desce, = verticais.itens_de_eletroduto([], [dict(TRANSICAO, sentido="desce")])
        self.assertEqual(desce["sentido"], "desce")  # o sentido da rede vai para o símbolo e o texto
        self.assertTrue(verticais.texto(desce).startswith('Ø1" desce 2,90 m'))
        subida = verticais.itens_de_eletroduto([dict(DESCIDA, sentido="subida", altura_caixa=1200.0,
                                                     altura_eletroduto=-100.0)], [])[0]
        self.assertEqual((subida["sentido"], subida["de"], subida["ate"]), ("sobe", -100.0, 1200.0))

    def test_itens_de_eletrocalha(self):
        (e,) = verticais.itens_de_eletrocalha([BANDEJA])
        self.assertEqual((e["tipo"], e["sentido"], e["largura"], e["aba"], e["de"], e["ate"]),
                         ("eletrocalha", "desce", 200.0, 50.0, 2300.0, 2800.0))

    def test_textos(self):
        d, t = verticais.itens_de_eletroduto([DESCIDA], [TRANSICAO])
        (e,) = verticais.itens_de_eletrocalha([BANDEJA])
        self.assertEqual(verticais.texto(d), 'Ø3/4" desce 2,50 m')
        self.assertEqual(verticais.texto(t), 'Ø1" sobe/desce 2,90 m')
        self.assertEqual(verticais.texto(e), "EL 200x50 desce 0,50 m")
        leito = verticais.itens_de_eletrocalha([dict(BANDEJA, tipo="leito", sentido="sobe")])[0]
        self.assertEqual(verticais.texto(leito), "LT 200x50 sobe 0,50 m")


def pontas_de_seta(simbolo):
    """Pontas das setas: pares de traços curtos que se encontram num ponto."""
    curtas = [l for l in simbolo["linhas"] if math.hypot(l[2] - l[0], l[3] - l[1]) < 100]
    return {(round(l[0]), round(l[1])) for l in curtas}


class TestSimbolos(unittest.TestCase):
    def setUp(self):
        self.desce, self.passa = verticais.itens_de_eletroduto([DESCIDA], [TRANSICAO])
        self.sobe = dict(self.desce, sentido="sobe")

    def test_eletroduto_e_um_circulo_com_seta(self):
        s = verticais.simbolo(self.desce, 300)
        self.assertEqual(s["circulos"], [(0.0, 0.0, 75.0)])
        diagonal = max(s["linhas"], key=lambda l: math.hypot(l[2] - l[0], l[3] - l[1]))
        self.assertAlmostEqual(math.hypot(diagonal[2], diagonal[3]), 300.0)

    def test_desce_aponta_para_o_circulo_e_sobe_para_fora(self):
        perto, longe = {(53, 53)}, {(212, 212)}  # borda do círculo e ponta da diagonal, a 45°
        self.assertEqual(pontas_de_seta(verticais.simbolo(self.desce, 300)), perto)
        self.assertEqual(pontas_de_seta(verticais.simbolo(self.sobe, 300)), longe)
        self.assertEqual(pontas_de_seta(verticais.simbolo(self.passa, 300)), perto | longe)

    def test_eletrocalha_e_a_secao_com_diagonal(self):
        (e,) = verticais.itens_de_eletrocalha([dict(BANDEJA, angulo=0.0)])
        s = verticais.simbolo(e, 300)
        self.assertEqual(s["circulos"], [])
        xs = sorted({round(v) for l in s["linhas"][:4] for v in (l[0], l[2])})
        ys = sorted({round(v) for l in s["linhas"][:4] for v in (l[1], l[3])})
        self.assertEqual((xs, ys), ([-25, 25], [-100, 100]))  # aba ao longo da bandeja, largura atravessada
        self.assertIn((-25.0, -100.0, 25.0, 100.0), s["linhas"])  # diagonal da seção

    def test_ponto_do_texto_depois_da_seta(self):
        s = verticais.simbolo(self.desce, 300)
        self.assertGreater(s["texto"][0], 212)


class TestDetalhes(unittest.TestCase):
    def test_verticais_iguais_viram_um_detalhe_com_quantidade(self):
        itens = verticais.itens_de_eletroduto([DESCIDA, dict(DESCIDA, caixa="T2"), dict(DESCIDA, caixa="T3",
                                                                                         altura_caixa=1200.0)], [])
        itens += verticais.itens_de_eletrocalha([BANDEJA])
        detalhes = verticais.detalhes(itens)
        self.assertEqual([(d["id"], d["quantidade"]) for d in detalhes], [("V1", 2), ("V2", 1), ("V3", 1)])
        self.assertEqual(detalhes[0]["locais"], ["T1", "T2"])
        self.assertEqual(detalhes[2]["tipo"], "eletrocalha")

    def test_geometria_do_detalhe_de_eletroduto(self):
        (detalhe,) = verticais.detalhes(verticais.itens_de_eletroduto([DESCIDA], []))
        g = verticais.geometria_detalhe(detalhe, pe_direito=3000.0)
        horizontais = {round(l[1]) for l in g["linhas"] if l[1] == l[3] and abs(l[2] - l[0]) >= 1500}
        self.assertEqual(horizontais, {0, 3000})  # piso e laje
        d = 26.9  # diâmetro externo do 3/4"
        raio = verticais.RAIO_CURVA_ELETRODUTO_FATOR * d
        centro_y = 2800 - d / 2 - raio
        # curva no alto em arco: duas paredes, de raio R ± d/2, no quarto de cima à esquerda do centro
        self.assertEqual(sorted((round(a[0], 2), round(a[1], 2), round(a[2], 2), a[3], a[4]) for a in g["arcos"]),
                         [(round(raio, 2), round(centro_y, 2), round(raio - d / 2, 2), 90.0, 90.0),
                          (round(raio, 2), round(centro_y, 2), round(raio + d / 2, 2), 90.0, 90.0)])
        paredes = sorted((round(l[0], 2), round(min(l[1], l[3])), round(max(l[1], l[3]), 2))
                         for l in g["linhas"] if l[0] == l[2] and abs(l[0]) < 20)
        # as duas paredes vão da caixa até onde o arco começa
        self.assertEqual(paredes, [(-13.45, 300, round(centro_y, 2)), (13.45, 300, round(centro_y, 2))])
        inicio_do_trecho = min(min(l[0], l[2]) for l in g["linhas"] if l[1] == l[3] and 2700 < l[1] <= 2800)
        self.assertAlmostEqual(inicio_do_trecho, raio)  # o trecho horizontal sai de onde o arco termina
        textos = [t[2] for t in g["textos"]]
        self.assertTrue(any(t.startswith("V1") and "1 un" in t for t in textos))
        self.assertIn("+2,80", textos)
        self.assertIn("+0,30", textos)
        fim_do_trecho = max(max(l[0], l[2]) for l in g["linhas"] if l[1] == l[3] and abs(l[2] - l[0]) < 1500)
        cota = next(t for t in g["textos"] if t[2] == "+2,80")
        self.assertGreater(cota[0], fim_do_trecho)  # a cota não fica em cima do eletroduto

    def test_geometria_do_detalhe_de_eletrocalha(self):
        (detalhe,) = verticais.detalhes(verticais.itens_de_eletrocalha([BANDEJA]))
        g = verticais.geometria_detalhe(detalhe, pe_direito=3000.0)
        # vista lateral na espessura da aba (50 mm); curvas em arco de raio = largura (200 mm) no alto e embaixo
        arcos = sorted((round(a[0]), round(a[1]), round(a[2]), a[3]) for a in g["arcos"])
        self.assertEqual(arcos, [(-200, 2525, 175, 270.0), (-200, 2525, 225, 270.0),
                                 (200, 2575, 175, 90.0), (200, 2575, 225, 90.0)])
        paredes = sorted((round(l[0]), round(min(l[1], l[3])), round(max(l[1], l[3])))
                         for l in g["linhas"] if l[0] == l[2] and abs(l[0]) < 100)
        self.assertEqual(paredes, [(-25, 2525, 2575), (25, 2525, 2575)])  # só o reto entre as duas curvas
        self.assertTrue(any("CVE" in t[2] for t in g["textos"]))
        self.assertTrue(any("CVI" in t[2] for t in g["textos"]))


if __name__ == "__main__":
    unittest.main()


import importlib  # noqa: E402
import sys  # noqa: E402
import types  # noqa: E402
from unittest import mock  # noqa: E402

from freecad.Circuits.core import parametros  # noqa: E402

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Spreadsheet", "Sketcher")
RECARREGAR = ("freecad.Circuits.services.verticais", "freecad.Circuits.services.rede",
              "freecad.Circuits.services.bandejas", "freecad.Circuits.services.legenda",
              "freecad.Circuits.services.parametros", "freecad.Circuits.services.pavimentos",
              "freecad.Circuits.services.planilhas", "freecad.Circuits.services.alinhamento",
              "freecad.Circuits.services.eletrodutos", "freecad.Circuits.services.tomadas",
              "freecad.Circuits.services.documento", "freecad.Circuits.objects.ponto")


class Vetor(tuple):
    def __add__(self, outro):
        return Vetor(a + b for a, b in zip(self, outro))


class Objeto:
    def __init__(self, nome):
        self.Name = self.Label = nome
        self.Group = []
        self.Placement = types.SimpleNamespace(Base=(0, 0, 0))

    def addProperty(self, tipo, nome, grupo="", dica=""):
        setattr(self, nome, "")

    def addObject(self, obj):
        self.Group.append(obj)

    def removeObjectsFromDocument(self):
        pass


class Documento:
    def __init__(self):
        self.Objects = []

    def addObject(self, tipo, nome):
        obj = Objeto(f"{nome}{len(self.Objects)}" if self.getObject(nome) else nome)
        self.Objects.append(obj)
        return obj

    def getObject(self, nome):
        return next((o for o in self.Objects if o.Name == nome), None)

    def removeObject(self, nome):
        self.Objects = [o for o in self.Objects if o.Name != nome]

    def recompute(self):
        pass


class TestServico(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.dict(sys.modules, {n: mock.MagicMock(name=n) for n in MODULOS_FREECAD})
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        fc = sys.modules["FreeCAD"]
        fc.Vector = lambda x=0.0, y=0.0, z=0.0: Vetor((x, y, z))
        self.servico = importlib.import_module("freecad.Circuits.services.verticais")
        self.mudancas = mock.patch.multiple(
            self.servico.pavimentos, por_nome=mock.DEFAULT, pasta=mock.DEFAULT, elevacao=mock.DEFAULT)
        falsos = self.mudancas.start()
        falsos["por_nome"].return_value = None

    def tearDown(self):
        self.mudancas.stop()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def coletar(self, simbolos_nas_caixas="S"):
        with mock.patch.object(self.servico.rede, "analisar",
                               return_value={"verticais": [DESCIDA], "transicoes": [TRANSICAO]}), \
                mock.patch.object(self.servico.bandejas, "analisar", return_value={"Térreo": {"verticais": [BANDEJA]}}), \
                mock.patch.object(self.servico.parametros, "ler",
                                  return_value=parametros.ler({"simbolos_descida_caixas": simbolos_nas_caixas})):
            return self.servico.coletar(Documento(), com_caixas=None)

    def test_coleta_eletrodutos_transicoes_e_eletrocalhas(self):
        itens = self.coletar()
        self.assertEqual(sorted((i["tipo"], i["sentido"]) for i in itens),
                         [("eletrocalha", "desce"), ("eletroduto", "desce"), ("eletroduto", "sobe_desce")])

    def test_parametro_tira_os_simbolos_das_caixas(self):
        self.assertEqual(sorted(i["sentido"] for i in self.coletar("N")), ["desce", "sobe_desce"])  # só a calha desce

    def test_simbolos_um_objeto_por_pavimento_e_tipo_e_um_texto_por_item(self):
        doc = Documento()
        itens = verticais.itens_de_eletroduto([DESCIDA], [TRANSICAO]) + verticais.itens_de_eletrocalha([BANDEJA])
        draft = sys.modules["Draft"]
        with mock.patch.object(self.servico, "coletar", return_value=itens):
            self.assertEqual(self.servico.desenhar_simbolos(doc), 3)
            self.assertEqual(draft.make_text.call_count, 3)
            self.servico.desenhar_simbolos(doc)  # de novo: substitui
        desenhos = [o for o in doc.Objects if hasattr(o, "simbolo_vertical")]
        self.assertEqual(len(desenhos), 2)  # eletrodutos e eletrocalha do Térreo

    def test_detalhes_um_por_tipo_e_ficam_onde_estavam(self):
        doc = Documento()
        itens = verticais.itens_de_eletroduto([DESCIDA, dict(DESCIDA, caixa="T2")], [])
        fc = sys.modules["FreeCAD"]
        with mock.patch.object(self.servico, "coletar", return_value=itens), \
                mock.patch.object(self.servico.legenda, "_canto_livre", return_value=Vetor((5000.0, 0.0, 0.0))), \
                mock.patch.object(self.servico.bandejas, "pe_direito", return_value=3000.0):
            part = sys.modules["Part"]
            part.ArcOfCircle.reset_mock()
            self.assertEqual(self.servico.desenhar_detalhes(doc), 1)
            self.assertEqual([o.Name for o in doc.Objects if o.Name.startswith("Detalhe_V")], ["Detalhe_V1"])
            esperado = verticais.geometria_detalhe(verticais.detalhes(itens)[0], 3000.0)
            self.assertEqual(part.ArcOfCircle.call_count, len(esperado["arcos"]))  # curvas em arco
            grupo = doc.getObject(self.servico.GRUPO_DETALHES)
            grupo.Group[0].Placement = types.SimpleNamespace(Base=Vetor((123.0, 456.0, 0.0)))  # o usuário moveu
            fc.Placement.reset_mock()
            self.servico.desenhar_detalhes(doc)
        self.assertEqual(fc.Placement.call_args_list[0].args[0], (123.0, 456.0, 0.0))  # título no mesmo lugar
        self.assertEqual(len([o for o in doc.Objects if o.Name == self.servico.GRUPO_DETALHES]), 1)
