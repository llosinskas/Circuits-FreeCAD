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
        # na mesma altura, o cruzamento vira nó e cruzeta mesmo sem vértice desenhado lá
        self.assertIn(regras.CRUZETA, pecas(resultado))
        self.assertEqual(len(resultado["trechos"]), 4)
        passando = regras.analisar([
            caminho([(-3000, 0), (3000, 0)], altura=2800.0), caminho([(0, -3000), (0, 3000)], altura=2400.0),
        ])
        self.assertNotIn(regras.CRUZETA, pecas(passando))  # em alturas diferentes, uma passa sob a outra
        self.assertEqual(len(passando["trechos"]), 2)
        quina = regras.analisar([caminho([(0, 0), (3000, 0)]), caminho([(3000, 0), (3000, 3000)])])
        self.assertEqual(len(quina["trechos"]), 2)  # tocar na ponta não é cruzamento
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

    def test_reducao_quando_muda_so_a_aba(self):
        r = regras.analisar([caminho([(0, 0), (3000, 0)], aba=100, nome="A"),
                             caminho([(3000, 0), (6000, 0)], aba=50, nome="B")])
        reducao = next(c for c in r["conexoes"] if c["peca"] == regras.REDUCAO)
        self.assertEqual((reducao["aba"], reducao["para_aba"]), (100, 50))

    def test_mesma_secao_nao_tem_reducao(self):
        r = regras.analisar([caminho([(0, 0), (3000, 0)], nome="A"), caminho([(3000, 0), (6000, 0)], nome="B")])
        self.assertNotIn(regras.REDUCAO, pecas(r))

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


class TestJuncoes(unittest.TestCase):
    """Encaixe das pontas soltas: junção com outra bandeja no vértice (curva, cruzeta) ou no meio (tê)."""

    def test_ponta_perto_do_meio_de_outra_bandeja_vira_te(self):
        novos, juncoes = regras.encaixar([[(0, 0), (6000, 0)], [(3000, 250), (3000, 3000)]])
        self.assertEqual((novos[1][0], juncoes), ((3000.0, 0.0), 1))
        self.assertIn(regras.TE, pecas(regras.analisar([caminho(novos[0]), caminho(novos[1])])))

    def test_pontas_proximas_viram_um_no_so(self):
        novos, juncoes = regras.encaixar([[(0, 0), (3000, 0)], [(3100, 150), (3100, 3000)]])
        self.assertEqual((novos[0][-1], juncoes), (novos[1][0], 1))  # uma das pontas vai até a outra
        self.assertIn("Curva horizontal 90°", pecas(regras.analisar([caminho(novos[0]), caminho(novos[1])])))

    def test_prefere_o_vertice_ao_meio_do_trecho(self):
        novos, _ = regras.encaixar([[(0, 0), (3000, 0), (3000, 3000)], [(2900, 100), (0, 3000)]])
        self.assertEqual(novos[1][0], (3000.0, 0.0))

    def test_longe_ou_ja_ligada_fica_como_esta(self):
        caminhos = [[(0, 0), (6000, 0)], [(3000, 500), (3000, 3000)], [(6000, 0), (6000, 2000)]]
        novos, juncoes = regras.encaixar(caminhos)
        self.assertEqual((novos, juncoes), ([[(float(x), float(y)) for x, y in c] for c in caminhos], 0))

    def test_vertice_do_meio_nao_e_movido(self):
        novos, juncoes = regras.encaixar([[(0, 0), (6000, 0)], [(3000, 2000), (3000, 100), (5000, 600)]])
        self.assertEqual((novos[1][1], juncoes), ((3000.0, 100.0), 0))


def no_ponto(resultado, x, y):
    """Recuo de cada trecho no nó (x, y)."""
    recuos = []
    for t in resultado["trechos"]:
        if (round(t["x1"]), round(t["y1"])) == (x, y):
            recuos.append(round(t["recuo_inicio"], 2))
        if (round(t["x2"]), round(t["y2"])) == (x, y):
            recuos.append(round(t["recuo_fim"], 2))
    return sorted(recuos)


class TestPecasNosNos(unittest.TestCase):
    """Os trechos retos são recortados para a peça do nó caber: curva, tê, cruzeta."""

    def test_curva_de_90_recorta_o_raio_dos_dois_lados(self):
        r = regras.analisar([caminho([(0, 0), (3000, 0), (3000, 3000)], largura=200)])
        self.assertEqual(no_ponto(r, 3000, 0), [200.0, 200.0])  # raio da curva = largura
        self.assertEqual(no_ponto(r, 0, 0), [0.0])  # terminal não recorta

    def test_curva_de_45_recorta_menos(self):
        r = regras.analisar([caminho([(0, 0), (3000, 0), (5000, 2000)], largura=200)])
        self.assertEqual(no_ponto(r, 3000, 0), [82.84, 82.84])  # 200 · tg 22,5°

    def test_arco_da_curva_tangente_aos_dois_trechos(self):
        r = regras.analisar([caminho([(0, 0), (3000, 0), (3000, 3000)], largura=200)])
        curva = next(c for c in r["conexoes"] if c["peca"].startswith(regras.CURVA))
        cx, cy, raio, inicio, varredura = curva["arco"]
        self.assertAlmostEqual(cx, 2800.0)
        self.assertAlmostEqual(cy, 200.0)
        self.assertEqual((raio, round(varredura, 6), round(inicio % 360, 6)), (200.0, 90.0, 270.0))

    def test_te_e_cruzeta_recortam_meia_largura_da_principal(self):
        te = regras.analisar([caminho([(0, 0), (6000, 0)], largura=300), caminho([(3000, 0), (3000, 2000)], largura=100)])
        self.assertEqual(no_ponto(te, 3000, 0), [150.0, 150.0, 150.0])
        reta = regras.analisar([caminho([(0, 0), (3000, 0), (6000, 0)])])
        self.assertEqual(no_ponto(reta, 3000, 0), [0.0, 0.0])  # emenda


class TestPecaDeReducao(unittest.TestCase):
    """A redução é uma peça de COMPRIMENTO_REDUCAO_MM no começo do trecho mais estreito."""

    def reta(self, **mais):
        return regras.analisar([caminho([(0, 0), (3000, 0)], largura=300, nome="A", **mais),
                                caminho([(3000, 0), (6000, 0)], largura=200, nome="B")])

    def test_emenda_com_reducao_recorta_so_o_trecho_estreito(self):
        r = self.reta()
        recortes = {t["nome"]: (round(t["recuo_inicio"]), round(t["recuo_fim"])) for t in r["trechos"]}
        self.assertEqual(recortes, {"A": (0, 0), "B": (regras.COMPRIMENTO_REDUCAO_MM, 0)})
        trapezio = next(c for c in r["conexoes"] if c["peca"] == regras.REDUCAO)["trapezio"]
        self.assertEqual((trapezio["x"], trapezio["y"], round(trapezio["angulo"])), (3000.0, 0.0, 0))
        self.assertEqual((trapezio["comprimento"], trapezio["largura_de"], trapezio["largura_para"]),
                         (regras.COMPRIMENTO_REDUCAO_MM, 300.0, 200.0))
        self.assertEqual((trapezio["aba_de"], trapezio["aba_para"]), (50.0, 50.0))

    def test_reducao_depois_da_curva_comeca_no_fim_do_arco(self):
        r = regras.analisar([caminho([(0, 0), (3000, 0)], largura=300, nome="A"),
                             caminho([(3000, 0), (3000, 3000)], largura=200, nome="B")])
        estreito = next(t for t in r["trechos"] if t["nome"] == "B")
        self.assertEqual(round(estreito["recuo_inicio"]), 300 + regras.COMPRIMENTO_REDUCAO_MM)  # raio 300 + redução
        trapezio = next(c for c in r["conexoes"] if c["peca"] == regras.REDUCAO)["trapezio"]
        self.assertEqual((round(trapezio["x"]), round(trapezio["y"]), round(trapezio["angulo"])), (3000, 300, 90))
        curva = next(c for c in r["conexoes"] if c["peca"].startswith(regras.CURVA))
        self.assertEqual(curva["largura"], 300)  # a curva é da seção maior

    def test_te_com_ramal_estreito_nao_tem_peca_separada(self):
        r = regras.analisar([caminho([(0, 0), (6000, 0)], largura=300), caminho([(3000, 0), (3000, 2000)], largura=100)])
        reducao = next(c for c in r["conexoes"] if c["peca"] == regras.REDUCAO)
        self.assertNotIn("trapezio", reducao)  # a boca do tê já sai na largura do ramal

    def test_contorno_tem_as_bordas_inclinadas(self):
        c = regras.contorno_2d(self.reta())
        inclinadas = sorted(l for l in c["linhas"] if l[0] != l[2] and l[1] != l[3])
        self.assertEqual(inclinadas, [(3000.0, -150.0, 3300.0, -100.0), (3000.0, 150.0, 3300.0, 100.0)])
        bordas_estreitas = [l for l in c["linhas"] if l[1] == l[3] == 100.0]
        self.assertEqual([min(l[0], l[2]) for l in bordas_estreitas], [3300.0])

    def test_blocos_3d_da_reducao(self):
        trapezio = next(c for c in self.reta()["conexoes"] if c["peca"] == regras.REDUCAO)["trapezio"]
        fundo, *abas = regras.faces_da_reducao(trapezio)
        self.assertEqual(fundo["pontos"], [(0.0, -150.0, 0.0), (300.0, -100.0, 0.0), (300.0, 100.0, 0.0),
                                           (0.0, 150.0, 0.0)])
        self.assertEqual(fundo["espessura"], (0.0, 0.0, regras.ESPESSURA_MM))
        self.assertEqual(len(abas), 2)
        self.assertEqual(sorted(p[2] for p in abas[0]["pontos"]), [0.0, 0.0, 50.0, 50.0])
        self.assertGreater(abas[0]["espessura"][1], 0)  # aba do lado -y engrossa para dentro (+y)
        self.assertLess(abas[1]["espessura"][1], 0)


class TestContorno(unittest.TestCase):
    """Bandeja na planta em linha dupla, com as curvas em arco e os tês fechados."""

    def test_curva_tem_dois_arcos_e_as_bordas_param_no_recorte(self):
        c = regras.contorno_2d(regras.analisar([caminho([(0, 0), (3000, 0), (3000, 3000)], largura=200)]))
        self.assertEqual(sorted(a[2] for a in c["arcos"]), [100.0, 300.0])
        bordas = [l for l in c["linhas"] if l[1] == l[3] and abs(l[1]) == 100.0]  # bordas do trecho horizontal
        self.assertEqual(sorted(round(max(l[0], l[2])) for l in bordas), [2800, 2800])
        self.assertEqual(len(c["linhas"]), 4 + 2)  # 2 bordas por trecho e o fechamento das 2 pontas

    def test_te_fecha_o_lado_sem_derivacao(self):
        c = regras.contorno_2d(regras.analisar([caminho([(0, 0), (6000, 0)]), caminho([(3000, 0), (3000, 2000)])]))
        fechamentos = [l for l in c["linhas"] if l[1] == l[3] == -100.0 and 2900 <= l[0] <= 3100 and 2900 <= l[2] <= 3100]
        self.assertEqual(len(fechamentos), 1)
        self.assertEqual(c["arcos"], [])

    def test_ramal_mais_estreito_fecha_o_resto_do_lado(self):
        # principal de 300 mm, ramal de 100 mm subindo: o lado de cima do quadrado fica aberto só 100 mm
        r = regras.analisar([caminho([(0, 0), (6000, 0)], largura=300), caminho([(3000, 0), (3000, 2000)], largura=100)])
        c = regras.contorno_2d(r)
        de_cima = sorted((round(min(l[0], l[2])), round(max(l[0], l[2])))
                         for l in c["linhas"] if l[1] == l[3] == 150.0 and 2850 <= min(l[0], l[2]) and max(l[0], l[2]) <= 3150)
        self.assertEqual(de_cima, [(2850, 2950), (3050, 3150)])
        te = next(x for x in r["conexoes"] if x["peca"] == regras.TE)
        self.assertEqual(te["quadrado"]["aberturas"], {90.0: 100.0})

    def test_cruzeta_fica_toda_aberta(self):
        r = regras.analisar([caminho([(-3000, 0), (0, 0), (3000, 0)]), caminho([(0, -3000), (0, 0), (0, 3000)])])
        c = regras.contorno_2d(r)
        self.assertEqual(len(c["linhas"]), 4 * 2 + 4)  # 4 trechos com 2 bordas e 4 terminais


class TestBlocosDaDerivacao(unittest.TestCase):
    def test_te_tem_fundo_e_aba_no_lado_fechado(self):
        blocos = regras.blocos_da_derivacao({"lado": 200, "angulo": 0.0, "fechados": [270.0], "aberturas": {}}, 50)
        self.assertEqual(blocos, [(-100.0, -100.0, 0.0, 200.0, 200.0, regras.ESPESSURA_MM),
                                  (-100.0, -100.0, 0.0, 200.0, regras.ESPESSURA_MM, 50.0)])

    def test_ramal_estreito_deixa_aba_dos_dois_lados_dele(self):
        blocos = regras.blocos_da_derivacao({"lado": 300, "angulo": 0.0, "fechados": [], "aberturas": {90.0: 100.0}}, 50)
        abas = blocos[1:]
        self.assertEqual([(b[0], round(b[0] + b[3])) for b in abas], [(-150.0, -50), (50.0, 150)])
        self.assertTrue(all(b[1] == 150.0 - regras.ESPESSURA_MM for b in abas))

    def test_cruzeta_so_tem_o_fundo(self):
        self.assertEqual(len(regras.blocos_da_derivacao({"lado": 200, "angulo": 0.0, "fechados": []}, 50)), 1)


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

    def test_ajustes_personalizados_de_vao_pendente_e_tipo(self):
        c = dict(
            caminho([(0, 0), (6000, 0)], largura=200, altura=2200.0),
            vao_suporte=1000.0,
            distancia_no=300.0,
            pendente=600.0,
            folga_perfilado=150.0,
            tipo_suporte="pendural",
        )
        resultado = regras.analisar([c])
        suportes = resultado["suportes"]
        # De 300 a 5700 mm (5400 mm) com vão máx 1000 mm -> 6 intervalos -> 7 suportes
        self.assertEqual(len(suportes), 7)
        self.assertAlmostEqual(suportes[0]["x"], 300.0)
        self.assertAlmostEqual(suportes[-1]["x"], 5700.0)
        self.assertEqual(suportes[0]["pendente"], 600.0)
        self.assertEqual(suportes[0]["tipo_suporte"], "pendural")
        self.assertEqual(suportes[0]["folga_perfilado"], 150.0)

        itens = {(i["grupo"], i["item"]): i["quantidade"] for i in regras.materiais(resultado, pe_direito_mm=3000.0)}
        self.assertEqual(itens[("Suportes", "Suporte suspenso (pendural central)")], 7)
        # 7 suportes * 0,60 m de pendente fixo = 4,20 m
        self.assertEqual(itens[("Suportes", "Vergalhão roscado 3/8\"")], 4.2)

        blocos_pend = regras.blocos_do_suporte(200, 2200, 3000, pendente_mm=600.0, tipo_suporte="pendural")
        self.assertEqual(len(blocos_pend), 2)
        # Topo do tirante = base (2200) + pendente (600) = 2800
        self.assertEqual(blocos_pend[1][2] + blocos_pend[1][5], 2800.0)

        blocos_mf = regras.blocos_do_suporte(200, 2200, 3000, tipo_suporte="mao_francesa")
        self.assertEqual(len(blocos_mf), 2)


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
        self.assertEqual(itens[("Bandejas e leitos", "Redução", "Eletrocalha perfurada 300x50 mm para 200x50 mm")], 1)
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
        nivel = object()  # o pavimento onde os símbolos entram (nível ativo do BIM, selecionado ou ativo)
        with mock.patch.object(self.servico.pavimentos, "pavimento_do_objeto", return_value=None), \
                mock.patch.object(self.servico.pavimentos, "pavimento_para_insercao", return_value=nivel), \
                mock.patch.object(self.servico.pavimentos, "arquivar") as arquivar:
            marcadas = self.servico.marcar(doc, [a, Objeto("sem pontos")], tipo="leito", largura=300, aba=100,
                                           altura=2500, tampa=True)
            self.servico.marcar(doc, [b])
        self.assertEqual(marcadas, [a])
        self.assertEqual([c.args for c in arquivar.call_args_list], [(doc, a, nivel), (doc, b, nivel)])
        self.assertEqual((a.TipoBandeja, a.Largura, a.Aba, a.AlturaBandeja, a.Tampa), ("leito", 300.0, 100.0, 2500.0, True))
        self.assertEqual(a.ViewObject.LineColor, self.servico.COR_BANDEJA)
        self.assertEqual(self.servico.listar(doc), [a, b])
        pavs = {"A": "Térreo", "B": "Superior"}
        with mock.patch.object(self.servico, "_nome_pavimento", lambda doc, obj: pavs[obj.Name]):
            resultado = self.servico.analisar(doc)
        self.assertEqual(sorted(resultado), ["Superior", "Térreo"])
        self.assertIn("Curva horizontal 90°", pecas(resultado["Térreo"]))
        self.assertEqual(resultado["Superior"]["trechos"][0]["tipo"], "eletrocalha_perfurada")


class DocumentoFalso:
    def __init__(self, *objetos):
        self.Objects = list(objetos)

    def addObject(self, tipo, nome):
        obj = Objeto(nome, ViewObject=types.SimpleNamespace())
        self.Objects.append(obj)
        return obj

    def getObject(self, nome):
        return next((o for o in self.Objects if o.Name == nome), None)

    def removeObject(self, nome):
        self.Objects = [o for o in self.Objects if o.Name != nome]

    def recompute(self):
        pass


class TestServicoJuncoes(TestServico):
    """Junções gravadas nas linhas, peças no 3D e contorno na planta, com o FreeCAD simulado."""

    def setUp(self):
        super().setUp()
        fc = sys.modules["FreeCAD"]
        fc.Vector = lambda x=0.0, y=0.0, z=0.0: types.SimpleNamespace(x=x, y=y, z=z)
        self.pavimento = mock.patch.multiple(
            self.servico.pavimentos, pavimento_do_objeto=mock.DEFAULT, elevacao_do_objeto=mock.DEFAULT,
            guardar_3d=mock.DEFAULT, por_nome=mock.DEFAULT, elevacao=mock.DEFAULT)
        falsos = self.pavimento.start()
        falsos["pavimento_do_objeto"].return_value = None
        falsos["elevacao_do_objeto"].return_value = 0.0
        falsos["por_nome"].return_value = None

    def tearDown(self):
        self.pavimento.stop()
        super().tearDown()

    def bandeja(self, nome, pontos, largura=200.0):
        obj = self.linha(nome, pontos)
        obj.Placement.inverse = lambda: types.SimpleNamespace(multVec=lambda p: p)
        obj.__dict__.update(TipoBandeja="eletrocalha_perfurada", Largura=largura, Aba=50.0, AlturaBandeja=2800.0,
                            Tampa=False, Label=nome)
        return obj

    def test_encaixar_grava_as_pontas_nas_linhas(self):
        a, b = self.bandeja("A", [(0, 0), (6000, 0)]), self.bandeja("B", [(3000, 250), (3000, 3000)])
        doc = DocumentoFalso(a, b)
        self.assertEqual(self.servico.encaixar(doc), 1)
        self.assertEqual([(p.x, p.y, p.z) for p in b.Points], [(3000.0, 0.0, 0.0), (3000.0, 3000.0, 0.0)])
        self.assertEqual([(p.x, p.y) for p in a.Points], [(0.0, 0.0), (6000.0, 0.0)])  # a outra não muda

    def test_peca_3d_so_quando_ha_curva_ou_te(self):
        doc = DocumentoFalso(self.bandeja("A", [(0, 0), (3000, 0), (3000, 3000)]))
        self.servico.gerar_3d(doc)
        pecas_3d = [o for o in doc.Objects if hasattr(o, "conexoes_3d_de")]
        self.assertEqual(len(pecas_3d), 1)
        self.assertTrue(any(o.Name == "A_3D" for o in doc.Objects))
        self.servico.gerar_3d(doc)  # de novo: substitui, não duplica
        self.assertEqual(len([o for o in doc.Objects if hasattr(o, "conexoes_3d_de")]), 1)
        reta = DocumentoFalso(self.bandeja("R", [(0, 0), (3000, 0)]))
        self.servico.gerar_3d(reta)
        self.assertEqual([o for o in reta.Objects if hasattr(o, "conexoes_3d_de")], [])

    def test_reducao_entra_nas_pecas_3d(self):
        doc = DocumentoFalso(self.bandeja("A", [(0, 0), (3000, 0)], largura=300.0),
                             self.bandeja("B", [(3000, 0), (6000, 0)], largura=200.0))
        part = sys.modules["Part"]
        part.makePolygon.reset_mock()
        self.servico.gerar_3d(doc)
        self.assertEqual(len([o for o in doc.Objects if hasattr(o, "conexoes_3d_de")]), 1)
        self.assertEqual(part.makePolygon.call_count, 3)  # fundo e duas abas

    def test_contorno_tem_uma_aresta_por_linha_e_por_arco(self):
        part = sys.modules["Part"]
        part.makeLine.reset_mock()
        part.ArcOfCircle.reset_mock()
        doc = DocumentoFalso(self.bandeja("A", [(0, 0), (3000, 0), (3000, 3000)]))
        self.assertEqual(self.servico.desenhar_contorno(doc), 1)
        esperado = regras.contorno_2d(regras.analisar([caminho([(0, 0), (3000, 0), (3000, 3000)])]))
        self.assertEqual(part.makeLine.call_count, len(esperado["linhas"]))
        self.assertEqual(part.ArcOfCircle.call_count, len(esperado["arcos"]))
        self.assertEqual(len([o for o in doc.Objects if hasattr(o, "contorno_bandejas_de")]), 1)
        self.servico.desenhar_contorno(doc)
        self.assertEqual(len([o for o in doc.Objects if hasattr(o, "contorno_bandejas_de")]), 1)


class TestSnapNaBorda(unittest.TestCase):
    def test_ponto_na_borda_do_lado_do_cursor(self):
        from freecad.Circuits.core import bandejas as b
        pontos = [(0, 0), (4000, 0), (4000, 3000)]
        self.assertEqual(b.ponto_na_borda(pontos, 200, (1000, 30)), ((1000.0, 100.0), 30.0))
        self.assertEqual(b.ponto_na_borda(pontos, 200, (1000, -30)), ((1000.0, -100.0), 30.0))
        (x, y), _ = b.ponto_na_borda(pontos, 200, (3950, 2000))  # no trecho vertical, lado de dentro
        self.assertEqual((round(x), round(y)), (3900, 2000))

    def test_eletrocalha_sob_o_cursor(self):
        from freecad.Circuits.core import bandejas as b
        larga = {"pontos": [(0, 0), (5000, 0)], "largura": 600, "nome": "larga"}
        estreita = {"pontos": [(0, 1000), (5000, 1000)], "largura": 100, "nome": "estreita"}
        caminho, ponto = b.bandeja_sob_o_cursor([larga, estreita], (2000, 950))
        self.assertEqual((caminho["nome"], ponto), ("estreita", (2000.0, 950.0)))
        self.assertIsNone(b.bandeja_sob_o_cursor([larga, estreita], (2000, 600)))  # entre as duas

