"""Diagrama multifilar na vertical (core.multifilar)."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import multifilar as m

H = 10.0
QUADRO = {"numero_fases": "3", "neutro": "True", "terra": "True", "indentificacao_painel": "QD1", "origem": "QM",
          "tensao": "220", "curva_disjuntor": "C", "corrente_nominal_disjuntor": "63"}


def circuito(n, fases, dr="False", neutro="True", potencia="1000", descricao=None):
    return {"N_circuito": n, "Destino": descricao or f"Circuito {n}", "Potencia": potencia,
            "Fase_R": str("R" in fases), "Fase_S": str("S" in fases), "Fase_T": str("T" in fases), "DR": dr,
            "Neutro": neutro, "Terra": "True", "Cabo": "2.5", "Disjuntor": "16", "Curva": "C", "Corrente_DR": "30"}


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

    def test_barramentos_na_vertical_e_circuitos_na_horizontal(self):
        forma = m.geometria(QUADRO, [circuito("1", "R")], H)
        barras = [l for l in forma["linhas"] if l[0] == l[2] and l[1] == 0.0 and l[3] < 0]
        self.assertEqual(sorted(l[0] for l in barras), [i * m.PASSO_BARRA * H for i in range(5)])
        y = -m.X_PRIMEIRO * H
        x_fim = 4 * m.PASSO_BARRA * H + m.X_FIM * H
        self.assertIn((m.X_DISJUNTOR * H + 4 * m.PASSO_BARRA * H + m.RAIO_POLO * 2 * H
                       + 0.08 * H, y, x_fim, y), forma["linhas"])  # fase R depois do polo até o retângulo

    def test_um_polo_por_fase_e_ligacao_em_cada_barramento(self):
        forma = m.geometria(QUADRO, [circuito("1", "R"), circuito("2", "RST", neutro="False")], H)
        self.assertEqual(len([a for a in forma["arcos"] if a[3] == 0.0]), 4)  # 1 + 3 polos dos circuitos
        self.assertEqual(len([a for a in forma["arcos"] if a[3] == -90.0]), 3)  # disjuntor geral tripolar
        ligacoes = [c for c in forma["circulos"] if c[2] == m.RAIO_LIGACAO * H]
        self.assertEqual(len(ligacoes), 3 + 4)  # R, N, PE do primeiro; R, S, T, PE do segundo

    def test_dr_interrompe_fases_e_neutro_mas_nao_o_terra(self):
        forma = m.geometria(QUADRO, [circuito("1", "R", dr="True")], H)
        x_dr = 4 * m.PASSO_BARRA * H + m.X_DR * H
        cortados = {l[1] for l in forma["linhas"]  # trechos de condutor que param na entrada do DR
                    if l[1] == l[3] and l[2] > l[0] and abs(l[2] - (x_dr - m.LARGURA_DR * H / 2)) < 1e-6}
        y = -m.X_PRIMEIRO * H
        self.assertEqual(cortados, {y, y - m.PASSO_CONDUTOR * H})  # R e N, não o PE
        self.assertIn("DR", textos(forma))
        self.assertIn("30mA", textos(forma))

    def test_cada_circuito_termina_num_retangulo_com_numero_e_descricao(self):
        forma = m.geometria(QUADRO, [circuito("1", "R"), circuito("2", "RST", descricao="Motor da bomba de recalque")],
                            H)
        self.assertEqual(len(forma["cargas"]), 2)
        x1, topo, x2, base = forma["cargas"][1]
        self.assertGreater(x2 - x1, m.LARGURA_CARGA * H)  # alargado para a descrição
        dentro = [t for t in forma["textos"] if x1 < t[0] < x2 and base < t[1] < topo]
        self.assertEqual([t[2] for t in dentro], ["C2", "Motor da bomba de recalque"])
        self.assertLess(forma["cargas"][1][1], forma["cargas"][0][3])  # um embaixo do outro

    def test_textos_do_circuito_e_do_quadro(self):
        forma = m.geometria(QUADRO, [circuito("1", "R")], H)
        for esperado in ("C1", "C16A", "#2,5 mm² · 1000 W", "Circuito 1", "C63A", "de QM",
                         "Multifilar QD1 · 220 V", "PE", "N"):
            self.assertIn(esperado, textos(forma))

    def test_circuitos_um_embaixo_do_outro(self):
        um = m.geometria(QUADRO, [circuito("1", "R")], H)
        dois = m.geometria(QUADRO, [circuito("1", "R"), circuito("2", "R")], H)
        self.assertAlmostEqual(dois["altura"] - um["altura"], m.altura_do_circuito(3, H))


if __name__ == "__main__":
    unittest.main()
