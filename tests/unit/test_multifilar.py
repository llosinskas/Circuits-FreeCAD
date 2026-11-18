"""Diagrama multifilar (core.multifilar)."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import multifilar as m

H = 10.0
QUADRO = {"numero_fases": "3", "neutro": "True", "terra": "True", "indentificacao_painel": "QD1", "origem": "QM",
          "tensao": "220", "curva_disjuntor": "C", "corrente_nominal_disjuntor": "63"}


def circuito(n, fases, dr="False", neutro="True", potencia="1000"):
    return {"N_circuito": n, "Destino": f"Circuito {n}", "Potencia": potencia, "Fase_R": str("R" in fases),
            "Fase_S": str("S" in fases), "Fase_T": str("T" in fases), "DR": dr, "Neutro": neutro, "Terra": "True",
            "Cabo": "2.5", "Disjuntor": "16", "Curva": "C", "Corrente_DR": "30"}


def textos(forma):
    return [t[2] for t in forma["textos"]]


class TestMultifilar(unittest.TestCase):
    def test_barramentos_pelos_dados_do_quadro(self):
        self.assertEqual(m.barramentos(QUADRO), ["R", "S", "T", "N", "PE"])
        self.assertEqual(m.barramentos({"numero_fases": "2", "neutro": "False", "terra": "True"}), ["R", "S", "PE"])

    def test_condutores_do_circuito(self):
        barras = m.barramentos(QUADRO)
        self.assertEqual(m.condutores(circuito("1", "R"), barras), ["R", "N", "PE"])
        self.assertEqual(m.condutores(circuito("2", "RT", neutro="False"), barras), ["R", "T", "PE"])
        self.assertEqual(m.condutores(circuito("3", "RST", neutro="False"), m.barramentos({"numero_fases": "2"})),
                         ["R", "S", "PE"])  # a fase T não existe num quadro bifásico

    def test_um_polo_por_fase_e_ligacao_em_cada_barramento(self):
        forma = m.geometria(QUADRO, [circuito("1", "R"), circuito("2", "RST", neutro="False")], H)
        arcos_verticais = [a for a in forma["arcos"] if a[3] == -90.0]
        self.assertEqual(len(arcos_verticais), 4)  # 1 + 3 polos
        self.assertEqual(len([a for a in forma["arcos"] if a[3] == 0.0]), 3)  # disjuntor geral tripolar
        ligacoes = [c for c in forma["circulos"] if c[2] == m.RAIO_LIGACAO * H]
        self.assertEqual(len(ligacoes), 3 + 4)  # R, N, PE do primeiro; R, S, T, PE do segundo

    def test_dr_interrompe_fases_e_neutro_mas_nao_o_terra(self):
        forma = m.geometria(QUADRO, [circuito("1", "R", dr="True")], H)
        y_dr = -4 * m.PASSO_BARRA * H - m.Y_DR * H
        cortados = {l[0] for l in forma["linhas"]  # trechos de condutor (descem) que param no topo do DR
                    if l[0] == l[2] and l[1] > l[3] and abs(l[3] - (y_dr + m.ALTURA_DR * H / 2)) < 1e-6}
        x = m.X_PRIMEIRO * H
        self.assertEqual(cortados, {x, x + m.PASSO_CONDUTOR * H})  # R e N, não o PE
        self.assertIn("DR", textos(forma))
        self.assertIn("DR 30mA", textos(forma))

    def test_textos_do_circuito_e_do_quadro(self):
        forma = m.geometria(QUADRO, [circuito("1", "R")], H)
        for esperado in ("C1", "C16A", "#2,5 mm²", "1000 W", "Circuito 1", "C63A", "de QM", "Multifilar QD1 · 220 V",
                         "PE", "N"):
            self.assertIn(esperado, textos(forma))
        descricao = next(t for t in forma["textos"] if t[2] == "Circuito 1")
        self.assertEqual(descricao[4], -90.0)  # na vertical

    def test_circuitos_lado_a_lado(self):
        um = m.geometria(QUADRO, [circuito("1", "R")], H)
        dois = m.geometria(QUADRO, [circuito("1", "R"), circuito("2", "R")], H)
        self.assertAlmostEqual(dois["largura"] - um["largura"], m.largura_do_circuito(3, H))


if __name__ == "__main__":
    unittest.main()
