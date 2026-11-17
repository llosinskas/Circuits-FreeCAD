"""Legenda: pontos do catálogo e interruptores usados na planta."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet")
RECARREGAR = ("freecad.Circuits.services.legenda", "freecad.Circuits.objects.ponto")


class TestLegenda(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.legenda = importlib.import_module("freecad.Circuits.services.legenda")

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def test_interruptores_entram_depois_dos_pontos_sem_repetir(self):
        def obj(tipo, **props):
            return types.SimpleNamespace(Proxy=types.SimpleNamespace(Type=tipo), **props)

        doc = types.SimpleNamespace(Objects=[
            obj("Switch", Tipo="Paralelo"), obj("Ponto", Simbolo="luz_teto"), obj("Switch", Tipo="Simples"),
            obj("Switch", Tipo="Paralelo"), obj("Ponto", Simbolo="tomada_baixa"),
        ])
        itens = self.legenda.itens_da_legenda(doc)
        self.assertEqual([chave for chave, _, _ in itens],
                         ["tomada_baixa", "luz_teto", "interruptor_simples", "interruptor_paralelo"])
        self.assertTrue(itens[3][2].startswith("Interruptor paralelo - "))
        self.assertEqual(len(itens[3][1]), 3)  # círculo e duas linhas

    def test_so_interruptores(self):
        doc = types.SimpleNamespace(Objects=[types.SimpleNamespace(Proxy=types.SimpleNamespace(Type="Switch"),
                                                                   Tipo="Intermediário")])
        self.assertEqual([c for c, _, _ in self.legenda.itens_da_legenda(doc)], ["interruptor_intermediario"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
