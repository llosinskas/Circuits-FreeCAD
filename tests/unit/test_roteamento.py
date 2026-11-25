"""Rota dos cabos pela infraestrutura e ocupação dos eletrodutos no documento (services/roteamento.py)."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet")
RECARREGAR = ("freecad.Circuits.services.roteamento", "freecad.Circuits.services.rede",
              "freecad.Circuits.services.bandejas", "freecad.Circuits.services.eletrodutos",
              "freecad.Circuits.services.pavimentos", "freecad.Circuits.services.alinhamento",
              "freecad.Circuits.services.planilhas", "freecad.Circuits.services.tomadas",
              "freecad.Circuits.services.documento", "freecad.Circuits.services.estilo")


class Vetor:
    def __init__(self, x, y, z=0.0):
        self.x, self.y, self.z = x, y, z


class Identidade:
    def multVec(self, v):
        return v


class Documento:
    def __init__(self, *objetos):
        self.Objects = list(objetos)
        self.removidos, self.recomputado = [], 0

    def getObject(self, nome):
        return next((o for o in self.Objects if o.Name == nome), None)

    def removeObject(self, nome):
        self.removidos.append(nome)
        self.Objects = [o for o in self.Objects if o.Name != nome]

    def addObject(self, tipo, nome):
        planilha = Planilha(nome)
        self.Objects.append(planilha)
        return planilha

    def recompute(self):
        self.recomputado += 1


class Planilha:
    def __init__(self, nome):
        self.Name = self.Label = nome
        self.celulas = {}

    def addProperty(self, tipo, nome, grupo, dica):
        setattr(self, nome, "")

    def set(self, celula, valor):
        self.celulas[celula] = valor


def eletroduto(nome, *pontos, diametro="1/2", tipo="Rígido"):
    obj = types.SimpleNamespace(Name=nome, Label=f"Eletroduto {nome}", Points=[Vetor(*p) for p in pontos],
                                Placement=Identidade(), Diametro=diametro, Altura3D=2800.0, Tipo=tipo)
    obj.getEnumerationsOfProperty = lambda prop: ["1/2", "3/4", "1", "1 1/4", "1 1/2", "2", "3", "4"]
    return obj


def ponto(nome, simbolo, x, y, altura, circuito="1", **extra):
    props = dict(Name=nome, Label=nome, Simbolo=simbolo, Altura3D=altura, Circuito=circuito, Comando="", Quadro="",
                 Ligacao="F+N", Descricao=nome, Planilha="", Proxy=types.SimpleNamespace(Type="Ponto"),
                 Placement=types.SimpleNamespace(Base=Vetor(x, y)))
    props.update(extra)
    return types.SimpleNamespace(**props)


class TestRoteamento(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        falsos["FreeCAD"].Vector = Vetor
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.s = importlib.import_module("freecad.Circuits.services.roteamento")
        # quadro em (0, 0); seis circuitos de tomada pelo mesmo eletroduto E1 até a caixa do fim
        self.quadro = ponto("QD", "quadro_distribuicao", 0, 0, 1500, circuito="", Descricao="QD1")
        self.tomadas = [ponto(f"T{n}", "tomada_baixa", 3000, 0, 300, circuito=str(n)) for n in range(1, 7)]
        self.e1 = eletroduto("E1", (0, 0), (3000, 0))
        self.doc = Documento(self.quadro, *self.tomadas, self.e1)
        simbolos = [self.quadro] + self.tomadas
        self.patches = [mock.patch.object(self.s.rede, "listar_simbolos", return_value=simbolos),
                        mock.patch.object(self.s.rede.pavimentos, "pavimento_do_objeto", return_value=None),
                        mock.patch.object(self.s.bandejas, "listar", return_value=[])]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def test_seis_circuitos_nao_cabem_no_meia_polegada(self):
        dados = self.s.ocupacao(self.doc)
        e1 = dados["eletrodutos"][0]
        self.assertEqual((e1["objeto"], e1["cabos"], e1["pequeno"]), ("E1", 18, True))  # 6 × F+N+T
        self.assertEqual(e1["minimo"], "1")
        self.assertEqual(len(dados["rotas"]), 6)
        self.assertTrue(dados["avisos"])

    def test_aplicar_so_aumenta(self):
        trocados = self.s.aplicar_diametros(self.doc, self.s.ocupacao(self.doc))
        self.assertEqual(trocados, [("Eletroduto E1", "1/2", "1")])
        self.assertEqual(self.e1.Diametro, "1")
        self.assertEqual(self.s.aplicar_diametros(self.doc, self.s.ocupacao(self.doc)), [])

    def test_planilha_recriada(self):
        primeira = self.s.gravar_planilha(self.doc, self.s.ocupacao(self.doc))
        self.assertEqual(primeira.celulas["A1"], "'Infraestrutura")
        self.assertEqual(primeira.celulas["A2"], "'Eletroduto E1")
        self.assertEqual(primeira.celulas["K2"], "'aumentar para 1")
        self.s.gravar_planilha(self.doc, self.s.ocupacao(self.doc))
        self.assertEqual(self.doc.removidos, [primeira.Name])

    def test_rotas_pela_selecao(self):
        todas = self.s.rotas_dos_objetos(self.doc, [])
        self.assertEqual(len(todas), 6)
        self.assertEqual(todas[0]["objetos"], ["E1"])
        so_t2 = self.s.rotas_dos_objetos(self.doc, [self.tomadas[1]])
        self.assertEqual([r["circuito"] for r in so_t2], ["2"])
        self.assertEqual(len(self.s.rotas_dos_objetos(self.doc, [self.e1])), 6)  # quem passa no eletroduto
        self.assertEqual(len(self.s.rotas_dos_objetos(self.doc, [self.quadro])), 6)  # todos do quadro
        texto = self.s.descrever(self.doc, so_t2[0])
        self.assertIn("QD → Eletroduto E1 → T2", texto)


if __name__ == "__main__":
    unittest.main()
