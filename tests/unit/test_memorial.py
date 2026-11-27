"""Memorial descritivo e de cálculo (core/memorial.py): fórmulas com os valores e verificações."""
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import memorial as m
from freecad.Circuits.core import parametros as regras_parametros

PARAMETROS = regras_parametros.ler({})


def circuito(n, destino, potencia, tensao, fases, disjuntor, cabo, dr="True", curva="C", **extra):
    c = {"N_circuito": str(n), "Destino": destino, "Potencia": str(potencia), "Tensao": str(tensao),
         "Fase_R": str("R" in fases), "Fase_S": str("S" in fases), "Fase_T": str("T" in fases),
         "Disjuntor": str(disjuntor), "Cabo": str(cabo), "Curva": curva, "DR": dr, "Corrente_DR": "30",
         "Neutro": "True", "Terra": "True", "Comprimento": "", "Criterio": "capacidade", "Grupo_DR": ""}
    c.update(extra)
    return c


def textos(blocos):
    return "\n".join(str(b[1]) for b in blocos if b[0] in ("formula", "paragrafo", "aviso", "subtitulo"))


class TestVerificarCircuito(unittest.TestCase):
    def test_tomadas_atende_com_todas_as_contas(self):
        r = m.verificar_circuito(circuito(1, "Tomadas sala", 1200, 127, "R", 16, 2.5), PARAMETROS,
                                 {"comprimento": 20.0, "agrupados": 1})
        t = textos(r["blocos"])
        self.assertTrue(r["ok"])
        self.assertIn("Ib = S / V = 1200 / 127 = 9,45 A", t)
        self.assertIn("Iz = Iz0 · FCT · FCA = 24 × 1,00 × 1,00 = 24,00 A", t)
        self.assertIn("ΔV = b · ρ · L / S · Ib = 2 × 0,0225 × 20,0 / 2,5 × 9,45 = 3,40 V", t)
        self.assertIn("= 2,68 % ≤ 4 % → atende", t)
        self.assertIn("SPE = S = 2,5 mm²", t)
        self.assertIn("DR 30mA", t)
        self.assertEqual(r["linha"][-1], "atende")

    def test_bifasico_usa_a_tensao_entre_fases(self):
        r = m.verificar_circuito(circuito(2, "Chuveiro", 5400, 220, "RS", 32, 4), PARAMETROS,
                                 {"comprimento": 15.0, "agrupados": 1})
        self.assertIn("Ib = S / V = 5400 / 220 = 24,55 A", textos(r["blocos"]))
        self.assertTrue(r["ok"])

    def test_trifasico_usa_raiz_de_3(self):
        r = m.verificar_circuito(circuito(3, "Motor", 10000, 380, "RST", 20, 4), PARAMETROS,
                                 {"comprimento": 10.0, "agrupados": 1})
        t = textos(r["blocos"])
        self.assertIn("Ib = S / (√3 · V) = 10000 / (1,732 × 380) = 15,19 A", t)
        self.assertIn("ΔV = b · ρ · L / S · Ib = √3", t)

    def test_cabo_fino_para_o_disjuntor_nao_atende(self):
        r = m.verificar_circuito(circuito(4, "Tomadas", 2000, 127, "R", 20, 1.5), PARAMETROS,
                                 {"comprimento": 40.0, "agrupados": 3})
        t = textos(r["blocos"])
        self.assertFalse(r["ok"])
        self.assertIn("NÃO ATENDE", t)
        self.assertIn("× 0,70", t)  # FCA de 3 circuitos no trecho
        self.assertIn("Seção mínima (tomadas, tabela 47): 1,5 ≥ 2,5 mm² → NÃO ATENDE", t)
        self.assertTrue(r["avisos"])

    def test_sem_dr_no_tn_verifica_o_comprimento_maximo(self):
        r = m.verificar_circuito(circuito(5, "Iluminação", 400, 127, "R", 10, 1.5, dr="False", curva="B"),
                                 PARAMETROS, {"comprimento": 25.0, "agrupados": 1})
        t = textos(r["blocos"])
        self.assertIn("Lmáx = 0,8·U0·S / (ρ·(1+m)·Ia)", t)
        self.assertIn("Seção mínima (iluminação, tabela 47): 1,5 ≥ 1,5 mm² → atende", t)
        tt = m.verificar_circuito(circuito(5, "Iluminação", 400, 127, "R", 10, 1.5, dr="False"),
                                  dict(PARAMETROS, esquema="TT"), {"comprimento": 25.0})
        self.assertFalse(tt["ok"])

    def test_curto_so_com_tempo_de_atuacao(self):
        c = circuito(6, "Tomadas", 1000, 127, "R", 16, 2.5)
        self.assertNotIn("Curto:", textos(m.verificar_circuito(c, PARAMETROS, {"comprimento": 5})["blocos"]))
        t = textos(m.verificar_circuito(c, dict(PARAMETROS, tempo_curto=0.1), {"comprimento": 5}, icc_ka=3.0)["blocos"])
        self.assertIn("Curto: S ≥ I·√t / k = 3000 × √0,1 / 115 = 8,25 mm² → NÃO ATENDE", t)

    def test_reserva_fica_sem_conta(self):
        r = m.verificar_circuito(circuito(7, "Reserva", "", "", "", "", ""), PARAMETROS)
        self.assertEqual((r["blocos"], r["ok"]), ([], True))


class TestMontar(unittest.TestCase):
    def dados(self):
        circuitos = [circuito(1, "Iluminação", 600, 127, "R", 10, 1.5),
                     circuito(2, "Tomadas sala", 1200, 127, "S", 16, 2.5, Grupo_DR="DR1"),
                     circuito(3, "Chuveiro", 5400, 220, "RT", 32, 6),
                     circuito(4, "Reserva", "", "", "", "", "")]
        quadro = {"indentificacao_painel": "QD1", "numero_fases": "3", "corrente_nominal_disjuntor": "50",
                  "neutro": "True", "terra": "True", "IDR": "True", "tensao": "220", "corrente_curto_circuito": "6"}
        return {
            "projeto": {"projeto": "Casa Ana", "obra": "Rua A", "data": "27/11/2026"},
            "contagem": {"Tomadas": 10},
            "parametros": PARAMETROS,
            "rotulos_parametros": {k: v[1] for k, v in regras_parametros.CAMPOS.items()},
            "ambientes": [{"nome": "Sala", "tipo": "Sala", "area": 16.0, "perimetro": 16.0,
                           "previsao": {"tugs": 4, "total_tug_va": 400, "iluminacao_va": 220, "potencias": []},
                           "luminotecnico": {"altura_util": 1.95, "indice_local": 1.03, "iluminancia": 150,
                                             "fluxo_luminaria": 1000, "fator_utilizacao": 0.45,
                                             "fator_manutencao": 0.8, "quantidade_calculada": 6.67,
                                             "quantidade": 8, "iluminancia_resultante": 180}}],
            "quadros": [{"nome": "QD1", "dados": quadro, "circuitos": circuitos,
                         "rede": {"1": {"comprimento": 12.0, "agrupados": 2}}}],
            "curto": {"tensao": 380.0, "resultado": {"QD1": {"origem": "Entrada", "r": 10.0, "x": 12.0, "ik3": 15.0,
                                                             "ip": 30.0, "ik1_min": 5.0, "icu_minimo": 20}}},
            "gerador": {"cargas": [{"descricao": "QD1", "tipo": "Geral", "quantidade": 1, "kw": 20.0, "kva": 22.2,
                                    "fator_potencia": 0.9, "fator_demanda": 0.8, "partida": "",
                                    "no_gerador": True}],
                        "resumo": {"Gerador [kVA]": "30"}},
            "ocupacao": {"tabela": [("Infraestrutura", "Situação"), ("Wire", "ok")], "avisos": ["Wire001: pequeno"]},
        }

    def test_secoes_do_memorial(self):
        secoes = m.montar(self.dados())
        titulos = [t for t, _ in secoes]
        self.assertEqual(titulos[:4], ["Identificação do projeto", "Objetivo e normas",
                                       "Parâmetros e premissas de cálculo",
                                       "Previsão de cargas e iluminação por ambiente"])
        for esperado in ("Quadro QD1", "Curto-circuito", "Grupo gerador", "Ocupação dos eletrodutos e eletrocalhas",
                         "Avisos e limitações"):
            self.assertIn(esperado, titulos)
        quadro = dict(secoes)["Quadro QD1"]
        t = textos(quadro)
        self.assertIn("Desequilíbrio = (Fmáx − Fmín) / Fmáx × 100", t)
        self.assertIn("D(TUE) = 5400 × 1,00", t)  # o chuveiro é uso específico
        self.assertIn("Id = D / (√3 · Vff)", t)
        self.assertIn("C1 — Iluminação", t)
        self.assertIn("× 0,80", t)  # FCA dos 2 circuitos no trecho do C1, da rede
        tabelas = [b for b in quadro if b[0] == "tabela"]
        dr = next(b for b in tabelas if b[1] == ["DR", "Circuitos", "Especificação"])
        self.assertEqual([linha[0] for linha in dr[2]], ["IDR geral", "C1", "DR1", "C3"])
        self.assertEqual(dr[2][3][2], "2P 40 A, 30mA")  # DR próprio do chuveiro bifásico: como nos componentes
        resumo = next(b for b in tabelas if b[1] == m.CABECALHO_CIRCUITOS)
        self.assertEqual(len(resumo[2]), 4)
        self.assertIn("NBR 5410", textos(dict(secoes)["Objetivo e normas"]) + str(dict(secoes)["Objetivo e normas"]))
        avisos = str(dict(secoes)["Avisos e limitações"])
        self.assertIn("capacidade de interrupção de 6 kA menor que o curto de 15,00 kA", avisos)
        self.assertIn("Wire001: pequeno", avisos)
        lum = textos(dict(secoes)["Previsão de cargas e iluminação por ambiente"])
        self.assertIn("N = E · A / (Φ · Fu · Fm) = 150 × 16,00 / (1000 × 0,45 × 0,80) = 6,67 → 8 luminária(s)", lum)

    def test_sem_dados_opcionais(self):
        dados = self.dados()
        for chave in ("ambientes", "curto", "gerador", "ocupacao"):
            dados.pop(chave)
        titulos = [t for t, _ in m.montar(dados)]
        self.assertNotIn("Curto-circuito", titulos)
        self.assertEqual(titulos[-1], "Avisos e limitações")

    def test_tipo_do_circuito(self):
        self.assertEqual(m.tipo_do_circuito({"Destino": "Iluminação sala"}), m.ILUM)
        self.assertEqual(m.tipo_do_circuito({"Destino": "Ar-condicionado", "Potencia": "1300"}), m.TUE)
        self.assertEqual(m.tipo_do_circuito({"Destino": "Tomadas", "Potencia": "2800", "Fase_R": "True"}), m.TUG)


class TestLuminotecnicoEAterramento(unittest.TestCase):
    CALCULO = {"comprimento": 5.0, "largura": 4.0, "ambiente": "Escritório", "lampada": "LED 18 W",
               "potencia": 18.0, "iluminancia": 500.0, "fluxo_luminaria": 2000.0, "pe_direito": 2.7,
               "plano_trabalho": 0.75, "suspensao": 0.0, "fator_utilizacao_informado": 0.0}

    def secao(self, dados, titulo):
        return dict(m.montar(dict(dados, parametros=PARAMETROS, projeto={}, contagem={})))[titulo]

    def test_luminotecnico_com_as_contas(self):
        dados = {"luminotecnico": [{"nome": "Sala 1", "calculo": self.CALCULO, "luminarias": 9,
                                    "potencia_va": 162.0}]}
        blocos = self.secao(dados, "Luminotécnico")
        t = textos(blocos)
        self.assertIn("Hu = H − hp − hs = 2,70 − 0,75 − 0,00 = 1,95 m", t)
        self.assertIn("K = C · L / (Hu · (C + L)) = 5,00 × 4,00 / (1,95 × (5,00 + 4,00)) = 1,14", t)
        self.assertIn("N = E · A / (Φ · Fu · Fm) = 500 × 20,00 / (2000 ×", t)
        self.assertIn("lx ≥ 500 lx → atende", t)
        self.assertIn("W/m²", t)
        tabela = next(b for b in blocos if b[0] == "tabela")
        self.assertEqual(tabela[2][0][0], "Sala 1")
        quantidade = int(tabela[2][0][4])
        avisos = str(dict(m.montar(dict(dados, parametros=PARAMETROS, projeto={}, contagem={})))["Avisos e limitações"])
        self.assertEqual(quantidade == 9, "a planta tem 9" not in avisos)

    def test_luminotecnico_antigo_sem_calculo(self):
        t = textos(self.secao({"luminotecnico": [{"nome": "Sala", "calculo": None, "luminarias": 4,
                                                  "potencia_va": 400.0}]}, "Luminotécnico"))
        self.assertIn("sem o cálculo gravado", t)

    def test_aterramento_com_o_calculo_gravado(self):
        dados = {"aterramento": {"levantamento": {"hastes": 2, "caixas_inspecao": 1, "bep": 1,
                                                  "condutores": {"50": 12.5}},
                                 "calculo": {"resistividade": 100.0, "resistencia_alvo": 10.0, "hastes": 0,
                                             "espacamento": 3.0, "comprimento_haste": 2.4, "diametro_haste": 15.9}}}
        blocos = self.secao(dados, "Aterramento")
        t = textos(blocos)
        self.assertIn("R1 = ρ / (2π·L) · [ln(4L/a) − 1] = 100 / (2π × 2,40) × [ln(4 × 2,40 / 0,00795) − 1]", t)
        self.assertIn("Rn = R1 · (1 + λ · α) / n", t)
        self.assertIn("→ atende", t)
        tabela = next(b for b in blocos if b[0] == "tabela")
        self.assertIn(["Cabo de cobre nu 50 mm² [m]", "12,5"], tabela[2])
        avisos = str(dict(m.montar(dict(dados, parametros=PARAMETROS, projeto={}, contagem={})))["Avisos e limitações"])
        self.assertIn("a planta tem 2 haste(s) e o cálculo usa", avisos)

    def test_aterramento_sem_calculo_usa_as_hastes_da_planta(self):
        dados = {"aterramento": {"levantamento": {"hastes": 3, "condutores": {}}, "calculo": None}}
        t = textos(self.secao(dados, "Aterramento"))
        self.assertIn("resistividade adotada de 100 Ω·m e as 3 haste(s) da planta", t)
        self.assertIn("/ 3 =", t)

    def test_sem_aterramento_nem_luminotecnico_ficam_de_fora(self):
        titulos = [t for t, _ in m.montar({"parametros": PARAMETROS, "projeto": {}, "contagem": {},
                                           "aterramento": {"levantamento": {"hastes": 0, "condutores": {}},
                                                           "calculo": None}})]
        self.assertNotIn("Aterramento", titulos)
        self.assertNotIn("Luminotécnico", titulos)


class TestCentroEBusway(unittest.TestCase):
    ANDARES = [{"nome": "Térreo", "cota": 0.0, "unidades": 0, "demanda_a": 63.0, "fases": 2}] + [
        {"nome": f"{i}º", "cota": 3.0 * i, "unidades": 4, "demanda_a": 63.0, "fases": 2} for i in range(1, 7)]
    PARAMETROS_CENTRO = {"tensao": 220.0, "uso": 2.0, "distancia_horizontal": 15.0, "comprimento_ramal": 10.0,
                         "demanda_total_a": 300.0, "andares_por_centro": 3.0}

    def secoes(self, desenho):
        dados = {"parametros": PARAMETROS, "projeto": {}, "contagem": {},
                 "centro_medicao": {"andares": self.ANDARES, "parametros": self.PARAMETROS_CENTRO, "precos": {},
                                    "desenho": desenho}}
        return dict(m.montar(dados))

    def test_descentralizada_gerada_e_busway_como_alternativa(self):
        secoes = self.secoes({"solucoes": ["descentralizado"], "colunas": [], "busways": []})
        centro = secoes["Centro de medição"]
        t = textos(centro)
        self.assertIn("Solução adotada: Medição descentralizada", t)
        self.assertIn("(gerada no projeto)", t)
        self.assertIn("Centro 1 no 1º: atende 1º, 2º, 3º", t)
        self.assertIn("I andar = Id edifício × (n · Iun) do andar / Σ (n · Iun) = 300", t)
        tabelas = [b for b in centro if b[0] == "tabela"]
        comparacao = next(b for b in tabelas if b[1][0] == "Solução")
        self.assertEqual(len(comparacao[2]), 3)
        self.assertTrue(any("adotada" in linha[-1] for linha in comparacao[2]))
        self.assertTrue(any(b[1][0] == "Item" for b in tabelas))  # orçamento da adotada
        busway = textos(secoes["Busway"])
        self.assertIn("alternativa comparada; não adotada", busway)
        self.assertIn("Ramal de entrada (1 × 4 × 240 mm²): ΔV = k · L · I / 100", busway)
        self.assertIn("% ≤ 2 % → atende", busway)

    def test_busway_desenhado_e_a_adotada(self):
        desenho = {"solucoes": ["descentralizado"], "colunas": [], "busways": [
            {"nome": "BW", "pavimento": "Térreo", "corrente": 250, "trecho": "horizontal", "metros": 15.0}]}
        secoes = self.secoes(desenho)
        self.assertIn("Solução adotada: Busway com medição centralizada (desenhada no projeto)",
                      textos(secoes["Centro de medição"]))
        busway = secoes["Busway"]
        self.assertIn("solução adotada no projeto", textos(busway))
        self.assertTrue(any(b[0] == "tabela" and b[1][0] == "Item" for b in busway))
        avisos = str(secoes["Avisos e limitações"])
        self.assertIn("desenhado 250 A e o cálculo atual pede 400 A", avisos)
        self.assertIn("também tem desenhada a medição descentralizada", avisos)

    def test_sem_unidades_avisa(self):
        dados = {"parametros": PARAMETROS, "projeto": {}, "contagem": {},
                 "centro_medicao": {"andares": [{"nome": "Térreo", "cota": 0.0, "unidades": 0, "demanda_a": 63.0,
                                                 "fases": 2}], "parametros": {}, "precos": {}, "desenho": {}}}
        secoes = dict(m.montar(dados))
        self.assertIn("coluna C", textos(secoes["Centro de medição"]))
        self.assertNotIn("Busway", secoes)


if __name__ == "__main__":
    unittest.main()
