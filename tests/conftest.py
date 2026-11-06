import sys 
import os 
import pytest
from unittest.mock import Mock, MagicMock

# Adiciona a raiz do projeto ao path 
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,REPO_ROOT)

#==============================
# MOCKS DO FREECAD
#==============================
class MockFreeCADApp:
    """Mock para FreeCAD.APP"""
    class Document:
        def __init__(self, name="TestDoc"):
            self.name = name
            self.Objects = []
            self.recompute_called = False
            
        def addObject(self, obj_type, name):
            obj = MagicMock()
            obj.Proxy = None
            self.Objects.append(obj)
            return obj
        
        def getObject(self, label):
            for obj in self.Objects:
                if obj.Label == label:
                    return obj 
                return None
        def recompute(self):
            self.recompute_called = True
        def saveAs(self, path):
            return True
        
    @staticmethod
    def activeDocument():
        return MockFreeCADApp.Document()
    
    @staticmethod
    def newDocument(name="NewDoc"):
        return MockFreeCADApp.Document(name)
    

class MockFreeCADGui:
    """Mock para FreeCADGui"""
    
    @staticmethod
    def addCommand(cmd_id, command):
        pass
    
    @staticmethod
    def activateWorkbench(name):
        pass
    
    @staticmethod
    def removeWorkbench(name):
        pass

    @staticmethod
    def updateGui():
        pass

#===========================================================
# FIXTURES (Utilities para testes)
#===========================================================

@pytest.fixture
def mock_freecad():
    """Injeta mocks de FreeCAD em todos os testes"""
    sys.modules["FreeCAD"]      = MagicMock()
    sys.modules["FreeCADGui"]   = MagicMock()
    sys.modules["Spreadsheet"]  = MagicMock()

    # Configurar os atributos específicos
    sys.modules["FreeCAD"].App          = MockFreeCADApp
    sys.modules["FreeCAD"].Console      = MagicMock()
    sys.modules["FreeCADGui"].Workbench = type("Workbench", (), {})
    return sys.modules["FreeCAD"]

@pytest.fixture
def freecad_document(mock_freecad):
    """Fornece um documento FreeCAD mock para testes"""
    return MockFreeCADApp.activeDocument()

@pytest.fixture
def sample_circuit_data():
    """Dados de exemplo para testes de circuitos"""
    return {
        "origin": "Q1",
        "destiny": "L1",
        "power_kw": 5.0,
        "voltage_v": 220,
        "power_factor": 0.95,
        "cable_section_mm2": 4.0,
        "breaker_current_a": 20.0
    }

@pytest.fixture
def sample_project_data():
    """Dados de exemplo para testes de projetos"""
    return {
        "name": "Projeto_Teste",
        "location": "São Paulo, SP",
        "type": "residencial",
        "voltage": 220
    }
