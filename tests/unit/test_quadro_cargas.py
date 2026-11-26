"""Quadro de cargas, para o unifilar como folha de projeto (core/quadro_cargas.py).

Quadro de cargas por fase, desequilíbrio, sugestão de fases, reservas e DR por grupo.
Os circuitos são as linhas da planilha de circuitos (``planilhas.ler_circuitos_completos``).
"""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import quadro_cargas


def circuito(numero, potencia, fases="R", destino="", dr=False, grupo_dr="", **outros):
    """Linha da planilha de circuitos, no formato de ``planilhas.ler_circuitos_completos``."""
    linha = {
        "N_circuito": str(numero), "Destino": destino, "Potencia": str(potencia),
        "Fase_R": str("R" in fases), "Fase_S": str("S" in fases), "Fase_T": str("T" in fases),
        "DR": str(dr), "Grupo_DR": grupo_dr, "Corrente": "", "Disjuntor": "", "Cabo": "",
    }
    linha.update(outros)
    return linha


class Base(unittest.TestCase):
    def setUp(self):
        self.qc = quadro_cargas


class TestCargaPorFase(Base):
    def test_monofasicos_somam_na_propria_fase(self):
        carga = self.qc.carga_por_fase([circuito(1, 1000, "R"), circuito(2, 600, "R"), circuito(3, 800, "T")])
        self.assertEqual(carga, {"R": 1600.0, "S": 0.0, "T": 800.0})

    def test_bifasico_divide_a_potencia_entre_as_fases(self):
        carga = self.qc.carga_por_fase([circuito(1, 5400, "RS")])
        self.assertEqual(carga, {"R": 2700.0, "S": 2700.0, "T": 0.0})

    def test_circuito_sem_fase_nao_entra_e_e_avisado(self):
        circuitos = [circuito(1, 1000, "R"), circuito(2, 500, "")]
        self.assertEqual(self.qc.carga_por_fase(circuitos)["R"], 1000.0)
        self.assertEqual(self.qc.sem_fase(circuitos), ["2"])

    def test_potencia_com_virgula_decimal(self):
        self.assertEqual(self.qc.carga_por_fase([circuito(1, "1500,5", "S")])["S"], 1500.5)


class TestDesequilibrio(Base):
    def test_percentual_sobre_a_fase_mais_carregada(self):
        self.assertAlmostEqual(self.qc.desequilibrio({"R": 3000.0, "S": 2400.0, "T": 3000.0}), 20.0)

    def test_quadro_vazio_nao_divide_por_zero(self):
        self.assertEqual(self.qc.desequilibrio({"R": 0.0, "S": 0.0, "T": 0.0}), 0.0)


class TestSugerirFases(Base):
    def test_equilibra_e_nao_altera_a_planilha(self):
        circuitos = [circuito(n, p, "R") for n, p in enumerate((3000, 2000, 2000, 1000, 1000), start=1)]
        sugestao = self.qc.sugerir_fases(circuitos)
        self.assertEqual(set(sugestao), {"1", "2", "3", "4", "5"})
        carga = self.qc.carga_por_fase([dict(c, **self._fases(sugestao[c["N_circuito"]])) for c in circuitos])
        self.assertEqual(self.qc.desequilibrio(carga), 0.0)
        self.assertTrue(all(c["Fase_R"] == "True" for c in circuitos))  # a entrada continua igual

    def test_bifasico_continua_com_duas_fases(self):
        sugestao = self.qc.sugerir_fases([circuito(1, 5400, "RS"), circuito(2, 1000, "T")])
        self.assertEqual(len(sugestao["1"]), 2)

    def test_quadro_monofasico_poe_tudo_em_r(self):
        sugestao = self.qc.sugerir_fases([circuito(1, 1000, "S"), circuito(2, 800, "T")], fases_quadro=1)
        self.assertEqual(sugestao, {"1": "R", "2": "R"})

    @staticmethod
    def _fases(texto):
        return {f"Fase_{f}": str(f in texto) for f in "RST"}


class TestReservas(Base):
    def test_acrescenta_as_reservas_da_nbr_5410_numeradas_em_seguida(self):
        linhas = self.qc.com_reservas([circuito(n, 100, "R") for n in range(1, 6)])
        reservas = [l for l in linhas if l["Destino"] == "Reserva"]
        self.assertEqual([r["N_circuito"] for r in reservas], ["6", "7"])
        self.assertEqual(len(linhas), 7)

    def test_reserva_nao_tem_potencia_nem_fase(self):
        reserva = self.qc.com_reservas([circuito(1, 100, "R")])[-1]
        self.assertEqual((reserva["Potencia"], self.qc.carga_por_fase([reserva])), ("", {"R": 0.0, "S": 0.0, "T": 0.0}))


class TestQuadroDeCargas(Base):
    def test_uma_linha_por_circuito_e_a_linha_de_total(self):
        linhas = self.qc.quadro_de_cargas([circuito(1, 1000, "R", "Tomadas"), circuito(2, 5400, "RS", "Chuveiro")])
        self.assertEqual([l["circuito"] for l in linhas], ["1", "2", "Total"])
        self.assertEqual((linhas[1]["R"], linhas[1]["S"], linhas[1]["T"]), (2700.0, 2700.0, 0.0))
        self.assertEqual((linhas[-1]["R"], linhas[-1]["S"], linhas[-1]["T"]), (3700.0, 2700.0, 0.0))
        self.assertEqual(linhas[0]["descricao"], "Tomadas")


class TestGruposDR(Base):
    def test_circuitos_do_mesmo_grupo_ficam_sob_um_dr(self):
        circuitos = [circuito(1, 100, "R", dr=True, grupo_dr="DR1"), circuito(2, 100, "S", dr=True, grupo_dr="DR1"),
                     circuito(3, 100, "T", dr=True), circuito(4, 100, "R")]
        self.assertEqual(self.qc.grupos_dr(circuitos), [("DR1", ["1", "2"]), ("C3", ["3"])])

    def test_grupo_preenchido_vale_mesmo_sem_marcar_dr(self):
        self.assertEqual(self.qc.grupos_dr([circuito(1, 100, "R", grupo_dr="DR2")]), [("DR2", ["1"])])


if __name__ == "__main__":
    unittest.main()
