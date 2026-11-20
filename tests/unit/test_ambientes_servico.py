"""Ambientes e pontos automáticos no documento (services/ambientes.py), com o FreeCAD simulado."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)

MODULOS = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Spreadsheet", "Sketcher")
RECARREGAR = ("freecad.Circuits.services.ambientes", "freecad.Circuits.services.identificacao",
              "freecad.Circuits.services.pavimentos", "freecad.Circuits.objects.ponto",
              "freecad.Circuits.objects.switch")


class Vetor:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z


class Objeto(types.SimpleNamespace):
    def addProperty(self, tipo, nome, grupo="", dica=""):
        setattr(self, nome, None)
        return self


class TestAmbientesNoDocumento(unittest.TestCase):
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
        app.Placement = lambda base, rotacao: types.SimpleNamespace(Base=base, Rotation=rotacao)
        app.Rotation = lambda eixo, angulo: angulo
        self.s = importlib.import_module("freecad.Circuits.services.ambientes")

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def test_contorno_da_face_de_baixo_do_espaco(self):
        vertices = [types.SimpleNamespace(Point=Vetor(x, y)) for x, y in ((0, 0), (4000, 0), (4000, 3000), (0, 3000))]
        baixo = types.SimpleNamespace(BoundBox=types.SimpleNamespace(ZLength=0.0, ZMin=0.0, ZMax=0.0), Area=12e6,
                                      OuterWire=types.SimpleNamespace(OrderedVertexes=vertices))
        forma = mock.MagicMock(Faces=[baixo], isNull=lambda: False)
        espaco = Objeto(Name="Space", Label="Sala", Shape=forma, Proxy=types.SimpleNamespace(Type="Space"))
        self.assertEqual(self.s.contorno(espaco), [(0, 0), (4000, 0), (4000, 3000), (0, 3000)])
        tomada = Objeto(Name="T", Proxy=types.SimpleNamespace(Type="Ponto"), Shape=forma)
        self.assertEqual(self.s.contorno(tomada), [])  # símbolo não é ambiente

    def test_portas_pelo_meio(self):
        porta = Objeto(Name="Door", IfcType="Door", Width=800.0,
                       Placement=types.SimpleNamespace(multVec=lambda v: Vetor(1000 + v.x, 0, 0)))
        doc = types.SimpleNamespace(Objects=[porta, Objeto(Name="Wall", IfcType="Wall")])
        self.assertEqual(self.s.portas(doc), [(1400.0, 0, 800.0)])

    def test_gerar_pontos_cria_tomadas_luz_e_interruptor_ligados(self):
        ambiente = Objeto(Name="Wire", TipoAmbiente="Sala",
                          Points=[Vetor(0, 0), Vetor(4000, 0), Vetor(4000, 3000), Vetor(0, 3000)],
                          Placement=types.SimpleNamespace(multVec=lambda v: v))
        antigo = Objeto(Name="Velho", AmbienteAuto="Wire")
        porta = Objeto(Name="Door", IfcType="Door", Width=800.0,
                       Placement=types.SimpleNamespace(multVec=lambda v: Vetor(1600 + v.x, 0, 0)))
        objetos = [ambiente, antigo, porta]
        doc = types.SimpleNamespace(Objects=objetos, removeObject=mock.Mock(), recompute=mock.Mock())
        criados = []

        def ponto(simbolo):
            obj = Objeto(Name=f"P{len(criados)}", Simbolo=simbolo, Comando="",
                         Proxy=types.SimpleNamespace(Type="Ponto"))
            criados.append(obj)
            return obj

        def interruptor(nome):
            obj = Objeto(Name="Sw", Comando="a", Proxy=types.SimpleNamespace(Type="Switch"))
            criados.append(obj)
            return obj

        with mock.patch.object(self.s, "create_ponto", side_effect=ponto), \
                mock.patch.object(self.s, "create_switch", side_effect=interruptor), \
                mock.patch.multiple(self.s.pavimentos, pavimento_do_objeto=mock.DEFAULT, arquivar=mock.DEFAULT,
                                    elevacao=mock.DEFAULT) as pav:
            pav["elevacao"].return_value = 3000.0
            resultado = self.s.gerar_pontos(doc, ambiente, "Sala")
        doc.removeObject.assert_called_once_with("Velho")
        simbolos = [getattr(o, "Simbolo", "interruptor") for o in criados]
        self.assertEqual(simbolos, ["tomada_baixa"] * 3 + ["luz_teto", "interruptor"])
        self.assertTrue(all(o.AmbienteAuto == "Wire" for o in criados))
        self.assertTrue(all(o.Placement.Base.z == 3000.0 for o in criados))
        luz, chave = criados[3], criados[4]
        self.assertEqual((luz.Potencia, luz.Circuito), (160.0, ""))
        self.assertEqual(luz.Comando, chave.Comando)
        self.assertEqual(resultado["portas"], 1)

    def test_gerar_pontos_com_luminotecnico_e_chuveiro(self):
        ambiente = Objeto(Name="Wire", TipoAmbiente="Banheiro",
                          Points=[Vetor(0, 0), Vetor(2000, 0), Vetor(2000, 1500), Vetor(0, 1500)],
                          Placement=types.SimpleNamespace(multVec=lambda v: v))
        doc = types.SimpleNamespace(Objects=[ambiente], removeObject=mock.Mock(), recompute=mock.Mock())
        criados = []

        def ponto(simbolo):
            obj = Objeto(Name=f"P{len(criados)}", Simbolo=simbolo, Comando="", Proxy=types.SimpleNamespace(Type="Ponto"))
            criados.append(obj)
            return obj

        opcoes = {"porta": 0, "posicao_porta": 0.3, "bancada": 2, "chuveiro": 6800.0,
                  "luminotecnico": {"fluxo": 1000.0, "potencia": 12.0, "pe_direito": 2.7}}
        with mock.patch.object(self.s, "create_ponto", side_effect=ponto), \
                mock.patch.object(self.s, "create_switch",
                                  return_value=Objeto(Name="Sw", Proxy=types.SimpleNamespace(Type="Switch"))), \
                mock.patch.multiple(self.s.pavimentos, pavimento_do_objeto=mock.DEFAULT, arquivar=mock.DEFAULT,
                                    elevacao=mock.DEFAULT) as pav:
            pav["elevacao"].return_value = 0.0
            resultado = self.s.gerar_pontos(doc, ambiente, "Banheiro", opcoes)
        luzes = [o for o in criados if o.Simbolo == "luz_teto"]
        self.assertEqual(len(luzes), resultado["luminotecnico"]["quantidade"])
        self.assertGreater(len(luzes), 1)
        self.assertEqual({o.Comando for o in luzes}, {"a"})
        self.assertEqual([o.Simbolo for o in criados if o.Simbolo in ("chuveiro", "tomada_media")],
                         ["tomada_media", "chuveiro"])
        self.assertEqual(criados[-1].Potencia, 6800.0)


if __name__ == "__main__":
    unittest.main()
