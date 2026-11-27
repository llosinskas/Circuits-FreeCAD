"""Quadro de distribuição em 3D (core.quadro_3d)."""
import unittest

from freecad.Circuits.core import quadro_3d as q

QUADRO = {"numero_fases": "3", "neutro": "S", "terra": "S", "corrente_nominal_disjuntor": "63",
          "curva_disjuntor": "C", "DPS": "S", "IDR": "N"}


def _c(n, fases="R", disjuntor="16", dr="N", grupo=""):
    return {"N_circuito": str(n), "Fase_R": "S" if "R" in fases else "N", "Fase_S": "S" if "S" in fases else "N",
            "Fase_T": "S" if "T" in fases else "N", "Disjuntor": disjuntor, "Curva": "C", "DR": dr, "Grupo_DR": grupo,
            "Corrente_DR": "30", "Neutro": "S", "Terra": "S"}


class TestDispositivos(unittest.TestCase):
    def test_ordem_de_montagem(self):
        circuitos = [_c(1, grupo="DR1", dr="S"), _c(2, grupo="DR1", dr="S"), _c(3, "RS", "25", dr="S"), _c(4)]
        lista, reserva = q.dispositivos(QUADRO, circuitos)
        tipos = [d["tipo"] for d in lista]
        self.assertEqual(tipos, ["geral", "dps", "dps", "dps", "dps", "dr", "disjuntor", "disjuntor", "dr",
                                 "disjuntor", "disjuntor"])
        self.assertEqual(lista[0]["polos"], 3)
        self.assertEqual(lista[5]["circuitos"], ["C1", "C2"])
        self.assertEqual(lista[9]["polos"], 2)
        self.assertIn("C3", lista[9]["rotulo"])
        self.assertGreaterEqual(reserva, 1)

    def test_distribuir_nao_divide_dispositivo(self):
        lista = [{"polos": 3}] * 4 + [{"polos": 4}]
        posicoes, usadas = q.distribuir(lista, 12)
        self.assertEqual(posicoes[-1], (1, 0))
        self.assertEqual(usadas, 2)

    def test_fileiras_pela_caixa_comercial(self):
        self.assertEqual(q.fileiras(20), (12, 2))
        self.assertEqual(q.fileiras(40), (12, 4))
        self.assertEqual(q.fileiras(60), (18, 4))


class TestMontar(unittest.TestCase):
    def test_pecas_dentro_da_caixa(self):
        modelo = q.montar(QUADRO, [_c(i) for i in range(1, 15)])
        largura, prof, altura = modelo["dimensoes"]
        tipos = {p["tipo"] for p in modelo["pecas"]}
        for tipo in ("caixa", "trilho", "geral", "dps", "disjuntor", "fases", "neutro", "terra", "porta"):
            self.assertIn(tipo, tipos)
        for peca in modelo["pecas"]:
            for b in peca["blocos"]:
                (x, y, z), (dx, dy, dz) = b["origem"], b["dims"]
                self.assertGreaterEqual(x, -largura / 2 - 1e-6, peca["rotulo"])
                self.assertLessEqual(x + dx, largura / 2 + 1e-6, peca["rotulo"])
                self.assertGreaterEqual(z, -altura / 2 - 1e-6, peca["rotulo"])
                self.assertLessEqual(z + dz, altura / 2 + 1e-6, peca["rotulo"])
                self.assertLessEqual(y + dy, prof / 2 + 2.0 + 1e-6, peca["rotulo"])
        self.assertEqual(sum(1 for p in modelo["pecas"] if p["tipo"] == "disjuntor"), 14)

    def test_dispositivos_nao_se_sobrepoem(self):
        modelo = q.montar(QUADRO, [_c(i, "RST" if i % 3 == 0 else "R", dr="S") for i in range(1, 12)])
        caixas = [(p["blocos"][0]["origem"], p["blocos"][0]["dims"]) for p in modelo["pecas"]
                  if p["tipo"] in ("geral", "dps", "idr", "dr", "disjuntor")]
        for i, ((x1, _, z1), (dx1, _, dz1)) in enumerate(caixas):
            for (x2, _, z2), (dx2, _, dz2) in caixas[i + 1:]:
                sobrepoe = x1 < x2 + dx2 - 1e-6 and x2 < x1 + dx1 - 1e-6 and z1 < z2 + dz2 - 1e-6 and z2 < z1 + dz1 - 1e-6
                self.assertFalse(sobrepoe)

    def test_quadro_sem_neutro_nem_dps(self):
        modelo = q.montar({"numero_fases": "1", "corrente_nominal_disjuntor": "40"}, [_c(1)])
        tipos = [p["tipo"] for p in modelo["pecas"]]
        self.assertNotIn("neutro", tipos)
        self.assertNotIn("dps", tipos)


if __name__ == "__main__":
    unittest.main()
