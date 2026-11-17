"""Testes das regras puras de ``core``. Rodam sem FreeCAD."""
import unittest
import xml.etree.ElementTree as ET

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core.functions.Cabo.corrente_capacitor import corrente_capacitor
from freecad.Circuits.core.functions.Cabo.corrente_corrigida import corrente_corrigida
from freecad.Circuits.core.functions.Cabo.Correntes import Circuito_monofasico
from freecad.Circuits.core.planilha import CABECALHO_CIRCUITOS, CABECALHO_QUADRO, coluna, ultima_linha
from freecad.Circuits.core.qet import extrair_linhas
from freecad.Circuits.core.simbologia import posicoes_fase


class TestPosicoesFase(unittest.TestCase):
    def test_sem_neutro_e_terra_comeca_na_origem(self):
        self.assertEqual(posicoes_fase(3, False, False, 100), [0, 50, 100])

    def test_neutro_ou_terra_desloca_meia_altura(self):
        self.assertEqual(posicoes_fase(2, True, False, 100), [50, 100])
        self.assertEqual(posicoes_fase(2, False, True, 100), [50, 100])

    def test_neutro_e_terra_deslocam_uma_altura(self):
        self.assertEqual(posicoes_fase(3, True, True, 100), [100, 150, 200])

    def test_aceita_numero_real_vindo_da_planilha(self):
        self.assertEqual(posicoes_fase(1.0, False, False, 100), [0])

    def test_numero_de_fases_invalido_nao_desenha(self):
        self.assertEqual(posicoes_fase(0, True, True, 100), [])
        self.assertEqual(posicoes_fase("3", True, True, 100), [])


class TestPlanilha(unittest.TestCase):
    def test_coluna(self):
        self.assertEqual(coluna(0), "A")
        self.assertEqual(coluna(18), "S")

    def test_cabecalhos_cabem_nas_colunas_mescladas(self):
        self.assertEqual(len(CABECALHO_QUADRO), 19)  # mergeCells A:S
        self.assertEqual(len(CABECALHO_CIRCUITOS), 19)

    def test_ultima_linha(self):
        self.assertEqual(ultima_linha([]), 0)
        self.assertEqual(ultima_linha(["A1", "C5", "B3"]), 5)

    def test_ultima_linha_com_dois_digitos(self):
        self.assertEqual(ultima_linha(["A1", "A9", "A12", "AB10"]), 12)


class TestPlanilhaDeCircuitos(unittest.TestCase):
    def test_colunas_sem_repeticao_e_com_as_chaves_dos_circuitos(self):
        from freecad.Circuits.core import planilha as layout
        colunas = [coluna for coluna, _, _ in layout.PLANILHA_CIRCUITOS]
        chaves = {chave for _, chave, _ in layout.PLANILHA_CIRCUITOS}
        self.assertEqual(colunas, sorted(set(colunas)))
        esperadas = {c for c in layout.COLUNAS_CIRCUITO.values() if not c.startswith("Fase_")} | {"Fases"}
        self.assertEqual(chaves, esperadas)

    def test_sim_ou_nao(self):
        from freecad.Circuits.core.planilha import sim_ou_nao
        self.assertEqual([sim_ou_nao(t) for t in ("S", "sim", "True", "x", "1", " s ")], [True] * 6)
        self.assertEqual([sim_ou_nao(t) for t in ("N", "não", "False", "", "0")], [False] * 5)

    def test_ida_e_volta_de_um_circuito(self):
        from freecad.Circuits.core import planilha as layout
        circuito = {"N_circuito": "3", "Destino": "Chuveiro", "Potencia": "5500", "Tensao": "220", "Corrente": "25",
                    "Cabo": "4", "Disjuntor": "25", "Curva": "C", "Fase_R": "True", "Fase_S": "True", "Fase_T": "False",
                    "Neutro": "False", "Terra": "True", "DR": "True", "Corrente_DR": "30mA"}
        linha = layout.circuito_para_linha(circuito)
        self.assertEqual((linha["E"], linha["J"], linha["L"], linha["M"]), ("RS", "S", "N", "S"))
        por_chave = {chave: linha[coluna] for coluna, chave, _ in layout.PLANILHA_CIRCUITOS}
        self.assertEqual(layout.linha_para_circuito(por_chave), circuito)


class TestQet(unittest.TestCase):
    def linhas(self, xml):
        return extrair_linhas(ET.fromstring(f"<project>{xml}</project>"))

    def test_condutor_direto(self):
        linhas = self.linhas(
            '<conductor num="W1" element1_name="X" element2_name="Y" element1_label="K1" element2_label="K2" '
            'terminalname1="A1" terminalname2="A2" conductor_color="azul" conductor_section="1.5"/>'
        )
        self.assertEqual(linhas, [["W1", "K1", "A1", "K2", "A2", "1.5", "azul"]])

    def test_elemento_vinculado_tem_prioridade_sobre_o_rotulo(self):
        linhas = self.linhas('<conductor num="W2" element1_label="K3" element1_linked="K9" element2_label="K4"/>')
        self.assertEqual(linhas[0][1], "K9")
        self.assertEqual(linhas[0][3], "K4")

    def test_setas_com_mesmo_numero_viram_uma_ligacao(self):
        linhas = self.linhas(
            '<conductor num="W3" element1_name="Going arrow" element2_label="K5" terminalname2="11"/>'
            '<conductor num="W3" element2_name="Coming arrow" element1_label="K6" terminalname1="12"/>'
        )
        self.assertEqual(linhas, [["W3", "K5", "11", "K6", "12", "", ""]])

    def test_seta_sem_o_outro_lado_e_ignorada(self):
        linhas = self.linhas('<conductor num="W4" element1_name="Going arrow" element2_label="K7"/>')
        self.assertEqual(linhas, [])


class TestCalculos(unittest.TestCase):
    def test_corrente_monofasica(self):
        self.assertAlmostEqual(Circuito_monofasico(1000, 127, 0.8), 9.8425, places=4)

    def test_corrente_corrigida(self):
        self.assertAlmostEqual(corrente_corrigida(20, 0.8, 0.5), 50)

    def test_corrente_capacitor(self):
        self.assertAlmostEqual(corrente_capacitor(10), 13.5)


if __name__ == "__main__":
    unittest.main()
