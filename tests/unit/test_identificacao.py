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
            "freecad.Circuits.services.planilhas",
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

    def test_condutores_no_ponto(self):
        self.assertEqual(identificacao.condutores_no_ponto("ponto", "F+N"), "F+N+T")
        self.assertEqual(identificacao.condutores_no_ponto("ponto", "F+F"), "2F+T")
        self.assertEqual(identificacao.condutores_no_ponto("ponto", "3F"), "3F+T")
        self.assertEqual(identificacao.condutores_no_ponto("ponto", "F+N", comando="a"), "R+N+T")
        self.assertEqual(identificacao.condutores_no_ponto("interruptor", tipo_interruptor="Simples"), "F+R")
        self.assertEqual(identificacao.condutores_no_ponto("interruptor", tipo_interruptor="Paralelo"), "F+2R")
        self.assertEqual(identificacao.condutores_no_ponto("interruptor", tipo_interruptor="Intermediário"), "4R")
        self.assertEqual(identificacao.condutores_no_ponto("interruptor", tipo_interruptor="Botão de campainha"), "F+R")
        self.assertEqual(identificacao.condutores_no_ponto("interruptor", tipo_interruptor="Fotocélula"), "F+N+R")

    def test_texto_dos_cabos(self):
        self.assertEqual(identificacao.texto_cabos(2.5, "F+N+T"), "#2,5 F+N+T")
        self.assertEqual(identificacao.texto_cabos(10.0, "2F+T"), "#10 2F+T")

    def test_texto_do_quadro(self):
        self.assertEqual(identificacao.texto_quadro("QD1"), "QD1")
        self.assertEqual(identificacao.texto_quadro("QM", 1), "QM")
        self.assertEqual(identificacao.texto_quadro("CM", 12), "CM · 12 medidores")
        self.assertEqual(identificacao.texto_quadro("QC", None, "8"), "QC · C8")
        self.assertEqual(identificacao.texto_quadro(""), "")


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

    def test_cabos_pela_planilha_ou_pela_secao_minima(self):
        secoes = {("QD1", "2"): 4.0, ("", "2"): 4.0, ("QD2", "2"): 6.0}
        tomada_qd2 = tomada("T1", "2")
        tomada_qd2.Ligacao, tomada_qd2.Quadro = "F+N", "QD2"
        self.assertEqual(self.servico.texto_dos_cabos(tomada_qd2, secoes), "#6 F+N+T")
        sem_quadro = tomada("T2", "2")
        sem_quadro.Ligacao = "F+F"
        self.assertEqual(self.servico.texto_dos_cabos(sem_quadro, secoes), "#4 2F+T")
        luz = luz_ligada = objeto("L1", "Ponto", Simbolo="luz_teto", Circuito="9", Comando="b", Quadro="", Ligacao="F+N")
        self.assertEqual(self.servico.texto_dos_cabos(luz_ligada, secoes), "#1,5 R+N+T")  # sem planilha: 1,5 mm²
        chave = interruptor("S1", "9", "b")
        chave.Tipo = "Paralelo"
        self.assertEqual(self.servico.texto_dos_cabos(chave, secoes), "#1,5 F+2R")
        self.assertEqual(self.servico.texto_dos_cabos(tomada("T3", ""), secoes), "")  # sem circuito
        self.assertEqual(luz.Name, "L1")

    def test_botao_de_campainha_liga_a_campainha(self):
        botao = objeto("B1", "Ponto", Simbolo="botao_campainha", Circuito="", Comando="", Quadro="")
        campainha = objeto("C1", "Ponto", Simbolo="campainha", Circuito="3", Comando="", Quadro="", Potencia=20.0)
        fotocelula = objeto("F1", "Ponto", Simbolo="fotocelula", Circuito="", Comando="", Quadro="")
        self.assertTrue(self.servico.eh_interruptor(botao) and self.servico.eh_interruptor(fotocelula))
        self.assertFalse(self.servico.eh_ponto_de_luz(botao))
        self.assertTrue(self.servico.eh_ponto_de_luz(campainha))
        doc = self.documento(botao, campainha)
        self.assertEqual(self.servico.ligar_interruptor(doc, [botao, campainha]), "a")
        self.assertEqual((botao.Comando, botao.Circuito, campainha.Comando), ("a", "3", "a"))
        self.assertEqual(self.servico.texto_dos_cabos(botao, {}), "#1,5 F+R")
        fotocelula.Circuito = "1"
        self.assertEqual(self.servico.texto_dos_cabos(fotocelula, {}), "#1,5 F+N+R")

    def test_mapa_de_secoes(self):
        quadros = [types.SimpleNamespace(Label="QD1"), types.SimpleNamespace(Label="QD2")]
        linhas = {"QD1": [{"N_circuito": "1", "Cabo": "2.5"}, {"N_circuito": "2", "Cabo": ""}],
                  "QD2": [{"N_circuito": "1", "Cabo": "4"}]}
        with mock.patch.object(self.servico.planilhas, "listar_quadros", return_value=quadros), \
                mock.patch.object(self.servico.planilhas, "ler_circuitos_completos", side_effect=lambda q: linhas[q.Label]):
            self.assertEqual(self.servico.mapa_de_secoes(self.documento()),
                             {("QD1", "1"): 2.5, ("", "1"): 2.5, ("QD2", "1"): 4.0})

    def test_anotar_poe_os_textos_na_pasta_circuitos_do_pavimento(self):
        base = types.SimpleNamespace(x=0.0, y=0.0, z=3000.0)
        l1, t1 = luz("L1"), tomada("T1", "2")
        for obj in (l1, t1):
            obj.Placement = types.SimpleNamespace(Base=base)
        antigo = types.SimpleNamespace(Name="Texto009", identificacao_de="L1")
        doc = self.documento(l1, t1, antigo)
        pasta, chaves = mock.MagicMock(), []

        def pasta_do_pavimento(documento, obj, chave):
            chaves.append(chave)
            return pasta if obj is l1 else None
        with mock.patch.object(self.servico, "listar_simbolos", return_value=[l1, t1]), \
                mock.patch.object(self.servico, "mapa_de_secoes", return_value={}), \
                mock.patch.object(self.servico.pavimentos, "pasta_do_pavimento", side_effect=pasta_do_pavimento):
            self.assertEqual(self.servico.anotar(doc), 2)
        doc.removeObject.assert_called_once_with("Texto009")  # o texto anterior sai
        self.assertEqual(chaves, ["circuitos", "circuitos"])
        self.assertEqual(pasta.addObject.call_count, 1)
        doc.addObject.assert_called_once_with("App::DocumentObjectGroup", self.servico.NOME_GRUPO)  # T1 fora de pavimento
        self.assertTrue(self.servico.existe_anotacao(doc))
        self.assertFalse(self.servico.existe_anotacao(self.documento(l1)))

    def test_texto_dos_quadros(self):
        medicao = objeto("CM", "Ponto", Simbolo="medicao_agrupada", Descricao="CM", Medidores=12, Circuito="")
        quadro = objeto("QD", "Ponto", Simbolo="quadro_distribuicao", Descricao="QD1", Circuito="")
        self.assertEqual(self.servico.texto_do_objeto(medicao), "CM · 12 medidores")
        self.assertEqual(self.servico.texto_do_objeto(quadro), "QD1")
        self.assertFalse(self.servico.eh_ponto_de_luz(quadro))


if __name__ == "__main__":
    unittest.main(verbosity=2)
