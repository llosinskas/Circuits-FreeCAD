"""Formulários de cálculo: campos coerentes, predefinições e valores guardados."""
import inspect
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import formularios
from freecad.Circuits.core.functions.Predial import luminotecnico, pressurizacao, recalque

FORMULARIOS = {
    "luminotecnico": formularios.LUMINOTECNICO,
    "pressurizacao": formularios.PRESSURIZACAO,
    "recalque": formularios.RECALQUE,
    "aterramento": formularios.ATERRAMENTO,
    "gerador": formularios.GERADOR,
    "centro_medicao": formularios.CENTRO_MEDICAO,
}
BASICOS_MAXIMOS = 4


class TestCampos(unittest.TestCase):
    def test_todo_campo_tem_rotulo_dica_e_chave_unica(self):
        for nome, campos in FORMULARIOS.items():
            chaves = [campo["chave"] for campo in campos]
            self.assertEqual(len(chaves), len(set(chaves)), nome)
            for campo in campos:
                with self.subTest(formulario=nome, campo=campo["chave"]):
                    self.assertTrue(campo["rotulo"])
                    self.assertTrue(campo.get("dica"))

    def test_poucas_perguntas_fora_das_opcoes_avancadas(self):
        for nome, campos in FORMULARIOS.items():
            basicos = [campo["chave"] for campo in campos if not campo.get("avancado")]
            self.assertLessEqual(len(basicos), BASICOS_MAXIMOS, nome)

    def test_valor_inicial_dentro_dos_limites(self):
        for nome, campos in FORMULARIOS.items():
            for campo in campos:
                valor = campo["valor"]
                with self.subTest(formulario=nome, campo=campo["chave"]):
                    if isinstance(valor, list):
                        self.assertGreaterEqual(len(valor), 2)
                        continue
                    self.assertIn("minimo", campo)
                    self.assertIn("maximo", campo)
                    self.assertTrue(campo["minimo"] <= valor <= campo["maximo"])
                    # inteiro com inteiro, decimal com decimal: o tipo decide a caixa de entrada
                    self.assertIs(type(campo["minimo"]), type(valor))
                    self.assertIs(type(campo["maximo"]), type(valor))

    def test_predefinicoes_preenchem_campos_que_existem_com_valores_validos(self):
        for nome, campos in FORMULARIOS.items():
            por_chave = {campo["chave"]: campo for campo in campos}
            for campo in campos:
                for opcao, valores in campo.get("preenche", {}).items():
                    self.assertIn(opcao, campo["valor"])
                    for chave, valor in valores.items():
                        with self.subTest(formulario=nome, opcao=opcao, chave=chave):
                            alvo = por_chave[chave]
                            if isinstance(alvo["valor"], list):
                                self.assertIn(valor, alvo["valor"])
                            else:
                                self.assertTrue(alvo["minimo"] <= valor <= alvo["maximo"])

    def test_chaves_sao_argumentos_das_funcoes_de_calculo(self):
        aceitos = set(inspect.signature(pressurizacao.dimensionar).parameters)
        self.assertEqual({c["chave"] for c in formularios.PRESSURIZACAO} - {"alimentacao"} - aceitos, set())
        aceitos = set(inspect.signature(recalque.dimensionar).parameters)
        self.assertEqual({c["chave"] for c in formularios.RECALQUE} - {"alimentacao"} - aceitos, set())
        from freecad.Circuits.core.functions.Predial import aterramento
        aceitos = set(inspect.signature(aterramento.dimensionar).parameters)
        self.assertEqual({c["chave"] for c in formularios.ATERRAMENTO} - {"solo"} - aceitos, set())

    def test_formulario_do_gerador_vira_argumentos_de_dimensionar(self):
        from freecad.Circuits.core.functions.Predial import gerador
        argumentos = formularios.argumentos_gerador(formularios.valores_iniciais(formularios.GERADOR))
        self.assertEqual(set(argumentos) - set(inspect.signature(gerador.dimensionar).parameters), set())
        self.assertEqual((argumentos["tensao"], argumentos["metodo"], argumentos["carregamento"]), (380.0, "B1", 0.8))
        resultado = gerador.dimensionar([gerador.carga("QD", potencia=50)], **argumentos)
        self.assertEqual(resultado["gerador_kva"], 80)


class TestValores(unittest.TestCase):
    def test_valores_iniciais_aplicam_a_primeira_predefinicao(self):
        valores = formularios.valores_iniciais(formularios.LUMINOTECNICO)
        self.assertEqual(valores["lampada"], "Lâmpada LED 9 W (cerca de 800 lm)")
        self.assertEqual((valores["fluxo_luminaria"], valores["potencia"], valores["simbolo"]), (800.0, 9.0, "Luz de teto"))

    def test_padroes_calculam_sem_erro(self):
        v = formularios.valores_iniciais(formularios.LUMINOTECNICO)
        r = luminotecnico.dimensionar(
            5, 4, luminotecnico.ILUMINANCIAS[v["ambiente"]], v["fluxo_luminaria"], pe_direito=v["pe_direito"],
            plano_trabalho=v["plano_trabalho"], suspensao=v["suspensao"],
            fator_utilizacao_informado=v["fator_utilizacao_informado"],
        )
        self.assertGreater(r["quantidade"], 0)

        v = formularios.padroes(formularios.PRESSURIZACAO)
        tensao, _ = formularios.ALIMENTACOES[v.pop("alimentacao")]
        self.assertGreater(pressurizacao.dimensionar(tensao=tensao, **v)["vazao_ventilador"], 0)

        v = formularios.padroes(formularios.RECALQUE)
        tensao, fases = formularios.ALIMENTACOES[v.pop("alimentacao")]
        self.assertGreater(recalque.dimensionar(tensao=tensao, fases=fases, **v)["motor"]["motor_cv"], 0)

    def test_toda_lampada_aponta_para_um_simbolo_de_iluminacao(self):
        for nome, valores in formularios.LAMPADAS.items():
            if nome == formularios.OUTRA:
                self.assertEqual(valores, {})
                continue
            self.assertIn(valores["simbolo"], formularios.SIMBOLOS_ILUMINACAO)
            self.assertGreater(valores["fluxo_luminaria"] / valores["potencia"], 60)  # eficiência plausível de LED

    def test_converter_valida_o_valor_guardado(self):
        campos = {campo["chave"]: campo for campo in formularios.LUMINOTECNICO}
        self.assertEqual(formularios.converter(campos["circuito"], "7"), 7)
        self.assertEqual(formularios.converter(campos["circuito"], "7.0"), 7)
        self.assertEqual(formularios.converter(campos["pe_direito"], "3.2"), 3.2)
        self.assertIsNone(formularios.converter(campos["pe_direito"], "99"))      # fora do limite
        self.assertIsNone(formularios.converter(campos["pe_direito"], "abc"))
        self.assertEqual(formularios.converter(campos["ambiente"], "Garagem (75 lx)"), "Garagem (75 lx)")
        self.assertIsNone(formularios.converter(campos["ambiente"], "Opção que não existe mais"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
