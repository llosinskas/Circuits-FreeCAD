"""Montagem e dimensionamento dos circuitos a partir dos pontos da planta."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import circuitos, parametros
from freecad.Circuits.core.planilha import COLUNAS_CIRCUITO
from freecad.Circuits.core.simbolos import ILUM, TUE, TUG


def ponto(circuito, potencia, tipo=TUG, tensao=127, ligacao="F+N", fp=1.0, descricao=""):
    return {
        "circuito": circuito, "potencia_va": potencia, "fator_potencia": fp, "tensao": tensao,
        "ligacao": ligacao, "tipo_circuito": tipo, "descricao": descricao,
    }


class TestPotencia(unittest.TestCase):
    def test_textos_dos_objetos_antigos(self):
        self.assertEqual(circuitos.potencia_va("600VA"), 600)
        self.assertEqual(circuitos.potencia_va("100 W"), 100)
        self.assertEqual(circuitos.potencia_va("1,5kW"), 1500)
        self.assertEqual(circuitos.potencia_va(250), 250)
        self.assertEqual(circuitos.potencia_va("sem número", padrao=7), 7)


class TestDimensionar(unittest.TestCase):
    def test_iluminacao_pequena_fica_na_secao_minima(self):
        resultado = circuitos.dimensionar(600, 127, 1, ILUM)  # Ib = 4,72 A
        self.assertAlmostEqual(resultado["corrente"], 4.724, places=3)
        self.assertEqual((resultado["disjuntor"], resultado["cabo"]), (6, 1.5))

    def test_tomadas_respeitam_2_5_mm2(self):
        resultado = circuitos.dimensionar(600, 127, 1, TUG)
        self.assertEqual(resultado["cabo"], 2.5)

    def test_chuveiro_5500_w_em_220_v(self):
        # Ib = 25 A -> In = 25 A; 2,5 mm² conduz 24 A (< In), então sobe para 4 mm² (32 A).
        resultado = circuitos.dimensionar(5500, 220, 2, TUE)
        self.assertEqual((resultado["disjuntor"], resultado["cabo"]), (25, 4))

    def test_trifasico_usa_raiz_de_tres_e_tres_condutores_carregados(self):
        resultado = circuitos.dimensionar(15000, 380, 3, TUE)  # Ib = 22,8 A
        self.assertAlmostEqual(resultado["corrente"], 22.79, places=2)
        # In = 25 A; com 3 condutores carregados, 2,5 mm² conduz 21 A e 4 mm² conduz 28 A.
        self.assertEqual((resultado["disjuntor"], resultado["cabo"]), (25, 4))

    def test_condicao_de_coordenacao(self):
        for potencia in range(100, 20000, 370):
            r = circuitos.dimensionar(potencia, 220, 1, TUG)
            capacidade = circuitos.CAPACIDADE_B1_PVC[2][r["cabo"]]
            self.assertLessEqual(r["corrente"], r["disjuntor"])
            self.assertLessEqual(r["disjuntor"], capacidade)

    def test_corrente_acima_das_tabelas(self):
        with self.assertRaises(ValueError):
            circuitos.dimensionar(100000, 127, 1, TUE)


class TestAgrupar(unittest.TestCase):
    def test_soma_por_circuito_e_ordena_pelo_numero(self):
        resultado = circuitos.agrupar([
            ponto("10", 100), ponto("2", 100, fp=0.8), ponto("2", 300, fp=0.8), ponto("", 999),
        ])
        self.assertEqual([c["numero"] for c in resultado], ["2", "10"])
        self.assertEqual(resultado[0]["potencia_va"], 400)
        self.assertAlmostEqual(resultado[0]["potencia_w"], 320)
        self.assertEqual(resultado[0]["pontos"], 2)

    def test_destino_e_tipo(self):
        resultado = circuitos.agrupar([
            ponto("1", 100, ILUM), ponto("2", 100, TUG),
            ponto("3", 5500, TUE, 220, "F+F", descricao="Chuveiro suíte"),
        ])
        self.assertEqual([c["destino"] for c in resultado], ["Iluminação", "Tomadas", "Chuveiro suíte"])
        self.assertEqual(resultado[2]["n_fases"], 2)

    def test_avisos(self):
        resultado = circuitos.agrupar([
            ponto("1", 100, ILUM), ponto("1", 100, TUG),
            ponto("2", 5500, TUE, 220, "F+F"), ponto("2", 100, TUG, 127),
        ])
        self.assertIn("iluminação e tomadas no mesmo circuito", resultado[0]["avisos"])
        self.assertEqual(len(resultado[1]["avisos"]), 2)


class TestFases(unittest.TestCase):
    def test_equilibra_as_tres_fases(self):
        grupo = circuitos.agrupar([ponto(str(n), 1000) for n in range(1, 7)])
        carga = circuitos.distribuir_fases(grupo, 3)
        self.assertEqual(carga, {"R": 2000.0, "S": 2000.0, "T": 2000.0})

    def test_bifasico_ocupa_duas_fases(self):
        grupo = circuitos.agrupar([ponto("1", 5500, TUE, 220, "F+F"), ponto("2", 1000)])
        carga = circuitos.distribuir_fases(grupo, 3)
        self.assertEqual(grupo[0]["fases"], ["R", "S"])
        self.assertEqual(grupo[1]["fases"], ["T"])
        self.assertEqual(carga["R"], 2750.0)

    def test_quadro_monofasico(self):
        grupo = circuitos.agrupar([ponto("1", 500), ponto("2", 700)])
        self.assertEqual(circuitos.distribuir_fases(grupo, 1), {"R": 1200.0})


class TestLinhaPlanilha(unittest.TestCase):
    def test_tem_todas_as_colunas_da_planilha(self):
        grupo = circuitos.agrupar([ponto("1", 600, TUG, fp=0.8)])
        circuitos.distribuir_fases(grupo, 3)
        linha = circuitos.linha_planilha(grupo[0])
        # o grupo do DR é escolha do projetista: Montar circuitos não o escreve (a planilha o mantém)
        self.assertEqual(set(linha), set(COLUNAS_CIRCUITO.values()) - {"Grupo_DR"}
                         | {"Comprimento", "Queda", "Criterio", "_avisos"})
        self.assertEqual(linha["Potencia"], "480")
        self.assertEqual(linha["Corrente"], "4.72")
        self.assertEqual((linha["Cabo"], linha["Disjuntor"]), ("2.5", "6"))
        self.assertEqual((linha["Fase_R"], linha["Fase_S"], linha["Neutro"]), ("True", "False", "True"))
        self.assertEqual((linha["DR"], linha["Corrente_DR"]), ("True", "30mA"))

    def test_iluminacao_sem_dr(self):
        grupo = circuitos.agrupar([ponto("1", 300, ILUM)])
        linha = circuitos.linha_planilha(grupo[0])
        self.assertEqual((linha["DR"], linha["Corrente_DR"], linha["Cabo"]), ("False", "", "1.5"))


class TestLinhaPlanilhaNBR5410(unittest.TestCase):
    """A linha da planilha dimensiona pela NBR 5410 com o comprimento, o agrupamento e os parâmetros."""

    def circuito(self, potencia=1270, tipo=TUG):
        grupo = circuitos.agrupar([ponto("1", potencia, tipo)])  # 1270 VA em 127 V = 10 A
        circuitos.distribuir_fases(grupo, 3)
        return grupo[0]

    def test_sem_dados_da_rede_fica_como_antes_e_diz_o_criterio(self):
        linha = circuitos.linha_planilha(self.circuito())
        self.assertEqual((linha["Cabo"], linha["Disjuntor"]), ("2.5", "10"))
        self.assertEqual((linha["Criterio"], linha["Comprimento"], linha["Queda"]), ("Seção mínima", "", ""))
        self.assertEqual(linha["_avisos"], [])

    def test_circuito_longo_aumenta_o_cabo_pela_queda(self):
        linha = circuitos.linha_planilha(self.circuito(), comprimento=60.0)
        self.assertEqual((linha["Cabo"], linha["Criterio"]), ("6", "Queda de tensão"))
        self.assertEqual((linha["Comprimento"], linha["Queda"]), ("60", "3.54"))

    def test_agrupamento_aumenta_o_cabo(self):
        linha = circuitos.linha_planilha(self.circuito(2286), agrupados=4)  # 18 A, disjuntor 20 A
        self.assertEqual((linha["Disjuntor"], linha["Cabo"], linha["Criterio"]),
                         ("20", "4", "Capacidade de condução"))

    def test_temperatura_dos_parametros(self):
        quente = parametros.ler({"temperatura_ambiente": "45"})
        linha = circuitos.linha_planilha(self.circuito(2794), parametros=quente)  # 22 A, disjuntor 25 A
        self.assertEqual((linha["Disjuntor"], linha["Cabo"]), ("25", "4"))

    def test_curva_e_sensibilidade_dos_parametros(self):
        p = parametros.ler({"curva_tomadas": "B", "sensibilidade_dr": "300"})
        linha = circuitos.linha_planilha(self.circuito(), parametros=p)
        self.assertEqual((linha["Curva"], linha["Corrente_DR"]), ("B", "300mA"))
        luz = circuitos.linha_planilha(self.circuito(300, ILUM), parametros=parametros.ler({}))
        self.assertEqual(luz["Curva"], "B")  # padrão da iluminação

    def test_esquema_tt_poe_dr_em_todos_os_circuitos(self):
        luz = circuitos.linha_planilha(self.circuito(300, ILUM), parametros=parametros.ler({"esquema": "TT"}))
        self.assertEqual((luz["DR"], luz["Corrente_DR"]), ("True", "30mA"))

    def test_aviso_quando_o_disjuntor_nao_secciona_no_tn(self):
        # 16 A em curva D (Ia = 320 A): L máx = 0,8·127·S / (0,0225·2·320) ≈ 7,1·S m. Com queda de 4 % o
        # cabo da queda já atende (L ≤ 7,1·S também); com 7 %, 45 m pedem só 4 mm², e L máx = 28 m.
        p = parametros.ler({"curva_iluminacao": "D", "queda_terminal": "7"})
        longe = circuitos.linha_planilha(self.circuito(2032, ILUM), parametros=p, comprimento=45.0)
        self.assertEqual(longe["Cabo"], "4")
        self.assertEqual(len(longe["_avisos"]), 1)
        self.assertIn("contatos indiretos", longe["_avisos"][0])
        perto = circuitos.linha_planilha(self.circuito(2032, ILUM), parametros=p, comprimento=8.0)  # 1,5 mm²: 10,6 m
        self.assertEqual(perto["_avisos"], [])

    def test_curto_circuito_dos_parametros(self):
        p = parametros.ler({"icc_entrada_ka": "6", "tempo_curto": "0.1"})  # 6000·√0,1/115 = 16,5 → 25 mm²
        linha = circuitos.linha_planilha(self.circuito(), parametros=p)
        self.assertEqual((linha["Cabo"], linha["Criterio"]), ("25", "Curto-circuito"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
