"""Desenho de um circuito do unifilar: disjuntor com arco, DR, condutores e textos."""
import importlib
import sys
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
                  "freecad.Circuits.services.documento", "freecad.Circuits.objects.ponto")

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


if __name__ == "__main__":
    unittest.main()
