"""Rede de eletrodutos: encaixe nas caixas, derivações, roteamento dos circuitos, fios e verticais."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import rede

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet")
RECARREGAR = ("freecad.Circuits.services.rede", "freecad.Circuits.services.eletrodutos",
              "freecad.Circuits.services.pavimentos", "freecad.Circuits.services.alinhamento",
              "freecad.Circuits.services.planilhas", "freecad.Circuits.services.tomadas",
              "freecad.Circuits.services.documento", "freecad.Circuits.services.estilo")


def caminho(*pontos, altura=2800.0, diametro="3/4"):
    return {"pontos": list(pontos), "altura": altura, "diametro": diametro}


def caixa(id_, x, y, altura, tipo="ponto", circuito="", comando="", quadro="", **extra):
    dados = {"id": id_, "nome": id_, "x": x, "y": y, "altura": altura, "tipo": tipo, "circuito": circuito,
             "comando": comando, "quadro": quadro, "pavimento": ""}
    dados.update(extra)
    return dados


def info_fixa(secao=2.5, fases=1, neutro=True, terra=True):
    return lambda quadro, numero, membros: {"secao": secao, "fases": fases, "neutro": neutro, "terra": terra}


class TestGeometria(unittest.TestCase):
    def test_projetar(self):
        self.assertEqual(rede.projetar((5, 3), (0, 0), (10, 0)), ((5.0, 0.0), 0.5, 3.0))
        self.assertEqual(rede.projetar((-4, 3), (0, 0), (10, 0)), ((0.0, 0.0), 0.0, 5.0))
        self.assertEqual(rede.projetar((1, 1), (2, 2), (2, 2))[1:], (0.0, 2 ** 0.5))

    def test_encaixar_vertices_e_trechos(self):
        novos, encaixadas = rede.encaixar(
            [(0, 0), (4000, 0), (4000, 3000)],
            [(120, 50), (2000, 200), (4100, 2950), (9000, 9000)],
        )
        self.assertEqual(novos, [(120, 50), (2000, 200), (4000, 0), (4100, 2950)])
        self.assertEqual(encaixadas, [0, 1, 2])

    def test_encaixar_respeita_a_tolerancia(self):
        novos, encaixadas = rede.encaixar([(0, 0), (1000, 0)], [(500, 400)], tolerancia=300)
        self.assertEqual((novos, encaixadas), ([(0, 0), (1000, 0)], []))

    def test_dois_pontos_no_mesmo_trecho_entram_em_ordem(self):
        novos, _ = rede.encaixar([(0, 0), (3000, 0)], [(2000, 100), (1000, -100)])
        self.assertEqual(novos, [(0, 0), (1000, -100), (2000, 100), (3000, 0)])


class TestRede(unittest.TestCase):
    def test_derivacao_em_t_e_caminho_mais_curto(self):
        r = rede.Rede.construir([caminho((0, 0), (4000, 0)), caminho((2000, 0), (2000, 3000))])
        meio = r.no_mais_proximo((2000, 0))
        self.assertEqual(len(r.vizinhos[meio]), 3)  # o tronco foi dividido na derivação
        dist, _ = r.distancias(r.no_mais_proximo((0, 0)))
        self.assertEqual(dist[r.no_mais_proximo((2000, 3000))], 5000.0)

    def test_vertices_proximos_viram_um_no(self):
        r = rede.Rede.construir([caminho((0, 0), (1000, 0)), caminho((1020, 10), (1020, 2000))])
        self.assertEqual(len(r.nos), 3)

    def test_arvore_soma_o_trecho_comum_uma_vez(self):
        r = rede.Rede.construir([caminho((0, 0), (2000, 0), (2000, 1000)), caminho((2000, 0), (2000, -1000))])
        origem = r.no_mais_proximo((0, 0))
        destinos = [r.no_mais_proximo((2000, 1000)), r.no_mais_proximo((2000, -1000))]
        self.assertEqual(r.arvore(origem, destinos), (4000.0, []))

    def test_destino_sem_caminho(self):
        r = rede.Rede.construir([caminho((0, 0), (1000, 0)), caminho((5000, 0), (6000, 0))])
        isolado = r.no_mais_proximo((6000, 0))
        self.assertEqual(r.arvore(r.no_mais_proximo((0, 0)), [isolado]), (0, [isolado]))


class TestAnalisar(unittest.TestCase):
    def setUp(self):
        self.caminhos = [caminho((0, 0), (4000, 0)), caminho((2000, 0), (2000, 3000))]
        self.caixas = [
            caixa("QD1", 0, 0, 1500, tipo="quadro", refs={"QD1"}),
            caixa("T1", 4000, 0, 300, circuito="2"),
            caixa("L1", 2000, 3000, 2800, circuito="1", comando="a"),
            caixa("S1", 2000, 0, 1300, tipo="interruptor", circuito="1", comando="a"),
        ]

    def info(self, quadro, numero, membros):
        return {"secao": 1.5 if numero == "1" else 2.5, "fases": 1, "neutro": True, "terra": True}

    def test_fios_por_secao_e_funcao(self):
        r = rede.analisar(self.caminhos, self.caixas, self.info)
        # circuito 2: 4 m + verticais 1,3 (quadro) e 2,5 (tomada) + 2 folgas de 0,3 = 8,4 m por condutor
        self.assertAlmostEqual(r["fios"][(2.5, "fase")], 8.4)
        self.assertAlmostEqual(r["fios"][(2.5, "neutro")], 8.4)
        # circuito 1, fase até a luz e o interruptor: 5 + 1,3 + 0 + 1,5 + 3 folgas = 8,7 m
        self.assertAlmostEqual(r["fios"][(1.5, "fase")], 8.7)
        # neutro e terra só até a luz: 5 + 1,3 + 0 + 2 folgas = 6,9 m
        self.assertAlmostEqual(r["fios"][(1.5, "terra")], 6.9)
        # retorno do interruptor até a luz: 3 + 1,5 + 0 + 2 folgas = 5,1 m
        self.assertAlmostEqual(r["fios"][(1.5, "retorno")], 5.1)
        self.assertEqual(r["avisos"], [])

    def test_fiacao_por_circuito(self):
        r = rede.analisar(self.caminhos, self.caixas, self.info)
        self.assertEqual([(c["circuito"], c["condutores"], c["pontos"], c["trajeto"], c["fio"]) for c in r["circuitos"]],
                         [("1", "F+N+T", 2, 5.0, 22.5), ("2", "F+N+T", 1, 4.0, 25.2)])

    def test_verticais(self):
        r = rede.analisar(self.caminhos, self.caixas, self.info)
        verticais = {v["caixa"]: (v["comprimento"], v["sentido"], v["diametro"]) for v in r["verticais"]}
        self.assertEqual(verticais, {"QD1": (1.3, "descida", "3/4"), "T1": (2.5, "descida", "3/4"),
                                     "S1": (1.5, "descida", "3/4")})  # a luz no teto não tem vertical

    def test_eletroduto_no_piso_sobe_ate_a_caixa(self):
        r = rede.analisar([caminho((0, 0), (1000, 0), altura=0.0)],
                          [caixa("QD1", 0, 0, 1500, tipo="quadro", refs={"QD1"}), caixa("T1", 1000, 0, 300, circuito="1")],
                          info_fixa())
        self.assertEqual({v["caixa"]: v["sentido"] for v in r["verticais"]}, {"QD1": "subida", "T1": "subida"})

    def test_bifasico_sem_neutro(self):
        r = rede.analisar(self.caminhos, self.caixas[:2], info_fixa(secao=4, fases=2, neutro=False))
        self.assertAlmostEqual(r["fios"][(4.0, "fase")], 16.8)
        self.assertNotIn((4.0, "neutro"), r["fios"])
        self.assertEqual(r["circuitos"][0]["condutores"], "F+F+T")

    def test_interruptores_paralelos_levam_dois_condutores_entre_eles(self):
        caixas = self.caixas + [caixa("S2", 2000, 3000, 1300, tipo="interruptor", circuito="1", comando="a")]
        r = rede.analisar(self.caminhos, caixas, self.info)
        # retorno até a luz e o S2 (3 + 1,5 + 0 + 1,5 + 3 folgas = 6,9) + 2 x entre S1 e S2 (3 + 1,5 + 1,5 + 0,6 = 6,6)
        self.assertAlmostEqual(r["fios"][(1.5, "retorno")], 6.9 + 2 * 6.6)

    def test_quadro_pela_referencia_do_ponto(self):
        # as caixas precisam estar em vértices: é o que o Conectar às caixas garante
        caminhos = [caminho((0, 0), (1000, 0), (1500, 0), (6000, 0))]
        caixas = [caixa("QD1", 0, 0, 1500, tipo="quadro", refs={"QD1"}),
                  caixa("QD2", 6000, 0, 1500, tipo="quadro", refs={"QD2"}),
                  caixa("T1", 1000, 0, 300, circuito="1"),
                  caixa("T2", 1500, 0, 300, circuito="1", quadro="QD2")]
        r = rede.analisar(caminhos, caixas, info_fixa())
        self.assertEqual(sorted((c["quadro"], c["circuito"], c["pontos"]) for c in r["circuitos"]),
                         [("QD1", "1", 1), ("QD2", "1", 1)])  # T1 vai ao mais próximo; T2 ao QD2 indicado

    def test_caixa_no_meio_de_um_trecho_sem_vertice_nao_fica_ligada(self):
        r = rede.analisar([caminho((0, 0), (6000, 0))],
                          [caixa("QD1", 0, 0, 1500, tipo="quadro", refs={"QD1"}), caixa("T1", 1000, 0, 300, circuito="1")],
                          info_fixa())
        self.assertEqual(r["avisos"], ["T1: sem eletroduto chegando na caixa."])

    def test_avisos(self):
        caixas = self.caixas + [caixa("T9", 9000, 9000, 300, circuito="3"), caixa("T8", 5000, 5000, 300)]
        caminhos = self.caminhos + [caminho((7000, 0), (8000, 0))]
        caixas.append(caixa("T7", 8000, 0, 300, circuito="4"))
        r = rede.analisar(caminhos, caixas, self.info)
        self.assertIn("T9: sem eletroduto chegando na caixa.", r["avisos"])
        self.assertIn("T7: nenhum quadro ligado pela rede ao circuito 4.", r["avisos"])
        self.assertFalse(any(a.startswith("T8") for a in r["avisos"]))  # sem circuito: não é cobrado

    def test_juntar_pavimentos(self):
        a = rede.analisar(self.caminhos, self.caixas, self.info)
        total = rede.juntar([a, a])
        self.assertAlmostEqual(total["fios"][(2.5, "fase")], 16.8)
        self.assertEqual(len(total["verticais"]), 6)


class Vetor:
    def __init__(self, x, y, z=0.0):
        self.x, self.y, self.z = x, y, z


class Identidade:
    def multVec(self, v):
        return v

    def inverse(self):
        return self


class TestServico(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        falsos["FreeCAD"].Vector = Vetor
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.servico = importlib.import_module("freecad.Circuits.services.rede")

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def ponto(self, nome, simbolo, x, y, altura, circuito="1", **extra):
        props = dict(Name=nome, Label=nome, Simbolo=simbolo, Altura3D=altura, Circuito=circuito, Comando="",
                     Quadro="", Ligacao="F+N", Descricao=nome, Planilha="",
                     Proxy=types.SimpleNamespace(Type="Ponto"), Placement=types.SimpleNamespace(Base=Vetor(x, y)))
        props.update(extra)
        return types.SimpleNamespace(**props)

    def documento(self, *objetos):
        doc = mock.MagicMock()
        doc.Objects = list(objetos)
        doc.getObject.return_value = None
        return doc

    def test_dados_dos_circuitos_do_quadro_da_planilha(self):
        planilha = types.SimpleNamespace(Name="Spreadsheet001")
        caixas = [{"tipo": "quadro", "nome": "QD1", "refs": {"QD1", "Spreadsheet001"}},
                  {"tipo": "quadro", "nome": "QD2", "refs": {"QD2", "Spreadsheet002"}},
                  {"tipo": "ponto", "nome": "T1"}]
        circuitos = [{"quadro": "QD1", "circuito": "1", "comprimento": 12.5, "agrupados": 3},
                     {"quadro": "QD2", "circuito": "1", "comprimento": 40.0, "agrupados": 1}]
        with mock.patch.object(self.servico, "listar_caixas", return_value=caixas), \
                mock.patch.object(self.servico, "analisar", return_value={"circuitos": circuitos}) as analisar:
            self.assertEqual(self.servico.dados_dos_circuitos(None, planilha),
                             {"1": {"comprimento": 12.5, "agrupados": 3}})
            analisar.reset_mock()
            self.assertEqual(self.servico.dados_dos_circuitos(None, types.SimpleNamespace(Name="Outra")), {})
            analisar.assert_not_called()  # sem símbolo ligado à planilha, nem lê a rede

    def test_eh_eletroduto(self):
        self.assertTrue(self.servico.eh_eletroduto(types.SimpleNamespace(Proxy=types.SimpleNamespace(Type="ConduitPath"))))
        self.assertTrue(self.servico.eh_eletroduto(types.SimpleNamespace(Points=[], Diametro="1", Altura3D=2800)))
        self.assertFalse(self.servico.eh_eletroduto(types.SimpleNamespace(Points=[])))  # linha comum do Draft

    def test_caixas_do_documento(self):
        quadro = self.ponto("QD", "quadro_distribuicao", 0, 0, 1500, circuito="", Descricao="QD1")
        medicao = self.ponto("CM", "medicao_agrupada", 0, 0, 1200, circuito="")
        tomada = self.ponto("T1", "tomada_baixa", 1000, 0, 300, Ligacao="F+F")
        with mock.patch.object(self.servico, "listar_simbolos", return_value=[quadro, medicao, tomada]), \
                mock.patch.object(self.servico.pavimentos, "pavimento_do_objeto", return_value=None):
            caixas = self.servico.listar_caixas(self.documento(quadro, medicao, tomada))
        self.assertEqual([(c["id"], c["tipo"]) for c in caixas], [("QD", "quadro"), ("T1", "ponto")])  # medição fica fora
        self.assertIn("QD1", caixas[0]["refs"])
        self.assertEqual((caixas[1]["fases"], caixas[1]["altura"], caixas[1]["tipo_circuito"]), (2, 300, "TUG"))

    def test_conectar_encaixa_os_vertices_e_marca_o_eletroduto(self):
        tomada = self.ponto("T1", "tomada_baixa", 3000, 150, 300)
        linha = types.SimpleNamespace(Name="Wire", Points=[Vetor(0, 0), Vetor(2900, 0)], Placement=Identidade())

        def preparar(obj):
            obj.Diametro, obj.Altura3D = "3/4", 2800.0

        doc = self.documento(tomada, linha)
        nivel = object()  # o pavimento onde os símbolos entram (nível ativo do BIM, selecionado ou ativo)
        with mock.patch.object(self.servico, "_preparar_caminho", side_effect=preparar), \
                mock.patch.object(self.servico, "listar_simbolos", return_value=[tomada]), \
                mock.patch.object(self.servico.pavimentos, "pavimento_do_objeto", return_value=None), \
                mock.patch.object(self.servico.pavimentos, "pavimento_para_insercao", return_value=nivel), \
                mock.patch.object(self.servico.pavimentos, "arquivar") as arquivar:
            tratados, ligadas, soltas = self.servico.conectar(doc, [linha])
        self.assertEqual((tratados, ligadas, soltas), (1, 1, []))
        self.assertEqual([(p.x, p.y) for p in linha.Points], [(0, 0), (3000, 150)])
        arquivar.assert_called_once_with(doc, linha, nivel)
        doc.commitTransaction.assert_called_once()

    def test_campainha_passagem_e_aterramento_na_rede(self):
        botao = self.ponto("B1", "botao_campainha", 0, 0, 1300, circuito="3", Comando="a")
        passagem = self.ponto("CP", "caixa_passagem", 0, 0, 2800, circuito="")
        haste = self.ponto("H1", "haste_aterramento", 0, 0, -1200, circuito="")
        with mock.patch.object(self.servico, "listar_simbolos", return_value=[botao, passagem, haste]), \
                mock.patch.object(self.servico.pavimentos, "pavimento_do_objeto", return_value=None):
            caixas = self.servico.listar_caixas(self.documento(botao, passagem, haste))
        self.assertEqual([(c["id"], c["tipo"]) for c in caixas], [("B1", "interruptor"), ("CP", "passagem")])
        self.assertEqual((caixas[0]["comando"], caixas[0]["circuito"]), ("a", "3"))

    def test_info_do_circuito_pela_planilha_e_pelos_pontos(self):
        planilha = object()
        linha = {"N_circuito": "3", "Cabo": "6", "Fase_R": "True", "Fase_S": "True", "Fase_T": "False", "Neutro": "False"}
        with mock.patch.object(self.servico.planilhas, "ler_circuitos_completos", return_value=[linha]):
            info = self.servico._info_circuito(self.documento(), {})
            quadro = {"id": "QD", "planilha": planilha, "refs": set()}
            self.assertEqual(info(quadro, "3", [{"tipo": "ponto", "tipo_circuito": "TUE", "fases": 2}]),
                             {"secao": 6.0, "fases": 2, "neutro": False, "terra": True})
            # circuito que não está na planilha: seção mínima e condutores pelos pontos
            self.assertEqual(info(quadro, "9", [{"tipo": "ponto", "tipo_circuito": "ILUM", "fases": 1}]),
                             {"secao": 1.5, "fases": 1, "neutro": True, "terra": True})


if __name__ == "__main__":
    unittest.main(verbosity=2)
