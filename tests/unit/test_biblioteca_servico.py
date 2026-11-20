"""Biblioteca no documento (services/biblioteca.py): itens, miniaturas e a pasta Equipamentos do pavimento."""
import importlib
import os
import sys
import types
import unittest
from unittest import mock

from tests import ROOT

MODULOS = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Spreadsheet", "Sketcher")
RECARREGAR = ("freecad.Circuits.services.biblioteca", "freecad.Circuits.services.pavimentos",
              "freecad.Circuits.services.documento")
PASTA = os.path.join(ROOT, "freecad", "Circuits", "Componentes", "Eletrica")


class Objeto(types.SimpleNamespace):
    def addProperty(self, tipo, nome, grupo="", dica=""):
        setattr(self, nome, None)
        return self

    def addObject(self, obj):
        self.Group.append(obj)


class Documento:
    def __init__(self, arquivo=""):
        self.Objects, self.FileName = [], arquivo

    def addObject(self, tipo, nome):
        obj = Objeto(Name=nome, Label=nome, TypeId=tipo, Group=[],
                     Placement=types.SimpleNamespace(Base=None), ViewObject=types.SimpleNamespace())
        self.Objects.append(obj)
        return obj

    def recompute(self):
        pass


class TestBibliotecaNoDocumento(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.dict(sys.modules, {n: mock.MagicMock(name=n) for n in MODULOS})
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
            pai, _, filho = nome.rpartition(".")
            if pai in sys.modules and hasattr(sys.modules[pai], filho):
                delattr(sys.modules[pai], filho)
        sys.modules["FreeCAD"].Vector = lambda x=0, y=0, z=0: (x, y, z)
        self.s = importlib.import_module("freecad.Circuits.services.biblioteca")
        self.equipamentos = Objeto(Name="Pasta_equipamentos", Group=[])
        self.pav = mock.patch.multiple(self.s.pavimentos, pasta=mock.DEFAULT, elevacao=mock.DEFAULT)
        falsos = self.pav.start()
        falsos["pasta"].return_value = self.equipamentos
        falsos["elevacao"].return_value = 3000.0
        self.pasta = falsos["pasta"]

    def tearDown(self):
        self.pav.stop()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def test_itens_com_exemplos_e_arquivos(self):
        itens = self.s.listar_itens(PASTA)
        self.assertTrue(any(i["exemplo"] for i in itens))
        arquivos = [i for i in itens if not i["exemplo"]]
        self.assertEqual(len(arquivos), len([f for f in os.listdir(PASTA) if f.endswith(".FCStd")]))
        self.assertTrue(all(os.path.exists(i["caminho"]) for i in arquivos))

    def test_miniatura_do_fcstd(self):
        com_imagem = [self.s.miniatura(os.path.join(PASTA, f)) for f in os.listdir(PASTA) if f.endswith(".FCStd")]
        self.assertTrue(any(dados and dados.startswith(b"\x89PNG") for dados in com_imagem))
        self.assertIsNone(self.s.miniatura(os.path.join(PASTA, "nao_existe.FCStd")))

    def test_exemplo_vira_pasta_no_equipamentos_do_pavimento(self):
        doc, pav = Documento(), Objeto(Label="Térreo")
        parte = self.s.inserir(doc, "exemplo:motor_3cv", pavimento=pav)
        self.assertEqual(parte.TypeId, "App::Part")
        self.assertEqual(parte.componente_biblioteca, "exemplo:motor_3cv")
        self.pasta.assert_called_once_with(doc, pav, "equipamentos")
        self.assertEqual(self.equipamentos.Group, [parte])
        self.assertEqual(parte.Placement.Base, (0, 0, 3000.0))  # no piso do pavimento
        corpo = parte.Group[0]
        self.assertEqual((corpo.TypeId, corpo.Potencia), ("Part::Feature", 2600.0))

    def test_copia_do_arquivo_poe_as_raizes_na_pasta(self):
        doc, pav = Documento(), Objeto(Label="Térreo")
        filho = Objeto(Name="Corpo", Group=[])
        grupo = Objeto(Name="Grupo", Group=[filho])

        def mesclar(caminho):
            doc.Objects += [grupo, filho]
        doc.mergeProject = mesclar
        parte = self.s.inserir(doc, os.path.join(PASTA, "Tomada.FCStd"), self.s.COPIA, pav)
        self.assertEqual(parte.Label, "Tomada")
        self.assertEqual(parte.Group, [grupo])  # o filho continua dentro do grupo
        self.assertEqual(self.equipamentos.Group, [parte])

    def test_link_exige_projeto_salvo(self):
        with self.assertRaisesRegex(RuntimeError, "salve o projeto"):
            self.s.inserir(Documento(), os.path.join(PASTA, "Tomada.FCStd"), self.s.LINK, Objeto(Label="T"))


if __name__ == "__main__":
    unittest.main()
