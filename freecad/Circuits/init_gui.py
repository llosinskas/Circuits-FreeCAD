"""
Módulo de inicialização da bancada Circuits para FreeCAD.
Projetos Elétricos Residenciais, Industriais e Comerciais.

Author: Lucas Losinskas
"""

import os
import FreeCAD as app
import FreeCADGui as gui

try:
    from PySide2 import QtCore
except ImportError:
    try:
        from PySide6 import QtCore
    except ImportError:
        # Fallback para o shim legado do FreeCAD
        from PySide import QtCore

__dirname__ = os.path.dirname(__file__)

# Registrar traduções
gui.addLanguagePath(os.path.join(__dirname__, "Resources", "translations"))
gui.updateLocale()


class CircuitsWorkbench(gui.Workbench):
    """Bancada para a criação e gerenciamento de projetos elétricos."""

    try:
        from PySide2 import QtCore as _QtCore
    except ImportError:
        try:
            from PySide6 import QtCore as _QtCore
        except ImportError:
            from PySide import QtCore as _QtCore

    MenuText = _QtCore.QCoreApplication.translate("Workbench", "Engenharia")
    ToolTip = _QtCore.QCoreApplication.translate(
        "Workbench",
        "Bancada para projetos elétricos residenciais, industriais e comerciais",
    )
    Icon = os.path.join(__dirname__, "Resources", "Icons", "logo.svg")

    # ==========================================
    # Definição dos comandos por toolbar
    SNAP_TOOLS = [
        "Draft_ToggleGrid",
        "Draft_Snap_Lock",
        "Draft_Snap_Midpoint",
        "Draft_Snap_Perpendicular",
        "Draft_Snap_Grid",
        "Draft_Snap_Intersection",
        "Draft_Snap_Parallel",
        "Draft_Snap_Endpoint",
        "Draft_Snap_Angle",
        "Draft_Snap_Center",
        "Draft_Snap_Extension",
        "Draft_Snap_Near",
        "Draft_Snap_Ortho",
        "Draft_Snap_Special",
        "Draft_Snap_Dimensions",
        "Draft_Snap_WorkingPlane",
    ]

    DRAWING_TOOLS = [
        "BIM_Sketch",
        "Draft_Line",
        "Draft_Circle",
        "Draft_Wire",
        "Draft_Arc",
        "Draft_Arc_3Points",
        "Draft_Ellipse",
        "Draft_Polygon",
        "Draft_Rectangle",
        "Draft_BSpline",
        "Draft_BezCurve",
        "Draft_Point",
    ]

    MODIFY_TOOLS = [
        "Draft_Move",
        "Draft_Rotate",
        "Draft_Offset",
        "Draft_Trimex",
        "Draft_Join",
        "Draft_Scale",
        "Draft_Edit",
        "Draft_Mirror",
        "Draft_OrthoArray",
        "Draft_PathArray",
        "Draft_Draft2Sketch",
    ]

    BIM_TOOLS = [
        "BIM_Project",
        "Arch_Space",
        "Arch_Wall",
        "BIM_Column",
        "BIM_Beam",
        "BIM_Slab",
        "BIM_Door",
        "BIM_Library",
    ]

    ANNOTATION_TOOLS = [
        "BIM_Text",
        "Arch_SectionPlane",
        "BIM_TDView",
        "BIM_Shape2DView",
    ]

    PROJECT_TOOLS = [
        "ComponentEletric",
        "Gerar3D",
        "Cabo",
    ]

    NEW_PROJECT_TOOLS = [
        "newProjetctEletrical",
        "newSpreadsheet",
        "AddSpreadsheet",
        "ListElements",
        "CreateModel",
    ]

    INSERT_COMPONENTS_TOOLS = [
        "InsertComponent",
        "InsertTugs",
        "InsertEquipaments",
        "InsertSwitch",
        "InsertLighting",
        "InsertOutlet",
        "InsertWire",
        "InsertConduit",
        "Generate3DConduits",
        "Generate3DSwitches",
        "InsertCableTray",
    ]

    REPORT_TOOLS = [
        "GenerateReport",
    ]

    UTILITY_TOOLS = [
        "GetSpaces",
        "ReiniciarBancada",
    ]

    UNIFILAR_TOOLS = [
        "GerarUnifilar",
        "GerarPlanilha",
        "AddCircuito",
    ]

    QELETROTECH_TOOLS = [
        "ImportQET",
        "Add_Node",
    ]

    QUADRO_TOOLS = [
        "NewQuadro",
    ]

    # ==========================================
    # Toolbars com labels traduzíveis
    QT_TRANSLATE_NOOP = _QtCore.QT_TRANSLATE_NOOP
    TOOLBARS = [
        (QT_TRANSLATE_NOOP("Workbench", "Snap"), SNAP_TOOLS),
        (QT_TRANSLATE_NOOP("Workbench", "Desenho"), DRAWING_TOOLS),
        (QT_TRANSLATE_NOOP("Workbench", "Modificador"), MODIFY_TOOLS),
        (QT_TRANSLATE_NOOP("Workbench", "BIM"), BIM_TOOLS),
        (QT_TRANSLATE_NOOP("Workbench", "Anotações"), ANNOTATION_TOOLS),
        (QT_TRANSLATE_NOOP("Workbench", "Inserir Componentes"), PROJECT_TOOLS),
        (QT_TRANSLATE_NOOP("Workbench", "Novo Projeto"), NEW_PROJECT_TOOLS),
        (QT_TRANSLATE_NOOP("Workbench", "Componentes"), INSERT_COMPONENTS_TOOLS),
        (QT_TRANSLATE_NOOP("Workbench", "Relatórios"), REPORT_TOOLS),
        (QT_TRANSLATE_NOOP("Workbench", "Ferramentas"), UTILITY_TOOLS),
        (QT_TRANSLATE_NOOP("Workbench", "Diagrama Unifilar"), UNIFILAR_TOOLS),
        (QT_TRANSLATE_NOOP("Workbench", "QEletrotech"), QELETROTECH_TOOLS),
        (QT_TRANSLATE_NOOP("Workbench", "Quadro Elétrico"), QUADRO_TOOLS),
    ]

    def GetClassName(self):
        return "Gui::PythonWorkbench"

    def Initialize(self):
        """Executada na primeira ativação da bancada.
        Importa módulos e configura toolbars/menus.
        """
        # Importações lazy — só quando a bancada é ativada
        import bimcommands
        import DraftTools
        from .commands import (
            new_project,
            projeto_eletrico,
            insert_component,
            generate_3d,
            gerar_unifilar,
            reports,
            tools,
            import_QEletrotech,
            projeto_quadro,
        )
        import Arch
        import Draft

        # Configurar toolbars
        for label, cmd_list in self.TOOLBARS:
            self.appendToolbar(label, cmd_list)

        # Configurar menus
        self.appendMenu("&Componentes", self.INSERT_COMPONENTS_TOOLS)
        self.appendMenu("&Novo Projeto", self.NEW_PROJECT_TOOLS)
        self.appendMenu("&Diagrama Unifilar", self.UNIFILAR_TOOLS)
        self.appendMenu("&Quadro Elétrico", self.QUADRO_TOOLS)
        self.appendMenu("&Relatórios", self.REPORT_TOOLS)

        gui.updateGui()

    def Activated(self):
        """Executado quando a bancada é ativada."""
        app.Console.PrintMessage("✓ Bancada Circuits ativada!\n")

    def Deactivated(self):
        """Executado quando a bancada é desativada."""
        pass

    def ContextMenu(self, recipient):
        """Menu de contexto (botão direito)."""
        pass


gui.addWorkbench(CircuitsWorkbench())
