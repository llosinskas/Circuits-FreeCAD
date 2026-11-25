"""Folhas de desenho: formato e carimbo NBR, escala, arrumação, SVG das vistas, cortes (core/folhas.py)."""
import unittest
import xml.etree.ElementTree as ET

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import folhas

FREECAD_NS = "http://www.freecadweb.org/wiki/index.php?title=Svg_Namespace"


class TestFormato(unittest.TestCase):
    def test_margens_da_nbr_10068(self):
        self.assertEqual(folhas.margens("A1"), (25.0, 10.0, 10.0, 10.0))
        self.assertEqual(folhas.margens("A3"), (25.0, 7.0, 7.0, 7.0))
        with self.assertRaises(ValueError):
            folhas.tamanho("B2")

    def test_carimbo_no_canto_inferior_direito(self):
        x0, y0, x1, y1 = folhas.retangulo_do_carimbo("A3")
        self.assertEqual((x1, y0), (413.0, 7.0))
        self.assertEqual((x1 - x0, y1 - y0), (folhas.CARIMBO_LARGURA, folhas.CARIMBO_ALTURA))

    def test_modelo_e_svg_valido_com_campos_editaveis(self):
        raiz = ET.fromstring(folhas.modelo_svg("A1"))
        self.assertEqual(raiz.get("width"), "841mm")
        self.assertEqual(raiz.get("viewBox"), "0 0 841 594")
        editaveis = [t.get(f"{{{FREECAD_NS}}}editable") for t in raiz.iter("{http://www.w3.org/2000/svg}text")]
        self.assertEqual([e for e in editaveis if e], folhas.campos_do_carimbo())

    def test_campos_cabem_no_carimbo(self):
        for linha in range(4):
            campos = [c for c in folhas.CAMPOS_CARIMBO if c[4] == linha]
            self.assertEqual(sum(c[3] for c in campos), folhas.CARIMBO_LARGURA)

    def test_numeros_e_nomes(self):
        self.assertEqual(folhas.rotulo_folha(2, 5), "02/05")
        self.assertEqual(folhas.proxima_letra(["A", "B"]), "C")
        self.assertEqual(folhas.proxima_letra([chr(65 + i) for i in range(26)]), "AA")
        self.assertEqual(folhas.proximo_detalhe(["D1", "D3"]), "D2")
        self.assertEqual(folhas.texto_escala(50), "1:50")
        self.assertEqual(folhas.escala_do_detalhe(50), 25)
        self.assertEqual(folhas.escala_do_detalhe(100), 50)
        self.assertEqual(folhas.escala_do_detalhe(2), 1)


class TestOrganizar(unittest.TestCase):
    def test_maior_escala_que_cabe(self):
        # planta de 30 × 20 m num A1 (área útil ~796 × 569 mm): 1:50 = 600 × 400 mm cabe
        r = folhas.organizar([{"nome": "P", "largura": 30000, "altura": 20000, "tipo": "desenho"}], "A1")
        self.assertTrue(r["cabe"])
        self.assertEqual(r["escala"], 50)
        vista = r["vistas"][0]
        self.assertAlmostEqual(vista["largura"], 600.0)
        self.assertLess(vista["titulo_y"], vista["y"] - vista["altura"] / 2)  # título embaixo

    def test_vistas_nao_se_sobrepoem_nem_ao_carimbo(self):
        vistas = [{"nome": f"V{i}", "largura": 9000, "altura": 6000, "tipo": "desenho"} for i in range(6)]
        r = folhas.organizar(vistas, "A1")
        self.assertTrue(r["cabe"])
        caixas = [(v["x"] - v["largura"] / 2, v["titulo_y"] - folhas.ALTURA_TITULO / 2,
                   v["x"] + v["largura"] / 2, v["y"] + v["altura"] / 2) for v in r["vistas"]]
        carimbo = folhas.retangulo_do_carimbo("A1")
        x0, y0, x1, y1 = folhas.area_util("A1")
        for i, a in enumerate(caixas):
            self.assertTrue(x0 - 1e-6 <= a[0] and a[2] <= x1 + 1e-6 and y0 - 1e-6 <= a[1] and a[3] <= y1 + 1e-6)
            self.assertFalse(a[0] < carimbo[2] and a[2] > carimbo[0] and a[1] < carimbo[3] and a[3] > carimbo[1])
            for b in caixas[i + 1:]:
                self.assertFalse(a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1])

    def test_detalhe_ampliado_e_tabela_em_tamanho_real(self):
        r = folhas.organizar([{"nome": "P", "largura": 30000, "altura": 20000, "tipo": "desenho"},
                              {"nome": "D", "largura": 2000, "altura": 2000, "tipo": "detalhe"},
                              {"nome": "T", "largura": 150, "altura": 60, "tipo": "tabela"}], "A0")
        escalas = {v["nome"]: v["escala"] for v in r["vistas"]}
        self.assertEqual(escalas["D"], folhas.escala_do_detalhe(r["escala"]))
        self.assertEqual(escalas["T"], 1.0)

    def test_escala_fixa_e_nao_cabe(self):
        grande = [{"nome": "P", "largura": 60000, "altura": 40000, "tipo": "desenho"}]
        self.assertEqual(folhas.organizar(grande, "A1", escala=100)["escala"], 100)
        r = folhas.organizar(grande, "A1", escala=20)
        self.assertFalse(r["cabe"])
        self.assertEqual(len(r["vistas"]), 1)


class TestSvg(unittest.TestCase):
    def test_limites_de_caminhos_circulos_linhas_e_textos(self):
        svg = ('<path d="M 0,0 L 100,0 A 10 10 0 0 1 120,-30 Z"/><circle cx="300" cy="40" r="5"/>'
               '<line x1="-20" y1="5" x2="10" y2="60"/><text transform="translate(50,90) scale(1,-1)">x</text>')
        self.assertEqual(folhas.limites_do_svg(svg), (-20.0, -30.0, 305.0, 90.0))
        self.assertIsNone(folhas.limites_do_svg("<g></g>"))

    def test_caminho_relativo_e_horizontal_vertical(self):
        self.assertEqual(folhas.limites_do_svg('<path d="m 10,10 l 5,5 h 20 v -40 z"/>'), (10.0, -25.0, 35.0, 15.0))

    def test_posicao_do_simbolo_centra_o_desenho(self):
        # desenho de (1000, -2000) a (3000, 0) no SVG, na escala 1:50: centro (2000, -1000)
        x, y = folhas.posicao_do_simbolo((400, 300), (1000, -2000, 3000, 0), 0.02)
        self.assertAlmostEqual(x, 400 - (2000 - 50) * 0.02)
        self.assertAlmostEqual(y, 300 + (-1000 - 50) * 0.02)

    def test_simbolo_com_e_sem_recorte(self):
        self.assertTrue(folhas.montar_simbolo(["<path d='M 0 0'/>"]).startswith(folhas.CABECALHO_SVG))
        recorte = folhas.recorte_do_svg('<circle cx="10" cy="20" r="5" style=""/>')
        self.assertEqual(recorte, ("circulo", 10.0, 20.0, 5.0))
        svg = folhas.montar_simbolo(["<path d='M 0 0'/>"], recorte)
        self.assertIn('clip-path="url(#recorte)"', svg)
        ET.fromstring(svg.replace("'", '"'))  # SVG bem formado
        self.assertEqual(folhas.recorte_do_svg('<path d="M 0,0 L 10,0 L 10,8 Z"/>'), ("retangulo", 0.0, 0.0, 10.0, 8.0))


class TestCorte(unittest.TestCase):
    def test_plano_pela_linha(self):
        plano = folhas.corte((0, 0), (1000, 0))  # linha para +x: olha para -y (a direita dela)
        self.assertEqual(plano["olhar"], (0.0, -1.0))
        self.assertEqual(plano["normal"], (-0.0, 1.0, 0.0))
        self.assertEqual(plano["comprimento"], 1000)
        with self.assertRaises(ValueError):
            folhas.corte((1, 1), (1, 1))

    def test_tamanho_pela_extensao_do_modelo(self):
        plano = folhas.corte((0, 0), (0, 500))
        self.assertEqual(folhas.tamanho_do_corte((0, 0, 0, 8000, 12000, 6000), plano), (12000, 6000))

    def test_setas_nas_duas_pontas(self):
        marcas = folhas.marcas_do_corte((0, 0), (1000, 0), "A", 100)
        self.assertEqual(len(marcas["setas"]), 4)
        self.assertEqual([letra for *_, letra in marcas["letras"]], ["A", "A"])
        self.assertTrue(all(y < 0 for _, y, _ in marcas["letras"]))  # do lado para onde olha
        self.assertEqual(folhas.titulo_do_corte("B"), "Corte B-B")
        self.assertEqual(folhas.titulo_da_vista("Planta baixa - Térreo", 50), ["PLANTA BAIXA - TÉRREO", "ESCALA 1:50"])
        self.assertEqual(folhas.titulo_da_vista("Circuitos QD1", 1, "tabela"), ["CIRCUITOS QD1"])


if __name__ == "__main__":
    unittest.main()
