"""Objeto paramétrico das colunas de medição (objects/coluna_medicao.py), com o FreeCAD simulado."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)

MODULO = "freecad.Circuits.objects.coluna_medicao"


class Forma:
    def __init__(self, faces=6):
        self.Faces = [None] * faces


class Composto:
    def __init__(self, solidos):
        self.Solids = list(solidos)
        self.Faces = [f for s in self.Solids for f in s.Faces]


class Objeto:
    """Objeto do FreeCAD simulado: propriedades com restrição (tupla) e enumeração (lista)."""

    def __init__(self):
        object.__setattr__(self, "_tipos", {})
        object.__setattr__(self, "Placement", "posicao")
        object.__setattr__(self, "Shape", None)
        object.__setattr__(self, "editor", {})

    def addProperty(self, tipo, nome, grupo="", dica=""):
        self._tipos[nome] = tipo
        object.__setattr__(self, nome, None)
        return self

    def setEditorMode(self, nome, modo):
        self.editor[nome] = modo

    def __setattr__(self, nome, valor):
        tipo = self._tipos.get(nome, "")
        if tipo.endswith("Constraint") and isinstance(valor, tuple):
            valor = valor[0]
        if tipo.endswith("Enumeration") and isinstance(valor, list):
            valor = valor[0]
        object.__setattr__(self, nome, valor)


class TestColunaParametrica(unittest.TestCase):
    def setUp(self):
        falsos = {n: mock.MagicMock(name=n) for n in ("FreeCAD", "FreeCADGui", "Part")}
        falsos["FreeCAD"].Vector = lambda *v: v
        falsos["Part"].makeBox = lambda *a: Forma(6)
        falsos["Part"].makeCylinder = lambda *a: Forma(3)
        falsos["Part"].makeCompound = Composto
        falsos["Part"].Shape = lambda: Composto([])
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        sys.modules.pop(MODULO, None)
        self.m = importlib.import_module(MODULO)
        self.obj = Objeto()
        self.m.ColunaMedicao(self.obj)

    def tearDown(self):
        sys.modules.pop(MODULO, None)
        self.patch.stop()

    def test_padrao_e_entradas(self):
        self.assertEqual((self.obj.Medidores, self.obj.MedidoresPorColuna, self.obj.Fases, self.obj.Modelo),
                         (12, 3, 2, "Automático"))
        self.assertEqual(self.obj.editor["Conjuntos"], 1)  # só leitura

    def test_execute_dimensiona_e_desenha(self):
        self.obj.Medidores, self.obj.DemandaTotal = 30, 250.0
        self.obj.Proxy.execute(self.obj)
        self.assertEqual(self.obj.Solucao, "Caixas P em agrupamento modular")
        self.assertEqual(self.obj.coluna_medicao, 30)
        self.assertEqual(self.obj.CDPMs, ["Coluna dupla"])
        self.assertIn("30 caixas P, Coluna dupla: 250 A, disjuntor geral 250 A, barramento 25x5 mm",
                      self.obj.Conjuntos[0])
        self.assertEqual(self.obj.DisjuntorUnidade, 63)
        self.assertEqual(len(self.obj.Shape.Solids), len(self.obj.TiposDasPecas))
        self.assertEqual(self.obj.Placement, "posicao")  # a posição na planta não muda

    def test_mudar_medidores_por_coluna_refaz(self):
        self.obj.Medidores, self.obj.DemandaTotal = 30, 250.0
        self.obj.MedidoresPorColuna = 2
        self.obj.Proxy.execute(self.obj)
        self.assertEqual(len(self.obj.CDPMs), 2)

    def test_trifasica_em_caixas_metalicas_e_indireta_sem_desenho(self):
        self.obj.Medidores, self.obj.Fases, self.obj.DemandaPorMedidor = 12, 3, 20.0
        self.obj.Proxy.execute(self.obj)
        self.assertEqual((self.obj.CaixasMetalicas, self.obj.MedicoesMetalicas, self.obj.coluna_medicao),
                         (["N"], 12, 0))
        self.obj.DemandaPorMedidor = 150.0
        self.obj.Proxy.execute(self.obj)
        self.assertIn("indireta", self.obj.Avisos[0])
        self.assertEqual(self.obj.Shape.Solids, [])

    def test_cores_por_face(self):
        forma = Composto([Forma(6), Forma(3)])
        cores = self.m.cores_das_faces(forma, ["tampa", "eletroduto"])
        self.assertEqual(len(cores), 9)
        self.assertAlmostEqual(cores[0][3], 0.7)  # tampa transparente
        self.assertEqual(cores[-1][3], 0.0)


if __name__ == "__main__":
    unittest.main()
