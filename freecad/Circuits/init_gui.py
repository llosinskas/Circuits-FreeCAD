"""Registro da bancada no FreeCAD.

O FreeCAD importa este módulo na inicialização, para todo pacote ``freecad.*``.
Mantenha-o leve: os comandos só são importados em ``Initialize``, na primeira
ativação da bancada.
"""
import os

import FreeCAD as app
import FreeCADGui as gui

from freecad.Circuits import ICON_PATH, TRANSLATIONS_PATH
from freecad.Circuits.qt import QtCore, QtWidgets

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

# Barras da bancada, na ordem do fluxo de um projeto em planta (2D primeiro).
PROJECT_TOOLS = ["newProjetctEletrical", "newSpreadsheet", "ImportQET"]
POINT_TOOLS = [
    "InsertOutlet",
    "InsertTugs",
    "InsertSwitch",
    "InsertLighting",
    "InsertEquipaments",
    "InsertComponent",
]
INFRA_TOOLS = ["InsertConduit", "Add_Node", "Cabo"]
BOARD_TOOLS = ["GerarPlanilha", "AddCircuito", "GerarUnifilar"]
DOCUMENT_TOOLS = [
    "BIM_Text",
    "Draft_Dimension",
    "Draft_Label",
    "Arch_SectionPlane",
    "BIM_Shape2DView",
    "BIM_TDView",
    "GenerateReport",
]
MODEL_3D_TOOLS = ["Generate3DSwitches", "Generate3DConduits", "Gerar3D"]
LIBRARY_TOOLS = ["CreateModel", "ListElements", "ReiniciarBancada"]

# Só no menu: comandos antigos, incompletos ou de uso raro.
EXTRA_TOOLS = ["ComponentEletric", "InsertWire", "InsertCableTray", "AddSpreadsheet", "NewQuadro", "GetSpaces"]

_tr = QtCore.QT_TRANSLATE_NOOP
ELECTRIC_TOOLBARS = [
    (_tr("Workbench", "Projeto elétrico"), PROJECT_TOOLS),
    (_tr("Workbench", "Pontos elétricos"), POINT_TOOLS),
    (_tr("Workbench", "Infraestrutura"), INFRA_TOOLS),
    (_tr("Workbench", "Quadros e diagramas"), BOARD_TOOLS),
    (_tr("Workbench", "Documentação"), DOCUMENT_TOOLS),
]
SUPPORT_TOOLBARS = [
    (_tr("Workbench", "Modelo 3D"), MODEL_3D_TOOLS),
    (_tr("Workbench", "Biblioteca e ferramentas"), LIBRARY_TOOLS),
]
TOOLBARS = ELECTRIC_TOOLBARS + [
    (_tr("Workbench", "Desenho"), DRAWING_TOOLS),
    (_tr("Workbench", "Modificador"), MODIFY_TOOLS),
    (_tr("Workbench", "Snap"), SNAP_TOOLS),
    (_tr("Workbench", "Arquitetura"), BIM_TOOLS),
] + SUPPORT_TOOLBARS
MENU = "&Elétrica"
MENUS = [
    ([MENU, "Projeto"], PROJECT_TOOLS),
    ([MENU, "Pontos elétricos"], POINT_TOOLS),
    ([MENU, "Infraestrutura"], INFRA_TOOLS),
    ([MENU, "Quadros e diagramas"], BOARD_TOOLS),
    ([MENU, "Documentação"], ["GenerateReport"]),
    ([MENU, "Modelo 3D"], MODEL_3D_TOOLS),
    ([MENU, "Biblioteca e ferramentas"], LIBRARY_TOOLS),
    ([MENU, "Outros"], EXTRA_TOOLS),
]

# Barras que mostram a legenda (texto) embaixo de cada ícone.
BARRAS_COM_LEGENDA = [label for label, _ in ELECTRIC_TOOLBARS + SUPPORT_TOOLBARS]
PREFERENCIAS = "User parameter:BaseApp/Preferences/Mod/Circuits"


def _aplicar_legendas(mostrar):
    """Mostra ou esconde o texto dos botões nas barras próprias da bancada.

    Desligue pela preferência booleana ``LegendaBotoes`` em ``PREFERENCIAS``.
    """
    estilo = QtCore.Qt.ToolButtonTextUnderIcon if mostrar else QtCore.Qt.ToolButtonIconOnly
    try:
        for barra in gui.getMainWindow().findChildren(QtWidgets.QToolBar):
            if barra.objectName() in BARRAS_COM_LEGENDA:
                barra.setToolButtonStyle(estilo)
    except Exception as erro:  # a legenda é só estética: nunca impede a ativação
        app.Console.PrintWarning(f"Circuits: não foi possível ajustar as legendas dos botões: {erro}\n")


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
        if app.ParamGet(PREFERENCIAS).GetBool("LegendaBotoes", True):
            # As barras só existem depois que o FreeCAD termina de montar a bancada.
            QtCore.QTimer.singleShot(0, lambda: _aplicar_legendas(True))

    def Deactivated(self):
        # Outra bancada pode reutilizar uma barra com o mesmo nome.
        _aplicar_legendas(False)

    def ContextMenu(self, recipient):
        pass


gui.addWorkbench(CircuitsWorkbench())
