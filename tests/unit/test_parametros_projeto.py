"""Planilha "Parâmetros do projeto": criação com os padrões e leitura (services/parametros.py)."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import parametros as regras

MODULO = "freecad.Circuits.services.parametros"


class Folha:
    def __init__(self):
        self.celulas = {}
        self.Label = ""

    def addProperty(self, tipo, nome, grupo="", dica=""):
        setattr(self, nome, "")

    def set(self, celula, valor):
        self.celulas[celula] = valor

    def getContents(self, celula):
        return self.celulas.get(celula, "")


class Documento:
    def __init__(self):
        self.Objects = []

    def addObject(self, tipo, nome):
        folha = Folha()
        folha.Name = nome
        self.Objects.append(folha)
        return folha

    def recompute(self):
        pass


class TestParametrosDoProjeto(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.dict(sys.modules, {"Spreadsheet": mock.MagicMock(), "FreeCAD": mock.MagicMock()})
        self.patch.start()
        sys.modules.pop(MODULO, None)
        self.servico = importlib.import_module(MODULO)
        self.doc = Documento()

    def tearDown(self):
        sys.modules.pop(MODULO, None)
        self.patch.stop()

    def linha_de(self, folha, chave):
        return next(c[1:] for c, v in folha.celulas.items() if c.startswith("C") and v == f"'{chave}")

    def test_sem_planilha_valem_os_padroes(self):
        self.assertIsNone(self.servico.planilha(self.doc))
        self.assertEqual(self.servico.ler(self.doc), regras.PADROES)

    def test_cria_uma_vez_com_todos_os_parametros(self):
        folha = self.servico.planilha(self.doc, criar=True)
        self.assertIs(self.servico.planilha(self.doc, criar=True), folha)
        self.assertEqual(folha.Label, "Parâmetros do projeto")
        self.assertEqual(len([c for c in folha.celulas if c.startswith("C") and c != "C2"]), len(regras.CAMPOS))
        self.assertEqual(folha.celulas[f"B{self.linha_de(folha, 'tensao_fn')}"], "'127")
        self.assertEqual(self.servico.ler(self.doc), regras.PADROES)

    def test_le_o_que_o_usuario_editou(self):
        folha = self.servico.planilha(self.doc, criar=True)
        folha.set(f"B{self.linha_de(folha, 'tensao_fn')}", "220")
        folha.set(f"B{self.linha_de(folha, 'esquema')}", "'TT")
        folha.set(f"B{self.linha_de(folha, 'queda_terminal')}", "")  # apagado: volta ao padrão
        p = self.servico.ler(self.doc)
        self.assertEqual((p["tensao_fn"], p["esquema"], p["queda_terminal"]), (220.0, "TT", 4.0))


if __name__ == "__main__":
    unittest.main()
