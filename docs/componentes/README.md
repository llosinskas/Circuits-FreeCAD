> **Nota:** guia escrito antes da reorganização; caminhos e imports podem estar desatualizados. A estrutura atual está em [AGENTS.md](../../AGENTS.md).

# Guia de Uso: Sistema de Seleção e Inserção de Componentes

## Visão Geral

O sistema de componentes oferece classes reutilizáveis para:
- ✅ Listar arquivos de uma pasta específica
- ✅ Mostrar prévia (thumbnail) dos componentes
- ✅ Permitir seleção do usuário
- ✅ Inserir o componente no documento FreeCAD
- ✅ Executar callbacks personalizados após inserção

Totalmente extensível para outras funcionalidades (cálculos, relatórios, etc.).

---

## Classes Principais

### 1. ComponentSelectorDialog

**Propósito**: Diálogo reutilizável para seleção de componentes com preview.

**Características**:
- Lista arquivos `.FCStd` de uma pasta
- Extrai e mostra thumbnails automáticamente
- Busca/filtro em tempo real
- Emite signal quando componente é selecionado
- Retorna o caminho do arquivo selecionado

**Uso Básico**:

```python
from UI.dialogs import ComponentSelectorDialog

def my_select_component():
    folder = "Componentes/Eletrica"
    dialog = ComponentSelectorDialog(
        components_path=folder,
        title="Selecionar Componente",
        parent=my_parent_widget
    )
    
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        filepath = dialog.get_selected_component()
        print(f"Selecionado: {filepath}")
```

**Sinais (Signals)**:

```python
dialog = ComponentSelectorDialog(folder)
dialog.component_selected.connect(my_callback)  # Emitido ao selecionar
dialog.exec_()

def my_callback(filepath: str):
    print(f"Componente selecionado: {filepath}")
```

---

### 2. ComponentInserter

**Propósito**: Gerenciar todo o fluxo de seleção e inserção de componentes.

**Características**:
- Valida documento FreeCAD ativo
- Abre diálogo de seleção
- Carrega componente em documento temporário
- Copia para documento ativo
- Executa callbacks personalizados

**Uso Básico**:

```python
from UI.dialogs import ComponentInserter

def my_insert_function():
    folder = "Componentes/Eletrica"
    inserter = ComponentInserter(
        components_folder=folder,
        on_component_loaded=print_component_name
    )
    
    success = inserter.insert_component()
    if success:
        print("Componente inserido com sucesso!")

def print_component_name(filepath: str, freecad_obj):
    print(f"Arquivo: {filepath}")
    print(f"Nome do objeto: {freecad_obj.Label}")
```

**Inserir múltiplos componentes**:

```python
inserter = ComponentInserter(folder)
filepaths = [
    "Componentes/Eletrica/Tomada.FCStd",
    "Componentes/Eletrica/Lampada.FCStd"
]
count = inserter.insert_multiple_components(filepaths)
print(f"{count} componentes inseridos")
```

---

## Exemplos de Reutilização

### Exemplo 1: Criar Função para Seleção de Cabos

```python
"""
Exemplo: Função para seleção de cabos para cálculo de bitola
"""

from UI.dialogs import ComponentSelectorDialog
from core.functions.Cabo import Cabo

def select_cable_for_calculation():
    """Abre diálogo para seleção de cabo para cálculo."""
    
    # Seleciona o arquivo do cabo
    folder = "Componentes/Cabos"  # Pasta futura com cabos
    dialog = ComponentSelectorDialog(
        components_path=folder,
        title="Selecionar Cabo para Cálculo",
        parent=my_gui_parent
    )
    
    def on_cable_selected(filepath: str):
        # Carrega propriedades do cabo
        cable = Cabo.from_fcstd(filepath)
        
        # Abre diálogo de cálculo
        calculate_cable_section(cable)
    
    dialog.component_selected.connect(on_cable_selected)
    dialog.exec_()
```

### Exemplo 2: Integração com Sistema de Cálculo

```python
"""
Exemplo: Usar selecionador junto com cálculo de corrente
"""

from UI.dialogs import ComponentInserter
from core.functions.Cabo.Correntes import calcular_corrente_monofasica

class CableCalculationWorkflow:
    def __init__(self):
        self.selected_cable = None
        self.calculated_current = None
    
    def step1_select_cable(self):
        """Step 1: Seleciona o cabo do armazém de componentes."""
        inserter = ComponentInserter(
            components_folder="Componentes/Cabos",
            on_component_loaded=self.on_cable_loaded,
            parent=self.gui_parent
        )
        return inserter.insert_component()
    
    def on_cable_loaded(self, filepath: str, cable_obj):
        """Callback: Cabo foi carregado."""
        self.selected_cable = cable_obj
        print(f"Cabo selecionado: {cable_obj.Label}")
        # Passa para próximo passo automaticamente
        self.step2_calculate()
    
    def step2_calculate(self):
        """Step 2: Calcula a corrente do cabo."""
        if not self.selected_cable:
            return
        
        # Exemplo de cálculo
        current = calcular_corrente_monofasica(
            potencia=10000,  # W
            tensao=220,      # V
            fator_potencia=0.92
        )
        self.calculated_current = current
        print(f"Corrente calculada: {current:.2f} A")
        
        # Passa para próximo step
        self.step3_show_results()
    
    def step3_show_results(self):
        """Step 3: Mostra resultados."""
        print(f"Cabo: {self.selected_cable.Label}")
        print(f"Corrente: {self.calculated_current:.2f} A")
```

### Exemplo 3: Criador de Painel Customizado

```python
"""
Exemplo: Função para criar categoria customizada de seleção
"""

def select_from_custom_category(category: str):
    """Abre selecionador para categoria customizada."""
    
    # Mapeia categorias para pastas
    categories = {
        "tomadas": "Componentes/Eletrica/Tomadas",
        "lampadas": "Componentes/Eletrica/Lampadas",
        "disjuntores": "Componentes/Protecao/Disjuntores",
        "cabos": "Componentes/Cabos/Tipos"
    }
    
    if category not in categories:
        raise ValueError(f"Categoria inválida: {category}")
    
    folder = categories[category]
    dialog = ComponentSelectorDialog(
        components_path=folder,
        title=f"Selecionar {category.title()}",
    )
    
    return dialog.exec_(), dialog.get_selected_component()
```

---

## Estendendo para Outras Funcionalidades

### Passo 1: Criar uma classe base para seu domínio

```python
"""
Exemplo: ComponentSelector para cálculos de cabo
"""

from UI.dialogs import ComponentSelectorDialog

class CableComponentSelector(ComponentSelectorDialog):
    """Selecionador especializado para cabos."""
    
    def __init__(self, parent=None):
        super().__init__(
            components_path="Componentes/Cabos",
            title="Selecionador de Cabos",
            parent=parent
        )
    
    def load_cable_properties(self):
        """Load propriedades do cabo após seleção."""
        filepath = self.get_selected_component()
        if not filepath:
            return None
        
        # Seu código para carregar propriedades
        from pathlib import Path
        return {
            "name": Path(filepath).stem,
            "filepath": filepath
        }
```

### Passo 2: Usar em sua funcionalidade

```python
def calculate_with_selected_cable():
    """Fluxo: Seleciona cabo → Calcula → Mostra resultado."""
    
    selector = CableComponentSelector(parent=my_gui)
    
    if selector.exec_() == QtWidgets.QDialog.Accepted:
        props = selector.load_cable_properties()
        
        # Execute cálculo
        from core.functions.Cabo import calcular_secao_minima
        
        secao = calcular_secao_minima(
            comprimento=50,  # metros
            corrente=30,     # amperes
            queda_tensao_percentual=3  # %
        )
        
        print(f"Seção mínima do cabo: {secao} mm²")
```

---

## Boas Práticas

### ✅ DO's (Recomendado)

1. **Reutilizar ComponentSelectorDialog**
   ```python
   # Bom: Pode usar em múltiplos contextos
   dialog = ComponentSelectorDialog(folder, parent=self)
   ```

2. **Usar callbacks com ComponentInserter**
   ```python
   # Bom: Executa lógica após inserção
   inserter.on_component_loaded = minha_logica
   ```

3. **Validar documento ativo**
   ```python
   # Bom: Verifica antes de usar
   if not App.activeDocument():
       # Tratamento de erro
   ```

4. **Usar signals para reatividade**
   ```python
   # Bom: UI responde imediatamente
   dialog.component_selected.connect(update_ui)
   ```

### ❌ DON'Ts (Evitar)

1. **Não criar múltiplas instâncias**
   ```python
   # Ruim: Cria muitas instâncias
   for i in range(10):
       components_layout.addWidget(ComponentSelectorDialog(folder))
   ```

2. **Não ignorar erros**
   ```python
   # Ruim: Sem tratamento
   dialog.exec_()
   filepath = dialog.get_selected_component()  # Pode ser None!
   ```

3. **Não hardcodificar caminhos**
   ```python
   # Ruim: Não é portável
   folder = "C:\\Users\\lucas\\...\\Componentes"
   
   # Bom: Relativo ao arquivo
   from pathlib import Path
   base = Path(__file__).parent.parent
   folder = base / "Componentes"
   ```

---

## Estrutura de Pastas Recomendada

```
Componentes/
├── Eletrica/              # Componentes elétricos
│   ├── Tomadas/
│   │   ├── Tomada.FCStd
│   │   └── TomadaEspecial.FCStd
│   ├── Lampadas/
│   │   ├── Lampada.FCStd
│   │   └── LampadaLED.FCStd
│   └── Equipamentos/
├── Cabos/                 # Seção para cabos (futuro)
│   ├── PVC_Cobre.FCStd
│   └── Blindado.FCStd
├── Protecao/              # Disjuntores, fusíveis (futuro)
└── Infraestrutura/        # Eletrodutos, canaletas (futuro)
    ├── Eletrodutos/
    └── Eletrocalhas/
```

---

## Troubleshooting

### Problema: "Nenhum thumbnail carregado"
```python
# Solução: Verifique se o arquivo FCStd é válido
# e tem a imagem de thumbnail armazenada
import zipfile
with zipfile.ZipFile("arquivo.FCStd") as z:
    print(z.namelist())  # Procura por "Thumbnails/Thumbnail.png"
```

### Problema: "Pasta não encontrada"
```python
# Solução: Use Path relativo ao arquivo
from pathlib import Path
base = Path(__file__).parent.parent
folder = str(base / "Componentes" / "Eletrica")
```

### Problema: "Componente não inserido corretamente"
```python
# Solução: Verifique o callback on_component_loaded
def debug_callback(filepath: str, obj):
    print(f"Filepath: {filepath}")
    print(f"Object Label: {obj.Label}")
    print(f"Object Type: {obj.TypeId}")
```

---

## API Completa

### ComponentSelectorDialog

```python
class ComponentSelectorDialog(QtWidgets.QDialog):
    component_selected: QtCore.Signal(str)  # filepath
    
    def __init__(
        self,
        components_path: str,
        title: str = "Selecionador de Componentes",
        parent=None
    )
    
    def load_components(self) -> None
    def on_component_selected(self, filepath: str) -> None
    def on_search_text_changed(self, text: str) -> None
    def get_selected_component(self) -> Optional[str]
```

### ComponentInserter

```python
class ComponentInserter:
    def __init__(
        self,
        components_folder: str,
        on_component_loaded: Optional[Callable[[str, Any], None]] = None,
        parent: Optional[QtWidgets.QWidget] = None
    )
    
    def insert_component(self) -> bool
    def load_and_insert_component(self, filepath: str) -> bool
    def insert_component_with_placement(self, filepath: str) -> bool
    def insert_multiple_components(self, filepaths: list) -> int
```

---

## Próximos Passos

Para expandir o sistema:

1. **Adicionar suporte a múltiplas pastas**
   - ComponentSelectorDialog aceita lista de pastas
   - Mostra todas em abas

2. **Implementar modo de posicionamento com mouse**
   - Usar eventos do FreeCADGui
   - Função `insert_component_with_placement()`

3. **Criar componentes filtrados por tipo**
   - Ler propriedades de metadados do arquivo
   - Filtrar antes de mostrar

4. **Integrar com sistema de cálculos**
   - Preencher automaticamente dados do componente
   - Validar antes de cálculo

---

*Documentação atualizada em 2026-04-08*
