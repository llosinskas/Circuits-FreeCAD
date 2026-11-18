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
        self.assertIn("DR 30mA", escritos)
        descricao = next(c for c in texto.call_args_list if c.args[0] == "Tomadas")
        self.assertEqual(descricao.args[2], -90.0)


if __name__ == "__main__":
    unittest.main()
