"""Desenho de um circuito do unifilar: disjuntor com arco, DR, condutores e textos."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import unifilar as u

TOMADA = {"N_circuito": "2", "Destino": "Tomadas sala", "Potencia": "1200", "Cabo": "2.5", "Disjuntor": "16",
          "Curva": "C", "Fase_R": "False", "Fase_S": "True", "Fase_T": "False", "Neutro": "True", "Terra": "True",
          "DR": "True", "Corrente_DR": ""}


class TestGeometria(unittest.TestCase):
    def test_disjuntor_tem_dois_terminais_e_o_arco(self):
        g = u.geometria(100)
        self.assertEqual(g["circulos"], [(100.0, 0.0, 8.0), (200.0, 0.0, 8.0)])
        self.assertEqual(g["arcos"], [(150.0, 0.0, 50.0, 0.0, 180.0)])  # meia volta por cima, entre os terminais
        self.assertEqual(g["linhas"][0], (0.0, 0.0, 92.0, 0.0))  # do barramento até o primeiro terminal

    def test_dr_interrompe_a_linha(self):
        sem, com = u.geometria(100), u.geometria(100, dr=True)
        self.assertEqual(len(com["linhas"]) - len(sem["linhas"]), 5)  # um trecho a mais e os 4 lados
        horizontais = [l for l in com["linhas"] if l[1] == l[3] == 0.0]
        self.assertFalse(any(l[0] < u.X_DR * 100 + 1 < l[2] for l in horizontais))  # nada passa por dentro

    def test_um_traco_por_condutor(self):
        def tracos(**opcoes):
            g = u.geometria(100, **opcoes)
            return [l for l in g["linhas"] if l[0] == l[2] and l[0] >= u.X_CONDUTORES * 100 - 1]
        self.assertEqual(len(tracos(fases=1, neutro=True, terra=True)), 3)
        self.assertEqual(len(tracos(fases=3, neutro=False, terra=True)), 4)
        self.assertEqual(len(tracos(fases=2, neutro=False, terra=False)), 2)

    def test_seta_e_texto_depois_da_ponta(self):
        g = u.geometria(100)
        fim = u.COMPRIMENTO * 100
        self.assertEqual(sum(1 for l in g["linhas"] if l[0] == fim and l[1] == 0.0), 2)
        self.assertGreater(g["textos"]["numero"][0], fim)


class TestTextos(unittest.TestCase):
    def test_circuito_de_tomadas(self):
        self.assertEqual(u.textos(TOMADA), {
            "protecao": "C16A", "fases": "S", "dr": "DR", "sensibilidade": "30mA", "secao": "#2,5 mm²",
            "potencia": "1200 W", "numero": "C2", "descricao": "Tomadas sala",
        })
        self.assertEqual(u.condutores_do_circuito(TOMADA), (1, True, True))

    def test_sem_dr_e_sem_disjuntor_usa_a_corrente(self):
        circuito = dict(TOMADA, DR="False", Disjuntor="", Corrente="12.5", Potencia="0")
        textos = u.textos(circuito)
        self.assertEqual(textos["protecao"], "12.5A")
        self.assertNotIn("dr", textos)
        self.assertNotIn("potencia", textos)

    def test_bifasico_sem_neutro(self):
        chuveiro = dict(TOMADA, Fase_R="True", Neutro="False", Corrente_DR="30")
        self.assertEqual(u.condutores_do_circuito(chuveiro), (2, False, True))
        self.assertEqual(u.textos(chuveiro)["fases"], "RS")
        # neutro em branco: só nos monofásicos
        self.assertEqual(u.condutores_do_circuito(dict(chuveiro, Neutro="")), (2, False, True))
        self.assertEqual(u.condutores_do_circuito(dict(TOMADA, Neutro="")), (1, True, True))


def _grupo(numero, fase, corrente, disjuntor, grupo="DR1", **extra):
    c = dict(TOMADA, N_circuito=str(numero), Fase_R=str(fase == "R"), Fase_S=str(fase == "S"),
             Fase_T=str(fase == "T"), Corrente=str(corrente), Disjuntor=str(disjuntor), Grupo_DR=grupo)
    c.update(extra)
    return c


class TestGrupoDR(unittest.TestCase):
    def test_grupo_fica_na_posicao_do_primeiro(self):
        c1, c2, c3, c4 = (_grupo(1, "R", 10, 16), _grupo(2, "R", 5, 10, grupo=""), _grupo(3, "S", 8, 16),
                          _grupo(4, "T", 4, 10, grupo="DR2"))
        blocos = u.blocos([c1, c2, c3, c4])
        self.assertEqual([b[0] for b in blocos], ["grupo", "circuito", "grupo"])
        self.assertEqual((blocos[0][1], [c["N_circuito"] for c in blocos[0][2]]), ("DR1", ["1", "3"]))
        self.assertEqual(blocos[1][1]["N_circuito"], "2")
        self.assertEqual(blocos[2][1], "DR2")

    def test_circuito_do_grupo_nao_tem_dr_proprio(self):
        textos = u.textos(_grupo(1, "R", 10, 16))
        self.assertNotIn("dr", textos)
        self.assertNotIn("sensibilidade", textos)
        self.assertEqual(u.textos(TOMADA)["sensibilidade"], "30mA")
        self.assertEqual(u.textos(dict(TOMADA, Corrente_DR="30mA"))["sensibilidade"], "30mA")  # sem "mAmA"

    def test_geometria_do_ramo_e_do_sub_barramento(self):
        g = u.geometria_grupo_dr(100, 500, 3)
        sub = u.X_SUB_BARRAMENTO * 100
        self.assertEqual(g["inicio_circuitos"], sub)
        self.assertIn((sub, 0.0, sub, -1000), g["linhas"])  # do primeiro ao terceiro circuito
        self.assertEqual(len(g["circulos"]), 3)  # um ponto de ligação por circuito
        self.assertEqual(g["linhas"][0], (0.0, 0.0, u.X_DR_GRUPO * 100, 0.0))
        um = u.geometria_grupo_dr(100, 500, 1)
        self.assertFalse(any(l[0] == l[2] == sub for l in um["linhas"]))  # sem sub-barramento com um só
        self.assertEqual(um["circulos"], [])

    def test_textos_do_dr_do_grupo(self):
        membros = [_grupo(1, "R", 18, 20), _grupo(3, "R", 12, 16)]
        self.assertEqual(u.textos_grupo_dr("DR1", membros), {"dr": "DR", "especificacao": "2P 40 A, 30mA",
                                                            "nome": "DR1"})
        tres_fases = membros + [_grupo(5, "S", 5, 10), _grupo(7, "T", 5, 10)]
        self.assertTrue(u.textos_grupo_dr("DR1", tres_fases)["especificacao"].startswith("4P 40 A"))


class TestIDR(unittest.TestCase):
    def test_sem_idr_a_linha_vai_direto_ao_barramento(self):
        self.assertEqual(u.entrada_com_idr(10, None), {"linhas": [(130, 25, 180, 25)], "textos": []})

    def test_idr_interrompe_a_linha_depois_do_dps(self):
        idr = {"especificacao": "4P 63 A, 30mA"}
        e = u.entrada_com_idr(10, idr)
        horizontais = [l for l in e["linhas"] if l[1] == l[3] == 25]
        self.assertEqual(horizontais, [(130, 25, u.X_IDR * 10, 25), ((u.X_IDR + u.LARGURA_IDR) * 10, 25, 180, 25)])
        self.assertGreater(u.X_IDR, 15)  # depois do DPS
        self.assertEqual(len(e["linhas"]), 6)
        self.assertEqual([t[2] for t in e["textos"]], ["IDR", "4P 63 A, 30mA"])


class TestServico(unittest.TestCase):
    MODULOS = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Spreadsheet", "Sketcher")
    RECARREGAR = ("freecad.Circuits.services.unifilar", "freecad.Circuits.services.cabos",
                  "freecad.Circuits.services.planilhas", "freecad.Circuits.services.pavimentos",
                  "freecad.Circuits.services.estilo", "freecad.Circuits.services.tomadas",
                  "freecad.Circuits.services.documento", "freecad.Circuits.objects.ponto",
                  "freecad.Circuits.services.gerador")

    def setUp(self):
        self.patch = mock.patch.dict(sys.modules, {nome: mock.MagicMock(name=nome) for nome in self.MODULOS})
        self.patch.start()
        for nome in self.RECARREGAR:
            sys.modules.pop(nome, None)
        self.servico = importlib.import_module("freecad.Circuits.services.unifilar")

    def tearDown(self):
        for nome in self.RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def test_desenha_o_sketch_e_os_textos(self):
        doc, grupo = mock.MagicMock(), mock.MagicMock()
        sketch = doc.addObject.return_value
        part = sys.modules["Part"]
        with mock.patch.object(self.servico, "add_texto") as texto:
            self.servico.desenhar_circuito(doc, TOMADA, mock.MagicMock(), 100, grupo)
        doc.addObject.assert_called_once_with("Sketcher::SketchObject", "Circuito")
        g = u.geometria(100, dr=True, fases=1, neutro=True, terra=True)
        self.assertEqual(sketch.addGeometry.call_count, len(g["linhas"]) + len(g["arcos"]) + len(g["circulos"]))
        self.assertEqual(part.ArcOfCircle.call_count, 1)
        grupo.addObject.assert_called_once_with(sketch)
        self.assertEqual(sorted(c.args[0] for c in texto.call_args_list), sorted(u.textos(TOMADA).values()))

    def test_grupo_de_dr_no_diagrama(self):
        doc, criados = self._doc()
        app = sys.modules["FreeCAD"]

        class V(tuple):
            def __new__(cls, x=0, y=0, z=0):
                return tuple.__new__(cls, (x, y, z))

            def __add__(self, o):
                return V(*(a + b for a, b in zip(self, o)))
        app.Vector.side_effect = V
        grupo = mock.MagicMock()
        circuitos = [_grupo(1, "R", 10, 16), _grupo(2, "R", 5, 10, grupo=""), _grupo(3, "S", 8, 16)]
        with mock.patch.object(self.servico.planilhas, "ler_circuitos_completos", return_value=circuitos), \
                mock.patch.object(self.servico, "desenhar_circuito") as circuito, \
                mock.patch.object(self.servico, "add_texto") as texto:
            self.assertEqual(self.servico._desenhar_circuitos(doc, 10, grupo, mock.MagicMock()), 3)
        inicios = [(c.args[1]["N_circuito"], c.args[2]) for c in circuito.call_args_list]
        sub = 180 + u.X_SUB_BARRAMENTO * 10
        self.assertEqual(inicios, [("1", V(sub, 25, 0)), ("3", V(sub, -25, 0)), ("2", V(180, -75, 0))])
        self.assertEqual(criados[0].grupo_dr, "DR1")
        self.assertIn("4P 25 A, 30mA", [c.args[0] for c in texto.call_args_list])  # R e S: tetrapolar
        # o barramento liga o grupo (y = 25) direto ao circuito 2 (y = −75)
        linha = sys.modules["Draft"].make_line
        self.assertEqual([c.args for c in linha.call_args_list], [(V(180, 25, 0), V(180, -75, 0))])

    def _doc(self, *objetos):
        doc = mock.MagicMock()
        doc.Objects = list(objetos)
        criados = []

        def add(tipo, nome):
            obj = mock.MagicMock(name=nome, TypeId=tipo, Group=[])
            criados.append(obj)
            return obj
        doc.addObject.side_effect = add
        return doc, criados

    def test_sem_gerador_calculado_nao_desenha(self):
        doc, criados = self._doc()
        with mock.patch.object(self.servico.servico_gerador, "planilha", return_value=None):
            self.assertIsNone(self.servico.gerar_diagrama_gerador(doc))
        self.assertEqual(criados, [])

    def test_com_gerador_calculado_recria_o_diagrama_da_transferencia(self):
        antigo = mock.MagicMock(spec=["Name", "Group", "removeObjectsFromDocument", "diagrama_gerador"], Group=[])
        antigo.Name = "diagrama_antigo"
        doc, criados = self._doc(antigo)
        servico_gerador = self.servico.servico_gerador
        resumo = {"Gerador [kVA]": "180", "Disjuntor [A]": "320"}
        with mock.patch.object(servico_gerador, "planilha", return_value=mock.MagicMock(Name="Cargas_gerador")), \
                mock.patch.object(servico_gerador, "ler_resumo", return_value=resumo), \
                mock.patch.object(servico_gerador, "cargas_no_gerador", return_value=["QGBT"]), \
                mock.patch.object(servico_gerador, "simbolo_do_gerador", return_value=None), \
                mock.patch.object(self.servico, "add_texto") as texto:
            grupo = self.servico.gerar_diagrama_gerador(doc, 10)
        doc.removeObject.assert_called_once_with("diagrama_antigo")
        self.assertEqual(grupo.diagrama_gerador, "Cargas_gerador")
        self.assertEqual([c.args[0] for c in doc.addObject.call_args_list],
                         ["App::DocumentObjectGroup", "Sketcher::SketchObject"])
        escritos = [c.args[0] for c in texto.call_args_list]
        self.assertIn("QTA 320 A", escritos)
        self.assertIn("QGBT", escritos)

    def test_transferencia_ligada_na_entrada_do_quadro_geral(self):
        quadro = mock.MagicMock(spec=["Name", "Label", "quadro"])
        quadro.Name, quadro.Label = "Sheet", "QGBT"
        diagrama = mock.MagicMock(spec=["quadro_origem", "base_diagrama"], quadro_origem="Sheet")
        diagrama.base_diagrama = types.SimpleNamespace(x=0.0, y=-1000.0)
        doc, _ = self._doc(quadro, diagrama)
        app = sys.modules["FreeCAD"]
        app.Vector.side_effect = lambda x=0, y=0, z=0: types.SimpleNamespace(x=x, y=y, z=z)
        servico_gerador = self.servico.servico_gerador
        with mock.patch.object(servico_gerador, "planilha", return_value=mock.MagicMock(Name="Cargas_gerador")), \
                mock.patch.object(servico_gerador, "ler_resumo", return_value={"Gerador [kVA]": "180"}), \
                mock.patch.object(servico_gerador, "cargas_no_gerador", return_value=["QGBT"]), \
                mock.patch.object(servico_gerador, "simbolo_do_gerador", return_value=None), \
                mock.patch.object(self.servico.planilhas, "ler_quadro", return_value={"origem": "QTA"}), \
                mock.patch.object(self.servico, "_deslocar") as deslocar, \
                mock.patch.object(self.servico, "add_texto") as texto:
            self.servico.gerar_diagrama_gerador(doc, 10)
        posicao = deslocar.call_args.args[1]
        self.assertEqual((posicao.x, posicao.y), (-320, -1000 + 25 + 20))  # saída (y = −2 h) na entrada (2,5 h)
        self.assertIn("Alimenta QGBT", [c.args[0] for c in texto.call_args_list])

    def test_multifilar_recria_um_grupo_por_quadro(self):
        quadro = mock.MagicMock(spec=["Name", "Label", "quadro"])
        quadro.Name, quadro.Label = "Sheet", "QD1"
        antigo = mock.MagicMock(spec=["Name", "Group", "removeObjectsFromDocument", "multifilar_de"], Group=[],
                                multifilar_de="Sheet")
        antigo.Name = "multifilar_velho"
        doc, criados = self._doc(antigo)
        circuito = {"N_circuito": "1", "Destino": "Tomadas", "Potencia": "1000", "Fase_R": "True", "Fase_S": "False",
                    "Fase_T": "False", "DR": "True", "Neutro": "True", "Terra": "True", "Cabo": "2.5",
                    "Disjuntor": "16", "Curva": "C", "Corrente_DR": "30"}
        with mock.patch.object(self.servico.planilhas, "ler_quadro", return_value={"numero_fases": "3"}), \
                mock.patch.object(self.servico.planilhas, "ler_circuitos_completos", return_value=[circuito]), \
                mock.patch.object(self.servico, "add_texto") as texto:
            self.assertEqual(self.servico.gerar_multifilares(doc, [quadro], 10), 1)
        doc.removeObject.assert_called_once_with("multifilar_velho")
        grupo = criados[0]
        self.assertEqual(grupo.multifilar_de, "Sheet")
        escritos = [c.args[0] for c in texto.call_args_list]
        self.assertIn("C1", escritos)
        self.assertIn("30mA", escritos)  # ao lado do retângulo do DR
        descricao = next(c for c in texto.call_args_list if c.args[0] == "Tomadas")
        self.assertEqual(descricao.args[2], 0.0)  # dentro do retângulo do circuito, na horizontal


if __name__ == "__main__":
    unittest.main()
