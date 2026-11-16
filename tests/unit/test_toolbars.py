"""Barras e botões: todo comando tem botão ou menu, legenda curta e ícone existente."""
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


class TestBarras(unittest.TestCase):
    def test_todo_comando_registrado_esta_em_uma_barra_ou_menu(self):
        ids = {nome for fonte in _fontes() for nome in re.findall(r'addCommand\("(\w+)"', fonte)}
        ids |= {f"Ponto_{simbolo}" for simbolo in CATALOGO}  # registrados em laço em commands/pontos.py
        ausentes = sorted(nome for nome in ids if f'"{nome}"' not in INIT_GUI)
        self.assertEqual(ausentes, [])

    def test_icones_existem(self):
        icones = {icone for fonte in _fontes() for icone, _, _ in RECURSOS.findall(fonte)}
        icones |= {f"simbologia/{simbolo}.svg" for simbolo in CATALOGO}
        ausentes = sorted(icone for icone in icones if not (PACOTE / "Resources" / "Icons" / icone).exists())
        self.assertEqual(ausentes, [])

    def test_legendas_sao_curtas_e_unicas(self):
        legendas = [legenda for fonte in _fontes() for _, legenda, _ in RECURSOS.findall(fonte)]
        legendas += [dados["legenda"] for dados in CATALOGO.values()]
        self.assertEqual([texto for texto in legendas if len(texto) > LEGENDA_MAXIMA], [])
        self.assertEqual(len(legendas), len(set(legendas)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
