"""Cor dos Sketches: sempre preta, com ou sem janela."""
import types
import unittest

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.services import estilo


def sketch(com_vista=True, tipo="Sketcher::SketchObject"):
    vista = types.SimpleNamespace(LineColor=(1.0, 1.0, 1.0), PointColor=(1.0, 1.0, 1.0)) if com_vista else None
    return types.SimpleNamespace(TypeId=tipo, ViewObject=vista)


class TestEstilo(unittest.TestCase):
    def test_pinta_linhas_e_pontos_de_preto(self):
        s = sketch()
        self.assertTrue(estilo.pintar_sketch(s))
        self.assertEqual((s.ViewObject.LineColor, s.ViewObject.PointColor), ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))

    def test_desliga_a_cor_automatica_para_a_cor_ficar_no_arquivo(self):
        s = sketch()
        s.ViewObject.AutoColor = True  # FreeCAD 1.0: com ela, o Sketch volta branco ao abrir o arquivo
        estilo.pintar_sketch(s)
        self.assertFalse(s.ViewObject.AutoColor)

    def test_sem_vista_nao_quebra(self):
        self.assertFalse(estilo.pintar_sketch(sketch(com_vista=False)))

    def test_vista_sem_a_propriedade_e_ignorada(self):
        s = types.SimpleNamespace(ViewObject=types.SimpleNamespace(LineColor=(1.0, 1.0, 1.0)))
        self.assertTrue(estilo.pintar_sketch(s))
        self.assertEqual(s.ViewObject.LineColor, (0.0, 0.0, 0.0))
        self.assertFalse(hasattr(s.ViewObject, "PointColor"))

    def test_pintar_todos_so_pinta_sketches_do_documento(self):
        a, b, linha = sketch(), sketch(), sketch(tipo="Part::Feature")
        doc = types.SimpleNamespace(Objects=[a, linha, b, sketch(com_vista=False)])
        self.assertEqual(estilo.pintar_todos(doc), 2)
        self.assertEqual(linha.ViewObject.LineColor, (1.0, 1.0, 1.0))
        self.assertEqual(a.ViewObject.LineColor, (0.0, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
