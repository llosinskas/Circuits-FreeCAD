"""
Comandos para inserção de componentes e elementos no projeto.
Utiliza o novo sistema reutilizável de seleção e inserção de componentes.
"""

import os
from pathlib import Path

import FreeCADGui as Gui
import FreeCAD as App
import freecad.Circuits as WB

try:
    from PySide2 import QtGui, QtCore, QtWidgets
except ImportError:
    try:
        from PySide6 import QtGui, QtCore, QtWidgets
    except ImportError:
        from PySide import QtGui, QtCore
        QtWidgets = QtGui

from freecad.Circuits.UI.dialogs import ComponentInserter


class InsertComponent:   
    """Comando para inserir componentes elétricos genéricos."""
  
    def Activated(self):
        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(
                None,
                "Erro",
                "Nenhum documento FreeCAD aberto."
            )
            return
        
        folder = self._get_components_folder()
        inserter = ComponentInserter(
            folder,
            on_component_loaded=self._on_component_loaded
        )
        inserter.insert_component_as_link_with_placement()
    
    def _get_components_folder(self) -> str:
        return WB.LIBRARY_PATH
    
    def _on_component_loaded(self, filepath: str, obj):
        print(f"Componente inserido: {obj.Label}")
    
    def IsActive(self):
        return True
    
    def GetResources(self):
        return {
            'Pixmap': os.path.join(WB.ICON_PATH, 'Componentes.svg'), 
            'MenuText': 'Inserir novo circuito elétrico', 
            'ToolTip': 'Inserir um novo circuito elétrico'
        }


class Tugs:
    """Comando para inserir pontos de conexão de energia (tomadas).
    
    Cria um Sketcher::SketchObject com a simbologia 2D da tomada
    (mesma geometria do ComponentEletric) e injeta as propriedades
    elétricas e de geração 3D. Espera o clique do usuário para posicionar.
    """
    
    def Activated(self):
        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento FreeCAD aberto.")
            return

        import Sketcher
        import Part as PartModule
        from freecad.Circuits.UI.dialogs.ComponentInserter import ComponentInsertionMode

        # --- Cria o Sketch com a simbologia da tomada ---
        sketch = doc.addObject('Sketcher::SketchObject', 'Tomada')
        
        # Desenha a simbologia (triângulo com linha de conexão)
        heigth = 100
        sketch.addGeometry(PartModule.LineSegment(
            App.Vector(0, 0), App.Vector(heigth / 3, 0)), False)
        sketch.addGeometry(PartModule.LineSegment(
            App.Vector(heigth / 3, heigth / 4), App.Vector(heigth / 3, -heigth / 4)), False)
        sketch.addGeometry(PartModule.LineSegment(
            App.Vector(heigth / 3, heigth / 4), App.Vector(heigth, 0)), False)
        sketch.addGeometry(PartModule.LineSegment(
            App.Vector(heigth / 3, -heigth / 4), App.Vector(heigth, 0)), False)

        # --- Propriedades elétricas (compatíveis com ComponentEletric) ---
        sketch.addProperty("App::PropertyPower", "potencia")
        sketch.addProperty("App::PropertyInteger", "Fase")
        sketch.addProperty("App::PropertyFloat", "Fator_potencia")
        sketch.addProperty("App::PropertyFloat", "altura_piso")
        sketch.addProperty("App::PropertyString", "Descricao")
        sketch.addProperty("App::PropertyInteger", "Circuito")
        sketch.addProperty("App::PropertyElectricPotential", "Tensao")
        sketch.addProperty("App::PropertyString", "tipo")
        sketch.addProperty("App::PropertyBool", "terra")
        sketch.addProperty("App::PropertyBool", "neutro")

        # --- Propriedades de geração 3D (caixa) ---
        sketch.addProperty("App::PropertyFloat", "CaixaAltura", "Caixa 3D",
                           "Altura da caixa 4x2 em mm")
        sketch.addProperty("App::PropertyFloat", "CaixaLargura", "Caixa 3D",
                           "Largura da caixa 4x2 em mm")
        sketch.addProperty("App::PropertyFloat", "CaixaProfundidade", "Caixa 3D",
                           "Profundidade da caixa 4x2 em mm")

        # --- Valores padrão ---
        sketch.terra = True
        sketch.neutro = True
        sketch.tipo = 'tomada'
        sketch.Fase = 2
        sketch.Fator_potencia = 0.9
        sketch.Descricao = "Descrição da tomada"
        sketch.potencia = 100
        sketch.altura_piso = 300
        sketch.Circuito = 1
        sketch.Tensao = "220"
        sketch.CaixaAltura = 100.0
        sketch.CaixaLargura = 60.0
        sketch.CaixaProfundidade = 40.0

        doc.recompute()

        # --- Posicionamento interativo com o mouse ---
        App.Console.PrintMessage("Tomada criada. Clique na planta para posicionar.\n")
        mode = ComponentInsertionMode(sketch)
        mode.start()
    
    def IsActive(self):
        return True
    
    def GetResources(self):
        return {
            'Pixmap': os.path.join(WB.ICON_PATH, 'tomadas.svg'), 
            'MenuText': 'Inserir ponto de conexão de energia', 
            'ToolTip': 'Inserir tomada com simbologia 2D (clique para posicionar)'
        }


class Equipaments:
    """Comando para inserir equipamentos elétricos.
    
    Permite posicionamento interativo com o mouse.
    """
    
    def Activated(self):
        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento FreeCAD aberto.")
            return
        
        folder = self._get_components_folder()
        inserter = ComponentInserter(
            folder,
            on_component_loaded=self._on_component_loaded
        )
        inserter.insert_component_as_link_with_placement()
    
    def _get_components_folder(self) -> str:
        return os.path.join(WB.LIBRARY_PATH, "Eletrica")
    
    def _on_component_loaded(self, filepath: str, obj):
        print(f"Equipamento inserido (link com posicionamento): {obj.Label}")

    def IsActive(self):
        return True

    def GetResources(self):
        return {
            'Pixmap': os.path.join(WB.ICON_PATH, 'equipamentos.svg'), 
            'MenuText': 'Inserir um equipamento elétrico', 
            'ToolTip': 'Inserir um novo equipamento elétrico'
        }


class Wire:
    """Comando para inserir fiação."""
    
    def Activated(self):
        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento FreeCAD aberto.")
            return
        
        QtWidgets.QMessageBox.information(
            None,
            "Funcionalidade",
            "Fiação será implementada em breve com traçado automático."
        )
    
    def IsActive(self):
        return True
    
    def GetResources(self):
        return {
            'Pixmap': os.path.join(WB.ICON_PATH, 'fio.svg'), 
            'MenuText': 'Inserir fiação', 
            'ToolTip': 'Inserir fiação no projeto'
        }

class Conduit:
    """Comando para iniciar o desenho do caminho dos eletrodutos usando Draft Wire nativo."""
    
    def Activated(self):
        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento FreeCAD aberto.")
            return
            
        App.Console.PrintMessage("Ferramenta de Eletroduto ativada. Desenhe a linha base usando as propriedades de Wire do FreeCAD.\n")
        Gui.runCommand('Draft_Wire')
    
    def IsActive(self):
        return True
    
    def GetResources(self):
        return {
            'Pixmap': os.path.join(WB.ICON_PATH, 'conduite.svg'), 
            'MenuText': 'Desenhar Eletroduto (Draft Wire)', 
            'ToolTip': 'Desenha a linha guia do eletroduto usando a ferramenta nativa de Wire'
        }



class CableTray:
    """Comando para inserir eletrocalhas."""
    
    def Activated(self):
        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento FreeCAD aberto.")
            return
        
        QtWidgets.QMessageBox.information(
            None,
            "Funcionalidade",
            "Eletrocalhas serão implementadas em breve."
        )
    
    def IsActive(self):
        return True
    
    def GetResources(self):
        return {
            'Pixmap': os.path.join(WB.ICON_PATH, 'eletrocalha.svg'), 
            'MenuText': 'Inserir eletrocalha na instalação', 
            'ToolTip': 'Inserir eletrocalha na instalação'
        }


class InsertSwitch:
    """Comando para inserir um Interruptor na planta 2D.
    
    Cria o objeto FeaturePython Switch com símbolo 2D (círculo + linha)
    e ativa o modo de posicionamento interativo com o mouse.
    """

    def Activated(self):
        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento FreeCAD aberto.")
            return

        from freecad.Circuits.objects.switch import create_switch
        from freecad.Circuits.UI.dialogs.ComponentInserter import ComponentInsertionMode

        obj = create_switch()
        if obj:
            App.Console.PrintMessage("Interruptor criado. Clique na planta para posicionar.\n")
            mode = ComponentInsertionMode(obj)
            mode.start()

    def IsActive(self):
        return True

    def GetResources(self):
        return {
            'Pixmap': os.path.join(WB.ICON_PATH, 'interruptor.svg'),
            'MenuText': 'Inserir Interruptor',
            'ToolTip': 'Inserir um interruptor na planta e posicionar com o mouse'
        }


class InsertLighting:
    """Comando para inserir um Ponto de Iluminação na planta 2D.
    
    Cria o objeto FeaturePython Lighting com símbolo 2D (círculo + cruz)
    e ativa o modo de posicionamento interativo com o mouse.
    """

    def Activated(self):
        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento FreeCAD aberto.")
            return

        from freecad.Circuits.objects.lighting import create_lighting
        from freecad.Circuits.UI.dialogs.ComponentInserter import ComponentInsertionMode

        obj = create_lighting()
        if obj:
            App.Console.PrintMessage("Ponto de iluminação criado. Clique na planta para posicionar.\n")
            mode = ComponentInsertionMode(obj)
            mode.start()

    def IsActive(self):
        return True

    def GetResources(self):
        return {
            'Pixmap': os.path.join(WB.ICON_PATH, 'iluminacao.svg'),
            'MenuText': 'Inserir Ponto de Iluminação',
            'ToolTip': 'Inserir um ponto de iluminação na planta e posicionar com o mouse'
        }


class InsertOutlet:
    """Comando para inserir uma Tomada na planta 2D.
    
    Cria o objeto FeaturePython Outlet com símbolo 2D (semicírculo NBR 5444)
    e ativa o modo de posicionamento interativo com o mouse.
    """

    def Activated(self):
        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento FreeCAD aberto.")
            return

        from freecad.Circuits.objects.outlet import create_outlet
        from freecad.Circuits.UI.dialogs.ComponentInserter import ComponentInsertionMode

        obj = create_outlet()
        if obj:
            App.Console.PrintMessage("Tomada criada. Clique na planta para posicionar.\n")
            mode = ComponentInsertionMode(obj)
            mode.start()

    def IsActive(self):
        return True

    def GetResources(self):
        return {
            'Pixmap': os.path.join(WB.ICON_PATH, 'tomadas.svg'),
            'MenuText': 'Inserir Tomada',
            'ToolTip': 'Inserir uma tomada na planta e posicionar com o mouse'
        }


# Registra os comandos no FreeCAD
Gui.addCommand("InsertComponent", InsertComponent())
Gui.addCommand("InsertTugs", Tugs())
Gui.addCommand("InsertEquipaments", Equipaments())
Gui.addCommand("InsertWire", Wire())
Gui.addCommand("InsertConduit", Conduit())
Gui.addCommand("InsertCableTray", CableTray())
Gui.addCommand("InsertSwitch", InsertSwitch())
Gui.addCommand("InsertLighting", InsertLighting())
Gui.addCommand("InsertOutlet", InsertOutlet())
