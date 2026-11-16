"""Sequência pontos da planta -> circuitos -> planilha do quadro, com o FreeCAD simulado.

O FreeCAD real é coberto por ``tests/gui/smoke_gui.py``; aqui uma planilha e um
documento falsos conferem a lógica de gravação das linhas.
"""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet")
SERVICOS = ("freecad.Circuits.services.circuitos", "freecad.Circuits.services.planilhas",
            "freecad.Circuits.services.tomadas", "freecad.Circuits.services.documento")


class PlanilhaFalsa:
    Label = Name = "QD1"

    def __init__(self, fases="3"):
        self.celulas = {"G3": fases}
        self.aliases = {"numero_fases": "G3", "potencia_instalada": "M3"}

    def set(self, celula, valor):
        self.celulas[celula] = valor[1:] if valor.startswith("'") else valor

    def get(self, celula):
        celula = self.aliases.get(celula, celula)
        if celula not in self.celulas:
            raise ValueError(celula)
        return self.celulas[celula]

    def getUsedCells(self):
        return list(self.celulas)

    def getCellFromAlias(self, alias):
        return self.aliases[alias]


def objeto_ponto(simbolo, circuito, potencia, tensao="127V", ligacao="F+N", quadro=""):
    return types.SimpleNamespace(
        Proxy=types.SimpleNamespace(Type="Ponto"), Label=simbolo, Simbolo=simbolo, Circuito=circuito,
        Quadro=quadro, Potencia=potencia, FatorPotencia=1.0, Tensao=tensao, Ligacao=ligacao, Descricao=simbolo,
    )


class TestSequenciaQuadro(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in SERVICOS:
            sys.modules.pop(nome, None)
        self.circuitos = importlib.import_module("freecad.Circuits.services.circuitos")
        self.planilhas = importlib.import_module("freecad.Circuits.services.planilhas")

    def tearDown(self):
        for nome in SERVICOS:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def documento(self, *objetos):
        return types.SimpleNamespace(Objects=list(objetos), recompute=lambda: None)

    def test_pontos_viram_linhas_do_quadro(self):
        quadro = PlanilhaFalsa()
        doc = self.documento(
            objeto_ponto("luz_teto", "1", 100), objeto_ponto("luz_teto", "1", 100),
            objeto_ponto("tomada_baixa", "2", 600),
            objeto_ponto("chuveiro", "3", 5500, "220V", "F+F"),
            objeto_ponto("tomada_baixa", "9", 100, quadro="OUTRO"),  # pertence a outro quadro
        )
        gravados, avisos = self.circuitos.montar_circuitos(doc, quadro)

        self.assertEqual([c["numero"] for c in gravados], ["1", "2", "3"])
        self.assertEqual(avisos, [])
        self.assertEqual([quadro.get(f"A{linha}") for linha in (6, 7, 8)], ["1", "2", "3"])
        self.assertEqual((quadro.get("C6"), quadro.get("J6"), quadro.get("N6")), ("200", "1.5", "6"))
        self.assertEqual((quadro.get("J8"), quadro.get("N8"), quadro.get("U8")), ("4", "25", "True"))
        self.assertEqual(quadro.get("potencia_instalada"), "6.3")
        self.assertNotIn("A9", quadro.celulas)

    def test_repetir_atualiza_no_lugar_e_preserva_circuito_manual(self):
        quadro = PlanilhaFalsa()
        luz = objeto_ponto("luz_teto", "1", 100)
        doc = self.documento(luz)
        self.circuitos.montar_circuitos(doc, quadro)
        manual = dict.fromkeys(self.planilhas.layout.COLUNAS_CIRCUITO.values(), "x")
        manual["N_circuito"] = "20"
        self.assertEqual(self.planilhas.adicionar_circuito(quadro, manual), 7)

        luz.Potencia = 300
        self.circuitos.montar_circuitos(doc, quadro)
        self.assertEqual(quadro.get("C6"), "300")
        self.assertEqual(quadro.get("A7"), "20")
        self.assertEqual(self.planilhas.ultima_linha(quadro), 7)

    def test_mais_de_quatro_circuitos_nao_se_sobrescrevem(self):
        quadro = PlanilhaFalsa()
        doc = self.documento(*(objeto_ponto("tomada_baixa", str(n), 100) for n in range(1, 13)))
        self.circuitos.montar_circuitos(doc, quadro)
        self.assertEqual([quadro.get(f"A{linha}") for linha in range(6, 18)], [str(n) for n in range(1, 13)])

    def test_circuito_acima_das_tabelas_vira_aviso(self):
        quadro = PlanilhaFalsa()
        doc = self.documento(objeto_ponto("ponto_forca", "1", 90000))
        gravados, avisos = self.circuitos.montar_circuitos(doc, quadro)
        self.assertEqual(gravados, [])
        self.assertIn("não foi gravado", avisos[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
