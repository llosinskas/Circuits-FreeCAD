"""Comandos para inserir componentes e elementos no projeto."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits import ELECTRIC_LIBRARY_PATH, LIBRARY_PATH
from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.objects.lighting import create_lighting
from freecad.Circuits.objects.outlet import create_outlet
from freecad.Circuits.objects.switch import create_switch
from freecad.Circuits.qt import QtCore, QtWidgets
from freecad.Circuits.services import alinhamento, pavimentos
from freecad.Circuits.services.tomadas import criar_tug
from freecad.Circuits.UI.dialogs.ComponentInserter import ComponentInserter, ComponentInsertionMode


def _posicionar_com_mouse(obj, mensagem, ao_fixar=None, cota=0.0):
    """Posiciona um símbolo 2D na planta, na cota dada, com alinhamento aos símbolos vizinhos."""
    App.Console.PrintMessage(f"{mensagem} Clique na planta para posicionar.\n")
    ComponentInsertionMode(
        obj,
        ao_fixar=ao_fixar,
        cota=cota,
        referencias=alinhamento.posicoes_dos_simbolos(App.activeDocument(), exceto=obj),
    ).start()


class _InserirDaBiblioteca:
    """Abre o seletor da biblioteca e insere o componente como link."""

    pasta = LIBRARY_PATH
    mensagem = "Componente inserido"

    def Activated(self):
        if not documento_ou_aviso():
            return
        inserter = ComponentInserter(self.pasta, on_component_loaded=self._ao_carregar)
        inserter.insert_component_as_link_with_placement()

    def _ao_carregar(self, filepath, obj):
        print(f"{self.mensagem}: {obj.Label}")

    def IsActive(self):
        return True


class _CriarEPosicionar:
    """Cria um objeto FeaturePython e o posiciona com o mouse, em sequência até ESC."""

    criar = None
    mensagem = ""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        pavimento = pavimentos.pavimento_para_insercao(doc, Gui.Selection.getSelection())
        obj = type(self).criar()
        if obj:
            pavimentos.arquivar(doc, obj, pavimento)  # entra na pasta do tipo, dentro do pavimento
            # O próximo só começa depois que o clique atual terminar de ser tratado.
            _posicionar_com_mouse(
                obj, self.mensagem, lambda: QtCore.QTimer.singleShot(0, self.Activated), pavimentos.elevacao(pavimento)
            )

    def IsActive(self):
        return True


class InsertComponent(_InserirDaBiblioteca):
    def GetResources(self):
        return recursos(
            "Componentes.svg",
            "Componente",
            "Escolhe um componente da biblioteca e o posiciona na planta",
        )


class Equipaments(_InserirDaBiblioteca):
    pasta = ELECTRIC_LIBRARY_PATH
    mensagem = "Equipamento inserido (link com posicionamento)"

    def GetResources(self):
        return recursos(
            "equipamentos.svg",
            "Equipamento",
            "Escolhe um equipamento elétrico da biblioteca e o posiciona na planta",
        )


class Tugs:
    """Tomada em Sketch, compatível com ComponentEletric, posicionada com o mouse."""

    def Activated(self):
        doc = documento_ou_aviso()
        if doc:
            pavimento = pavimentos.pavimento_para_insercao(doc, Gui.Selection.getSelection())
            tug = criar_tug(doc)
            pavimentos.arquivar(doc, tug, pavimento)
            _posicionar_com_mouse(tug, "Tomada criada.", cota=pavimentos.elevacao(pavimento))

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "tug.svg",
            "Tomada TUG",
            "Insere uma tomada de uso geral com fases, neutro, terra e circuito (clique para posicionar)",
        )


class InsertSwitch(_CriarEPosicionar):
    criar = staticmethod(create_switch)
    mensagem = "Interruptor criado."

    def GetResources(self):
        return recursos(
            "interruptor.svg",
            "Interruptor simples",
            "Insere um interruptor simples (uma tecla, um ponto de comando) e posiciona com o mouse",
        )


def _criar_interruptor(tipo):
    def criar():
        obj = create_switch()
        if obj:
            obj.Tipo = tipo
            App.activeDocument().recompute()
        return obj
    return criar


class InsertSwitchParalelo(_CriarEPosicionar):
    criar = staticmethod(_criar_interruptor("Paralelo"))
    mensagem = "Interruptor paralelo criado."

    def GetResources(self):
        return recursos(
            "interruptor_paralelo.svg",
            "Interruptor paralelo",
            "Insere um interruptor paralelo (three-way), para comandar a luz de dois lugares",
        )


class InsertSwitchIntermediario(_CriarEPosicionar):
    criar = staticmethod(_criar_interruptor("Intermediário"))
    mensagem = "Interruptor intermediário criado."

    def GetResources(self):
        return recursos(
            "interruptor_intermediario.svg",
            "Interruptor intermed.",
            "Insere um interruptor intermediário (four-way), para comandar a luz de três ou mais lugares",
        )


class InsertLighting(_CriarEPosicionar):
    criar = staticmethod(create_lighting)
    mensagem = "Ponto de iluminação criado."

    def GetResources(self):
        return recursos(
            "iluminacao.svg",
            "Iluminação antiga",
            "Insere o símbolo de ponto de iluminação e posiciona com o mouse",
        )


class InsertOutlet(_CriarEPosicionar):
    criar = staticmethod(create_outlet)
    mensagem = "Tomada criada."

    def GetResources(self):
        return recursos(
            "tomadas.svg",
            "Tomada antiga",
            "Insere o símbolo de tomada (127 V, 220 V ou bifásica) e posiciona com o mouse",
        )


class Wire:
    def Activated(self):
        if documento_ou_aviso():
            QtWidgets.QMessageBox.information(
                None, "Funcionalidade", "Fiação será implementada em breve com traçado automático."
            )

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "fio.svg",
            "Fiação automática",
            "Traçado automático da fiação (em breve)",
        )


class Conduit:
    """Inicia o desenho do caminho do eletroduto com o Draft Wire nativo."""

    def Activated(self):
        if documento_ou_aviso():
            App.Console.PrintMessage(
                "Ferramenta de Eletroduto ativada. Desenhe a linha base usando as propriedades de Wire do FreeCAD.\n"
            )
            Gui.runCommand("Draft_Wire")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "conduite.svg",
            "Eletroduto",
            "Desenha na planta o caminho do eletroduto, ponto a ponto",
        )


class CableTray:
    def Activated(self):
        if documento_ou_aviso():
            QtWidgets.QMessageBox.information(None, "Funcionalidade", "Eletrocalhas serão implementadas em breve.")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "eletrocalha.svg",
            "Eletrocalha",
            "Eletrocalhas (em breve)",
        )


Gui.addCommand("InsertComponent", InsertComponent())
Gui.addCommand("InsertTugs", Tugs())
Gui.addCommand("InsertEquipaments", Equipaments())
Gui.addCommand("InsertWire", Wire())
Gui.addCommand("InsertConduit", Conduit())
Gui.addCommand("InsertCableTray", CableTray())
Gui.addCommand("InsertSwitch", InsertSwitch())
Gui.addCommand("InsertSwitchParalelo", InsertSwitchParalelo())
Gui.addCommand("InsertSwitchIntermediario", InsertSwitchIntermediario())
Gui.addCommand("InsertLighting", InsertLighting())
Gui.addCommand("InsertOutlet", InsertOutlet())
