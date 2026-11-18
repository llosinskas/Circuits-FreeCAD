"""Planilha "Cargas do gerador" (services/gerador.py), com o FreeCAD simulado."""
import importlib
import sys
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core.functions.Predial import gerador as regras

MODULO = "freecad.Circuits.services.gerador"


class Folha:
    def __init__(self, doc):
        self.celulas = {}
        self.Label = ""
        self.Document = doc

    def addProperty(self, tipo, nome, grupo="", dica=""):
        setattr(self, nome, "")

    def set(self, celula, valor):
        self.celulas[celula] = valor

    def getContents(self, celula):
        return self.celulas.get(celula, "")

    def getUsedCells(self):
        return list(self.celulas)

    def setColumnWidth(self, coluna, largura):
        pass


class Documento:
    def __init__(self):
        self.Objects = []

    def addObject(self, tipo, nome):
        folha = Folha(self)
        folha.Name = nome
        self.Objects.append(folha)
        return folha

    def recompute(self):
        pass


class Quadro:
    def __init__(self, label):
        self.Label = label


class TestPlanilhaDoGerador(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.dict(sys.modules, {"Spreadsheet": mock.MagicMock(), "FreeCAD": mock.MagicMock(),
                                                   "FreeCADGui": mock.MagicMock()})
        self.patch.start()
        sys.modules.pop(MODULO, None)
        self.servico = importlib.import_module(MODULO)
        self.planilhas = self.servico.planilhas
        self.doc = Documento()
        self.quadros = {}
        self.circuitos = {}
        patches = [
            mock.patch.object(self.planilhas, "listar_quadros", lambda doc: [Quadro(n) for n in self.quadros]),
            mock.patch.object(self.planilhas, "ler_quadro", lambda q: self.quadros[q.Label]),
            mock.patch.object(self.planilhas, "ler_circuitos", lambda q: self.circuitos.get(q.Label, [])),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        sys.modules.pop(MODULO, None)
        self.patch.stop()

    def test_sem_quadros_cria_com_exemplos_que_calculam(self):
        self.assertIsNone(self.servico.planilha(self.doc))
        folha, quadros = self.servico.criar(self.doc)
        self.assertEqual(quadros, 0)
        self.assertIs(self.servico.planilha(self.doc), folha)
        self.assertEqual(folha.celulas["A2"], "'Descrição")
        cargas = self.servico.ler_cargas(folha)
        self.assertEqual(len(cargas), len(regras.EXEMPLOS))
        regras.dimensionar(cargas)

    def test_uma_linha_por_quadro_com_demanda_ou_soma_dos_circuitos(self):
        self.quadros = {"QGBT": {"potencia_instalada": "80", "potencia_demanda": "56"},
                        "QD2": {"potencia_instalada": "", "potencia_demanda": ""}}
        self.circuitos = {"QD2": [{"Potencia": "1500"}, {"Potencia": "2500"}]}
        folha, quadros = self.servico.criar(self.doc)
        self.assertEqual(quadros, 2)
        cargas = self.servico.ler_cargas(folha)
        self.assertEqual([(c["descricao"], c["kw"], c["fator_demanda"]) for c in cargas],
                         [("QGBT", 80.0, 0.7), ("QD2", 4.0, 1.0)])

    def test_linha_invalida_diz_qual_e(self):
        folha, _ = self.servico.criar(self.doc)
        folha.set("E4", "'HP")
        with self.assertRaisesRegex(ValueError, "linha 4"):
            self.servico.ler_cargas(folha)

    def test_linhas_vazias_sao_puladas_e_resultado_gravado_ao_lado(self):
        folha, _ = self.servico.criar(self.doc)
        folha.set("A20", "'Chiller")
        folha.set("D20", "'30")
        cargas = self.servico.ler_cargas(folha)
        self.assertEqual(cargas[-1]["descricao"], "Chiller")
        self.servico.gravar_resultado(folha, regras.dimensionar(cargas))
        self.assertEqual(folha.celulas["K5"], "'Gerador [kVA]")
        self.assertTrue(folha.celulas["L5"].strip("'").isdigit())
        self.assertEqual(len(self.servico.ler_cargas(folha)), len(cargas))  # K e L não viram cargas


if __name__ == "__main__":
    unittest.main()
