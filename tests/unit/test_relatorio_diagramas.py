"""Diagramas no relatório PDF: quais entram e o que fica visível (services/pdf_generator.py)."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)

MODULOS = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Spreadsheet", "Sketcher", "Arch")
MODULO = "freecad.Circuits.services.pdf_generator"


def objeto(nome, label=None, grupo=None, **props):
    obj = types.SimpleNamespace(Name=nome, Label=label or nome, **props)
    if grupo is not None:
        obj.Group = grupo
    obj.ViewObject = types.SimpleNamespace(Visibility=True)
    return obj


class TestDiagramasNoRelatorio(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.dict(sys.modules, {n: mock.MagicMock(name=n) for n in MODULOS})
        self.patch.start()
        sys.modules.pop(MODULO, None)
        self.servico = importlib.import_module(MODULO)
        texto = objeto("Texto")
        self.sketch = objeto("Sketch")
        self.unifilar = objeto("diagrama", "diagrama_QD1", grupo=[self.sketch, texto], quadro_origem="Sheet")
        self.multifilar = objeto("multifilar", "multifilar_QD1", grupo=[objeto("Multi")], multifilar_de="Sheet")
        self.gerador = objeto("diagrama_gerador", grupo=[objeto("Transferencia")], diagrama_gerador="Cargas")
        self.planta = objeto("Tomada")
        quadro = objeto("Sheet", "QD1")
        objetos = [self.planta, quadro, self.gerador, self.multifilar, self.unifilar, self.sketch, texto]
        self.doc = types.SimpleNamespace(Objects=objetos, getObject={o.Name: o for o in objetos}.get)

    def tearDown(self):
        sys.modules.pop(MODULO, None)
        self.patch.stop()

    def test_lista_unifilar_multifilar_e_transferencia_com_o_nome_do_quadro(self):
        titulos = [t for t, _ in self.servico.listar_diagramas(self.doc)]
        self.assertEqual(titulos, ["Unifilar QD1", "Multifilar QD1", "Transferência rede/gerador (QTA)"])

    def test_descendentes_em_qualquer_nivel(self):
        dentro = objeto("Dentro")
        grupo = objeto("G", grupo=[objeto("Sub", grupo=[dentro])])
        self.assertEqual([o.Name for o in self.servico.descendentes(grupo)], ["Sub", "Dentro"])

    def test_captura_deixa_so_o_diagrama_visivel_de_topo_e_enquadrado(self):
        view = mock.MagicMock()
        gui = sys.modules["FreeCADGui"]
        self.servico.capturar_diagrama(self.doc, view, self.unifilar, "/tmp/x.png")
        visiveis = {o.Name for o in self.doc.Objects if o.ViewObject.Visibility}
        self.assertEqual(visiveis, {"diagrama", "Sketch", "Texto"})
        view.viewTop.assert_called_once()
        gui.SendMsgToActiveView.assert_called_with("ViewSelection")
        args = view.saveImage.call_args.args
        self.assertEqual((args[0], args[1], args[3]), ("/tmp/x.png", self.servico.LARGURA_IMAGEM, "White"))


if __name__ == "__main__":
    unittest.main()
