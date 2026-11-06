"""Comandos para inserir componentes e elementos no projeto."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits import ELECTRIC_LIBRARY_PATH, LIBRARY_PATH
from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.objects.lighting import create_lighting
from freecad.Circuits.objects.outlet import create_outlet
from freecad.Circuits.objects.switch import create_switch
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services.tomadas import criar_tug
from freecad.Circuits.UI.dialogs.ComponentInserter import ComponentInserter, ComponentInsertionMode


def _posicionar_com_mouse(obj, mensagem):
    App.Console.PrintMessage(f"{mensagem} Clique na planta para posicionar.\n")
    ComponentInsertionMode(obj).start()


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
    """Cria um objeto FeaturePython e o posiciona com o mouse."""

    criar = None
    mensagem = ""

    def Activated(self):
        if not documento_ou_aviso():
            return
        obj = type(self).criar()
        if obj:
            _posicionar_com_mouse(obj, self.mensagem)

    def IsActive(self):
        return True


class InsertComponent(_InserirDaBiblioteca):
    def GetResources(self):
        return recursos("Componentes.svg", "Inserir novo circuito elétrico", "Inserir um novo circuito elétrico")


class Equipaments(_InserirDaBiblioteca):
    pasta = ELECTRIC_LIBRARY_PATH
    mensagem = "Equipamento inserido (link com posicionamento)"

    def GetResources(self):
        return recursos("equipamentos.svg", "Inserir um equipamento elétrico", "Inserir um novo equipamento elétrico")


class Tugs:
    """Tomada em Sketch, compatível com ComponentEletric, posicionada com o mouse."""

    def Activated(self):
        doc = documento_ou_aviso()
        if doc:
            _posicionar_com_mouse(criar_tug(doc), "Tomada criada.")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "tomadas.svg",
            "Inserir ponto de conexão de energia",
            "Inserir tomada com simbologia 2D (clique para posicionar)",
        )


class InsertSwitch(_CriarEPosicionar):
    criar = staticmethod(create_switch)
    mensagem = "Interruptor criado."

    def GetResources(self):
        return recursos("interruptor.svg", "Inserir Interruptor", "Inserir um interruptor na planta e posicionar com o mouse")


class InsertLighting(_CriarEPosicionar):
    criar = staticmethod(create_lighting)
    mensagem = "Ponto de iluminação criado."

    def GetResources(self):
        return recursos(
            "iluminacao.svg",
            "Inserir Ponto de Iluminação",
            "Inserir um ponto de iluminação na planta e posicionar com o mouse",
        )


class InsertOutlet(_CriarEPosicionar):
    criar = staticmethod(create_outlet)
    mensagem = "Tomada criada."

    def GetResources(self):
        return recursos("tomadas.svg", "Inserir Tomada", "Inserir uma tomada na planta e posicionar com o mouse")


class Wire:
    def Activated(self):
        if documento_ou_aviso():
            QtWidgets.QMessageBox.information(
                None, "Funcionalidade", "Fiação será implementada em breve com traçado automático."
            )

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos("fio.svg", "Inserir fiação", "Inserir fiação no projeto")


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
            "Desenhar Eletroduto (Draft Wire)",
            "Desenha a linha guia do eletroduto usando a ferramenta nativa de Wire",
        )


class CableTray:
    def Activated(self):
        if documento_ou_aviso():
            QtWidgets.QMessageBox.information(None, "Funcionalidade", "Eletrocalhas serão implementadas em breve.")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos("eletrocalha.svg", "Inserir eletrocalha na instalação", "Inserir eletrocalha na instalação")


Gui.addCommand("InsertComponent", InsertComponent())
Gui.addCommand("InsertTugs", Tugs())
Gui.addCommand("InsertEquipaments", Equipaments())
Gui.addCommand("InsertWire", Wire())
Gui.addCommand("InsertConduit", Conduit())
Gui.addCommand("InsertCableTray", CableTray())
Gui.addCommand("InsertSwitch", InsertSwitch())
Gui.addCommand("InsertLighting", InsertLighting())
Gui.addCommand("InsertOutlet", InsertOutlet())
