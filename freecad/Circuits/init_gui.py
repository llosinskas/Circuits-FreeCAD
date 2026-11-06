"""Registro da bancada no FreeCAD.

O FreeCAD importa este módulo na inicialização, para todo pacote ``freecad.*``.
Mantenha-o leve: os comandos só são importados em ``Initialize``, na primeira
ativação da bancada.
"""
import os

import FreeCAD as app
import FreeCADGui as gui

from freecad.Circuits import ICON_PATH, TRANSLATIONS_PATH
from freecad.Circuits.qt import QtCore

gui.addLanguagePath(TRANSLATIONS_PATH)
gui.updateLocale()

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
ANNOTATION_TOOLS = ["BIM_Text", "Arch_SectionPlane", "BIM_TDView", "BIM_Shape2DView"]
PROJECT_TOOLS = ["ComponentEletric", "Gerar3D", "Cabo"]
NEW_PROJECT_TOOLS = ["newProjetctEletrical", "newSpreadsheet", "AddSpreadsheet", "ListElements", "CreateModel"]
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
REPORT_TOOLS = ["GenerateReport"]
UTILITY_TOOLS = ["GetSpaces", "ReiniciarBancada"]
UNIFILAR_TOOLS = ["GerarUnifilar", "GerarPlanilha", "AddCircuito"]
QELETROTECH_TOOLS = ["ImportQET", "Add_Node"]
QUADRO_TOOLS = ["NewQuadro"]

_tr = QtCore.QT_TRANSLATE_NOOP
TOOLBARS = [
    (_tr("Workbench", "Snap"), SNAP_TOOLS),
    (_tr("Workbench", "Desenho"), DRAWING_TOOLS),
    (_tr("Workbench", "Modificador"), MODIFY_TOOLS),
    (_tr("Workbench", "BIM"), BIM_TOOLS),
    (_tr("Workbench", "Anotações"), ANNOTATION_TOOLS),
    (_tr("Workbench", "Inserir Componentes"), PROJECT_TOOLS),
    (_tr("Workbench", "Novo Projeto"), NEW_PROJECT_TOOLS),
    (_tr("Workbench", "Componentes"), INSERT_COMPONENTS_TOOLS),
    (_tr("Workbench", "Relatórios"), REPORT_TOOLS),
    (_tr("Workbench", "Ferramentas"), UTILITY_TOOLS),
    (_tr("Workbench", "Diagrama Unifilar"), UNIFILAR_TOOLS),
    (_tr("Workbench", "QEletrotech"), QELETROTECH_TOOLS),
    (_tr("Workbench", "Quadro Elétrico"), QUADRO_TOOLS),
]
MENUS = [
    ("&Componentes", INSERT_COMPONENTS_TOOLS),
    ("&Novo Projeto", NEW_PROJECT_TOOLS),
    ("&Diagrama Unifilar", UNIFILAR_TOOLS),
    ("&Quadro Elétrico", QUADRO_TOOLS),
    ("&Relatórios", REPORT_TOOLS),
]


class CircuitsWorkbench(gui.Workbench):
    """Bancada para a criação e gerenciamento de projetos elétricos."""

    MenuText = QtCore.QCoreApplication.translate("Workbench", "Engenharia")
    ToolTip = QtCore.QCoreApplication.translate(
        "Workbench",
        "Bancada para projetos elétricos residenciais, industriais e comerciais",
    )
    Icon = os.path.join(ICON_PATH, "logo.svg")

    def GetClassName(self):
        return "Gui::PythonWorkbench"

    def Initialize(self):
        """Executada na primeira ativação: registra comandos, toolbars e menus."""
        # Registram os comandos Draft_*/BIM_*/Arch_* usados nas toolbars.
        import bimcommands  # noqa: F401
        import DraftTools  # noqa: F401
        import Arch  # noqa: F401
        import Draft  # noqa: F401

        # Cada módulo registra os próprios comandos ao ser importado.
        from .commands import (  # noqa: F401
            generate_3d,
            gerar_unifilar,
            import_QEletrotech,
            insert_component,
            new_project,
            projeto_eletrico,
            projeto_quadro,
            reports,
            tools,
        )

        for label, commands in TOOLBARS:
            self.appendToolbar(label, commands)
        for label, commands in MENUS:
            self.appendMenu(label, commands)

        gui.updateGui()

    def Activated(self):
        app.Console.PrintMessage("✓ Bancada Circuits ativada!\n")

    def Deactivated(self):
        pass

    def ContextMenu(self, recipient):
        pass


gui.addWorkbench(CircuitsWorkbench())
