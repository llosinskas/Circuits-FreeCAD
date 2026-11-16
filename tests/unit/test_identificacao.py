"""Circuito e comando dos pontos: regras puras e gravação com o FreeCAD simulado."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import identificacao

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet")
SERVICOS = ("freecad.Circuits.services.identificacao", "freecad.Circuits.services.alinhamento",
            "freecad.Circuits.services.tomadas", "freecad.Circuits.services.documento")


class TestRegras(unittest.TestCase):
    def test_proximo_comando(self):
        self.assertEqual(identificacao.proximo_comando([]), "a")
        self.assertEqual(identificacao.proximo_comando(["a", "B", "", " c "]), "d")
        self.assertEqual(identificacao.proximo_comando(["b"]), "a")
        todas = [chr(codigo) for codigo in range(ord("a"), ord("z") + 1)]
        self.assertEqual(identificacao.proximo_comando(todas), "aa")

    def test_escolher_comando_mantem_a_letra_livre_do_interruptor(self):
        self.assertEqual(identificacao.escolher_comando(["c"], ["a", "b"]), "c")

    def test_escolher_comando_troca_a_letra_ocupada(self):
        self.assertEqual(identificacao.escolher_comando(["a"], ["a", "b"]), "c")
        self.assertEqual(identificacao.escolher_comando([""], []), "a")

    def test_circuitos(self):
        self.assertEqual(identificacao.ordenar_circuitos(["10", "2", "2", "", "QF1", " 1 "]), ["1", "2", "10", "QF1"])
        self.assertEqual(identificacao.proximo_circuito(["1", "2", "7", "QF1"]), "8")
        self.assertEqual(identificacao.proximo_circuito([]), "1")

    def test_texto_do_ponto(self):
        self.assertEqual(identificacao.texto_ponto("1", "a", 100), "C1 · a · 100 VA")
        self.assertEqual(identificacao.texto_ponto("2", "", 600), "C2 · 600 VA")
        self.assertEqual(identificacao.texto_ponto("1", "A"), "C1 · a")
        self.assertEqual(identificacao.texto_ponto(), "")


def objeto(nome, tipo, **propriedades):
    return types.SimpleNamespace(Name=nome, Label=nome, Proxy=types.SimpleNamespace(Type=tipo), **propriedades)


def luz(nome, circuito="1", comando=""):
    return objeto(nome, "Ponto", Simbolo="luz_teto", Circuito=circuito, Comando=comando, Quadro="", Potencia=100.0)


def tomada(nome, circuito="1"):
    return objeto(nome, "Ponto", Simbolo="tomada_baixa", Circuito=circuito, Comando="", Quadro="", Potencia=600.0)


def interruptor(nome, circuito="1", comando="a"):
    return objeto(nome, "Switch", Circuito=circuito, Comando=comando)


class TestServico(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in SERVICOS:
            sys.modules.pop(nome, None)
        self.servico = importlib.import_module("freecad.Circuits.services.identificacao")

    def tearDown(self):
        for nome in SERVICOS:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def documento(self, *objetos):
        doc = mock.MagicMock()
        doc.Objects = list(objetos)
        doc.getObject.return_value = None  # sem anotação no documento
        return doc

    def test_definir_circuito_e_quadro(self):
        a, b = tomada("T1"), tomada("T2", "5")
        doc = self.documento(a, b)
        self.assertEqual(self.servico.definir_circuito(doc, [a, b], " 3 ", "QD1"), 2)
        self.assertEqual([(o.Circuito, o.Quadro) for o in (a, b)], [("3", "QD1"), ("3", "QD1")])
        doc.commitTransaction.assert_called_once()

    def test_quadro_none_nao_altera_o_quadro(self):
        a = tomada("T1")
        a.Quadro = "QD9"
        self.servico.definir_circuito(self.documento(a), [a], "2", None)
        self.assertEqual((a.Circuito, a.Quadro), ("2", "QD9"))

    def test_tomada_em_sketch_guarda_circuito_inteiro(self):
        tug = types.SimpleNamespace(Name="Tomada", Label="Tomada", Circuito=1, tipo="tomada")
        doc = self.documento(tug)
        self.assertEqual(self.servico.definir_circuito(doc, [tug], "4"), 1)
        self.assertEqual(tug.Circuito, 4)
        self.assertEqual(self.servico.definir_circuito(doc, [tug], "QF1"), 0)
        self.assertEqual(tug.Circuito, 4)

    def test_circuitos_existentes(self):
        doc = self.documento(tomada("T1", "10"), luz("L1", "2"), interruptor("S1", "2"))
        self.assertEqual(self.servico.circuitos_existentes(doc), ["2", "10"])

    def test_ligar_interruptor_usa_letra_livre_e_o_circuito_da_luz(self):
        outra_luz, outro_interruptor = luz("L0", "1", "a"), interruptor("S0", "1", "a")
        s1, l1, l2 = interruptor("S1", "9", "a"), luz("L1", "4"), luz("L2", "4")
        doc = self.documento(outra_luz, outro_interruptor, s1, l1, l2)
        self.assertEqual(self.servico.ligar_interruptor(doc, [s1, l1, l2]), "b")
        self.assertEqual([o.Comando for o in (s1, l1, l2)], ["b", "b", "b"])
        self.assertEqual(s1.Circuito, "4")
        self.assertEqual((outra_luz.Comando, outro_interruptor.Comando), ("a", "a"))

    def test_ligar_de_novo_mantem_a_letra(self):
        s1, l1 = interruptor("S1", "1", "c"), luz("L1", "1", "c")
        doc = self.documento(luz("L0", "1", "a"), s1, l1)
        self.assertEqual(self.servico.ligar_interruptor(doc, [s1, l1]), "c")

    def test_ligar_exige_interruptor_e_ponto_de_luz(self):
        doc = self.documento()
        with self.assertRaises(ValueError):
            self.servico.ligar_interruptor(doc, [interruptor("S1"), tomada("T1")])
        with self.assertRaises(ValueError):
            self.servico.ligar_interruptor(doc, [luz("L1")])

    def test_texto_do_objeto(self):
        self.assertEqual(self.servico.texto_do_objeto(luz("L1", "1", "a")), "C1 · a · 100 VA")
        self.assertEqual(self.servico.texto_do_objeto(tomada("T1", "2")), "C2 · 600 VA")
        self.assertEqual(self.servico.texto_do_objeto(interruptor("S1", "1", "a")), "C1 · a")


if __name__ == "__main__":
    unittest.main(verbosity=2)
