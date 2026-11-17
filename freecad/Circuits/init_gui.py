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

# --- Comandos nativos do FreeCAD ---------------------------------------------
# Nas barras ficam só os de uso frequente em planta; a lista completa está no menu.
SNAP_TOOLS = [
    "Draft_ToggleGrid",
    "Draft_Snap_Lock",
    "Draft_Snap_Endpoint",
    "Draft_Snap_Midpoint",
    "Draft_Snap_Intersection",
    "Draft_Snap_Perpendicular",
    "Draft_Snap_Near",
    "Draft_Snap_Ortho",
]
SNAP_EXTRA_TOOLS = [
    "Draft_Snap_Grid",
    "Draft_Snap_Parallel",
    "Draft_Snap_Angle",
    "Draft_Snap_Center",
    "Draft_Snap_Extension",
    "Draft_Snap_Special",
    "Draft_Snap_Dimensions",
    "Draft_Snap_WorkingPlane",
]
DRAWING_TOOLS = [
    "Draft_Line",
    "Draft_Wire",
    "Draft_Rectangle",
    "Draft_Circle",
    "Draft_Arc",
    "BIM_Text",
    "Draft_Dimension",
    "Draft_Label",
]
DRAWING_EXTRA_TOOLS = [
    "BIM_Sketch",
    "Draft_Arc_3Points",
    "Draft_Ellipse",
    "Draft_Polygon",
    "Draft_BSpline",
    "Draft_BezCurve",
    "Draft_Point",
    "Arch_SectionPlane",
    "BIM_Shape2DView",
    "BIM_TDView",
]
MODIFY_TOOLS = [
    "Draft_Move",
    "Draft_Rotate",
    "Draft_Mirror",
    "Draft_Offset",
    "Draft_Trimex",
    "Draft_Scale",
    "Draft_Edit",
    "AlinharPontos",
    "DistribuirPontos",
    "EscalaSimbolos",
]
ALIGN_TOOLS = ["AlinharPontos", "DistribuirPontos", "EscalaSimbolos"]
MODIFY_EXTRA_TOOLS = ["Draft_Join", "Draft_OrthoArray", "Draft_PathArray", "Draft_Draft2Sketch"]
BIM_TOOLS = ["Arch_Wall", "BIM_Door", "Arch_Space", "BIM_Library"]
BIM_EXTRA_TOOLS = ["BIM_Project", "BIM_Column", "BIM_Beam", "BIM_Slab"]

# --- Comandos da bancada -------------------------------------------------------
PROJECT_TOOLS = [
    "newProjetctEletrical",
    "ParametrosProjeto",
    "DefinirPavimento",
    "AdicionarNivelBIM",
    "MoverParaPavimento",
    "AjustarCotas",
    "newSpreadsheet",
    "ImportQET",
]
OUTLET_TOOLS = ["Ponto_tomada_baixa", "Ponto_tomada_media", "Ponto_tomada_alta", "Ponto_tomada_piso"]
POWER_TOOLS = ["Ponto_chuveiro", "Ponto_ar_condicionado", "Ponto_ventilador", "Ponto_ponto_forca", "Ponto_campainha"]
LIGHTING_TOOLS = [
    "Ponto_luz_teto",
    "Ponto_arandela",
    "Ponto_fluorescente",
    "Ponto_embutida",
    "Ponto_emergencia",
    "DistribuirLuminarias",
]
SWITCH_TOOLS = [
    "InsertSwitch",
    "InsertSwitchParalelo",
    "InsertSwitchIntermediario",
    "Ponto_botao_campainha",
    "Ponto_fotocelula",
]
GROUNDING_TOOLS = [
    "Ponto_haste_aterramento",
    "Ponto_caixa_inspecao",
    "Ponto_bep",
    "CondutorAterramento",
    "CalcAterramento",
]
BOARD_SYMBOL_TOOLS = ["Ponto_quadro_distribuicao", "Ponto_quadro_comando", "Ponto_quadro_medicao", "Ponto_medicao_agrupada"]
CIRCUIT_TOOLS = ["DefinirCircuito", "LigarInterruptor", "IdentificarPontos"]
INFRA_TOOLS = [
    "InsertConduit", "Ponto_caixa_passagem", "ConectarEletrodutos", "Add_Node", "ListaVerticais",
    "SimbolosVerticais", "DetalharVerticais", "Cabo",
    "InsertCableTray", "GerarSuportes",
]
BOARD_DATA_TOOLS = ["GerarPlanilha", "CircuitosQuadro", "AddCircuito"]
BOARD_TOOLS = ["GerarPlanilha", "CircuitosQuadro", "AddCircuito", "MontarCircuitos", "ComponentesQuadro", "GerarUnifilar"]
CALC_TOOLS = ["CalcDemanda", "CalcPressurizacao", "CalcRecalque"]
DOCUMENT_TOOLS = [
    "GerarQuantitativos",
    "LegendaSimbolos",
    "PlanilhaNotas",
    "GerarNotas",
    "PintarSketches",
    "GenerateReport",
]
MODEL_3D_TOOLS = ["Generate3DSwitches", "Generate3DConduits", "Gerar3D"]
LIBRARY_TOOLS = ["InsertEquipaments", "InsertComponent", "CreateModel", "ListElements"]

# Só no menu: comandos antigos, incompletos ou de uso raro.
EXTRA_TOOLS = [
    "InsertTugs",
    "InsertOutlet",
    "InsertLighting",
    "ComponentEletric",
    "InsertWire",
    "AddSpreadsheet",
    "NewQuadro",
    "GetSpaces",
    "ReiniciarBancada",
]

# Botões com lista suspensa: ID do grupo -> (legenda, dica, comandos).
# O botão mostra o ícone do último comando usado; a seta abre os demais.
GROUPS = {
    "Grupo_Projeto": ("Projeto", "Novo projeto, pavimentos, planilha de circuitos e importação do QElectroTech", PROJECT_TOOLS),
    "Grupo_Tomadas": ("Tomadas", "Tomadas baixa, média, alta e de piso", OUTLET_TOOLS),
    "Grupo_Energia": ("Energia", "Chuveiro, ar-condicionado, ventilador, ponto de força e campainha", POWER_TOOLS),
    "Grupo_Iluminacao": ("Iluminação", "Luz de teto, arandela, tubular, embutida, de emergência e o luminotécnico", LIGHTING_TOOLS),
    "Grupo_Interruptores": (
        "Comandos", "Interruptor simples, paralelo e intermediário, botão de campainha e fotocélula", SWITCH_TOOLS
    ),
    "Grupo_Aterramento": (
        "Aterramento", "Haste, caixa de inspeção, BEP, condutor de cobre nu e resistência de aterramento",
        GROUNDING_TOOLS,
    ),
    "Grupo_Quadros": ("Quadros", "Quadro de distribuição, de comando, de medição e medição agrupada, na planta", BOARD_SYMBOL_TOOLS),
    "Grupo_DadosQuadro": ("Dados do quadro", "Planilha de dados do quadro, planilha de circuitos e circuito digitado em formulário", BOARD_DATA_TOOLS),
    "Grupo_Circuitos": ("Circuitos", "Definir o circuito dos pontos, ligar interruptores e identificar na planta", CIRCUIT_TOOLS),
    "Grupo_Infra": (
        "Infraestrutura",
        "Eletroduto, caixa de passagem, conexão às caixas, divisão de trecho, verticais, fiação, "
        "bandejas e leitos com conexões e suportes",
        INFRA_TOOLS,
    ),
    "Grupo_Calculos": ("Cálculos", "Demanda do quadro, pressurização de escada e bomba de recalque", CALC_TOOLS),
    "Grupo_Documentos": ("Documentos", "Quantitativos, legenda de símbolos, notas, Sketches em preto e relatório em PDF", DOCUMENT_TOOLS),
    "Grupo_3D": ("Modelo 3D", "Caixas, eletrodutos e tomadas em 3D, gerados a partir da planta", MODEL_3D_TOOLS),
    "Grupo_Biblioteca": ("Biblioteca", "Equipamentos e componentes da biblioteca; criar e importar modelos", LIBRARY_TOOLS),
}

_tr = QtCore.QT_TRANSLATE_NOOP
ELECTRIC_TOOLBARS = [
    (
        _tr("Workbench", "Planta elétrica"),
        [
            "Grupo_Projeto",
            "Grupo_Tomadas",
            "Grupo_Energia",
            "Grupo_Iluminacao",
            "Grupo_Interruptores",
            "Grupo_Circuitos",
            "Grupo_Infra",
            "Grupo_Aterramento",
        ],
    ),
    (
        _tr("Workbench", "Quadros e documentos"),
        [
            "Grupo_Quadros",
            "Grupo_DadosQuadro",
            "MontarCircuitos",
            "ComponentesQuadro",
            "GerarUnifilar",
            "Grupo_Calculos",
            "Grupo_Documentos",
        ],
    ),
    (_tr("Workbench", "Modelo e biblioteca"), ["Grupo_3D", "Grupo_Biblioteca"]),
]
TOOLBARS = ELECTRIC_TOOLBARS + [
    (_tr("Workbench", "Desenho"), DRAWING_TOOLS),
    (_tr("Workbench", "Modificador"), MODIFY_TOOLS),
    (_tr("Workbench", "Snap"), SNAP_TOOLS),
    (_tr("Workbench", "Arquitetura"), BIM_TOOLS),
]
MENU = "&Elétrica"
MENU_DESENHO = "&Desenho 2D"
MENUS = [
    ([MENU, "Projeto"], PROJECT_TOOLS),
    ([MENU, "Tomadas"], OUTLET_TOOLS),
    ([MENU, "Pontos de energia"], POWER_TOOLS),
    ([MENU, "Iluminação"], LIGHTING_TOOLS),
    ([MENU, "Comandos e campainha"], SWITCH_TOOLS),
    ([MENU, "Aterramento"], GROUNDING_TOOLS),
    ([MENU, "Quadros e medição"], BOARD_SYMBOL_TOOLS),
    ([MENU, "Circuitos e comandos"], CIRCUIT_TOOLS),
    ([MENU, "Alinhar e escalar símbolos"], ALIGN_TOOLS),
    ([MENU, "Eletrodutos, bandejas e fiação"], INFRA_TOOLS),
    ([MENU, "Quadros e diagramas"], BOARD_TOOLS),
    ([MENU, "Cálculos prediais"], CALC_TOOLS),
    ([MENU, "Documentos"], DOCUMENT_TOOLS),
    ([MENU, "Modelo 3D"], MODEL_3D_TOOLS),
    ([MENU, "Biblioteca"], LIBRARY_TOOLS),
    ([MENU, "Outros"], EXTRA_TOOLS),
    ([MENU_DESENHO, "Desenhar e anotar"], DRAWING_TOOLS + DRAWING_EXTRA_TOOLS),
    ([MENU_DESENHO, "Modificar"], MODIFY_TOOLS + MODIFY_EXTRA_TOOLS),
    ([MENU_DESENHO, "Snap"], SNAP_TOOLS + SNAP_EXTRA_TOOLS),
    ([MENU_DESENHO, "Arquitetura"], BIM_TOOLS + BIM_EXTRA_TOOLS),
]

# Barras que mostram a legenda (texto) embaixo de cada ícone.
BARRAS_COM_LEGENDA = [label for label, _ in ELECTRIC_TOOLBARS]
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
            alinhar,
            aterramento,
            bandejas,
            identificacao,
            pavimentos,
            rede,
            calculos,
            generate_3d,
            gerar_unifilar,
            import_QEletrotech,
            insert_component,
            new_project,
            pontos,
            projeto_eletrico,
            projeto_quadro,
            reports,
            tools,
        )

        # Os grupos só podem ser registrados depois dos comandos que eles reúnem.
        from .commands import grupos

        grupos.registrar(GROUPS)

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
