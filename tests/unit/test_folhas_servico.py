"""Folhas no documento (services/folhas.py), com o FreeCAD e o TechDraw simulados."""
import importlib
import json
import sys
import tempfile
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import folhas as regras

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "TechDraw", "Spreadsheet")
RECARREGAR = ("freecad.Circuits.services.folhas", "freecad.Circuits.services.pavimentos",
              "freecad.Circuits.services.parametros")


class ParametrosFalsos:
    """A planilha Parâmetros do projeto, só com os textos (``services.parametros``)."""

    def __init__(self):
        self.valores = {}

    def completar(self, doc):
        return None

    def textos(self, doc):
        return dict(self.valores)

    def gravar(self, doc, valores):
        self.valores.update(valores)
        return list(valores)


class Vetor:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z


class Objeto(types.SimpleNamespace):
    def addProperty(self, tipo, nome, grupo="", dica=""):
        setattr(self, nome, "")
        return self


class Documento:
    def __init__(self):
        self.Objects, self.Label, self.removidos = [], "Casa Silva", []
        self.CreatedBy = "Projetista"

    def getObject(self, nome):
        return next((o for o in self.Objects if o.Name == nome), None)

    def removeObject(self, nome):
        self.removidos.append(nome)
        self.Objects = [o for o in self.Objects if o.Name != nome]

    def addObject(self, tipo, nome):
        obj = Objeto(Name=f"{nome}{len(self.Objects)}", Label=nome, TypeId=tipo, InList=[], X=0.0, Y=0.0, Scale=1.0)
        if tipo == "TechDraw::DrawPage":
            obj.Views = []

            def add_view(vista, folha=obj):
                folha.Views.append(vista)
                vista.InList = [folha]

            obj.addView = add_view
        if tipo == "TechDraw::DrawViewClip":
            obj.Views = []
            obj.addView = obj.Views.append
        if tipo == "TechDraw::DrawSVGTemplate":
            obj.EditableTexts = {chave: "" for chave in regras.campos_do_carimbo()}
        self.Objects.append(obj)
        return obj

    def recompute(self):
        pass


def grupo(nome, *filhos, **extra):
    return Objeto(Name=nome, Label=nome, TypeId="App::DocumentObjectGroup", Group=list(filhos), InList=[], **extra)


def desenho(nome, svg):
    obj = Objeto(Name=nome, Label=nome, TypeId="Part::FeaturePython", InList=[], svg=svg)
    obj.ViewObject = types.SimpleNamespace(Visibility=True)
    return obj


class TestFolhasServico(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        falsos["FreeCAD"].Vector = Vetor
        falsos["FreeCAD"].getUserAppDataDir.return_value = self.pasta.name
        falsos["Draft"].get_svg.side_effect = lambda obj, **_: obj.svg
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.s = importlib.import_module("freecad.Circuits.services.folhas")
        self.parametros = ParametrosFalsos()
        self.s.servico_parametros = self.parametros
        self.doc = Documento()
        # planta: tomada e eletroduto; a subpasta 3D não pode entrar
        self.tomada = desenho("T1", '<circle cx="1000" cy="-1000" r="100"/>')
        self.eletroduto = desenho("E1", '<path d="M 0,0 L 10000,-6000"/>')
        caixa_3d = desenho("T1_3D", '<path d="M -90000,0 L 0,0"/>')
        self.pav = grupo("Terreo", grupo("Tomadas", self.tomada, grupo("Tomadas3D", caixa_3d, pasta_3d="tomadas")),
                         grupo("Eletrodutos", self.eletroduto))
        self.doc.Objects += [self.pav, self.tomada, self.eletroduto, caixa_3d]

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()
        self.pasta.cleanup()

    def test_nova_folha_com_carimbo_e_numeracao(self):
        primeira = self.s.nova_folha(self.doc, "A1", "Planta baixa")
        textos = primeira.Template.EditableTexts
        self.assertEqual((textos["Projeto"], textos["Titulo"], textos["Folha"]), ("Casa Silva", "Planta baixa", "01/01"))
        self.assertTrue(primeira.Template.Template.endswith("Circuits_A1.svg"))
        textos["Responsavel"] = "Eng. Fulano"
        segunda = self.s.nova_folha(self.doc, "A3", "Diagramas")
        self.assertEqual(segunda.Template.EditableTexts["Responsavel"], "Eng. Fulano")  # copiado da anterior
        self.assertEqual(primeira.Template.EditableTexts["Folha"], "01/02")
        self.assertEqual(segunda.Template.EditableTexts["Folha"], "02/02")
        self.assertIs(self.s.folha_ativa(self.doc), segunda)
        self.assertIs(self.s.folha_ativa(self.doc, [primeira]), primeira)

    def test_carimbo_parametrico(self):
        primeira = self.s.nova_folha(self.doc, "A1", "Planta baixa")
        segunda = self.s.nova_folha(self.doc, "A3", "Diagramas")
        self.assertEqual(primeira.CarimboTitulo, "Planta baixa")
        self.assertEqual(segunda.CarimboRevisao, "00")
        # mudar a fonte (parâmetros do projeto) muda o carimbo de todas as folhas
        self.parametros.valores.update(obra="Rua A, 10", cliente="Ana", projeto="Residência Ana")
        segunda.CarimboRevisao = "01"
        self.assertEqual(self.s.atualizar_carimbos(self.doc), 2)
        for folha in (primeira, segunda):
            textos = folha.Template.EditableTexts
            self.assertEqual((textos["Obra"], textos["Cliente"], textos["Projeto"]),
                             ("Rua A, 10", "Ana", "Residência Ana"))
        self.assertEqual(segunda.Template.EditableTexts["Revisao"], "01")
        self.assertEqual(primeira.Template.EditableTexts["Revisao"], "00")
        self.assertEqual(self.s.atualizar_carimbos(self.doc), 0)  # nada mudou: não regrava
        # editar o campo na folha leva o texto para a fonte e para as outras folhas
        primeira.Template.EditableTexts = dict(primeira.Template.EditableTexts, Cliente="Ana Souza",
                                               Titulo="Planta - térreo", Folha="99/99")
        no_projeto, na_folha = self.s.sincronizar_do_carimbo(self.doc, primeira)
        self.assertEqual((no_projeto, na_folha), ({"cliente": "Ana Souza"}, {"CarimboTitulo": "Planta - térreo"}))
        self.assertEqual(segunda.Template.EditableTexts["Cliente"], "Ana Souza")
        self.assertEqual(primeira.Template.EditableTexts["Folha"], "01/02")  # a numeração é automática
        # apagar uma folha renumera as outras
        self.doc.Objects.remove(primeira)
        self.s.atualizar_carimbos(self.doc)
        self.assertEqual(segunda.Template.EditableTexts["Folha"], "01/01")

    def test_carimbo_antigo_vai_para_os_parametros(self):
        antiga = self.s.nova_folha(self.doc, "A1")
        self.parametros.valores.clear()
        for prop in self.s.regras.CARIMBO_DA_FOLHA.values():
            delattr(antiga, prop)  # folha de antes do carimbo paramétrico
        antiga.Template.EditableTexts = dict(antiga.Template.EditableTexts, Obra="Av. B", Titulo="Elétrica")
        self.s.atualizar_carimbos(self.doc)
        self.assertEqual(self.parametros.valores["obra"], "Av. B")
        self.assertEqual(antiga.CarimboTitulo, "Elétrica")

    def test_planta_sem_o_3d_arrumada_na_escala(self):
        with mock.patch.object(self.s.pavimentos, "eh_pavimento", return_value=True):
            folha = self.s.nova_folha(self.doc, "A1")
            vista, = self.s.inserir(self.doc, folha, [self.pav])
        self.assertEqual(vista.Label, "Planta baixa - Terreo")
        resultado = self.s.organizar(self.doc, folha)
        self.assertTrue(resultado["cabe"])
        self.assertEqual(resultado["escala"], 20)  # 10 × 6 m num A1
        self.assertNotIn("-90000", vista.Symbol)  # a caixa 3D ficou de fora
        self.assertIn('cx="1000"', vista.Symbol)
        self.assertAlmostEqual(vista.Scale, 1 / 20)
        info = json.loads(vista.vista_circuits)
        self.assertEqual(info["limites"], [0.0, -6000.0, 10000.0, 0.0])
        titulo = next(v for v in folha.Views if getattr(v, "titulo_de", "") == vista.Name)
        self.assertEqual(titulo.Text, ["PLANTA BAIXA - TERREO", "ESCALA 1:20"])
        self.assertEqual(folha.Template.EditableTexts["Escala"], "1:20")

    def test_atualizar_mantem_o_lugar_do_desenho(self):
        folha = self.s.nova_folha(self.doc, "A1")
        vista, = self.s.inserir(self.doc, folha, [self.pav])
        self.s.organizar(self.doc, folha)
        vista.X += 30  # o usuário arrastou a vista
        x, y = vista.X, vista.Y
        self.eletroduto.svg = '<path d="M 0,0 L 12000,-6000"/>'  # o projeto cresceu
        self.assertEqual(self.s.atualizar(self.doc), 1)
        self.assertEqual((vista.X, vista.Y), (x, y))  # o TechDraw centra o desenho no X, Y
        self.assertIn("12000", vista.Symbol)
        self.assertEqual(json.loads(vista.vista_circuits)["limites"], [0.0, -6000.0, 12000.0, 0.0])

    def test_planilha_vira_tabela(self):
        planilha = Objeto(Name="Circuitos_QD1", Label="Circuitos QD1", TypeId="Spreadsheet::Sheet", InList=[])
        planilha.getUsedCells = lambda: ["A1", "C2", "P14"]
        folha = self.s.nova_folha(self.doc, "A3")
        tabela, = self.s.inserir(self.doc, folha, [planilha])
        self.assertEqual((tabela.TypeId, tabela.CellEnd), ("TechDraw::DrawViewSpreadsheet", "P14"))
        self.s.organizar(self.doc, folha)
        self.assertEqual(tabela.Scale, 1.0)

    def test_detalhe_recorta_a_planta(self):
        regiao = desenho("Circulo", '<circle cx="1000" cy="-1000" r="500"/>')
        regiao.Shape = types.SimpleNamespace(BoundBox=types.SimpleNamespace(XMin=500, YMin=-1500, XMax=1500, YMax=-500,
                                                                            ZMin=0.0))
        self.pav.Group[0].Group.append(regiao)
        regiao.InList = [self.pav.Group[0]]
        self.doc.Objects.append(regiao)
        folha = self.s.nova_folha(self.doc, "A3")
        with mock.patch.object(self.s.pavimentos, "pavimento_do_objeto", return_value=self.pav), \
                mock.patch.object(self.s.pavimentos, "guardar_junto"):
            clip = self.s.inserir_detalhe(self.doc, folha, regiao)
        self.assertEqual((regiao.regiao_de_detalhe, clip.TypeId), ("D1", "TechDraw::DrawViewClip"))
        resultado = self.s.organizar(self.doc, folha)
        fator = next(v["fator"] for v in resultado["vistas"] if v["nome"] == clip.Name)
        self.assertEqual((clip.Width, clip.Height), (1000 * fator, 1000 * fator))  # a caixa da região, ampliada
        dentro = clip.Views[0]
        self.assertEqual(dentro.Scale, fator)
        # planta de (0, -6000) a (10000, 0): centro (5000, -3000); região centrada em (1000, -1000)
        self.assertEqual((dentro.X, dentro.Y), (4000 * fator, -2000 * fator))

    def test_corte_pela_linha_da_planta(self):
        forma = types.SimpleNamespace(isNull=lambda: False, Solids=[1],
                                      BoundBox=types.SimpleNamespace(XMin=0, YMin=0, ZMin=0, XMax=8000, YMax=5000,
                                                                     ZMax=3000))
        parede = Objeto(Name="Parede", Label="Parede", TypeId="Part::Feature", InList=[], Shape=forma,
                        ViewObject=types.SimpleNamespace(Visibility=True))
        linha = Objeto(Name="Linha", Label="Linha", TypeId="Part::Part2DObjectPython", InList=[],
                       Points=[Vetor(0, 2500), Vetor(8000, 2500)],
                       Placement=types.SimpleNamespace(multVec=lambda p: p))
        self.doc.Objects += [parede, linha]
        folha = self.s.nova_folha(self.doc, "A1")
        with mock.patch.object(self.s.pavimentos, "guardar_junto"):
            corte = self.s.inserir_corte(self.doc, folha, linha)
        self.assertEqual((linha.linha_de_corte, corte.SectionSymbol, corte.Label), ("A", "A", "Corte A-A"))
        self.assertTrue(corte.BaseView.base_dos_cortes)
        self.assertEqual((corte.SectionNormal.x, corte.SectionNormal.y), (-0.0, 1.0))
        self.assertEqual(corte.SectionOrigin.z, 1500.0)
        self.assertEqual(self.s.Draft.make_wire.call_count, 4)  # duas setas, cada uma com haste e ponta
        resultado = self.s.organizar(self.doc, folha)
        self.assertEqual(resultado["escala"], 20)  # 8 × 3 m


if __name__ == "__main__":
    unittest.main()
