"""Balanceamento de cargas entre as fases (core.balanceamento)."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import balanceamento as b


def c(numero, potencia, fases="R"):
    return {"numero": numero, "potencia": potencia, "fases": fases}


class TestBalanceamento(unittest.TestCase):
    def test_tudo_na_fase_r_e_espalhado(self):
        circuitos = [c("1", 1000), c("2", 1000), c("3", 1000)]
        r = b.balancear(circuitos)
        self.assertEqual(r["antes"], {"R": 3000.0, "S": 0.0, "T": 0.0})
        self.assertEqual(r["depois"], {"R": 1000.0, "S": 1000.0, "T": 1000.0})
        self.assertEqual((round(r["desequilibrio_antes"]), r["desequilibrio_depois"]), (100, 0.0))
        self.assertEqual(len(r["mudados"]), 2)  # um fica onde estava

    def test_bifasico_divide_a_potencia_entre_as_duas_fases(self):
        r = b.balancear([c("1", 4400, "RS"), c("2", 2200, "R")])
        self.assertEqual(sorted(r["depois"].values()), [2200.0, 2200.0, 2200.0])
        self.assertEqual(len(r["fases"]["1"]), 2)

    def test_trifasico_e_fixos_nao_mudam(self):
        circuitos = [c("1", 9000, "RST"), c("2", 3000, "R"), c("3", 1000, "R"), c("4", 1000, "R")]
        r = b.balancear(circuitos, fixos=["2"])
        self.assertEqual((r["fases"]["1"], r["fases"]["2"]), ("RST", "R"))
        self.assertEqual(r["depois"], {"R": 6000.0, "S": 4000.0, "T": 4000.0})

    def test_ja_equilibrado_nao_muda_nada(self):
        circuitos = [c("1", 1500, "R"), c("2", 1500, "S"), c("3", 1500, "T")]
        r = b.balancear(circuitos)
        self.assertEqual(r["mudados"], [])
        self.assertIn("Nenhum circuito", b.relatorio(r))

    def test_troca_resolve_o_que_a_gulosa_nao_resolve(self):
        # 5+5+4+4+3+3+3 = 27 kW: maiores primeiro dá 11/8/8; o ótimo é 9/9/9 ({5,4}, {5,4}, {3,3,3})
        circuitos = [c(str(i), p) for i, p in enumerate([5000, 5000, 4000, 4000, 3000, 3000, 3000], start=1)]
        r = b.balancear(circuitos)
        self.assertEqual(r["depois"], {"R": 9000.0, "S": 9000.0, "T": 9000.0})

    def test_quadro_bifasico_so_usa_r_e_s(self):
        r = b.balancear([c("1", 1000), c("2", 1000, "T")], fases="RS")
        self.assertEqual(set(r["depois"]), {"R", "S"})
        self.assertEqual(sorted(r["fases"].values()), ["R", "S"])

    def test_sem_fase_definida_vale_uma(self):
        r = b.balancear([c("1", 1000, ""), c("2", 1000, "")])
        self.assertEqual(sorted(len(f) for f in r["fases"].values()), [1, 1])
        self.assertEqual(r["mudados"], ["1", "2"])

    def test_relatorio_com_corrente(self):
        texto = b.relatorio(b.balancear([c("1", 1270), c("2", 1270)]), 127.0)
        self.assertIn("10,0 A", texto)
        self.assertIn("Circuitos que mudam de fase: C", texto)
        self.assertIn("Desequilíbrio: 100,0 %", texto)


if __name__ == "__main__":
    unittest.main()
