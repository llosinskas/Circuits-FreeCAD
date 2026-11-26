"""Componentes do quadro: disjuntores, DR, DPS, barramentos e tamanho da caixa."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import quadro

QUADRO = {
    "numero_fases": "3", "neutro": "True", "terra": "True", "curva_disjuntor": "C",
    "corrente_nominal_disjuntor": "63", "corrente_curto_circuito": "6", "material_quadro": "PVC",
    "DPS": "True", "classe_DPS": "II", "tensao_DPS": "275", "corrente_DPS": "20",
}


def circuito(numero, disjuntor, fases="R", dr=False, neutro=True):
    return {
        "N_circuito": str(numero), "Disjuntor": str(disjuntor), "Curva": "C",
        "Fase_R": str("R" in fases), "Fase_S": str("S" in fases), "Fase_T": str("T" in fases),
        "Neutro": str(neutro), "Terra": "True", "DR": str(dr), "Corrente_DR": "30mA" if dr else "",
    }


def por_item(itens):
    return {(i["item"], i["especificacao"]): i["quantidade"] for i in itens}


class TestRegras(unittest.TestCase):
    def test_numero_e_verdadeiro(self):
        self.assertEqual(quadro.numero("40"), 40)
        self.assertEqual(quadro.numero("2,5"), 2.5)
        self.assertEqual(quadro.numero("", 7), 7)
        self.assertTrue(quadro.verdadeiro("True"))
        self.assertFalse(quadro.verdadeiro("False"))
        self.assertFalse(quadro.verdadeiro(""))

    def test_valores_comerciais(self):
        self.assertEqual([quadro.dr_comercial(c) for c in (10, 25, 32, 63, 70)], [25, 25, 40, 63, 80])
        self.assertEqual([quadro.barramento_comercial(c) for c in (40, 63, 70, 100)], [50, 63, 80, 100])
        with self.assertRaises(ValueError):
            quadro.barramento_comercial(5000)

    def test_reserva_da_nbr_5410(self):
        self.assertEqual([quadro.reserva_de_circuitos(n) for n in (0, 1, 6, 7, 12, 13, 30, 31, 40)],
                         [0, 2, 2, 3, 3, 4, 4, 5, 6])

    def test_fases_do_circuito(self):
        self.assertEqual(quadro.fases_do_circuito(circuito(1, 16, "R")), 1)
        self.assertEqual(quadro.fases_do_circuito(circuito(1, 16, "RS")), 2)
        self.assertEqual(quadro.fases_do_circuito(circuito(1, 16, "RST")), 3)
        self.assertEqual(quadro.fases_do_circuito({}), 1)


class TestCompletar(unittest.TestCase):
    def base(self, **extra):
        dados = {"N_circuito": "1", "Destino": "Tomadas", "Potencia": "1200", "Tensao": "127", "Corrente": "",
                 "Cabo": "", "Disjuntor": "", "Curva": "", "Fase_R": "True", "Fase_S": "False", "Fase_T": "False"}
        dados.update(extra)
        return dados

    def test_completar_usa_os_parametros_e_o_comprimento(self):
        from freecad.Circuits.core import parametros
        p = parametros.ler({"isolacao": "EPR"})
        # 3000 W em 127 V = 23,6 A, disjuntor 25 A: PVC B1 2,5 mm² conduz 24 A (pede 4), EPR 2,5 mm² 31 A
        pvc = quadro.completar(self.base(Potencia="3000"))
        epr = quadro.completar(self.base(Potencia="3000"), p)
        self.assertLess(float(epr["Cabo"]), float(pvc["Cabo"]))
        longo = quadro.completar(self.base(Comprimento="60"), parametros.ler({}))
        self.assertGreater(float(longo["Cabo"]), float(quadro.completar(self.base(), parametros.ler({}))["Cabo"]))

    def test_preenche_o_que_esta_em_branco(self):
        c = quadro.completar(self.base())  # 1200 / 127 = 9,45 A
        self.assertEqual((c["Corrente"], c["Disjuntor"], c["Cabo"], c["Curva"]), ("9.45", "10", "2.5", "C"))

    def test_iluminacao_usa_a_secao_minima_de_iluminacao(self):
        self.assertEqual(quadro.completar(self.base(Destino="Iluminação sala", Potencia="400"))["Cabo"], "1.5")

    def test_valores_digitados_nao_mudam(self):
        c = quadro.completar(self.base(Cabo="6", Disjuntor="20", Curva="B", Corrente="9"))
        self.assertEqual((c["Cabo"], c["Disjuntor"], c["Curva"], c["Corrente"]), ("6", "20", "B", "9"))

    def test_cabo_em_branco_acompanha_o_disjuntor_digitado(self):
        self.assertEqual(quadro.completar(self.base(Disjuntor="40"))["Cabo"], "6")  # 6 mm² conduz 41 A
        self.assertEqual(quadro.completar(self.base(Disjuntor="500"))["Cabo"], "")  # acima da tabela

    def test_sem_potencia_ou_tensao_fica_como_esta(self):
        c = quadro.completar(self.base(Potencia=""))
        self.assertEqual((c["Corrente"], c["Cabo"], c["Disjuntor"], c["Curva"]), ("", "", "", "C"))
        c = quadro.completar(self.base(Potencia="900000"))  # acima do maior disjuntor
        self.assertEqual((c["Cabo"], c["Disjuntor"]), ("", ""))

    def test_nao_altera_o_dicionario_recebido(self):
        dados = self.base()
        quadro.completar(dados)
        self.assertEqual(dados["Cabo"], "")


class TestComponentes(unittest.TestCase):
    def setUp(self):
        self.circuitos = [
            circuito(1, 10), circuito(2, 16, dr=True), circuito(3, 16, dr=True),
            circuito(4, 25, "RS", dr=True, neutro=False), circuito(5, 32, "RST", dr=True),
        ]
        self.itens = quadro.componentes(QUADRO, self.circuitos)
        self.mapa = por_item(self.itens)

    def test_disjuntor_geral_e_dps(self):
        self.assertEqual(self.mapa[("Disjuntor geral", "3P 63 A curva C, 6 kA")], 1)
        self.assertEqual(self.mapa[("DPS", "Classe II, 275 V, 20 kA")], 4)  # três fases + neutro

    def test_disjuntores_agrupados_por_especificacao(self):
        self.assertEqual(self.mapa[("Disjuntor de circuito", "1P 10 A curva C")], 1)
        self.assertEqual(self.mapa[("Disjuntor de circuito", "1P 16 A curva C")], 2)
        self.assertEqual(self.mapa[("Disjuntor de circuito", "2P 25 A curva C")], 1)
        self.assertEqual(self.mapa[("Disjuntor de circuito", "3P 32 A curva C")], 1)

    def test_dr_bipolar_ou_tetrapolar(self):
        self.assertEqual(self.mapa[("Interruptor DR", "2P 25 A, 30mA")], 3)  # 16 A, 16 A e 25 A
        self.assertEqual(self.mapa[("Interruptor DR", "4P 40 A, 30mA")], 1)  # trifásico de 32 A

    def test_barramentos(self):
        self.assertEqual(self.mapa[("Barramento de fases", "trifásico, 63 A")], 1)
        # 4 circuitos com neutro + 2 de reserva + 1 da entrada; terra: 5 + 2 + 1
        self.assertEqual(self.mapa[("Barramento de neutro", "7 terminais")], 1)
        self.assertEqual(self.mapa[("Barramento de terra (PE)", "8 terminais")], 1)

    def test_caixa_em_modulos(self):
        # geral 3 + DPS 4 + disjuntores (1+1+1+2+3) + DR (2+2+2+4) = 25 ocupados, + 2 de reserva = 27 -> 28
        self.assertEqual(self.itens[0]["item"], "Quadro de distribuição")
        self.assertEqual(self.itens[0]["especificacao"], "28 módulos DIN (25 ocupados + 2 de reserva), PVC")

    def test_dr_por_grupo(self):
        grupo = [dict(circuito(1, 16, dr=True), Grupo_DR="DR1", Corrente="12"),
                 dict(circuito(2, 20), Grupo_DR="DR1", Corrente="15"),
                 dict(circuito(3, 10, dr=True), Corrente="5")]
        mapa = por_item(quadro.componentes(QUADRO, grupo))
        drs = {esp: n for (item, esp), n in mapa.items() if item == "Interruptor DR"}
        # o grupo: 12 + 15 = 27 A na fase R -> 40 A; o circuito 3 tem o dele (25 A)
        self.assertEqual(drs, {"2P 40 A, 30mA": 1, "2P 25 A, 30mA": 1})

    def test_dr_do_grupo(self):
        membros = [dict(circuito(1, 32, "RST"), Corrente="20"), dict(circuito(2, 16, "R"), Corrente="10")]
        dr = quadro.dr_do_grupo(membros)
        self.assertEqual((dr["polos"], dr["corrente"]), (4, 40))  # R: 30 A, mas o disjuntor de 32 A manda
        self.assertEqual(quadro.dr_do_grupo([dict(circuito(1, 10), Corrente_DR="300")])["sensibilidade"], "300mA")
        self.assertEqual(quadro.sensibilidade_texto(""), "30mA")

    def test_idr_geral(self):
        self.assertIsNone(quadro.idr_geral(QUADRO))  # sem a coluna IDR
        idr = quadro.idr_geral(dict(QUADRO, IDR="True", sensibilidade_IDR="30"))
        self.assertEqual(idr["especificacao"], "4P 63 A, 30mA")  # trifásico, disjuntor geral de 63 A
        mono = quadro.idr_geral(dict(QUADRO, IDR="S", numero_fases="1", corrente_nominal_disjuntor="40"))
        self.assertEqual((mono["polos"], mono["corrente"]), (2, 40))
        grande = quadro.idr_geral(dict(QUADRO, IDR="True", corrente_nominal_disjuntor="160"))
        self.assertEqual(grande["corrente"], "160")  # acima da tabela de DR: o do disjuntor
        mapa = por_item(quadro.componentes(dict(QUADRO, IDR="True"), self.circuitos))
        self.assertEqual(mapa[("Interruptor DR geral (IDR)", "4P 63 A, 30mA")], 1)

    def test_quadro_sem_dps_nem_neutro(self):
        dados = dict(QUADRO, DPS="False", neutro="False", numero_fases="1", corrente_nominal_disjuntor="40")
        mapa = por_item(quadro.componentes(dados, [circuito(1, 16, neutro=False)]))
        self.assertNotIn("DPS", {item for item, _ in mapa})
        self.assertNotIn("Barramento de neutro", {item for item, _ in mapa})
        self.assertEqual(mapa[("Barramento de fases", "monofásico, 50 A")], 1)

    def test_quadro_vazio(self):
        self.assertEqual(quadro.componentes({}, []), [])

    def test_corrente_do_barramento(self):
        self.assertEqual(quadro.corrente_do_barramento(QUADRO), 63)
        self.assertIsNone(quadro.corrente_do_barramento({}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
