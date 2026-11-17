"""Notas do projeto: formatação pura e leitura da planilha com o FreeCAD simulado."""
import importlib
import sys
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import notas

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet")
RECARREGAR = ("freecad.Circuits.services.notas", "freecad.Circuits.services.legenda",
              "freecad.Circuits.services.planilhas", "freecad.Circuits.objects.ponto")


class TestFormatacao(unittest.TestCase):
    def test_limpar_tira_vazias_e_espacos(self):
        self.assertEqual(notas.limpar(["  a ", "", "   ", "b"]), ["a", "b"])

    def test_numera_na_ordem(self):
        self.assertEqual(notas.formatar(["Primeira.", "", "Segunda."]), [["1 - Primeira."], ["2 - Segunda."]])

    def test_nota_longa_quebra_com_recuo(self):
        bloco = notas.formatar(["palavra " * 12], largura=30)[0]
        self.assertGreater(len(bloco), 1)
        self.assertTrue(bloco[0].startswith("1 - palavra"))
        self.assertTrue(all(linha.startswith("    palavra") for linha in bloco[1:]))
        self.assertTrue(all(len(linha) <= 30 for linha in bloco))

    def test_sem_notas(self):
        self.assertEqual(notas.formatar([]), [])


class PlanilhaFalsa:
    def __init__(self, celulas):
        self.celulas = dict(celulas)
        self.notas_do_projeto = "Notas"

    def get(self, celula):
        if celula not in self.celulas:
            raise ValueError(celula)
        return self.celulas[celula]

    def getUsedCells(self):
        return list(self.celulas)


class TestServico(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.servico = importlib.import_module("freecad.Circuits.services.notas")

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def test_le_da_linha_tres_em_diante_e_pula_vazias(self):
        planilha = PlanilhaFalsa({"A1": "Notas do projeto", "A2": "instrução", "A3": "Nota um", "A5": " Nota dois ",
                                  "A12": "Nota três", "B4": "outra coluna"})
        self.assertEqual(self.servico.ler_notas(planilha), ["Nota um", "Nota dois", "Nota três"])

    def test_cria_a_planilha_uma_vez_com_exemplos(self):
        doc = mock.MagicMock()
        doc.Objects = []
        nova = self.servico.planilha_de_notas(doc)
        doc.addObject.assert_called_once_with("Spreadsheet::Sheet", "Notas")
        escritas = {chamada.args[0] for chamada in nova.set.call_args_list}
        self.assertEqual(escritas, {"A1", "A2", "A3", "A4", "A5"})

        existente = PlanilhaFalsa({})
        doc.Objects = [existente]
        self.assertIs(self.servico.planilha_de_notas(doc), existente)

    def test_sem_planilha_nao_cria_quando_nao_pedido(self):
        doc = mock.MagicMock()
        doc.Objects = []
        self.assertIsNone(self.servico.planilha_de_notas(doc, criar=False))
        doc.addObject.assert_not_called()

    def test_gerar_desenha_titulo_e_uma_anotacao_por_nota(self):
        planilha = PlanilhaFalsa({"A3": "Nota um", "A4": "Nota dois"})
        doc = mock.MagicMock()
        doc.Objects = [planilha]
        doc.getObject.return_value = None  # sem quadro de notas nem legenda
        self.assertEqual(self.servico.gerar_notas(doc), 2)
        textos = [chamada.args[0] for chamada in sys.modules["Draft"].make_text.call_args_list]
        self.assertEqual(textos, ["NOTAS", ["1 - Nota um"], ["2 - Nota dois"]])

    def test_planilha_vazia_nao_desenha(self):
        doc = mock.MagicMock()
        doc.Objects = [PlanilhaFalsa({"A1": "Notas do projeto"})]
        doc.getObject.return_value = None
        self.assertEqual(self.servico.gerar_notas(doc), 0)
        doc.addObject.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
