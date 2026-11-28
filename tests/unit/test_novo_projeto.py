"""Regras do diálogo de novo projeto (core.novo_projeto)."""
import unittest

from freecad.Circuits.core import novo_projeto as np
from freecad.Circuits.core import parametros


class TestPavimentos(unittest.TestCase):
    def test_casa_terrea(self):
        self.assertEqual(np.pavimentos(), [{"nome": "Térreo", "cota": 0.0, "altura": 3000.0, "unidades": 0}])

    def test_unidades_so_nos_andares(self):
        lista = np.pavimentos(subsolos=1, andares=2, cobertura=True, unidades_por_andar=4)
        self.assertEqual([p["unidades"] for p in lista], [0, 0, 4, 4, 0])
        self.assertEqual(np.pavimentos(unidades_por_andar=3)[0]["unidades"], 3)  # só o térreo: as unidades nele
        self.assertIn("8 unidade(s)", np.resumo({"pavimentos": lista}))
        self.assertTrue(np.validar({"pavimentos": [{"nome": "A", "cota": 0, "altura": 1, "unidades": -1}]}))

    def test_predio_com_subsolos_e_cobertura(self):
        lista = np.pavimentos(subsolos=2, andares=3, cobertura=True, piso_a_piso=2880, altura_terreo=3500)
        self.assertEqual([p["nome"] for p in lista],
                         ["Subsolo 2", "Subsolo 1", "Térreo", "1º Pavimento", "2º Pavimento", "3º Pavimento", "Cobertura"])
        self.assertEqual([p["cota"] for p in lista], [-5760.0, -2880.0, 0.0, 3500.0, 6380.0, 9260.0, 12140.0])
        self.assertEqual(np.pavimento_inicial(lista), "Térreo")

    def test_limites(self):
        self.assertEqual(len(np.pavimentos(andares=1000)), np.MAXIMO_ANDARES + 1)
        self.assertEqual(len(np.pavimentos(subsolos=-3)), 1)


class TestValidacao(unittest.TestCase):
    def test_lista_valida(self):
        self.assertEqual(np.validar({"pavimentos": np.pavimentos(andares=2), "sistema": "127/220 V"}), [])

    def test_erros(self):
        lista = [{"nome": "A", "cota": 0, "altura": 3000}, {"nome": "A", "cota": 0, "altura": 0},
                 {"nome": "", "cota": 1, "altura": 1}]
        erros = " ".join(np.validar({"pavimentos": lista, "sistema": "999 V"}))
        for trecho in ("mesmo nome", "precisa de nome", "cotas", "piso a piso", "desconhecido"):
            self.assertIn(trecho, erros)
        self.assertTrue(np.validar({"pavimentos": []}))


class TestParametros(unittest.TestCase):
    def test_valores_para_a_planilha(self):
        valores = np.valores_dos_parametros({"projeto": "Casa", "sistema": "220/380 V", "icc_entrada_ka": 7.5,
                                             "esquema": "TT", "fornecimento": "Trifásico", "pavimentos": []})
        self.assertEqual(valores["tensao_fn"], "220")
        self.assertEqual(valores["tensao_ff"], "380")
        self.assertEqual(valores["icc_entrada_ka"], "7,5")
        self.assertNotIn("pavimentos", valores)
        lidos = parametros.ler(valores)
        self.assertEqual((lidos["tensao_ff"], lidos["icc_entrada_ka"], lidos["esquema"]), (380.0, 7.5, "TT"))
        self.assertEqual(lidos["fornecimento"], "Trifásico")

    def test_sistema_das_tensoes(self):
        self.assertEqual(np.sistema_das_tensoes(220, 380), "220/380 V")
        self.assertEqual(np.sistema_das_tensoes(1, 2), "127/220 V")


class TestDadosIniciais(unittest.TestCase):
    def test_projeto_novo_usa_a_sugestao_do_tipo(self):
        dados = np.dados_iniciais({}, [], tipo="Industrial")
        self.assertTrue(dados["novo"])
        self.assertTrue(dados["niveis_bim"])  # projeto novo: níveis do BIM, como o botão Nível do BIM
        self.assertEqual(dados["sistema"], "220/380 V")
        self.assertEqual(dados["pavimentos"][0]["altura"], 8000.0)

    def test_projeto_existente_vem_preenchido(self):
        textos = {"projeto": "Edifício X", "tensao_fn": "220", "tensao_ff": "380", "tipo_edificacao": "Comercial",
                  "esquema": "TT"}
        existentes = [{"nome": "Térreo", "cota": 0.0, "altura": 4000.0, "bim": True}]
        dados = np.dados_iniciais(textos, existentes)
        self.assertFalse(dados["novo"])
        self.assertEqual((dados["projeto"], dados["sistema"], dados["esquema"]), ("Edifício X", "220/380 V", "TT"))
        self.assertTrue(dados["niveis_bim"])
        self.assertTrue(dados["pavimentos"][0]["bim"])
        pastas = np.dados_iniciais(textos, [{"nome": "Térreo", "cota": 0.0, "altura": 3000.0, "bim": False}])
        self.assertFalse(pastas["niveis_bim"])  # projeto com pavimentos em pasta: só converte se o usuário marcar

    def test_resumo(self):
        texto = np.resumo({"pavimentos": np.pavimentos(andares=2), "sistema": "127/220 V",
                           "fornecimento": "Bifásico", "esquema": "TN-S"})
        self.assertIn("3 pavimento(s)", texto)
        self.assertIn("bifásico 127/220 V", texto)


if __name__ == "__main__":
    unittest.main()
