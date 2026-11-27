"""Classe IFC e propriedades BIM dos objetos da bancada (core.bim)."""
import unittest

from freecad.Circuits.core import bim
from freecad.Circuits.core import simbolos


def _props(resultado):
    return {(pset, nome): (tipo, valor) for pset, nome, tipo, valor in resultado["propriedades"]}


class TestPonto(unittest.TestCase):
    def test_tomada_e_outlet_com_psets_padrao(self):
        r = bim.classe("ponto", {"simbolo": "tomada_baixa", "legenda": "Tomada baixa", "potencia_va": 100,
                                 "fator_potencia": 0.8, "tensao": "127V", "ligacao": "F+N", "circuito": "3",
                                 "quadro": "QD1", "altura_mm": 300, "pavimento": "Térreo"})
        self.assertEqual((r["IfcType"], r["PredefinedType"], r["Tag"]), ("Outlet", "POWEROUTLET", "QD1-C3"))
        p = _props(r)
        self.assertEqual(p[("Pset_ElectricalDeviceCommon", "RatedVoltage")], ("IfcElectricVoltageMeasure", 127.0))
        self.assertEqual(p[("Pset_ElectricalDeviceCommon", "Power")], ("IfcPowerMeasure", 80.0))
        self.assertEqual(p[("Pset_ElectricalDeviceCommon", "NumberOfPoles")][1], 2)
        self.assertEqual(p[("Pset_OutletTypeCommon", "IsPluggableOutlet")], ("IfcLogical", True))
        self.assertAlmostEqual(p[(bim.PSET_CIRCUITS, "AlturaMontagem")][1], 0.3)
        self.assertEqual(p[(bim.PSET_CIRCUITS, "Pavimento")][1], "Térreo")

    def test_todo_simbolo_do_catalogo_tem_classe(self):
        for chave in simbolos.CATALOGO:
            self.assertIn(chave, bim.CLASSE_DO_SIMBOLO, chave)

    def test_luminaria_quadro_e_emergencia(self):
        luz = bim.classe("ponto", {"simbolo": "luz_teto", "potencia_va": 100, "fator_potencia": 1.0})
        self.assertEqual(luz["IfcType"], "Light Fixture")
        self.assertEqual(_props(luz)[("Pset_LightFixtureTypeCommon", "TotalWattage")][1], 100.0)
        self.assertEqual(bim.classe("ponto", {"simbolo": "emergencia"})["PredefinedType"], "SECURITYLIGHTING")
        quadro = bim.classe("ponto", {"simbolo": "quadro_distribuicao", "descricao": "QD1", "ligacao": "3F"})
        self.assertEqual((quadro["IfcType"], quadro["Tag"]), ("Electric Distribution Board", "QD1"))
        medicao = bim.classe("ponto", {"simbolo": "quadro_medicao", "legenda": "Quadro de medição"})
        self.assertEqual((medicao["PredefinedType"], medicao["ObjectType"]), ("USERDEFINED", "Quadro de medição"))

    def test_caixa_de_passagem_em_metros_ou_pes(self):
        dados = {"simbolo": "caixa_passagem", "caixa_mm": (100.0, 50.0, 100.0)}
        metro = _props(bim.classe("ponto", dados))
        self.assertAlmostEqual(metro[("Pset_JunctionBoxTypeCommon", "NominalWidth")][1], 0.1)
        pe = _props(bim.classe("ponto", dados, bim.fator_da_unidade(1)))
        self.assertAlmostEqual(pe[("Pset_JunctionBoxTypeCommon", "NominalWidth")][1], 0.328084)

    def test_valores_vazios_ficam_de_fora(self):
        r = bim.classe("ponto", {"simbolo": "tomada_baixa", "circuito": "", "comando": None})
        nomes = {nome for _, nome, _, _ in r["propriedades"]}
        self.assertNotIn("Circuito", nomes)
        self.assertNotIn("Comando", nomes)


class TestInfraestrutura(unittest.TestCase):
    def test_interruptor(self):
        r = bim.classe("interruptor", {"tipo": "Paralelo", "comando": "a", "circuito": "1"})
        self.assertEqual((r["IfcType"], r["PredefinedType"], r["ObjectType"]),
                         ("Switching Device", "TOGGLESWITCH", "Interruptor paralelo"))
        self.assertEqual(_props(r)[("Pset_SwitchingDeviceTypeCommon", "Legend")][1], "a")

    def test_eletroduto(self):
        r = bim.classe("eletroduto", {"diametro": '3/4"', "diametro_mm": 26.9, "tipo": "Rígido", "material": "PVC",
                                      "comprimento_mm": 2500})
        self.assertEqual((r["IfcType"], r["PredefinedType"]), ("Cable Carrier Segment", "CONDUITSEGMENT"))
        p = _props(r)
        self.assertEqual(p[("Pset_CableCarrierSegmentTypeConduitSegment", "IsRigid")][1], True)
        self.assertAlmostEqual(p[("Pset_CableCarrierSegmentTypeConduitSegment", "NominalDiameter")][1], 0.0269)
        self.assertAlmostEqual(p[(bim.PSET_CIRCUITS, "Comprimento")][1], 2.5)

    def test_bandeja_e_leito(self):
        calha = bim.classe("bandeja", {"tipo_bandeja": "eletrocalha_perfurada", "largura_mm": 200, "aba_mm": 50,
                                       "tampa": True})
        self.assertEqual(calha["PredefinedType"], "CABLETRAYSEGMENT")
        self.assertEqual(_props(calha)[("Pset_CableCarrierSegmentTypeCableTraySegment", "HasCover")][1], True)
        self.assertEqual(bim.classe("bandeja", {"tipo_bandeja": "leito"})["PredefinedType"], "CABLELADDERSEGMENT")

    def test_pecas_colunas_prumadas_busway(self):
        self.assertEqual(bim.classe("conexao", {"peca": "descida"})["PredefinedType"], "BEND")
        self.assertEqual(bim.classe("suporte", {"quantidade": 12})["PredefinedType"], "BRACKET")
        coluna = bim.classe("coluna_medicao", {"medidores": 12, "corrente_a": 180, "tensao": 220.0, "fases": 3})
        self.assertEqual(coluna["IfcType"], "Electric Distribution Board")
        self.assertEqual(_props(coluna)[("Pset_ElectricalDeviceCommon", "RatedCurrent")][1], 180.0)
        prumada = bim.classe("prumada", {"sistemas": ["Energia", "Dados"], "andares": 5})
        self.assertEqual(_props(prumada)[(bim.PSET_CIRCUITS, "Sistemas")][1], "Energia, Dados")
        busway = bim.classe("busway", {"corrente_a": 630})
        self.assertEqual((busway["IfcType"], busway["PredefinedType"]), ("Cable Segment", "BUSBARSEGMENT"))


class TestMapa(unittest.TestCase):
    def test_formato_do_exportador_do_freecad(self):
        mapa = bim.mapa_ifc([("Pset_X", "Ligado", "IfcBoolean", True), ("Pset_X", "Polos", "IfcCountMeasure", 2),
                             ("Pset_X", "Tensao", "IfcElectricVoltageMeasure", 127.0), ("Pset_X", "Nome", "IfcLabel", "a;;b"),
                             ("Pset_X", "Vazio", "IfcLabel", "")])
        self.assertEqual(mapa["Ligado;;Pset_X"], "IfcBoolean;;True")
        self.assertEqual(mapa["Polos;;Pset_X"], "IfcCountMeasure;;2")
        self.assertEqual(mapa["Tensao;;Pset_X"], "IfcElectricVoltageMeasure;;127.0")
        self.assertEqual(mapa["Nome;;Pset_X"], "IfcLabel;;a;b")
        self.assertNotIn("Vazio;;Pset_X", mapa)
        self.assertIn(("Pset_X", "Polos", "IfcCountMeasure", "2"), bim.ler_mapa(mapa))

    def test_mesmo_nome_em_psets_diferentes(self):
        mapa = bim.mapa_ifc([("A", "Reference", "IfcIdentifier", "x"), ("B", "Reference", "IfcIdentifier", "y")])
        self.assertEqual(len(mapa), 2)


if __name__ == "__main__":
    unittest.main()
