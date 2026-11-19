"""Conferência e instalação das bibliotecas que faltam (services/dependencias.py)."""
import importlib
import os
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

from tests import ROOT
MODULO = "freecad.Circuits.services.dependencias"


class TestDependencias(unittest.TestCase):
    def setUp(self):
        self.app = mock.MagicMock(name="FreeCAD")
        self.app.getUserAppDataDir.return_value = "/home/u/.local/share/FreeCAD/v1-1/"
        self.app.getHomePath.return_value = "/opt/freecad/"
        self.patch = mock.patch.dict(sys.modules, {"FreeCAD": self.app})
        self.patch.start()
        sys.modules.pop(MODULO, None)
        self.d = importlib.import_module(MODULO)

    def tearDown(self):
        sys.modules.pop(MODULO, None)
        self.patch.stop()

    def test_falta_o_que_nao_se_importa(self):
        with mock.patch.object(self.d.importlib.util, "find_spec", return_value=None):
            self.assertEqual(self.d.faltando(), ["reportlab"])
        with mock.patch.object(self.d.importlib.util, "find_spec", return_value=object()):
            self.assertEqual(self.d.faltando(), [])

    def test_instala_com_o_pip_na_pasta_do_addon_manager(self):
        versao = f"py{sys.version_info.major}{sys.version_info.minor}"
        pasta = os.path.join("/home/u/.local/share/FreeCAD/v1-1/", "AdditionalPythonPackages", versao)
        comando = self.d.comando_de_instalacao(["reportlab"])
        self.assertEqual(comando[1:], ["-m", "pip", "install", "--disable-pip-version-check", "--upgrade",
                                       "--target", pasta, "reportlab"])
        concluido = subprocess.CompletedProcess(comando, 0, "ok", "")
        with mock.patch.object(self.d.subprocess, "run", return_value=concluido) as run, \
                mock.patch.object(self.d.os, "makedirs"), \
                mock.patch.object(self.d, "faltando", return_value=[]), \
                mock.patch.object(self.d.sys, "path", list(sys.path)) as caminho:
            self.assertEqual(self.d.instalar(["reportlab"]), (True, "ok"))
            self.assertIn(pasta, caminho)
        self.assertEqual(run.call_args.args[0], comando)

    def test_erro_do_pip_volta_como_falha(self):
        falhou = subprocess.CompletedProcess([], 1, "", "sem rede")
        with mock.patch.object(self.d.subprocess, "run", return_value=falhou), \
                mock.patch.object(self.d.os, "makedirs"), \
                mock.patch.object(self.d.sys, "path", list(sys.path)):
            self.assertEqual(self.d.instalar(["reportlab"]), (False, "sem rede"))

    def test_nao_perguntar_de_novo_fica_nas_preferencias(self):
        self.app.ParamGet.return_value.GetBool.return_value = True
        self.assertFalse(self.d.perguntar())
        self.d.nunca_mais_perguntar()
        self.app.ParamGet.return_value.SetBool.assert_called_with(self.d.NAO_PERGUNTAR, True)


class TestPackageXml(unittest.TestCase):
    def test_addon_manager_pede_o_reportlab_e_acha_a_bancada(self):
        raiz = ET.parse(os.path.join(ROOT, "package.xml")).getroot()
        ns = {"p": "https://wiki.freecad.org/Package_Metadata"}
        bancada = raiz.find("p:content/p:workbench", ns)
        self.assertEqual(bancada.find("p:classname", ns).text, "CircuitsWorkbench")
        python = {d.text for d in bancada.findall("p:depend", ns) if d.get("type") == "python"}
        self.assertIn("reportlab", python)
        self.assertFalse(python & {"scipy", "sympy", "matplotlib"})  # sem uso no código


if __name__ == "__main__":
    unittest.main()
