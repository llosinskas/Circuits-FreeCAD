"""Centro de medição no documento (services/centro_medicao.py), com o FreeCAD simulado."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import centro_medicao as regras

MODULOS = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Spreadsheet", "Sketcher")
RECARREGAR = ("freecad.Circuits.services.centro_medicao", "freecad.Circuits.services.pavimentos",
              "freecad.Circuits.services.planilhas")


class Vetor:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z


class Objeto(types.SimpleNamespace):
    def addProperty(self, tipo, nome, grupo="", dica=""):
        setattr(self, nome, None)
        return self


class Folha(Objeto):
    def set(self, celula, valor):
        self.celulas[celula] = valor

    def getContents(self, celula):
        return self.celulas.get(celula, "")

    def getUsedCells(self):
        return list(self.celulas)

    def setColumnWidth(self, *_):
        pass


class Documento:
    def __init__(self):
        self.Objects = []

    def addObject(self, tipo, nome):
        if tipo == "Spreadsheet::Sheet":
            obj = Folha(Name=nome, Label=nome, celulas={}, Document=self)
        else:
            obj = Objeto(Name=nome, Label=nome, TypeId=tipo, Group=[], ViewObject=Objeto(),
                         Placement=types.SimpleNamespace(Base=None))
            obj.addObject = obj.Group.append
        self.Objects.append(obj)
        return obj

    def removeObject(self, nome):
        self.Objects = [o for o in self.Objects if o.Name != nome]

    def recompute(self):
        pass


class Forma:
    """Sólido simulado: guarda a caixa e as transformações."""

    def __init__(self, dx, dy, dz, base=None):
        self.dims, self.base, self.giros, self.translacoes = (dx, dy, dz), base, [], []

    def rotate(self, centro, eixo, angulo):
        self.giros.append(angulo)

    def translate(self, vetor):
        self.translacoes.append(vetor)


class TestServico(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.dict(sys.modules, {n: mock.MagicMock(name=n) for n in MODULOS})
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
            pai, _, filho = nome.rpartition(".")
            if pai in sys.modules and hasattr(sys.modules[pai], filho):
                delattr(sys.modules[pai], filho)
        app = sys.modules["FreeCAD"]
        app.Vector = Vetor
        part = sys.modules["Part"]
        part.makeBox = lambda dx, dy, dz, base=None: Forma(dx, dy, dz, base)
        part.makeCompound = lambda solidos: list(solidos)
        draft = sys.modules["Draft"]
        draft.make_wire = lambda pontos, **_: Objeto(Name="Wire", Label="", Points=pontos, ViewObject=Objeto())
        draft.make_text = lambda textos, posicao: Objeto(Name="Text", Label="", Text=textos, Posicao=posicao)
        self.s = importlib.import_module("freecad.Circuits.services.centro_medicao")
        self.doc = Documento()

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def test_planilha_com_os_pavimentos_e_precos_editaveis(self):
        pavs = [Objeto(Label="Térreo", e=0.0), Objeto(Label="1º", e=3000.0), Objeto(Label="2º", e=6000.0)]
        with mock.patch.object(self.s.pavimentos, "listar", return_value=pavs), \
                mock.patch.object(self.s.pavimentos, "elevacao", side_effect=lambda p: p.e):
            folha, quantidade = self.s.criar(self.doc)
        self.assertEqual(quantidade, 3)
        self.assertIs(self.s.planilha(self.doc), folha)
        andares = self.s.ler_andares(folha)
        self.assertEqual([(a["nome"], a["cota"], a["unidades"]) for a in andares],
                         [("Térreo", 0.0, 0), ("1º", 3.0, 4), ("2º", 6.0, 4)])
        linha = next(int(c[1:]) for c, v in folha.celulas.items() if c.startswith("G") and v == "'busway_m_630")
        folha.set(f"I{linha}", "'2500,50")
        self.assertEqual(self.s.ler_precos(folha)["busway_m_630"], 2500.5)
        self.assertEqual(self.s.ler_precos(folha)["caixa_p"], regras.PRECOS["caixa_p"][1])

    def test_resultado_e_parametros_gravados(self):
        folha = self.doc.addObject("Spreadsheet::Sheet", "F")
        andares = [regras.andar("1º", 3, 4)]
        r = regras.comparar(andares, demanda_total_a=200)
        parametros = {"tensao": 220.0, "uso": 2.0, "distancia_horizontal": 12.5}
        self.s.gravar_resultado(folha, r, parametros)
        self.assertEqual(folha.celulas["K3"], "'Recomendada")
        self.assertEqual(self.s.ler_parametros(folha), parametros)

    def test_colunas_de_medicao_lado_a_lado(self):
        grupos = regras.agrupamentos(36, 10.0)
        pavimento = Objeto(Label="Térreo")
        pasta = Objeto(Group=[])
        pasta.addObject = pasta.Group.append
        with mock.patch.object(self.s.pavimentos, "pasta", return_value=pasta) as pasta_de, \
                mock.patch.object(self.s.pavimentos, "elevacao", return_value=0.0):
            parte = self.s.inserir_colunas(self.doc, grupos, pavimento)
        pasta_de.assert_called_once_with(self.doc, pavimento, "busway")
        self.assertEqual(parte.coluna_medicao, 36)
        caixas = [o for o in parte.Group if o.Name == "Caixa_P"]
        self.assertEqual(len(caixas), 36)
        self.assertEqual(sum(1 for o in parte.Group if o.Name == "CDPM"), 2)
        xs = sorted(o.Shape.base.x for o in parte.Group)
        self.assertAlmostEqual(xs[0] + max(o.Shape.base.x + o.Shape.dims[0] for o in parte.Group), 0.0, delta=1.0)

    def test_prumada_sobe_do_fim_da_linha_com_as_caixas_dos_andares(self):
        pavs = {"Térreo": Objeto(Label="Térreo", e=0.0), "1º": Objeto(Label="1º", e=3000.0),
                "2º": Objeto(Label="2º", e=6000.0)}
        andares = [regras.andar("1º", 3, 4, 50), regras.andar("2º", 6, 6, 50)]
        resultado = regras.busway(andares, distancia_horizontal=8.0)
        linha = Objeto(Name="Wire001", Label="Caminho", Points=[Vetor(0, 0, 0), Vetor(8000, 0, 0)],
                       Placement=types.SimpleNamespace(multVec=lambda v: v), ViewObject=Objeto())
        pasta = Objeto(Group=[])
        pasta.addObject = pasta.Group.append
        with mock.patch.object(self.s.pavimentos, "por_nome", side_effect=lambda d, n: pavs.get(n)), \
                mock.patch.object(self.s.pavimentos, "elevacao", side_effect=lambda p: p.e), \
                mock.patch.object(self.s.pavimentos, "pasta", return_value=pasta), \
                mock.patch.object(self.s.pavimentos, "arquivar") as arquivar:
            vertical, corpo, textos = self.s.criar_prumada(self.doc, linha, resultado["linhas"][0],
                                                           resultado["andares"], pavs["Térreo"], 9000.0)
        self.assertEqual(linha.CorrenteBusway, resultado["linhas"][0]["nominal"])
        self.assertEqual(vertical.CorrenteBusway, linha.CorrenteBusway)
        self.assertEqual((vertical.Points[0].x, vertical.Points[0].y), (8000, 0))
        self.assertEqual(vertical.Points[-1].z, 9000.0)
        self.assertEqual(len(textos), 2)
        self.assertIn("MEC VI (6)", textos[1].Text[1])
        # trecho horizontal, vertical, uma MEC e um plug-in em cada andar
        self.assertEqual(len(corpo.Shape), 1 + 1 + 2 * 2)
        arquivar.assert_called_once_with(self.doc, linha, pavs["Térreo"])
        self.assertIn(vertical, pasta.Group)
        self.assertIn(corpo, pasta.Group)

    def test_linhas_desenhadas_ignora_simbolos(self):
        wire = Objeto(Points=[Vetor(), Vetor(1, 0, 0)], Proxy=types.SimpleNamespace(Type="Wire"))
        conduite = Objeto(Points=[Vetor(), Vetor(1, 0, 0)], Proxy=types.SimpleNamespace(Type="ConduitPath"))
        ponto = Objeto(Proxy=types.SimpleNamespace(Type="Ponto"))
        self.assertEqual(self.s.linhas_desenhadas([wire, conduite, ponto]), [wire])


if __name__ == "__main__":
    unittest.main()
