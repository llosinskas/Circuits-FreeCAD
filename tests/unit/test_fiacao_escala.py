"""Fiação de todos os símbolos e escala dos símbolos, com o FreeCAD simulado."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core.simbologia import condutores, tamanho_efetivo

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet")
RECARREGAR = (
    "freecad.Circuits.services.cabos", "freecad.Circuits.services.escala", "freecad.Circuits.services.tomadas",
    "freecad.Circuits.services.identificacao", "freecad.Circuits.services.alinhamento",
    "freecad.Circuits.services.documento", "freecad.Circuits.objects.ponto",
)


class TestRegras(unittest.TestCase):
    def test_condutores_pela_ligacao(self):
        self.assertEqual(condutores("F+N"), (1, True))
        self.assertEqual(condutores("F+F"), (2, False))
        self.assertEqual(condutores("3F"), (3, False))
        self.assertEqual(condutores("???"), (1, True))

    def test_tamanho_efetivo(self):
        self.assertEqual(tamanho_efetivo(200, 1.5), 300)
        self.assertEqual(tamanho_efetivo(200), 200)
        self.assertEqual(tamanho_efetivo(200, 0), 200)
        self.assertEqual(tamanho_efetivo(200, -3), 200)


def ponto(nome, simbolo, ligacao="F+N", escala=1.0):
    return types.SimpleNamespace(
        Name=nome, Label=nome, Proxy=types.SimpleNamespace(Type="Ponto", _add_properties=lambda obj: None),
        Simbolo=simbolo, Ligacao=ligacao, Tamanho=200.0, Escala=escala,
        Placement=types.SimpleNamespace(Base=mock.MagicMock()),
    )


class TestServicos(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.cabos = importlib.import_module("freecad.Circuits.services.cabos")
        self.escala = importlib.import_module("freecad.Circuits.services.escala")

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def documento(self, *objetos):
        doc = mock.MagicMock()
        doc.Objects = list(objetos)
        doc.getObject.return_value = None
        return doc

    def test_condutores_de_cada_tipo_de_ponto(self):
        self.assertEqual(self.cabos.condutores_do_ponto(ponto("T", "tomada_baixa")), (["F", "N", "T"], 100.0))
        self.assertEqual(self.cabos.condutores_do_ponto(ponto("C", "chuveiro", "F+F")), (["F", "F", "T"], 100.0))
        self.assertEqual(self.cabos.condutores_do_ponto(ponto("M", "ponto_forca", "3F")), (["F", "F", "F", "T"], 100.0))

    def test_luz_comandada_leva_retorno(self):
        luz = ponto("L", "luz_teto")
        luz.Comando = "a"
        self.assertEqual(self.cabos.condutores_do_ponto(luz)[0], ["N", "R", "T"])

    def test_fiacao_acompanha_a_escala_do_simbolo(self):
        self.assertEqual(self.cabos.condutores_do_ponto(ponto("T", "tomada_baixa", escala=2.0))[1], 200.0)

    def test_quadros_nao_recebem_fiacao_e_interruptores_recebem(self):
        self.assertIsNone(self.cabos.condutores_do_ponto(ponto("Q", "quadro_distribuicao", "3F")))
        self.assertIsNone(self.cabos.condutores_do_ponto(types.SimpleNamespace(Name="X")))
        simples = types.SimpleNamespace(Name="S", Proxy=types.SimpleNamespace(Type="Switch"), Tipo="Simples",
                                        RaioSimbolo=50.0, Escala=1.0)
        self.assertEqual(self.cabos.condutores_do_ponto(simples), (["F", "R"], 100.0))
        simples.Tipo = "Paralelo"
        self.assertEqual(self.cabos.condutores_do_ponto(simples)[0], ["F", "R", "R"])
        simples.Tipo = "Intermediário"
        self.assertEqual(self.cabos.condutores_do_ponto(simples)[0], ["R"] * 4)

    def test_tomada_tug_e_objetos_antigos(self):
        tug = types.SimpleNamespace(Name="Tomada", tipo="tomada", Fase=2, neutro=True, terra=False)
        self.assertEqual(self.cabos.condutores_do_ponto(tug), (["F", "F", "N"], 100.0))
        tug.Escala = 1.5
        self.assertEqual(self.cabos.condutores_do_ponto(tug)[1], 150.0)
        antiga = types.SimpleNamespace(Name="O", Proxy=types.SimpleNamespace(Type="Outlet"), Tensao="Bifásica")
        self.assertEqual(self.cabos.condutores_do_ponto(antiga)[0], ["F", "F", "T"])

    def test_desenha_todos_os_pontos_e_apaga_a_fiacao_anterior(self):
        antigo = types.SimpleNamespace(Name="Cabo007", fiacao_de="T")
        doc = self.documento(
            ponto("T", "tomada_baixa"), ponto("L", "luz_teto"), ponto("Q", "quadro_medicao"), antigo,
        )
        self.assertEqual(self.cabos.desenhar_cabos_planta(doc), 2)
        doc.removeObject.assert_called_once_with("Cabo007")
        criados = [chamada for chamada in doc.addObject.call_args_list if chamada.args[0] == "Sketcher::SketchObject"]
        self.assertEqual(len(criados), 2)

    def test_fiacao_vai_para_a_pasta_do_pavimento(self):
        pasta = mock.MagicMock()
        doc = self.documento(ponto("T", "tomada_baixa"), ponto("L", "luz_teto"))
        chaves = []

        def pasta_do_pavimento(documento, obj, chave):
            chaves.append(chave)
            return pasta if obj.Name == "T" else None
        with mock.patch.object(self.cabos.pavimentos, "pasta_do_pavimento", side_effect=pasta_do_pavimento), \
                mock.patch.object(self.cabos, "create_group") as criar_grupo:
            self.assertEqual(self.cabos.desenhar_cabos_planta(doc), 2)
        self.assertEqual(chaves, ["fiacao", "fiacao"])
        self.assertEqual(pasta.addObject.call_count, 1)  # T no pavimento
        criar_grupo.assert_called_once_with("Cabos", doc)  # L fora de pavimento
        self.assertEqual(criar_grupo.return_value.addObject.call_count, 1)

    def test_escala_na_selecao(self):
        a, b = ponto("A", "tomada_baixa"), ponto("B", "luz_teto")
        antiga = types.SimpleNamespace(Name="O", Proxy=types.SimpleNamespace(Type="Outlet"))
        doc = self.documento(a, b, antiga)
        self.assertEqual(self.escala.aplicar_escala(doc, [a, antiga], 2.5), (1, 1))
        self.assertEqual((a.Escala, b.Escala), (2.5, 1.0))

    def test_escala_em_todos_quando_nada_esta_selecionado(self):
        a, b = ponto("A", "tomada_baixa"), ponto("B", "luz_teto")
        interruptor = types.SimpleNamespace(
            Name="S", Proxy=types.SimpleNamespace(Type="Switch", _add_properties=lambda obj: setattr(obj, "Escala", 1.0)),
        )
        doc = self.documento(a, b, interruptor)
        self.assertEqual(self.escala.aplicar_escala(doc, [], 3.0), (3, 0))
        self.assertEqual((a.Escala, b.Escala, interruptor.Escala), (3.0, 3.0, 3.0))

    def test_escala_invalida(self):
        with self.assertRaises(ValueError):
            self.escala.aplicar_escala(self.documento(), [], 0)

    def test_tomada_tug_e_redesenhada(self):
        tug = mock.MagicMock()
        tug.tipo = "tomada"
        tug.Proxy = None
        doc = self.documento(tug)
        self.assertEqual(self.escala.aplicar_escala(doc, [tug], 2.0), (1, 0))
        tug.deleteAllGeometry.assert_called_once()
        self.assertEqual(tug.Escala, 2.0)
        self.assertEqual(tug.addGeometry.call_count, 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestDesenhoDaFiacao(unittest.TestCase):
    def test_lista_de_condutores(self):
        from freecad.Circuits.core.simbologia import lista_de_condutores
        self.assertEqual(lista_de_condutores("F+N+T"), ["F", "N", "T"])
        self.assertEqual(lista_de_condutores("T+2F"), ["F", "F", "T"])
        self.assertEqual(lista_de_condutores("R+N+T"), ["N", "R", "T"])
        self.assertEqual(lista_de_condutores("4R"), ["R"] * 4)
        self.assertEqual(lista_de_condutores(""), [])

    def test_tracos_iguais_e_marcas(self):
        from freecad.Circuits.core.simbologia import fiacao
        d = fiacao(["F", "N", "R", "T"], 100.0)
        base, *resto = d["linhas"]
        self.assertEqual(base, (0.0, 0.0, 250.0, 0.0))
        tracos = [l for l in resto if l[0] == l[2]]
        self.assertEqual(len(tracos), 4)
        self.assertTrue(all((l[1], l[3]) == (-50.0, 50.0) for l in tracos))  # todos do mesmo tamanho, cruzando
        self.assertEqual(d["circulos"], [(100.0, 60.0, 10.0)])  # neutro: bolinha
        self.assertIn((150.0, 50.0, 170.0, 30.0), resto)       # retorno: bandeirinha
        self.assertIn((180.0, 50.0, 220.0, 50.0), resto)       # terra: barra
        self.assertEqual(fiacao([], 100.0), {"linhas": [], "circulos": []})
