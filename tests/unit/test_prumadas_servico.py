"""Prumadas no documento (services/verticais.py, legenda, quantitativos), com o FreeCAD simulado."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import parametros

MODULOS = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Spreadsheet", "Sketcher")


def ponta(x=1000.0, y=2000.0, altura=2800.0, nome="E"):
    return {"x": x, "y": y, "diametro": "1", "altura": altura, "nome": nome}


class Base(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.dict(sys.modules, {n: mock.MagicMock(name=n) for n in MODULOS})
        self.patch.start()
        for nome in [n for n in sys.modules if n.startswith("freecad.Circuits.services")]:
            sys.modules.pop(nome, None)
        self.v = importlib.import_module("freecad.Circuits.services.verticais")
        terreo, primeiro = types.SimpleNamespace(Label="Térreo"), types.SimpleNamespace(Label="1º Pavimento")
        self.p = mock.patch.multiple(self.v.pavimentos, listar=mock.DEFAULT, elevacao=mock.DEFAULT, por_nome=mock.DEFAULT,
                                     pasta=mock.DEFAULT)
        falsos = self.p.start()
        falsos["listar"].return_value = [terreo, primeiro]
        falsos["elevacao"].side_effect = lambda pav: {"Térreo": 0.0, "1º Pavimento": 3000.0}[pav.Label]
        falsos["por_nome"].return_value = None
        self.eletrodutos = {"Térreo": {"pontas_soltas": [ponta(), ponta(x=5000.0, nome="Solta")], "avisos": []},
                            "1º Pavimento": {"pontas_soltas": [ponta(altura=-50.0, nome="F")], "avisos": []}}

    def tearDown(self):
        self.p.stop()
        for nome in [n for n in sys.modules if n.startswith("freecad.Circuits.services")]:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def com_rede(self):
        return [mock.patch.object(self.v.eletrodutos_planta, "analisar", return_value=self.eletrodutos),
                mock.patch.object(self.v.bandejas, "analisar", return_value={}),
                mock.patch.object(self.v.rede, "analisar", return_value={"verticais": [], "transicoes": []}),
                mock.patch.object(self.v.parametros, "ler", return_value=parametros.ler({}))]

    def rodar(self, funcao, *args):
        patches = self.com_rede()
        for p in patches:
            p.start()
        try:
            return funcao(*args)
        finally:
            for p in patches:
                p.stop()


class TestColeta(Base):
    def test_prumadas_entram_nas_verticais(self):
        itens = self.rodar(self.v.coletar, "doc")
        self.assertEqual(sorted((i["pavimento"], i["nivel"]) for i in itens),
                         [("1º Pavimento", "piso"), ("Térreo", "teto")])

    def test_so_a_ponta_sem_prumada_vira_aviso(self):
        avisos = self.rodar(self.v.avisos_de_pontas_soltas, "doc")
        self.assertEqual(len(avisos), 1)
        self.assertIn("Solta", avisos[0])

    def test_pontas_de_prumada_por_pavimento(self):
        pontas = self.rodar(self.v.pontas_de_prumada, "doc", "eletroduto")
        self.assertEqual(pontas, {"Térreo": [(1000.0, 2000.0)], "1º Pavimento": [(1000.0, 2000.0)]})


class TestModelo3D(Base):
    def test_uma_prumada_3d_por_ligacao(self):
        doc = mock.MagicMock()
        doc.Objects = []
        part = sys.modules["Part"]
        part.makeCylinder.reset_mock()
        self.assertEqual(self.rodar(self.v.gerar_3d_prumadas, doc), 1)
        part.makeCylinder.assert_called_once()
        raio, altura = part.makeCylinder.call_args.args[:2]
        self.assertAlmostEqual(altura, 3000.0 - 50.0 - 2800.0)  # de +2,80 no Térreo a -0,05 no 1º Pavimento


class TestLegenda(Base):
    def test_legenda_inclui_os_tipos_de_vertical(self):
        legenda = importlib.import_module("freecad.Circuits.services.legenda")
        doc = types.SimpleNamespace(Objects=[])
        itens = self.rodar(self.v.coletar, "doc")
        with mock.patch.object(self.v, "coletar", return_value=itens):
            chaves = [chave for chave, _, _ in legenda.itens_da_legenda(doc)]
        self.assertEqual(chaves, ["vertical_eletroduto_teto", "vertical_eletroduto_piso"])


class TestQuantitativos(Base):
    def test_prumadas_contadas_uma_vez_e_terminal_tirado(self):
        q = importlib.import_module("freecad.Circuits.services.quantitativos")
        itens = self.rodar(self.v.coletar, "doc")
        doc = types.SimpleNamespace(Label="Casa", FileName="", Objects=[])
        fiacao = {"fios": {}, "verticais": [], "circuitos": [], "avisos": []}
        with mock.patch.object(q.verticais, "prumadas", return_value=itens), \
                mock.patch.object(q.verticais, "pontas_de_prumada", return_value={"Térreo": [(1.0, 2.0)]}), \
                mock.patch.object(q.bandejas, "materiais_por_pavimento", return_value=[]) as bandejas, \
                mock.patch.object(q, "_componentes_por_quadro", return_value=[]), \
                mock.patch.object(q, "coletar_componentes_quadros", return_value=[]), \
                mock.patch.object(q, "_pecas_eletrodutos", return_value=[]), \
                mock.patch.object(q.rede, "analisar", return_value=fiacao):
            total = q.calcular(doc)
            por_pav = dict(q.levantar_por_pavimento(doc, fiacao))
        bandejas.assert_called_with(doc, sem_terminal={"Térreo": [(1.0, 2.0)]})
        esperado = ("Eletroduto", '1" verticais (inclui 10% de perdas)')
        self.assertEqual({(l["item"], l["especificacao"]): l["quantidade"] for l in total}[esperado], 0.17)
        self.assertNotIn("1º Pavimento", por_pav)  # contada no pavimento de baixo
        self.assertEqual({(l["item"], l["especificacao"]): l["quantidade"] for l in por_pav["Térreo"]}[esperado], 0.17)


if __name__ == "__main__":
    unittest.main()
