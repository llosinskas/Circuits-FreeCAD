"""Eletrodutos na planta com a dinâmica das eletrocalhas (services/eletrodutos_planta.py), FreeCAD simulado."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import pecas_eletroduto as regras

MODULOS = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Spreadsheet", "Sketcher")
RECARREGAR = ("freecad.Circuits.services.eletrodutos_planta", "freecad.Circuits.services.eletrodutos",
              "freecad.Circuits.services.rede", "freecad.Circuits.services.pavimentos",
              "freecad.Circuits.services.planilhas", "freecad.Circuits.services.alinhamento",
              "freecad.Circuits.services.tomadas", "freecad.Circuits.services.documento",
              "freecad.Circuits.objects.ponto")


class Vetor:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z


class Identidade:
    def multVec(self, v):
        return v

    def inverse(self):
        return self


class Linha:
    def __init__(self, nome, pontos, **props):
        self.Name = self.Label = nome
        self.Points = [Vetor(x, y, 0.0) for x, y in pontos]
        self.Placement = Identidade()
        self.Proxy = types.SimpleNamespace(Type="Wire")
        self.ViewObject = types.SimpleNamespace()
        self.__dict__.update(props)

    def addProperty(self, tipo, nome, grupo="", dica=""):
        setattr(self, nome, None)
        return self


def _esquecer():
    """Tira os módulos de ``sys.modules`` e do pacote pai: ``from pacote import modulo`` usa o
    atributo do pacote, se existir, e traria de volta a cópia importada por outro teste."""
    for nome in RECARREGAR:
        sys.modules.pop(nome, None)
        pai, _, filho = nome.rpartition(".")
        if pai in sys.modules and hasattr(sys.modules[pai], filho):
            delattr(sys.modules[pai], filho)


class TestServico(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.dict(sys.modules, {n: mock.MagicMock(name=n) for n in MODULOS})
        self.patch.start()
        _esquecer()
        sys.modules["FreeCAD"].Vector = Vetor
        self.servico = importlib.import_module("freecad.Circuits.services.eletrodutos_planta")
        self.nivel = object()
        self.pav = mock.patch.multiple(self.servico.pavimentos, pavimento_do_objeto=mock.DEFAULT,
                                       pavimento_para_insercao=mock.DEFAULT, arquivar=mock.DEFAULT,
                                       por_nome=mock.DEFAULT)
        falsos = self.pav.start()
        falsos["pavimento_do_objeto"].return_value = None
        falsos["pavimento_para_insercao"].return_value = self.nivel
        falsos["por_nome"].return_value = None
        self.arquivar = falsos["arquivar"]

    def tearDown(self):
        self.pav.stop()
        _esquecer()
        self.patch.stop()

    def test_marcar_grava_as_escolhas_arquiva_e_traceja_o_piso(self):
        teto, piso = Linha("A", [(0, 0), (3000, 0)]), Linha("B", [(0, 0), (0, 3000)])
        doc = types.SimpleNamespace(Objects=[teto, piso])
        def preparar(obj):  # como o real: só cria as propriedades que faltam
            for nome, valor in (("Diametro", "3/4"), ("Altura3D", 0.0), ("Tipo", "Flexível")):
                if not hasattr(obj, nome):
                    setattr(obj, nome, valor)

        with mock.patch.object(self.servico.eletrodutos, "_preparar_caminho", side_effect=preparar):
            self.servico.marcar(doc, [teto], diametro="1", tipo="Rígido", material="Aço galvanizado",
                                instalacao=regras.TETO, altura=2800.0)
            self.servico.marcar(doc, [piso], diametro="3/4", tipo="Flexível", material="PVC",
                                instalacao=regras.PISO, altura=-50.0)
        self.assertEqual((teto.Diametro, teto.Tipo, teto.Material, teto.Instalacao, teto.Altura3D),
                         ("1", "Rígido", "Aço galvanizado", regras.TETO, 2800.0))
        self.assertEqual((teto.ViewObject.DrawStyle, piso.ViewObject.DrawStyle), ("Solid", "Dashed"))
        self.assertEqual([c.args for c in self.arquivar.call_args_list], [(doc, teto, self.nivel), (doc, piso, self.nivel)])

    def test_caminho_le_as_escolhas_com_padroes_para_os_antigos(self):
        antigo = Linha("A", [(0, 0), (1000, 0)], Diametro="3/4", Altura3D=2800.0)
        caminho = self.servico.caminho(antigo)
        self.assertEqual((caminho["tipo"], caminho["material"], caminho["instalacao"]), ("Flexível", "PVC", regras.TETO))

    def test_encaixar_junta_as_pontas_dos_eletrodutos(self):
        a = Linha("A", [(0, 0), (6000, 0)], Diametro="3/4", Altura3D=2800.0)
        b = Linha("B", [(3000, 200), (3000, 3000)], Diametro="3/4", Altura3D=2800.0)
        doc = types.SimpleNamespace(Objects=[a, b])
        with mock.patch.object(self.servico.rede, "listar_eletrodutos", return_value=[a, b]):
            self.assertEqual(self.servico.encaixar(doc, [b]), 1)
        self.assertEqual([(p.x, p.y) for p in b.Points], [(3000.0, 0.0), (3000.0, 3000.0)])

    def test_cria_caixa_de_passagem_nas_derivacoes_embutidas(self):
        caixa = types.SimpleNamespace(Placement=types.SimpleNamespace(Base=None), Label="", Descricao="")
        resultados = {"": {"caixas_novas": [{"x": 3000.0, "y": 0.0, "diametro": "3/4"}]}}
        with mock.patch.object(self.servico, "create_ponto", return_value=caixa) as criar:
            self.assertEqual(self.servico.criar_caixas(types.SimpleNamespace(), resultados), 1)
        criar.assert_called_once_with("caixa_passagem")
        self.assertEqual((caixa.Placement.Base.x, caixa.Placement.Base.y), (3000.0, 0.0))
        self.assertEqual(self.arquivar.call_count, 1)

    def test_anotar_escreve_diametros_e_siglas(self):
        a = Linha("A", [(0, 0), (3000, 0), (3000, 2000)], Diametro="3/4", Altura3D=2800.0, Tipo="Rígido")
        doc = types.SimpleNamespace(Objects=[a], removeObject=mock.MagicMock(), recompute=lambda: None)
        draft = sys.modules["Draft"]
        draft.make_text.reset_mock()
        resultado = regras.analisar([self.servico.caminho(a)], caixas=[(0, 0), (3000, 2000)])
        with mock.patch.object(self.servico.rede, "listar_eletrodutos", return_value=[a]), \
                mock.patch.object(self.servico, "analisar", return_value={"": resultado}):
            self.assertEqual(self.servico.anotar(doc), 2)  # Ø3/4" e C90
        textos = [c.args[0] for c in draft.make_text.call_args_list]
        self.assertEqual(sorted(t[0] for t in textos), ["C90", 'Ø3/4"'])

    def _teto_e_piso(self):
        teto = Linha("A", [(0, 0), (3000, 0)], Diametro="3/4", Altura3D=2800.0, Tipo="Rígido")
        piso = Linha("B", [(3000, 0), (3000, 2000)], Diametro="3/4", Altura3D=-50.0, Tipo="Rígido")
        doc = types.SimpleNamespace(Objects=[teto, piso], getObject={"A": teto, "B": piso}.get)
        return doc, teto, piso

    def test_descidas_e_edicao_das_alturas(self):
        doc, teto, piso = self._teto_e_piso()
        with mock.patch.object(self.servico.rede, "listar_eletrodutos", return_value=[teto, piso]), \
                mock.patch.object(self.servico.rede, "listar_caixas", return_value=[]):
            descidas = self.servico.descidas(doc)
        self.assertEqual(len(descidas), 1)
        _, descida = descidas[0]
        self.assertEqual((descida["de"], descida["ate"]), (-50.0, 2800.0))
        alterados = self.servico.editar_descida(doc, descida, 0.0, 3000.0)
        self.assertEqual(sorted(o.Name for o in alterados), ["A", "B"])
        self.assertEqual((teto.Altura3D, piso.Altura3D), (3000.0, 0.0))
        self.assertEqual(self.servico.editar_descida(doc, descida, -50.0, 2800.0 + 3), [])  # dentro da tolerância
        self.assertEqual(teto.Altura3D, 3000.0)

    def test_mudar_altura_a_partir_do_vertice_sobe_ali(self):
        e = Linha("E", [(0, 0), (3000, 0), (3000, 2000), (6000, 2000)], Diametro="3/4", Altura3D=2800.0,
                  Tipo="Rígido")
        doc = types.SimpleNamespace(Objects=[e], getObject={"E": e}.get)
        self.assertEqual(self.servico.mudar_altura(e, 300.0, vertices=[(3000, 2000)]), [2800.0, 2800.0, 300.0])
        self.assertEqual((e.AlturasTrechos, e.Altura3D), ([2800.0, 2800.0, 300.0], 2800.0))
        caminhos = self.servico.caminhos_do_eletroduto(e)
        self.assertEqual([(c["altura"], c["rotulo_altura"]) for c in caminhos], [(2800.0, "+2,80"), (300.0, "+0,30")])
        with mock.patch.object(self.servico.rede, "listar_eletrodutos", return_value=[e]), \
                mock.patch.object(self.servico.rede, "listar_caixas", return_value=[]):
            (_, descida), = self.servico.descidas(doc)
        self.assertEqual((descida["x"], descida["y"], descida["de"], descida["ate"]), (3000, 2000, 300.0, 2800.0))
        # o editor de descidas muda só o lance que chega nela
        self.servico.editar_descida(doc, descida, 400.0, 2800.0)
        self.assertEqual(e.AlturasTrechos, [2800.0, 2800.0, 400.0])
        # de volta a uma altura só: a lista fica vazia
        self.servico.mudar_altura(e, 2800.0)
        self.assertEqual((e.AlturasTrechos, e.Altura3D), ([], 2800.0))
        self.assertEqual([c["rotulo_altura"] for c in self.servico.caminhos_do_eletroduto(e)], [""])

    def test_mudar_so_o_trecho_selecionado(self):
        e = Linha("E", [(0, 0), (3000, 0), (3000, 2000), (6000, 2000)], Diametro="3/4", Altura3D=2800.0)
        self.assertEqual(self.servico.mudar_altura(e, 3200.0, arestas=[(3000, 1000)]), [2800.0, 3200.0, 2800.0])

    def test_atualizar_marca_o_fim_para_o_observador(self):
        doc, teto, piso = self._teto_e_piso()
        doc.getObject = lambda nome: None
        doc.recompute = mock.Mock()
        verticais = types.SimpleNamespace(desenhar_simbolos=mock.Mock())
        with mock.patch.object(self.servico.rede, "listar_eletrodutos", return_value=[teto, piso]), \
                mock.patch.dict(sys.modules, {"freecad.Circuits.services.verticais": verticais}):
            antes = self.servico.ULTIMA_ATUALIZACAO
            self.servico.atualizar_depois_de_editar(doc)
        self.assertGreater(self.servico.ULTIMA_ATUALIZACAO, antes)
        self.assertFalse(self.servico.ATUALIZANDO)

    def test_atualizar_refaz_so_o_que_existe_ou_tudo_ao_ligar(self):
        doc, teto, piso = self._teto_e_piso()
        doc.getObject = lambda nome: None  # sem tubos 3D
        verticais = types.SimpleNamespace(desenhar_simbolos=mock.Mock())
        doc.recompute = mock.Mock()
        with mock.patch.object(self.servico.rede, "listar_eletrodutos", return_value=[teto, piso]), \
                mock.patch.dict(sys.modules, {"freecad.Circuits.services.verticais": verticais}), \
                mock.patch.object(self.servico.eletrodutos, "gerar_descidas", return_value=1) as descidas, \
                mock.patch.object(self.servico.eletrodutos, "gerar_tubos") as tubos:
            self.assertEqual(self.servico.atualizar_depois_de_editar(doc), (False, False))
            descidas.assert_not_called()
            self.assertEqual(self.servico.atualizar_depois_de_editar(doc, sempre=True), (True, True))
            descidas.assert_called_once()
            tubos.assert_not_called()
            verticais.desenhar_simbolos.assert_called_once_with(doc)

    def test_ponta_perto_da_eletrocalha_vai_para_a_borda_e_vira_saida(self):
        eletroduto = Linha("E", [(2000, 3000), (2000, 300)], Diametro="3/4", Altura3D=2650.0, Tipo="Rígido")
        calha = {"nome": "B", "pontos": [(0, 0), (6000, 0)], "largura": 300.0, "aba": 100.0, "altura": 2600.0}
        doc = types.SimpleNamespace(Objects=[eletroduto])
        with mock.patch.object(self.servico.rede, "listar_eletrodutos", return_value=[eletroduto]), \
                mock.patch.object(self.servico.rede, "listar_caixas", return_value=[]), \
                mock.patch.object(self.servico.bandejas, "listar", return_value=["B"]), \
                mock.patch.object(self.servico.bandejas, "_caminho", return_value=calha), \
                mock.patch.object(self.servico.bandejas, "_nome_pavimento", return_value=""):
            self.assertEqual(self.servico.encaixar_nas_bandejas(doc), 1)
            self.assertEqual((eletroduto.Points[-1].x, eletroduto.Points[-1].y), (2000.0, 150.0))
            resultado = self.servico.analisar(doc)[""]
        self.assertEqual([s["tipo"] for s in resultado["saidas"]], ["horizontal"])
        self.assertEqual(len(resultado["avisos"]), 1)  # só a outra ponta, que não chega a nada


if __name__ == "__main__":
    unittest.main()
