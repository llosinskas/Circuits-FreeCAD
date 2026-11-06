"""Metadados e caminhos da bancada Circuits.

Este módulo não pode importar FreeCAD nem Qt: ele é carregado também pelos
testes que rodam fora do FreeCAD.
"""
import os

try:
    from .version import __version__
except ImportError:
    __version__ = "0.0.1"

__dir__ = os.path.dirname(os.path.abspath(__file__))

ICON_PATH = os.path.join(__dir__, "Resources", "Icons")
DATA_PATH = os.path.join(__dir__, "Resources", "data")
UI_PATH = os.path.join(__dir__, "Resources", "UI")
TRANSLATIONS_PATH = os.path.join(__dir__, "Resources", "translations")

# NÃO MOVER: projetos salvos guardam App::Link apontando para esta pasta.
LIBRARY_PATH = os.path.join(__dir__, "Componentes")
ELECTRIC_LIBRARY_PATH = os.path.join(LIBRARY_PATH, "Eletrica")

__title__ = "Engenharia"
__author__ = "Lucas Losinskas"
__url__ = "https://github.com/llosinskas/Circuits-FreeCAD"
__ToolTip__ = "Bancada para a criação e gerenciamento de projetos elétricos: Residênciais, Indústriais e Comerciais"
