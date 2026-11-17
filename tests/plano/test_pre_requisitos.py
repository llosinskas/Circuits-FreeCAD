"""O que o plano reaproveita e já existe. Estes testes passam hoje.

Se um deles falhar, o plano precisa ser revisto antes de continuar.
"""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import circuitos, quadro, rede


class TestJaExiste(unittest.TestCase):
    def test_reserva_de_circuitos_para_o_quadro_de_cargas(self):
        self.assertEqual([quadro.reserva_de_circuitos(n) for n in (0, 5, 10, 20, 40)], [0, 2, 3, 4, 6])

    def test_distribuir_fases_e_a_base_do_balanco(self):
        cargas = [{"potencia_va": p, "n_fases": 1} for p in (3000, 2000, 2000, 1000, 1000)]
        self.assertEqual(circuitos.distribuir_fases(cargas), {"R": 3000.0, "S": 3000.0, "T": 3000.0})

    def test_capacidade_b1_pvc_usada_hoje(self):
        self.assertEqual(circuitos.CAPACIDADE_B1_PVC[2][2.5], 24)
        self.assertEqual(circuitos.CAPACIDADE_B1_PVC[3][2.5], 21)

    def test_rede_entrega_o_trajeto_horizontal_de_cada_circuito(self):
        # O "trajeto" é só o trecho horizontal: as descidas do eletroduto até o quadro e até a
        # caixa ficam de fora. A Etapa 3 precisa do comprimento completo (ver test_etapa3).
        caixas = [
            {"id": "Q", "nome": "QD1", "x": 0.0, "y": 0.0, "tipo": "quadro", "altura": 1500.0, "pavimento": "",
             "circuito": "", "quadro": "QD1", "descricao": "QD1"},
            {"id": "T", "nome": "T1", "x": 10000.0, "y": 0.0, "tipo": "ponto", "altura": 300.0, "pavimento": "",
             "circuito": "1", "quadro": "", "ligacao": "F+N", "comando": ""},
        ]
        caminhos = [{"pontos": [(0.0, 0.0), (10000.0, 0.0)], "altura": 2800.0, "diametro": "3/4"}]
        resultado = rede.analisar(caminhos, caixas, lambda quadro_, numero, membros: {"secao": 2.5, "fases": 1, "neutro": True, "terra": True})
        (circuito,) = resultado["circuitos"]
        self.assertEqual(circuito["trajeto"], 10.0)


if __name__ == "__main__":
    unittest.main()
