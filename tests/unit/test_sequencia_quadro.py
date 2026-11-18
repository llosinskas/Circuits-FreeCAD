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
            "freecad.Circuits.services.rede", "freecad.Circuits.services.parametros",
            "freecad.Circuits.services.pavimentos", "freecad.Circuits.services.alinhamento",
            "freecad.Circuits.services.tomadas", "freecad.Circuits.services.documento",
            "freecad.Circuits.objects.ponto")


class DocumentoDePlanilhas:
    """Documento que guarda as planilhas: a do quadro e as criadas a partir dela."""

    def __init__(self):
        self.Objects = []

    def addObject(self, tipo, nome):
        return PlanilhaFalsa(documento=self, nome=nome, vazia=True)

    def recompute(self):
        pass


class PlanilhaFalsa:
    def __init__(self, fases="3", documento=None, nome="QD1", vazia=False):
        self.Name = self.Label = nome
        self.Document = documento or DocumentoDePlanilhas()
        self.Document.Objects.append(self)
        self.celulas = {} if vazia else {"G3": fases}
        self.aliases = {"numero_fases": "G3", "potencia_instalada": "M3"}

    def addProperty(self, tipo, nome, grupo="", dica=""):
        setattr(self, nome, "")

    def set(self, celula, valor):
        self.celulas[celula] = valor[1:] if valor.startswith("'") else valor

    def get(self, celula):
        celula = self.aliases.get(celula, celula)
        if celula not in self.celulas:
            raise ValueError(celula)
        return self.celulas[celula]

    def clear(self, celula):
        self.celulas.pop(celula, None)

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
        planilha = self.planilhas.planilha_de_circuitos(quadro, criar=False)
        self.assertEqual((planilha.circuitos_de, planilha.Label), ("QD1", "Circuitos QD1"))
        self.assertEqual((planilha.get("A2"), planilha.get("B2"), planilha.get("E2")),
                         ("Circuito", "Descrição", "Fases (R, S, T)"))
        self.assertEqual([planilha.get(f"A{linha}") for linha in (3, 4, 5)], ["1", "2", "3"])
        self.assertEqual((planilha.get("C3"), planilha.get("G3"), planilha.get("H3"), planilha.get("J3")),
                         ("200", "1.5", "6", "N"))
        self.assertEqual((planilha.get("E5"), planilha.get("G5"), planilha.get("H5"), planilha.get("J5")),
                         ("RS", "4", "25", "S"))
        self.assertEqual(quadro.get("potencia_instalada"), "6.3")
        self.assertNotIn("A6", planilha.celulas)
        self.assertNotIn("A6", quadro.celulas)  # nada de circuito na planilha de dados do quadro

    def test_comprimento_e_agrupamento_vem_da_rede(self):
        quadro = PlanilhaFalsa()
        doc = self.documento(objeto_ponto("tomada_baixa", "2", 1270))  # 10 A
        da_rede = {"2": {"comprimento": 60.0, "agrupados": 1}}
        with mock.patch.object(self.circuitos.rede, "dados_dos_circuitos", return_value=da_rede) as rede:
            gravados, avisos = self.circuitos.montar_circuitos(doc, quadro)
        rede.assert_called_once_with(doc, quadro)
        planilha = self.planilhas.planilha_de_circuitos(quadro, criar=False)
        self.assertEqual((planilha.get("G3"), planilha.get("N3"), planilha.get("O3"), planilha.get("P3")),
                         ("6", "60", "3.54", "Queda de tensão"))
        self.assertEqual(planilha.get("P2"), "Critério determinante")

    def test_parametros_do_projeto_entram_no_calculo(self):
        quadro = PlanilhaFalsa()
        doc = self.documento(objeto_ponto("tomada_baixa", "2", 1270))
        with mock.patch.object(self.circuitos.parametros, "ler", return_value=self._parametros(curva_tomadas="B")):
            self.circuitos.montar_circuitos(doc, quadro)
        planilha = self.planilhas.planilha_de_circuitos(quadro, criar=False)
        self.assertEqual(planilha.get("I3"), "B")

    @staticmethod
    def _parametros(**mudancas):
        from freecad.Circuits.core import parametros
        return parametros.ler(mudancas)

    def test_avisos_de_seccionamento_voltam_para_o_usuario(self):
        quadro = PlanilhaFalsa()
        doc = self.documento(objeto_ponto("luz_teto", "1", 2032))  # 16 A de iluminação, sem DR
        with mock.patch.object(self.circuitos.parametros, "ler", return_value=self._parametros(curva_iluminacao="D",
                                                                                        queda_terminal="7")), \
                mock.patch.object(self.circuitos.rede, "dados_dos_circuitos",
                                  return_value={"1": {"comprimento": 45.0, "agrupados": 1}}):
            _, avisos = self.circuitos.montar_circuitos(doc, quadro)
        self.assertEqual(len(avisos), 1)
        self.assertIn("Circuito 1", avisos[0])

    def test_repetir_atualiza_no_lugar_e_preserva_circuito_manual(self):
        quadro = PlanilhaFalsa()
        luz = objeto_ponto("luz_teto", "1", 100)
        doc = self.documento(luz)
        self.circuitos.montar_circuitos(doc, quadro)
        manual = dict.fromkeys(self.planilhas.layout.COLUNAS_CIRCUITO.values(), "x")
        manual["N_circuito"] = "20"
        self.assertEqual(self.planilhas.adicionar_circuito(quadro, manual), 4)

        luz.Potencia = 300
        self.circuitos.montar_circuitos(doc, quadro)
        planilha = self.planilhas.planilha_de_circuitos(quadro, criar=False)
        self.assertEqual(planilha.get("C3"), "300")
        self.assertEqual(planilha.get("A4"), "20")
        self.assertEqual(self.planilhas.ultima_linha(planilha), 4)

    def test_mais_de_quatro_circuitos_nao_se_sobrescrevem(self):
        quadro = PlanilhaFalsa()
        doc = self.documento(*(objeto_ponto("tomada_baixa", str(n), 100) for n in range(1, 13)))
        self.circuitos.montar_circuitos(doc, quadro)
        planilha = self.planilhas.planilha_de_circuitos(quadro, criar=False)
        self.assertEqual([planilha.get(f"A{linha}") for linha in range(3, 15)], [str(n) for n in range(1, 13)])
        self.assertEqual(len(self.planilhas.ler_circuitos(quadro)), 12)

    def test_planilha_preenchida_a_mao_e_completada_na_leitura(self):
        quadro = PlanilhaFalsa()
        planilha = self.planilhas.planilha_de_circuitos(quadro)
        for celula, texto in {
            "A3": "1", "B3": "Iluminação social", "C3": 600.0, "D3": 127.0, "E3": "r",
            "A4": "2", "B4": "Tomadas cozinha", "C4": 2400.0, "D4": 127.0, "E4": "S", "J4": "sim", "L4": "S", "M4": "x",
            "A6": "5", "B6": "Chuveiro", "C6": 5500.0, "D6": 220.0, "E6": "ST", "H6": 32.0, "J6": "S",
            "B8": "linha sem número é ignorada",
        }.items():
            planilha.celulas[celula] = texto

        lidos = self.planilhas.ler_circuitos(quadro)
        self.assertEqual([c["N_circuito"] for c in lidos], ["1", "2", "5"])
        self.assertEqual((lidos[0]["Fase_R"], lidos[0]["Fase_S"], lidos[0]["Cabo"], lidos[0]["DR"]), ("True", "False", "", "False"))
        self.assertEqual((lidos[1]["DR"], lidos[1]["Neutro"], lidos[1]["Terra"]), ("True", "True", "True"))
        self.assertEqual((lidos[2]["Fase_S"], lidos[2]["Fase_T"], lidos[2]["Disjuntor"]), ("True", "True", "32"))

        completos = self.planilhas.ler_circuitos_completos(quadro)
        # iluminação: 600 W / 127 V = 4,72 A -> disjuntor 6 A, cabo 1,5 mm²
        self.assertEqual((completos[0]["Corrente"], completos[0]["Disjuntor"], completos[0]["Cabo"], completos[0]["Curva"]),
                         ("4.72", "6", "1.5", "C"))
        # tomadas: 2400 W / 127 V = 18,9 A -> disjuntor 20 A, cabo 2,5 mm²
        self.assertEqual((completos[1]["Disjuntor"], completos[1]["Cabo"]), ("20", "2.5"))
        # chuveiro: o disjuntor de 32 A digitado é mantido; só o que estava em branco é calculado
        self.assertEqual((completos[2]["Disjuntor"], completos[2]["Corrente"], completos[2]["Cabo"]), ("32", "25", "4"))

    def test_circuitos_do_formato_antigo_sao_levados_para_a_planilha_nova(self):
        quadro = PlanilhaFalsa()
        antigo = {"A5": "N_circuito", "A6": "1", "B6": "Tomadas", "C6": "1500", "D6": "220", "H6": "8.5", "J6": "2.5",
                  "N6": "16", "O6": "C", "P6": "True", "Q6": "False", "R6": "False", "S6": "True", "T6": "True",
                  "U6": "True", "V6": "30mA"}
        quadro.celulas.update(antigo)
        antes = self.planilhas.ler_circuitos(quadro)  # sem planilha nova, lê o formato antigo
        self.assertEqual((antes[0]["Cabo"], antes[0]["Fase_R"], antes[0]["DR"]), ("2.5", "True", "True"))

        planilha = self.planilhas.planilha_de_circuitos(quadro)
        self.assertEqual((planilha.get("A3"), planilha.get("E3"), planilha.get("G3"), planilha.get("J3"), planilha.get("K3")),
                         ("1", "R", "2.5", "S", "30mA"))
        self.assertEqual(self.planilhas.ler_circuitos(quadro), antes)
        self.assertEqual(sorted(quadro.celulas), ["G3"])  # as linhas antigas saíram da planilha do quadro
        self.assertIs(self.planilhas.planilha_de_circuitos(quadro), planilha)  # não cria outra

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
        self.assertEqual(itens[("Disjuntor de circuito", "1P 6 A curva B")], 1)  # iluminação: curva B por padrão
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

    def test_balancear_fases_grava_so_os_mudados_e_respeita_os_fixos(self):
        quadro = PlanilhaFalsa()
        planilha = self.planilhas.planilha_de_circuitos(quadro)
        for linha, (numero, potencia, fases) in enumerate(
                [("1", "2000", "R*"), ("2", "1000", "R"), ("3", "1000", "R"), ("4", "", "R")], start=3):
            planilha.set(f"A{linha}", numero)
            planilha.set(f"C{linha}", potencia)
            planilha.set(f"E{linha}", fases)
        planilha.set("F6", "8")  # sem potência: corrente × tensão = 8 × 125
        planilha.set("D6", "125")
        resultado = self.planilhas.balancear_fases(quadro)
        self.assertEqual(planilha.get("E4"), "R")  # sem aplicar, nada muda
        self.assertEqual(resultado["antes"]["R"], 5000.0)
        self.assertEqual(resultado["fases"]["1"], "R")  # fixo
        self.planilhas.balancear_fases(quadro, aplicar=True)
        self.assertEqual(planilha.get("E3"), "R*")
        self.assertEqual(sorted(planilha.get(f"E{n}") for n in (4, 5, 6)).count("R"), 0)
        self.assertEqual(resultado["depois"], {"R": 2000.0, "S": 2000.0, "T": 1000.0})

    def test_balancear_sem_planilha_de_circuitos(self):
        self.assertIsNone(self.planilhas.balancear_fases(PlanilhaFalsa()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
