"""Sequência pontos da planta -> circuitos -> planilha do quadro, com o FreeCAD simulado.

O FreeCAD real é coberto por ``tests/gui/smoke_gui.py``; aqui uma planilha e um
documento falsos conferem a lógica de gravação das linhas.
"""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet")
SERVICOS = ("freecad.Circuits.services.circuitos", "freecad.Circuits.services.planilhas",
            "freecad.Circuits.services.tomadas", "freecad.Circuits.services.documento",
            "freecad.Circuits.objects.ponto")


class PlanilhaFalsa:
    Label = Name = "QD1"

    def __init__(self, fases="3"):
        self.celulas = {"G3": fases}
        self.aliases = {"numero_fases": "G3", "potencia_instalada": "M3"}

    def set(self, celula, valor):
        self.celulas[celula] = valor[1:] if valor.startswith("'") else valor

    def get(self, celula):
        celula = self.aliases.get(celula, celula)
        if celula not in self.celulas:
            raise ValueError(celula)
        return self.celulas[celula]

    def getUsedCells(self):
        return list(self.celulas)

    def getCellFromAlias(self, alias):
        return self.aliases[alias]


def objeto_ponto(simbolo, circuito, potencia, tensao="127V", ligacao="F+N", quadro=""):
    return types.SimpleNamespace(
        Proxy=types.SimpleNamespace(Type="Ponto"), Label=simbolo, Simbolo=simbolo, Circuito=circuito,
        Quadro=quadro, Potencia=potencia, FatorPotencia=1.0, Tensao=tensao, Ligacao=ligacao, Descricao=simbolo,
    )


class TestSequenciaQuadro(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in SERVICOS:
            sys.modules.pop(nome, None)
        self.circuitos = importlib.import_module("freecad.Circuits.services.circuitos")
        self.planilhas = importlib.import_module("freecad.Circuits.services.planilhas")

    def tearDown(self):
        for nome in SERVICOS:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def documento(self, *objetos):
        return types.SimpleNamespace(Objects=list(objetos), recompute=lambda: None)

    def test_pontos_viram_linhas_do_quadro(self):
        quadro = PlanilhaFalsa()
        doc = self.documento(
            objeto_ponto("luz_teto", "1", 100), objeto_ponto("luz_teto", "1", 100),
            objeto_ponto("tomada_baixa", "2", 600),
            objeto_ponto("chuveiro", "3", 5500, "220V", "F+F"),
            objeto_ponto("tomada_baixa", "9", 100, quadro="OUTRO"),  # pertence a outro quadro
        )
        gravados, avisos = self.circuitos.montar_circuitos(doc, quadro)

        self.assertEqual([c["numero"] for c in gravados], ["1", "2", "3"])
        self.assertEqual(avisos, [])
        self.assertEqual([quadro.get(f"A{linha}") for linha in (6, 7, 8)], ["1", "2", "3"])
        self.assertEqual((quadro.get("C6"), quadro.get("J6"), quadro.get("N6")), ("200", "1.5", "6"))
        self.assertEqual((quadro.get("J8"), quadro.get("N8"), quadro.get("U8")), ("4", "25", "True"))
        self.assertEqual(quadro.get("potencia_instalada"), "6.3")
        self.assertNotIn("A9", quadro.celulas)

    def test_repetir_atualiza_no_lugar_e_preserva_circuito_manual(self):
        quadro = PlanilhaFalsa()
        luz = objeto_ponto("luz_teto", "1", 100)
        doc = self.documento(luz)
        self.circuitos.montar_circuitos(doc, quadro)
        manual = dict.fromkeys(self.planilhas.layout.COLUNAS_CIRCUITO.values(), "x")
        manual["N_circuito"] = "20"
        self.assertEqual(self.planilhas.adicionar_circuito(quadro, manual), 7)

        luz.Potencia = 300
        self.circuitos.montar_circuitos(doc, quadro)
        self.assertEqual(quadro.get("C6"), "300")
        self.assertEqual(quadro.get("A7"), "20")
        self.assertEqual(self.planilhas.ultima_linha(quadro), 7)

    def test_mais_de_quatro_circuitos_nao_se_sobrescrevem(self):
        quadro = PlanilhaFalsa()
        doc = self.documento(*(objeto_ponto("tomada_baixa", str(n), 100) for n in range(1, 13)))
        self.circuitos.montar_circuitos(doc, quadro)
        self.assertEqual([quadro.get(f"A{linha}") for linha in range(6, 18)], [str(n) for n in range(1, 13)])

    def test_componentes_lidos_da_planilha(self):
        from freecad.Circuits.core import quadro as regras
        planilha = PlanilhaFalsa()
        planilha.aliases.update({"corrente_nominal_disjuntor": "K3", "curva_disjuntor": "J3", "neutro": "I3",
                                 "terra": "H3", "DPS": "P3"})
        planilha.celulas.update({"K3": 40.0, "J3": "C", "I3": "True", "H3": "True", "P3": "False"})
        doc = self.documento(objeto_ponto("luz_teto", "1", 300), objeto_ponto("tomada_baixa", "2", 1200))
        self.circuitos.montar_circuitos(doc, planilha)

        dados = self.planilhas.ler_quadro(planilha)
        linhas = self.planilhas.ler_circuitos(planilha)
        self.assertEqual((dados["corrente_nominal_disjuntor"], dados["numero_fases"]), ("40", "3"))
        self.assertEqual([linha["N_circuito"] for linha in linhas], ["1", "2"])
        itens = {(i["item"], i["especificacao"]): i["quantidade"] for i in regras.componentes(dados, linhas)}
        self.assertEqual(itens[("Disjuntor geral", "3P 40 A curva C")], 1)
        self.assertEqual(itens[("Disjuntor de circuito", "1P 6 A curva C")], 1)
        self.assertEqual(itens[("Disjuntor de circuito", "1P 10 A curva C")], 1)
        self.assertEqual(itens[("Interruptor DR", "2P 25 A, 30mA")], 1)

    def test_simbolo_de_quadro_nao_entra_como_carga(self):
        quadro = PlanilhaFalsa()
        doc = self.documento(
            objeto_ponto("tomada_baixa", "1", 600),
            objeto_ponto("quadro_distribuicao", "1", 0, "220V", "3F"),
            objeto_ponto("medicao_agrupada", "", 0, "220V", "3F"),
        )
        gravados, avisos = self.circuitos.montar_circuitos(doc, quadro)
        self.assertEqual([(c["numero"], c["pontos"], c["potencia_va"]) for c in gravados], [("1", 1, 600)])
        self.assertEqual(avisos, [])

    def test_demanda_e_gravada_no_quadro(self):
        quadro = PlanilhaFalsa()
        quadro.aliases["potencia_demanda"] = "N3"
        doc = self.documento(
            objeto_ponto("luz_teto", "1", 800), objeto_ponto("tomada_baixa", "2", 1200),
            objeto_ponto("chuveiro", "3", 5500, "220V", "F+F"),
        )
        resultado = self.circuitos.calcular_demanda(doc, quadro)
        self.assertAlmostEqual(resultado["demanda_w"], 2000 * 0.75 + 5500)
        self.assertEqual((quadro.get("potencia_instalada"), quadro.get("potencia_demanda")), ("7.5", "7.0"))

    def test_demanda_sem_pontos(self):
        self.assertIsNone(self.circuitos.calcular_demanda(self.documento(), PlanilhaFalsa()))

    def test_ponto_do_motor_recebe_os_dados_eletricos(self):
        from freecad.Circuits.core.functions.Predial import motores
        criado = types.SimpleNamespace()
        with mock.patch.object(self.circuitos, "create_ponto", return_value=criado) as criar:
            obj = self.circuitos.criar_ponto_motor("Bomba de recalque 2 cv", motores.dados_motor(1.2, 380))
        criar.assert_called_once_with("ponto_forca")
        self.assertIs(obj, criado)
        self.assertEqual((obj.Descricao, obj.Tensao, obj.Ligacao), ("Bomba de recalque 2 cv", "380V", "3F"))
        self.assertAlmostEqual(obj.Potencia, 2 * 0.7355 / 0.85 / 0.85 * 1000, places=0)

    def test_circuito_acima_das_tabelas_vira_aviso(self):
        quadro = PlanilhaFalsa()
        doc = self.documento(objeto_ponto("ponto_forca", "1", 90000))
        gravados, avisos = self.circuitos.montar_circuitos(doc, quadro)
        self.assertEqual(gravados, [])
        self.assertIn("não foi gravado", avisos[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
