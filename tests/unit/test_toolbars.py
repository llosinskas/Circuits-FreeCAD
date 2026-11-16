"""Barras e botões: todo comando tem botão ou menu, legenda curta e ícone existente."""
import ast
import pathlib
import re
import unittest

from tests import ROOT

PACOTE = pathlib.Path(ROOT) / "freecad" / "Circuits"
COMANDOS = sorted((PACOTE / "commands").glob("*.py"))
INIT_GUI = (PACOTE / "init_gui.py").read_text(encoding="utf-8")
RECURSOS = re.compile(r'recursos\(\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",?\s*\)')
LEGENDA_MAXIMA = 24  # caracteres: o texto aparece embaixo do ícone


CATALOGO = __import__("freecad.Circuits.core.simbolos", fromlist=["CATALOGO"]).CATALOGO


def _fontes():
    return [arquivo.read_text(encoding="utf-8") for arquivo in COMANDOS if arquivo.name != "_base.py"]


def _configuracao():
    """Listas e dicionários em maiúsculas do ``init_gui.py``, sem importar o FreeCAD."""
    valores = {"_tr": lambda contexto, texto: texto}
    for no in ast.parse(INIT_GUI).body:
        if not isinstance(no, ast.Assign) or not isinstance(no.targets[0], ast.Name):
            continue
        nome = no.targets[0].id
        if nome != "_tr" and not nome.isupper():
            continue
        try:
            valores[nome] = eval(compile(ast.Expression(no.value), "init_gui", "eval"), {"__builtins__": {}}, valores)
        except Exception:
            pass  # depende do FreeCAD ou do Qt: não é configuração de barras
    return valores


CONFIG = _configuracao()
NATIVOS = ("Draft_", "BIM_", "Arch_")


def _registrados():
    ids = {nome for fonte in _fontes() for nome in re.findall(r'addCommand\("(\w+)"', fonte)}
    return ids | {f"Ponto_{simbolo}" for simbolo in CATALOGO}  # registrados em laço em commands/pontos.py


class TestBarras(unittest.TestCase):
    def test_todo_comando_registrado_esta_em_um_menu(self):
        no_menu = {comando for _, comandos in CONFIG["MENUS"] for comando in comandos}
        self.assertEqual(sorted(_registrados() - no_menu), [])

    def test_barras_so_tem_comandos_que_existem(self):
        conhecidos = _registrados() | set(CONFIG["GROUPS"])
        for barra, comandos in CONFIG["TOOLBARS"]:
            for comando in comandos:
                with self.subTest(barra=barra, comando=comando):
                    self.assertTrue(comando in conhecidos or comando.startswith(NATIVOS))

    def test_grupos_reunem_comandos_registrados(self):
        registrados = _registrados()
        for identificador, (legenda, dica, comandos) in CONFIG["GROUPS"].items():
            with self.subTest(identificador):
                self.assertGreaterEqual(len(comandos), 2)
                self.assertEqual([c for c in comandos if c not in registrados], [])
                self.assertLessEqual(len(legenda), LEGENDA_MAXIMA)
                self.assertTrue(dica)

    def test_todo_grupo_esta_em_uma_barra(self):
        nas_barras = {comando for _, comandos in CONFIG["TOOLBARS"] for comando in comandos}
        self.assertEqual(sorted(set(CONFIG["GROUPS"]) - nas_barras), [])

    def test_barras_proprias_sao_enxutas(self):
        for barra, comandos in CONFIG["ELECTRIC_TOOLBARS"]:
            self.assertLessEqual(len(comandos), 6, barra)

    def test_icones_existem(self):
        icones = {icone for fonte in _fontes() for icone, _, _ in RECURSOS.findall(fonte)}
        icones |= {f"simbologia/{simbolo}.svg" for simbolo in CATALOGO}
        ausentes = sorted(icone for icone in icones if not (PACOTE / "Resources" / "Icons" / icone).exists())
        self.assertEqual(ausentes, [])

    def test_legendas_sao_curtas_e_unicas(self):
        legendas = [legenda for fonte in _fontes() for _, legenda, _ in RECURSOS.findall(fonte)]
        legendas += [dados["legenda"] for dados in CATALOGO.values()]
        legendas += [legenda for legenda, _, _ in CONFIG["GROUPS"].values()]
        self.assertEqual([texto for texto in legendas if len(texto) > LEGENDA_MAXIMA], [])
        self.assertEqual(len(legendas), len(set(legendas)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
