"""Biblioteca: nomes, categorias, busca e exemplos paramétricos (core.biblioteca)."""
import os
import unittest

from tests import ROOT
from freecad.Circuits.core import biblioteca as b

PASTA = os.path.join(ROOT, "freecad", "Circuits", "Componentes", "Eletrica")


class TestBiblioteca(unittest.TestCase):
    def test_nome_amigavel(self):
        self.assertEqual(b.nome_amigavel("Tomada_Alta_1modulo_110v_com_simbologia.FCStd"),
                         "Tomada alta 1 módulo 110 V com simbologia")
        self.assertEqual(b.nome_amigavel("Disjuntor_Bifasio.FCStd"), "Disjuntor bifásico")
        self.assertEqual(b.nome_amigavel("Interruptor_2botoes.FCStd"), "Interruptor 2 botões")

    def test_categoria_pelo_nome(self):
        self.assertEqual([b.categoria(n) for n in (
            "Interruptor_Tomada_Media_1modulo_110v.FCStd", "Tomada.FCStd", "Bocal_Lampada.FCStd",
            "Disjuntor_Trifasio.FCStd", "Caixa_Distribuicao_Embutir.FCStd", "Caixa_4x2.FCStd", "Motor 3 cv",
            "Qualquer.FCStd")],
            ["Interruptores", "Tomadas", "Iluminação", "Quadros e proteção", "Quadros e proteção", "Caixas",
             "Equipamentos", "Outros"])

    def test_todos_os_arquivos_da_biblioteca_tem_categoria_conhecida(self):
        for arquivo in os.listdir(PASTA):
            if arquivo.endswith(".FCStd"):
                with self.subTest(arquivo=arquivo):
                    self.assertIn(b.categoria(arquivo), b.CATEGORIAS)

    def test_busca_por_palavras_e_categoria(self):
        itens = b.itens_dos_exemplos() + [b.item_do_arquivo("/x/Tomada.FCStd", "Tomada.FCStd")]
        self.assertEqual([i["nome"] for i in b.filtrar(itens, "motor 3")], ["Motor de indução trifásico 3 cv"])
        self.assertEqual({i["categoria"] for i in b.filtrar(itens, "", "Iluminação")}, {"Iluminação"})
        self.assertEqual([i["caminho"] for i in b.filtrar(itens, "tomada", "Tomadas")], ["/x/Tomada.FCStd"])
        self.assertIn("exemplo:caixa_4x2", [i["caminho"] for i in b.filtrar(itens, "tomada")])  # pela descrição

    def test_exemplos_validos(self):
        self.assertGreaterEqual(len(b.EXEMPLOS), 12)
        for chave, dados in b.EXEMPLOS.items():
            with self.subTest(exemplo=chave):
                self.assertIn(dados["categoria"], b.CATEGORIAS)
                self.assertTrue(dados["primitivas"])
                for primitiva in dados["primitivas"]:
                    if primitiva[0] == "caixa":
                        self.assertTrue(all(d > 0 for d in primitiva[2]))
                    else:
                        self.assertEqual(primitiva[0], "cilindro")
                        self.assertGreater(primitiva[2], 0)
                        self.assertGreater(primitiva[3], 0)
                self.assertEqual(b.chave_do_exemplo(b.caminho_do_exemplo(chave)), chave)
        self.assertIsNone(b.chave_do_exemplo("/caminho/Tomada.FCStd"))


if __name__ == "__main__":
    unittest.main()
