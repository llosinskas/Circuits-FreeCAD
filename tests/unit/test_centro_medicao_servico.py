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
        part.makeCylinder = lambda raio, altura, base=None, eixo=None: Forma(raio, raio, altura, base)
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

    def test_colunas_parametricas_na_pasta_do_pavimento(self):
        pavimento = Objeto(Label="Térreo")
        pasta = Objeto(Group=[])
        pasta.addObject = pasta.Group.append
        coluna = Objeto(Name="Colunas_medicao", Placement=types.SimpleNamespace(Base=None))
        with mock.patch.object(self.s, "create_coluna_medicao", return_value=coluna) as criar, \
                mock.patch.object(self.s.pavimentos, "pasta", return_value=pasta) as pasta_de, \
                mock.patch.object(self.s.pavimentos, "elevacao", return_value=3000.0):
            resultado = self.s.criar_colunas(self.doc, pavimento, Medidores=30, Fases=2)
        criar.assert_called_once_with(self.doc, Medidores=30, Fases=2)
        pasta_de.assert_called_once_with(self.doc, pavimento, "busway")
        self.assertIs(resultado, coluna)
        self.assertEqual(coluna.Placement.Base.z, 3000.0)

    def test_valores_da_planilha(self):
        andares = [regras.andar("Térreo", 0, 0), regras.andar("1º", 3, 4, 50, 2), regras.andar("2º", 6, 6, 63, 3)]
        valores = self.s.valores_da_planilha(andares, {"demanda_total_a": 180.0, "tensao": 220.0})
        self.assertEqual(valores, {"Medidores": 10, "DemandaPorMedidor": 63, "Fases": 3, "DemandaTotal": 180.0,
                                   "Tensao": 220.0})
        self.assertEqual(self.s.valores_da_planilha([regras.andar("Térreo", 0, 0)]), {})

    def test_quantitativos_do_busway_das_caixas_mec_e_das_colunas(self):
        linha = Objeto(Name="Wire001", CorrenteBusway=630, Points=[Vetor(0, 0, 0), Vetor(6000, 0, 0),
                                                                    Vetor(6000, 4000, 0)],
                       Placement=types.SimpleNamespace(multVec=lambda v: v))
        vertical = Objeto(Name="Wire002", CorrenteBusway=630, prumada_busway_de="Wire001", LajesAtravessadas=3,
                          Points=[Vetor(6000, 4000, 2500), Vetor(6000, 4000, 12500)],
                          Placement=types.SimpleNamespace(multVec=lambda v: v))
        texto1 = Objeto(Name="Text", prumada_busway_de="Wire001", CaixasMEC=["MEC IV"])
        texto2 = Objeto(Name="Text001", prumada_busway_de="Wire001", CaixasMEC=["MEC IX", "MEC II"])
        colunas = Objeto(Name="Colunas_medicao", coluna_medicao=24, CDPMs=["Coluna dupla"])
        metalicas = Objeto(Name="Colunas_medicao001", coluna_medicao=0, CDPMs=[], CaixasMetalicas=["N", "O"],
                           MedicoesMetalicas=28)
        self.doc.Objects = [linha, vertical, texto1, texto2, colunas, metalicas]
        pavimento_de = {"Wire001": "Térreo", "Wire002": "Térreo", "Text": "1º", "Text001": "2º",
                        "Colunas_medicao": "Térreo", "Colunas_medicao001": "Térreo"}
        with mock.patch.object(self.s.pavimentos, "pavimento_do_objeto",
                               side_effect=lambda d, o: Objeto(Label=pavimento_de[o.Name])):
            resultado = dict(self.s.materiais_por_pavimento(self.doc))
        terreo = {(i["item"], i["especificacao"]): i["quantidade"] for i in resultado["Térreo"]}
        self.assertAlmostEqual(terreo[("Busway (barramento blindado)", "630 A, cobre, IP 54")], 20.0)
        self.assertEqual(terreo[("Cotovelo de busway", "630 A, cobre, IP 54")], 2)  # na curva e na subida
        self.assertEqual(terreo[("Barreira corta-fogo", "630 A, cobre, IP 54")], 3)
        self.assertEqual(terreo[("Caixa de medição tipo P", "policarbonato, 260 × 520 × 190 mm")], 24)
        self.assertEqual(terreo[("Caixa de medição coletiva", "tipo N, aço, 1200 × 1300 × 250 mm")], 1)
        self.assertEqual(terreo[("Caixa de barramentos e CDPI", "Desenhos 20 e 32")], 1)  # a O já tem
        self.assertEqual(terreo[("Disjuntor da unidade", "DIN até 100 A, na CDPI")], 28)
        segundo = {(i["item"], i["especificacao"]): i["quantidade"] for i in resultado["2º"]}
        self.assertEqual(segundo[("Caixa de medição centralizada", "MEC IX")], 1)
        self.assertEqual(segundo[("Placa de comunicação", "")], 3)  # 2 na MEC IX e 1 na MEC II
        self.assertEqual(segundo[("Plug-in com disjuntor (derivação)", "63 a 400 A")], 2)
        self.assertTrue(all(i["grupo"] == "Busway e medição" for itens in resultado.values() for i in itens))

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
        self.assertEqual(textos[1].CaixasMEC, ["MEC VI"])
        self.assertEqual(vertical.LajesAtravessadas, 2)  # pisos do 1º e do 2º
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
