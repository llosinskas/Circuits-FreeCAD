"""Quantitativo de materiais: soma, caixas, eletrodutos e exportação em CSV, XLSX e PDF."""
import csv
import importlib
import os
import sys
import tempfile
import types
import unittest
import zipfile
from unittest import mock
from xml.etree import ElementTree

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import exportar, quantitativos
from freecad.Circuits.core.simbolos import CATALOGO, QUADRO

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet")
RECARREGAR = ("freecad.Circuits.services.quantitativos", "freecad.Circuits.services.planilhas",
              "freecad.Circuits.services.rede", "freecad.Circuits.services.eletrodutos",
              "freecad.Circuits.services.pavimentos", "freecad.Circuits.services.alinhamento",
              "freecad.Circuits.services.tomadas", "freecad.Circuits.services.documento",
              "freecad.Circuits.services.estilo")
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

try:
    import reportlab  # noqa: F401
    TEM_REPORTLAB = True
except ImportError:
    TEM_REPORTLAB = False


def ponto(item, caixa="4x2", grupo="Pontos", especificacao=""):
    return {"grupo": grupo, "item": item, "especificacao": especificacao, "caixa": caixa}


class TestMontar(unittest.TestCase):
    def test_caixa_de_cada_simbolo(self):
        self.assertEqual(quantitativos.caixa_do_simbolo("tomada_baixa"), "4x2")
        self.assertEqual(quantitativos.caixa_do_simbolo("luz_teto"), "octogonal")
        self.assertEqual(quantitativos.caixa_do_simbolo("tomada_piso"), "piso")
        self.assertIsNone(quantitativos.caixa_do_simbolo("quadro_distribuicao"))
        self.assertIsNone(quantitativos.caixa_do_simbolo("nao_existe"))
        self.assertEqual(quantitativos.caixa_do_simbolo("caixa_passagem"), "passagem")
        self.assertEqual(quantitativos.caixa_do_simbolo("botao_campainha"), "4x2")
        self.assertIsNone(quantitativos.caixa_do_simbolo("fotocelula"))
        self.assertIsNone(quantitativos.caixa_do_simbolo("haste_aterramento"))
        for chave, dados in CATALOGO.items():
            if dados["categoria"] not in (QUADRO, "Aterramento") and chave != "fotocelula":
                self.assertIn(quantitativos.caixa_do_simbolo(chave), quantitativos.CAIXAS)

    def test_caixa_de_passagem_e_aterramento(self):
        linhas = quantitativos.montar(
            pontos=[{"grupo": "Caixas", "item": "", "especificacao": "", "caixa": "passagem"},
                    {"grupo": "Aterramento", "item": "Haste de aterramento", "especificacao": "5/8", "caixa": None}],
            componentes_quadros=[{"item": "Conector haste-cabo", "especificacao": "", "quantidade": 1, "unidade": "un",
                                  "grupo": "Aterramento"}],
            aterramento=[("50", 6000.0), (50.0, 4000.0)],
        )
        self.assertEqual([(l["grupo"], l["item"], l["especificacao"], l["quantidade"]) for l in linhas], [
            ("Caixas", "Caixa de passagem 4x4\"", "", 1),
            ("Aterramento", "Cabo de cobre nu", "50 mm² (inclui 10% de perdas)", 11.0),
            ("Aterramento", "Conector haste-cabo", "", 1),
            ("Aterramento", "Haste de aterramento", "5/8", 1),
        ])

    def test_soma_pontos_caixas_e_eletrodutos_em_ordem(self):
        linhas = quantitativos.montar(
            pontos=[
                ponto("Tomada baixa", especificacao="127V"), ponto("Tomada baixa", especificacao="127V"),
                ponto("Luz de teto", "octogonal"),
                ponto("Interruptor", grupo="Interruptores", especificacao="Simples"),
                ponto("Quadro distribuição", None, grupo="Quadros", especificacao="QD1"),
            ],
            eletrodutos=[("3/4", 10000.0), ("3/4", 5000.0), ("1", 2000.0), ("1", 0.0)],
            componentes_quadros=[
                {"item": "Disjuntor de circuito", "especificacao": "1P 16 A curva C", "quantidade": 2, "unidade": "un"},
                {"item": "Disjuntor de circuito", "especificacao": "1P 16 A curva C", "quantidade": 3, "unidade": "un"},
            ],
        )
        tabela = [(l["grupo"], l["item"], l["especificacao"], l["unidade"], l["quantidade"]) for l in linhas]
        self.assertEqual(tabela, [
            ("Pontos", "Luz de teto", "", "un", 1),
            ("Pontos", "Tomada baixa", "127V", "un", 2),
            ("Interruptores", "Interruptor", "Simples", "un", 1),
            ("Caixas", "Caixa 4x2\" de embutir", "", "un", 3),
            ("Caixas", "Caixa octogonal 4x4\" de laje", "", "un", 1),
            ("Eletrodutos", "Eletroduto", "1\" (inclui 10% de perdas)", "m", 2.2),
            ("Eletrodutos", "Eletroduto", "3/4\" (inclui 10% de perdas)", "m", 16.5),
            ("Quadros", "Disjuntor de circuito", "1P 16 A curva C", "un", 5),
            ("Quadros", "Quadro distribuição", "QD1", "un", 1),
        ])

    def test_vazio(self):
        self.assertEqual(quantitativos.montar(), [])
        self.assertEqual(quantitativos.como_tabela([]), [quantitativos.COLUNAS])


class TestExportar(unittest.TestCase):
    TABELA = [["Grupo", "Item", "Especificação", "Unidade", "Quantidade"],
              ["Pontos", "Tomada <baixa> & média", "127 V", "un", 12],
              ["Eletrodutos", "Eletroduto", "3/4\"", "m", 16.5]]

    def setUp(self):
        self.pasta = tempfile.mkdtemp()

    def test_csv_com_ponto_e_virgula_e_virgula_decimal(self):
        caminho = exportar.para_csv(self.TABELA, os.path.join(self.pasta, "q.csv"))
        with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
            linhas = list(csv.reader(arquivo, delimiter=";"))
        self.assertEqual(linhas[0][2], "Especificação")
        self.assertEqual(linhas[1], ["Pontos", "Tomada <baixa> & média", "127 V", "un", "12"])
        self.assertEqual(linhas[2][4], "16,50")
        with open(caminho, "rb") as arquivo:
            self.assertTrue(arquivo.read().startswith(b"\xef\xbb\xbf"))  # BOM: o Excel abre com acentos

    def test_coluna_do_excel(self):
        self.assertEqual([exportar._coluna(i) for i in (0, 25, 26, 27, 701, 702)], ["A", "Z", "AA", "AB", "ZZ", "AAA"])

    def test_xlsx_e_um_zip_valido_com_numeros_e_textos(self):
        caminho = exportar.para_xlsx(self.TABELA, os.path.join(self.pasta, "q.xlsx"))
        with zipfile.ZipFile(caminho) as arquivo:
            self.assertIsNone(arquivo.testzip())
            nomes = set(arquivo.namelist())
            self.assertTrue({"[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet1.xml"} <= nomes)
            folha = ElementTree.fromstring(arquivo.read("xl/worksheets/sheet1.xml"))
        celulas = {c.get("r"): c for c in folha.iter(f"{{{NS['x']}}}c")}
        self.assertEqual(celulas["B2"].find("x:is/x:t", NS).text, "Tomada <baixa> & média")
        self.assertEqual(celulas["E2"].find("x:v", NS).text, "12")
        self.assertEqual(celulas["E3"].find("x:v", NS).text, "16.5")
        self.assertEqual(celulas["A1"].get("s"), "1")  # cabeçalho em negrito

    def test_xlsx_abre_no_openpyxl(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl não instalado")
        caminho = exportar.para_xlsx(self.TABELA, os.path.join(self.pasta, "q.xlsx"))
        folha = openpyxl.load_workbook(caminho).active
        self.assertEqual(folha.title, "Quantitativo")
        self.assertEqual([c.value for c in folha[2]], ["Pontos", "Tomada <baixa> & média", "127 V", "un", 12])
        self.assertEqual(folha["E3"].value, 16.5)
        self.assertTrue(folha["A1"].font.b)


class TestAbas(unittest.TestCase):
    def test_nomes_de_aba_validos_e_unicos(self):
        usados = set()
        nomes = [exportar._nome_de_aba(n, usados) for n in ("A/B", "A/B", "x" * 40, "", "[]")]
        self.assertEqual(nomes[:2], ["AB", "AB 2"])
        self.assertEqual(len(nomes[2]), 31)
        self.assertEqual(nomes[3:], ["Planilha", "Planilha 2"])

    def test_varias_abas_abrem_no_openpyxl(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl não instalado")
        caminho = os.path.join(tempfile.mkdtemp(), "abas.xlsx")
        exportar.para_xlsx_abas([("Um", [["a"], [1]]), ("Dois", [["b"], [2.5]])], caminho)
        livro = openpyxl.load_workbook(caminho)
        self.assertEqual(livro.sheetnames, ["Um", "Dois"])
        self.assertEqual(livro["Dois"]["A2"].value, 2.5)


class TestServico(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.servico = importlib.import_module("freecad.Circuits.services.quantitativos")
        self.pasta = tempfile.mkdtemp()

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def documento(self):
        def obj(tipo, **props):
            return types.SimpleNamespace(Proxy=types.SimpleNamespace(Type=tipo), **props)
        return types.SimpleNamespace(Label="Casa", FileName="", Objects=[
            obj("Ponto", Simbolo="tomada_baixa", Tensao="127V", Potencia=100.0, Descricao="Tomada baixa"),
            obj("Ponto", Simbolo="tomada_baixa", Tensao="127V", Potencia=100.0, Descricao="Tomada baixa"),
            obj("Ponto", Simbolo="luz_teto", Tensao="127V", Potencia=60.0, Descricao="Luz de teto"),
            obj("Ponto", Simbolo="quadro_distribuicao", Tensao="220V", Potencia=0.0, Descricao="QD1"),
            obj("Switch", Tipo="Paralelo"),
            obj("ConduitPath", Diametro="3/4", Shape=types.SimpleNamespace(Length=10000.0)),
            types.SimpleNamespace(Diametro="1", Altura3D=2800.0, Shape=types.SimpleNamespace(Length=1000.0)),
            types.SimpleNamespace(Diametro="1", Shape=types.SimpleNamespace(Length=999.0)),  # sem Altura3D: não é eletroduto
            types.SimpleNamespace(tipo="tomada"),
        ])

    def test_calcular_le_o_documento(self):
        fiacao = {"fios": {(2.5, "fase"): 12.0, (2.5, "terra"): 12.0, (1.5, "retorno"): 4.0},
                  "verticais": [{"diametro": "3/4", "comprimento": 2.5}], "circuitos": [], "avisos": []}
        with mock.patch.object(self.servico, "coletar_componentes_quadros", return_value=[]), \
                mock.patch.object(self.servico.rede, "analisar", return_value=fiacao):
            linhas = self.servico.calcular(self.documento())
        por_item = {(l["item"], l["especificacao"]): l["quantidade"] for l in linhas}
        self.assertEqual(por_item[("Tomada baixa", "127V, 100 VA")], 2)
        self.assertEqual(por_item[("Luz de teto", "127V, 60 VA")], 1)
        self.assertEqual(por_item[("Quadro distribuição", "QD1")], 1)
        self.assertEqual(por_item[("Interruptor", "Paralelo")], 1)
        self.assertEqual(por_item[("Tomada TUG", "")], 1)
        self.assertEqual(por_item[("Caixa 4x2\" de embutir", "")], 4)  # 2 tomadas + interruptor + TUG
        self.assertEqual(por_item[("Caixa octogonal 4x4\" de laje", "")], 1)
        self.assertEqual(por_item[("Eletroduto", "3/4\" (inclui 10% de perdas)")], 11.0)
        self.assertEqual(por_item[("Eletroduto", "1\" (inclui 10% de perdas)")], 1.1)
        self.assertEqual(por_item[("Eletroduto", "3/4\" verticais (inclui 10% de perdas)")], 2.75)
        self.assertEqual(por_item[("Cabo flexível 750 V", "2,5 mm² - fase")], 12.0)
        self.assertEqual(por_item[("Cabo flexível 750 V", "2,5 mm² - terra (verde e amarelo)")], 12.0)
        self.assertEqual(por_item[("Cabo flexível 750 V", "1,5 mm² - retorno")], 4.0)
        grupos = [l["grupo"] for l in linhas]
        self.assertEqual(grupos.index("Fios e cabos"), grupos.index("Eletrodutos") + 3)  # depois dos eletrodutos
        fios = [l["especificacao"] for l in linhas if l["grupo"] == "Fios e cabos"]
        self.assertEqual(fios, ["1,5 mm² - retorno", "2,5 mm² - fase", "2,5 mm² - terra (verde e amarelo)"])

    def test_quantitativo_separado_por_pavimento(self):
        doc = self.documento()
        doc.Objects[0].Pavimento = "Térreo"
        doc.Objects[2].Pavimento = "Superior"
        doc.Objects[5].Pavimento = "Superior"
        fiacao = {"fios": {(2.5, "fase"): 15.0}, "fios_por_pavimento": {"Térreo": {(2.5, "fase"): 10.0},
                                                                        "Superior": {(2.5, "fase"): 5.0}},
                  "verticais": [{"pavimento": "Superior", "diametro": "3/4", "comprimento": 2.0}],
                  "circuitos": [], "avisos": []}
        with mock.patch.object(self.servico, "_componentes_por_quadro", return_value=[]), \
                mock.patch.object(self.servico, "nome_do_pavimento", lambda doc, obj: getattr(obj, "Pavimento", "")), \
                mock.patch.object(self.servico, "_ordem_dos_pavimentos",
                                  lambda doc, nomes: [n for n in ("Térreo", "Superior", "") if n in nomes]):
            por_pav = dict(self.servico.levantar_por_pavimento(doc, fiacao))
        self.assertEqual(list(por_pav), ["Térreo", "Superior", ""])

        def item(pav, nome, espec):
            return next((l["quantidade"] for l in por_pav[pav] if l["item"] == nome and l["especificacao"] == espec), 0)
        self.assertEqual(item("Térreo", "Tomada baixa", "127V, 100 VA"), 1)
        self.assertEqual(item("", "Tomada baixa", "127V, 100 VA"), 1)
        self.assertEqual(item("Superior", "Luz de teto", "127V, 60 VA"), 1)
        self.assertEqual(item("Superior", "Eletroduto", "3/4\" (inclui 10% de perdas)"), 11.0)
        self.assertEqual(item("Superior", "Eletroduto", "3/4\" verticais (inclui 10% de perdas)"), 2.2)
        self.assertEqual(item("Térreo", "Cabo flexível 750 V", "2,5 mm² - fase"), 10.0)
        self.assertEqual(item("Superior", "Cabo flexível 750 V", "2,5 mm² - fase"), 5.0)

    def test_ordem_dos_pavimentos_pela_cota(self):
        pavs = [types.SimpleNamespace(Label="Superior"), types.SimpleNamespace(Label="Térreo")]
        with mock.patch.object(self.servico.pavimentos, "listar", return_value=pavs):
            self.assertEqual(self.servico._ordem_dos_pavimentos(None, {"", "Térreo", "Superior"}), ["Superior", "Térreo", ""])

    def test_mudanca_de_altura_entre_eletrodutos_entra_como_vertical(self):
        fiacao = {"fios": {}, "verticais": [], "circuitos": [], "avisos": [],
                  "transicoes": [{"diametro": "1", "comprimento": 2.9, "pavimento": ""}]}
        doc = types.SimpleNamespace(Label="Casa", FileName="", Objects=[])
        with mock.patch.object(self.servico, "coletar_componentes_quadros", return_value=[]), \
                mock.patch.object(self.servico, "_componentes_por_quadro", return_value=[]), \
                mock.patch.object(self.servico.rede, "analisar", return_value=fiacao):
            linhas = self.servico.calcular(doc)
            por_pav = dict(self.servico.levantar_por_pavimento(doc, fiacao))
        esperado = ("Eletroduto", "1\" verticais (inclui 10% de perdas)")
        self.assertEqual({(l["item"], l["especificacao"]): l["quantidade"] for l in linhas}[esperado], 3.19)
        self.assertEqual({(l["item"], l["especificacao"]): l["quantidade"] for l in por_pav[""]}[esperado], 3.19)

    def test_pecas_dos_eletrodutos_entram_no_total_e_por_pavimento(self):
        curva = {"grupo": "Eletrodutos", "item": "Curva 90°", "especificacao": 'PVC rígido 3/4"', "unidade": "un",
                 "quantidade": 3}
        fiacao = {"fios": {}, "verticais": [], "circuitos": [], "avisos": []}
        doc = types.SimpleNamespace(Label="Casa", FileName="", Objects=[])
        with mock.patch.object(self.servico, "_componentes_por_quadro", return_value=[]), \
                mock.patch.object(self.servico, "coletar_componentes_quadros", return_value=[]), \
                mock.patch.object(self.servico.rede, "analisar", return_value=fiacao), \
                mock.patch.object(self.servico.eletrodutos_planta, "materiais_por_pavimento",
                                  return_value=[("Térreo", [curva])]):
            total = self.servico.calcular(doc)
            por_pav = dict(self.servico.levantar_por_pavimento(doc, fiacao))
        self.assertIn(("Curva 90°", 3), [(l["item"], l["quantidade"]) for l in total])
        self.assertIn(("Curva 90°", 3), [(l["item"], l["quantidade"]) for l in por_pav["Térreo"]])

    def test_componentes_dos_quadros(self):
        quadro = object()
        with mock.patch.object(self.servico.planilhas, "listar_quadros", return_value=[quadro, quadro]), \
                mock.patch.object(self.servico.planilhas, "ler_quadro", return_value={}), \
                mock.patch.object(self.servico.planilhas, "ler_circuitos_completos", return_value=[]), \
                mock.patch.object(self.servico.regras_quadro, "componentes",
                                  side_effect=[[{"item": "DPS", "especificacao": "x", "quantidade": 4, "unidade": "un"}],
                                               ValueError("fora da tabela")]):
            self.assertEqual(self.servico.coletar_componentes_quadros(self.documento())[0]["item"], "DPS")

    def test_caminho_padrao(self):
        doc = types.SimpleNamespace(Label="Casa", FileName="")
        self.assertEqual(self.servico.caminho_padrao(doc), "Quantitativo_Casa")
        doc.FileName = os.path.join("projetos", "casa.FCStd")
        self.assertEqual(self.servico.caminho_padrao(doc), os.path.join("projetos", "Quantitativo_Casa"))

    def test_exportar_grava_os_tres_arquivos_com_o_mesmo_nome(self):
        linhas = quantitativos.montar([ponto("Tomada baixa")], [("3/4", 1000.0)])
        base = os.path.join(self.pasta, "lista.pdf")  # a extensão escolhida no diálogo é trocada
        fiacao = {
            "fios": {}, "avisos": ["T9: sem eletroduto chegando na caixa."],
            "circuitos": [{"quadro": "QD1", "circuito": "1", "secao": 2.5, "pontos": 3, "condutores": "F+N+T",
                           "trajeto": 7.5, "fio": 28.2}],
            "verticais": [{"pavimento": "Térreo", "caixa": "Tomada baixa", "circuito": "1", "altura_eletroduto": 2800.0,
                           "altura_caixa": 300.0, "comprimento": 2.5, "sentido": "descida", "diametro": "3/4"}],
        }
        por_pavimento = [("Térreo", linhas), ("", quantitativos.montar([ponto("Luz de teto")]))]
        gravados, avisos = self.servico.exportar(types.SimpleNamespace(Label="Casa"), base, linhas, fiacao, por_pavimento)
        esperados = [os.path.join(self.pasta, "lista" + ext)
                     for ext in (".csv", "_pavimentos.csv", "_verticais.csv", "_circuitos.csv", ".xlsx")]
        self.assertEqual(gravados[:5], esperados)
        with zipfile.ZipFile(esperados[4]) as arquivo:
            livro = ElementTree.fromstring(arquivo.read("xl/workbook.xml"))
            self.assertIn("xl/worksheets/sheet4.xml", arquivo.namelist())
        self.assertEqual([aba.get("name") for aba in livro.iter(f"{{{NS['x']}}}sheet")],
                         ["Quantitativo", "Por pavimento", "Verticais", "Fiação por circuito"])
        with open(esperados[1], encoding="utf-8-sig") as arquivo:
            pavs = [linha.split(";")[0] for linha in arquivo.read().splitlines()[1:]]
        self.assertEqual(pavs[0], "Térreo")
        self.assertEqual(pavs[-1], quantitativos.SEM_PAVIMENTO)
        with open(esperados[2], encoding="utf-8-sig") as arquivo:
            self.assertEqual(arquivo.read().splitlines()[1], "Térreo;Tomada baixa;1;2,80;0,30;2,50;descida;\"3/4\"\"\"")
        with open(esperados[3], encoding="utf-8-sig") as arquivo:
            self.assertTrue(arquivo.read().splitlines()[1].startswith(";QD1;1;2,5;"))  # circuito sem pavimento
        if TEM_REPORTLAB:
            self.assertEqual((gravados[5], avisos), (os.path.join(self.pasta, "lista.pdf"), []))
            with open(gravados[5], "rb") as arquivo:
                self.assertTrue(arquivo.read().startswith(b"%PDF"))
        else:
            self.assertEqual(len(gravados), 5)
            self.assertIn("reportlab", avisos[0])
        for caminho in gravados:
            self.assertGreater(os.path.getsize(caminho), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
