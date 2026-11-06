> **Nota:** guia escrito antes da reorganização; caminhos e imports podem estar desatualizados. A estrutura atual está em [AGENTS.md](../AGENTS.md).

# 🧪 Guia Completo de Testes Unitários - eletroAlpha

## Índice
1. [Setup Inicial](#setup-inicial)
2. [Estrutura de Testes](#estrutura-de-testes)
3. [Mockando FreeCAD](#mockando-freecad)
4. [Exemplos Práticos](#exemplos-práticos)
5. [Executando Testes](#executando-testes)
6. [Cobertura de Testes](#cobertura-de-testes)
7. [Boas Práticas](#boas-práticas)

---

## Setup Inicial

### 1. Instalar Dependências

```bash
pip install pytest pytest-cov pytest-mock unittest-xml-reporting
```

**O que cada um faz:**
- `pytest`: Framework de testes
- `pytest-cov`: Cobertura de código
- `pytest-mock`: Mocking simplificado
- `unittest-xml-reporting`: Relatórios em XML

### 2. Criar Arquivo `pytest.ini`

**Arquivo**: `pytest.ini` (na raiz do projeto)

```ini
[pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --tb=short
    --disable-warnings

markers =
    unit: testes unitários
    integration: testes de integração
    slow: testes lentos
    freecad: requerem FreeCAD em execução
```

### 3. Criar Arquivo `tests/conftest.py`

**Arquivo**: `tests/conftest.py` (configuração global dos testes)

```python
import sys
import os
import pytest
from unittest.mock import Mock, MagicMock

# Adiciona raiz do projeto ao path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

# ======================================
# MOCKS DO FREECAD
# ======================================

class MockFreeCADApp:
    """Mock para FreeCAD.App"""
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

# ======================================
# FIXTURES (Utilities para testes)
# ======================================

@pytest.fixture
def mock_freecad(monkeypatch):
    """Injeta mocks de FreeCAD em todos os testes"""
    sys.modules['FreeCAD'] = MagicMock()
    sys.modules['FreeCADGui'] = MagicMock()
    sys.modules['Spreadsheet'] = MagicMock()
    
    # Configurar atributos específicos
    sys.modules['FreeCAD'].App = MockFreeCADApp
    sys.modules['FreeCAD'].Console = MagicMock()
    sys.modules['FreeCADGui'].Workbench = type('Workbench', (), {})
    
    return sys.modules['FreeCAD']

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
```

---

## Estrutura de Testes

### Organização de Pastas

```
tests/
├── conftest.py                    # Configuração global
├── unit/                          # Testes unitários
│   ├── test_models/
│   │   ├── test_circuit_model.py
│   │   ├── test_component_model.py
│   │   └── __init__.py
│   ├── test_services/
│   │   ├── test_circuit_service.py
│   │   └── __init__.py
│   └── __init__.py
│
├── integration/                   # Testes de integração
│   ├── test_freecad_integration.py
│   ├── test_database_integration.py
│   └── __init__.py
│
└── fixtures/                      # Dados de teste reutilizáveis
    ├── sample_projects.py
    └── sample_circuits.py
```

---

## Mockando FreeCAD

O desafio principal é que FreeCAD é um grande framework. A solução é **desacoplar** seu código dele.

### ✅ BOA PRÁTICA: Abstrair FreeCAD

**Arquivo**: `adapters/freecad_adapter.py`

```python
class DocumentAdapter:
    """Abstração para nunca usar FreeCAD diretamente"""
    
    def __init__(self, doc=None):
        # Importar aqui evita erro se FreeCAD não estiver disponível
        try:
            import FreeCAD as App
            self.doc = doc or App.activeDocument()
        except ImportError:
            self.doc = None  # Para testes
    
    def add_group(self, name: str):
        if self.doc is None:
            return MockDocumentAdapter.add_group(name)
        return self.doc.addObject("App::DocumentObjectGroup", name)
    
    def save(self, path: str) -> bool:
        if self.doc is None:
            return True  # Teste
        self.doc.saveAs(path)
        return True
```

**Benefício**: Seu código de negócio **não importa FreeCAD**, então testes são fáceis!

---

## Exemplos Práticos

### Exemplo 1: Teste de Modelo (CircuitDTO)

**Arquivo**: `tests/unit/test_models/test_circuit_model.py`

```python
import pytest
from models.circuit_model import CircuitDTO

class TestCircuitDTO:
    """Testes para o modelo de Circuito"""
    
    @pytest.mark.unit
    def test_circuit_creation_valid(self, sample_circuit_data):
        """Criar um circuito com dados válidos"""
        circuit = CircuitDTO(**sample_circuit_data)
        
        assert circuit.origin == "Q1"
        assert circuit.power_kw == 5.0
        assert circuit.voltage_v == 220
    
    @pytest.mark.unit
    def test_circuit_power_positive(self):
        """Potência deve ser positiva"""
        with pytest.raises(ValueError):
            CircuitDTO(
                origin="Q1", destiny="L1",
                power_kw=-5.0,  # ❌ Inválido
                voltage_v=220,
                power_factor=0.95,
                cable_section_mm2=4.0,
                breaker_current_a=20.0
            )
    
    @pytest.mark.unit
    def test_circuit_voltage_minimum(self):
        """Tensão mínima deve ser 127V"""
        with pytest.raises(ValueError):
            CircuitDTO(
                origin="Q1", destiny="L1",
                power_kw=5.0,
                voltage_v=100,  # ❌ Abaixo de 127V
                power_factor=0.95,
                cable_section_mm2=4.0,
                breaker_current_a=20.0
            )
    
    @pytest.mark.unit
    def test_circuit_power_factor_warning(self):
        """Fator de potência abaixo de 0.8 gera aviso"""
        with pytest.raises(ValueError, match="0.8"):
            CircuitDTO(
                origin="Q1", destiny="L1",
                power_kw=5.0,
                voltage_v=220,
                power_factor=0.75,  # ⚠️ Abaixo de 0.8
                cable_section_mm2=4.0,
                breaker_current_a=20.0
            )
    
    @pytest.mark.unit
    def test_circuit_origin_required(self):
        """Origin não pode estar vazio"""
        with pytest.raises(ValueError):
            CircuitDTO(
                origin="",  # ❌ Vazio
                destiny="L1",
                power_kw=5.0,
                voltage_v=220,
                power_factor=0.95,
                cable_section_mm2=4.0,
                breaker_current_a=20.0
            )
```

### Exemplo 2: Teste de Serviço (Cálculos)

**Arquivo**: `tests/unit/test_services/test_demand_calculator.py`

```python
import pytest
from core.functions.Demanda import DemandaCalculator

class TestDemandaCalculator:
    """Testes para cálculos de demanda NBR5410"""
    
    @pytest.fixture
    def calculator(self):
        return DemandaCalculator()
    
    @pytest.mark.unit
    def test_metodo_cv_basic(self, calculator):
        """Método da Curva de Vigência - cálculo básico"""
        potencias = [10.0, 15.0, 20.0]  # kW
        resultado = calculator.metodo_cv(potencias, simultaneidade=0.8)
        
        # 10 + 15 + 20 = 45, 45 * 0.8 = 36
        assert resultado == pytest.approx(36.0, rel=0.01)
    
    @pytest.mark.unit
    def test_metodo_cv_sem_simultaneidade(self, calculator):
        """Sem fator de simultaneidade"""
        potencias = [10.0, 15.0]
        resultado = calculator.metodo_cv(potencias, simultaneidade=1.0)
        
        assert resultado == pytest.approx(25.0)
    
    @pytest.mark.unit
    def test_metodo_cv_lista_vazia(self, calculator):
        """Lista vazia retorna zero"""
        potencias = []
        resultado = calculator.metodo_cv(potencias)
        
        assert resultado == 0.0
    
    @pytest.mark.unit
    def test_metodo_cv_entrada_invalida(self, calculator):
        """Valores negativos causam erro"""
        potencias = [10.0, -5.0]  # ❌ Negativo
        
        with pytest.raises(ValueError):
            calculator.metodo_cv(potencias)
```

### Exemplo 3: Teste com Mock

**Arquivo**: `tests/unit/test_services/test_circuit_service.py`

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.circuit_service import CircuitService

class TestCircuitService:
    """Testes para serviço de circuitos"""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock do repositório de circuitos"""
        repo = Mock()
        repo.save = Mock(return_value=True)
        repo.load = Mock()
        return repo
    
    @pytest.fixture
    def service(self, mock_repository):
        return CircuitService(repository=mock_repository)
    
    @pytest.mark.unit
    def test_add_circuit_calls_repository(self, service, mock_repository, sample_circuit_data):
        """Adicionar circuito chama o repositório"""
        from models.circuit_model import CircuitDTO
        
        circuit = CircuitDTO(**sample_circuit_data)
        service.add_circuit(circuit)
        
        # Verificar que save foi chamado
        mock_repository.save.assert_called_once_with(circuit)
    
    @pytest.mark.unit
    def test_get_circuit_by_id(self, service, mock_repository, sample_circuit_data):
        """Obter circuito por ID"""
        from models.circuit_model import CircuitDTO
        
        circuit = CircuitDTO(**sample_circuit_data)
        mock_repository.load.return_value = circuit
        
        result = service.get_circuit("Q1_L1")
        
        mock_repository.load.assert_called_once_with("Q1_L1")
        assert result.origin == "Q1"
    
    @pytest.mark.unit
    def test_add_circuit_validation_fails(self, service):
        """Validação falha com dados inválidos"""
        invalid_circuit = {"origin": "", "power_kw": -5.0}
        
        with pytest.raises(ValueError):
            service.add_circuit(invalid_circuit)
```

### Exemplo 4: Teste de Integração com FreeCAD

**Arquivo**: `tests/integration/test_freecad_integration.py`

```python
import pytest

@pytest.mark.integration
@pytest.mark.freecad  # Requer FreeCAD rodando
class TestFreeCADIntegration:
    """Testes que requerem FreeCAD ativo"""
    
    def test_create_document_and_group(self, mock_freecad):
        """Criar documento e adicionar grupo"""
        import FreeCAD as App  # Usando mock
        
        doc = App.App.newDocument("TestProject")
        group = doc.addObject("App::DocumentObjectGroup", "Circuitos")
        
        assert doc.name == "TestProject"
        assert len(doc.Objects) == 1
        assert group is not None
    
    def test_document_recompute(self, freecad_document):
        """Recomputar documento"""
        freecad_document.recompute()
        
        assert freecad_document.recompute_called == True
```

---

## Executando Testes

### 1. Rodar Todos os Testes

```bash
pytest
```

**Output esperado:**
```
tests/unit/test_models/test_circuit_model.py::TestCircuitDTO::test_circuit_creation_valid PASSED
tests/unit/test_models/test_circuit_model.py::TestCircuitDTO::test_circuit_power_positive PASSED
...
======================== 12 passed in 0.45s ========================
```

### 2. Rodar Apenas Testes Unitários

```bash
pytest -m unit
```

### 3. Rodar Apenas Integração

```bash
pytest -m integration
```

### 4. Rodar Um Arquivo Específico

```bash
pytest tests/unit/test_models/test_circuit_model.py
```

### 5. Rodar Um Teste Específico

```bash
pytest tests/unit/test_models/test_circuit_model.py::TestCircuitDTO::test_circuit_power_positive
```

### 6. Rodar com Verbosidade Extra

```bash
pytest -vv
```

### 7. Pararar no Primeiro Erro

```bash
pytest -x
```

### 8. Rodar 3 Testes em Paralelo (mais rápido)

```bash
pip install pytest-xdist
pytest -n 3
```

---

## Cobertura de Testes

### Verificar Cobertura

```bash
pytest --cov=core --cov=models --cov=services --cov-report=html
```

Isso gera um relatório em `htmlcov/index.html`

### Checar Linhas Não Cobertas

```bash
pytest --cov=core --cov-report=term-missing
```

**Output:**
```
models/circuit_model.py     25      0   100%
core/functions/Demanda.py   45      5    89%  42-46
```

### Meta de Cobertura (>80%)

```bash
pytest --cov=core --cov-report=term --cov-fail-under=80
```

---

## Boas Práticas

### ✅ 1. Nome Descritivo

```python
# ❌ Ruim
def test_circuit():
    pass

# ✅ Bom
def test_circuit_creation_with_valid_power_values():
    pass
```

### ✅ 2. Arrange-Act-Assert (AAA)

```python
def test_demand_calculation():
    # ARRANGE: Preparar dados
    calculator = DemandaCalculator()
    potencias = [10.0, 15.0, 20.0]
    
    # ACT: Executar ação
    result = calculator.metodo_cv(potencias, simultaneidade=0.8)
    
    # ASSERT: Verificar resultado
    assert result == pytest.approx(36.0)
```

### ✅ 3. Testar Uma Coisa Por Vez

```python
# ❌ Ruim: testando múltiplas coisas
def test_circuit():
    circuit = CircuitDTO(...)
    assert circuit.power_kw > 0
    assert circuit.voltage_v >= 127
    assert circuit.origin != ""

# ✅ Bom: um assert por teste
def test_circuit_power_must_be_positive():
    circuit = CircuitDTO(...)
    assert circuit.power_kw > 0

def test_circuit_voltage_minimum():
    circuit = CircuitDTO(...)
    assert circuit.voltage_v >= 127
```

### ✅ 4. Usar Fixtures para Reutilização

```python
@pytest.fixture
def sample_circuit(sample_circuit_data):
    return CircuitDTO(**sample_circuit_data)

def test_circuit_1(sample_circuit):
    assert sample_circuit.origin == "Q1"

def test_circuit_2(sample_circuit):
    assert sample_circuit.power_kw == 5.0
```

### ✅ 5. Testar Exceções Corretamente

```python
# ✅ Bom
def test_invalid_power():
    with pytest.raises(ValueError, match="deve ser positiva"):
        CircuitDTO(power_kw=-5.0, ...)
```

### ✅ 6. Usar Mocks Para Dependências Externas

```python
def test_save_circuit(mocker, service):
    # Mock da dependência externa
    mock_db = mocker.patch('services.circuit_service.database')
    mock_db.save.return_value = True
    
    result = service.save_circuit(circuit_data)
    
    assert result == True
    mock_db.save.assert_called_once()
```

### ✅ 7. Testar Casos Extremos (Edge Cases)

```python
def test_demand_with_zero_load():
    """Carga zero"""
    result = calculator.metodo_cv([0.0])
    assert result == 0.0

def test_demand_with_very_large_load():
    """Carga muito grande"""
    result = calculator.metodo_cv([10000.0])
    assert result > 0
```

---

## Exemplo Completo: Setup Rápido

### 1. Instalar

```bash
pip install pytest pytest-cov pytest-mock
```

### 2. Criar Estrutura

```bash
mkdir -p tests/unit tests/integration
touch tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py
touch tests/conftest.py
```

### 3. Criar `tests/conftest.py`

Usar o código do início deste guia (seção Setup Inicial)

### 4. Criar Primeiro Teste

**Arquivo**: `tests/unit/test_models/test_circuit_model.py`

```python
import pytest
from models.circuit_model import CircuitDTO

def test_circuit_valid():
    circuit = CircuitDTO(
        origin="Q1", destiny="L1",
        power_kw=5.0, voltage_v=220,
        power_factor=0.95, cable_section_mm2=4.0,
        breaker_current_a=20.0
    )
    assert circuit.origin == "Q1"
```

### 5. Rodar

```bash
pytest -v
```

---

## Próximos Passos

1. ✅ Implementar `adapters/` para desacoplar FreeCAD
2. ✅ Criar `conftest.py` com mocks
3. ✅ Escrever testes para `models/`
4. ✅ Escrever testes para `core/functions/`
5. ✅ Atingir >80% cobertura
6. ✅ Integrar CI/CD (GitHub Actions, GitLab CI)

---

**Dúvidas?** Consulte a [documentação oficial do pytest](https://docs.pytest.org/)
