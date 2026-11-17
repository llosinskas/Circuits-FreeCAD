"""Teclas e alinhamento do modo de inserção, com o FreeCAD e o Qt simulados."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)

MODULO = "freecad.Circuits.UI.dialogs.ComponentInserter"
FALSOS = ("FreeCAD", "FreeCADGui", "freecad.Circuits.qt", "freecad.Circuits.UI.dialogs.ComponentSelectorDialog")
RECARREGAR = (MODULO, "freecad.Circuits.UI.dialogs", "freecad.Circuits.UI")


class Vetor:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z

    def __sub__(self, outro):
        return Vetor(self.x - outro.x, self.y - outro.y, self.z - outro.z)

    @property
    def Length(self):
        return (self.x ** 2 + self.y ** 2 + self.z ** 2) ** 0.5


class Vista:
    """Vista em que 1 pixel da tela vale 2 mm do desenho, com Z fora do plano."""

    def __init__(self):
        self.callbacks = {}

    def addEventCallback(self, evento, funcao):
        self.callbacks[evento] = funcao
        return funcao

    def removeEventCallback(self, evento, funcao):
        self.callbacks.pop(evento, None)

    def getPoint(self, x, y):
        return Vetor(x * 2.0, y * 2.0, 77.0)

    def redraw(self):
        pass


class TestModoDeInsercao(unittest.TestCase):
    def setUp(self):
        self.vista = Vista()
        gui = mock.MagicMock(name="FreeCADGui")
        gui.ActiveDocument.ActiveView = self.vista
        falsos = {nome: mock.MagicMock(name=nome) for nome in FALSOS}
        falsos["FreeCADGui"] = gui
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.Modo = importlib.import_module(MODULO).ComponentInsertionMode
        self.documento = mock.MagicMock()
        self.obj = types.SimpleNamespace(
            Name="Ponto", Document=self.documento, touch=lambda: None,
            Placement=types.SimpleNamespace(Base=Vetor(), Rotation=mock.MagicMock()),
        )

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def modo(self, **opcoes):
        modo = self.Modo(self.obj, **opcoes)
        modo.start()
        return modo

    def mover(self, x, y):
        self.vista.callbacks["SoLocation2Event"]({"Position": (x, y)})
        return self.obj.Placement.Base.x, self.obj.Placement.Base.y

    def tecla(self, nome):
        self.vista.callbacks["SoKeyboardEvent"]({"State": "DOWN", "Key": nome})

    def test_plano_z0(self):
        self.modo(plano_z0=True)
        self.assertEqual(self.mover(100, 50), (200.0, 100.0))
        self.assertEqual(self.obj.Placement.Base.z, 0.0)

    def test_cota_do_pavimento(self):
        self.modo(cota=3000.0, plano_z0=True)  # a cota tem prioridade
        self.assertEqual(self.mover(100, 50), (200.0, 100.0))
        self.assertEqual(self.obj.Placement.Base.z, 3000.0)

    def test_alinhamento_automatico_dentro_de_dez_pixels(self):
        self.modo(referencias=[(1000.0, 0.0)])
        # 10 pixels = 20 mm: a 12 mm do vizinho em X, alinha; em Y está longe, não mexe.
        self.assertEqual(self.mover(506, 300), (1000.0, 600.0))
        self.assertEqual(self.mover(520, 300), (1040.0, 600.0))

    def test_tecla_l_desliga_o_automatico(self):
        self.modo(referencias=[(1000.0, 0.0)])
        self.tecla("l")
        self.assertEqual(self.mover(506, 300), (1012.0, 600.0))

    def test_espaco_trava_um_eixo_depois_o_outro_depois_solta(self):
        modo = self.modo(referencias=[(1000.0, 0.0)])
        self.mover(600, 400)  # (1200, 800): mais perto do vizinho em X do que em Y
        self.tecla("SPACE")
        self.assertEqual(modo.trava, ("x", 1000.0))
        self.assertEqual(self.mover(900, 450), (1000.0, 900.0))  # preso na vertical do vizinho
        self.tecla(" ")
        self.assertEqual(modo.trava, ("y", 0.0))
        self.assertEqual(self.mover(900, 450), (1800.0, 0.0))  # preso na horizontal do vizinho
        self.tecla("a")
        self.assertIsNone(modo.trava)
        self.assertEqual(self.mover(900, 450), (1800.0, 900.0))

    def test_espaco_sem_vizinhos_nao_trava(self):
        modo = self.modo()
        self.mover(10, 10)
        self.tecla("SPACE")
        self.assertIsNone(modo.trava)

    def test_clique_fixa_e_a_sequencia_herda_a_trava(self):
        fixados = []
        modo = self.modo(referencias=[(1000.0, 0.0)], ao_fixar=lambda: fixados.append(True))
        self.mover(600, 400)
        self.tecla("SPACE")
        self.vista.callbacks["SoMouseButtonEvent"]({"State": "DOWN", "Button": "BUTTON1"})
        self.assertEqual(fixados, [True])
        self.assertFalse(modo.is_active)
        proximo = self.Modo(self.obj, referencias=[(1000.0, 0.0)], ao_fixar=lambda: None)
        self.assertEqual(proximo.trava, ("x", 1000.0))
        self.assertIsNone(self.Modo(self.obj).trava)  # inserção avulsa não herda

    def test_esc_apaga_o_objeto_e_esquece_a_trava(self):
        modo = self.modo(referencias=[(1000.0, 0.0)], ao_fixar=lambda: None)
        self.mover(600, 400)
        self.tecla("SPACE")
        self.tecla("ESCAPE")
        self.documento.removeObject.assert_called_once_with("Ponto")
        self.assertFalse(modo.is_active)
        self.assertIsNone(self.Modo(self.obj, ao_fixar=lambda: None).trava)

    def test_novo_comando_encerra_a_insercao_anterior(self):
        primeiro = self.modo()
        outro = types.SimpleNamespace(Name="Outro", Document=mock.MagicMock(), touch=lambda: None,
                                      Placement=types.SimpleNamespace(Base=Vetor(), Rotation=mock.MagicMock()))
        segundo = self.Modo(outro)
        segundo.start()
        self.assertFalse(primeiro.is_active)
        self.documento.removeObject.assert_called_once_with("Ponto")
        self.assertTrue(segundo.is_active)

    def test_r_gira_o_objeto(self):
        self.modo()
        antes = self.obj.Placement.Rotation
        self.tecla("r")
        self.assertIsNot(self.obj.Placement.Rotation, antes)

    def girar_registrando(self):
        graus = []
        fc = sys.modules["FreeCAD"]
        fc.Rotation.side_effect = lambda eixo, angulo: graus.append(angulo) or mock.MagicMock(name=f"rot{angulo}")
        return graus

    def test_shift_r_gira_45_graus(self):
        graus = self.girar_registrando()
        self.modo()
        self.tecla("r")
        self.vista.callbacks["SoKeyboardEvent"]({"State": "DOWN", "Key": "r", "ShiftDown": True})
        self.assertEqual(graus, [90.0, 45.0])

    def test_a_sequencia_herda_a_rotacao(self):
        self.girar_registrando()
        primeiro = self.modo(ao_fixar=lambda: None)
        self.tecla("r")
        girado = self.obj.Placement.Rotation
        self.vista.callbacks["SoMouseButtonEvent"]({"State": "DOWN", "Button": "BUTTON1"})
        self.assertFalse(primeiro.is_active)
        outro = types.SimpleNamespace(Name="P2", Document=self.documento, touch=lambda: None,
                                      Placement=types.SimpleNamespace(Base=Vetor(), Rotation="original"))
        self.Modo(outro, ao_fixar=lambda: None)
        self.assertIs(outro.Placement.Rotation, girado)
        avulso = types.SimpleNamespace(Name="P3", Placement=types.SimpleNamespace(Base=Vetor(), Rotation="original"))
        self.Modo(avulso)  # fora de uma sequência não herda
        self.assertEqual(avulso.Placement.Rotation, "original")

    def test_filtro_do_qt_impede_o_atalho_e_entrega_a_tecla(self):
        modulo = sys.modules[MODULO]
        Qt = types.SimpleNamespace(Key_R=82, Key_A=65, Key_L=76, Key_Space=32, Key_Escape=27, ShiftModifier=0x2000000)
        QEvent = types.SimpleNamespace(ShortcutOverride=51, KeyPress=6)
        foco = {"widget": None}

        class Campo:
            pass
        aplicacao = types.SimpleNamespace(focusWidget=lambda: foco["widget"])
        modulo.QtCore = types.SimpleNamespace(QObject=object, Qt=Qt, QEvent=QEvent)
        modulo.QtWidgets = types.SimpleNamespace(QApplication=aplicacao, QLineEdit=Campo)
        modo = types.SimpleNamespace(is_active=True, teclas=[])
        modo.tratar_tecla = lambda nome, shift: modo.teclas.append((nome, shift))
        filtro = modulo._criar_filtro_de_teclas(modo)

        def evento(tipo, tecla, shift=False, repeticao=False):
            return mock.MagicMock(type=lambda: tipo, key=lambda: tecla, isAutoRepeat=lambda: repeticao,
                                  modifiers=lambda: Qt.ShiftModifier if shift else 0)
        atalho = evento(51, 82)
        self.assertTrue(filtro.eventFilter(None, atalho))
        atalho.accept.assert_called_once()
        self.assertTrue(filtro.eventFilter(None, evento(6, 82, shift=True)))
        self.assertTrue(filtro.eventFilter(None, evento(6, 82, repeticao=True)))  # repetição: engolida, sem girar
        self.assertFalse(filtro.eventFilter(None, evento(6, 90)))  # outra tecla segue normal
        self.assertEqual(modo.teclas, [("R", True)])
        foco["widget"] = Campo()  # digitando num campo: a tecla é do campo
        self.assertFalse(filtro.eventFilter(None, evento(6, 82)))
        foco["widget"] = None
        modo.is_active = False
        self.assertFalse(filtro.eventFilter(None, evento(51, 82)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
