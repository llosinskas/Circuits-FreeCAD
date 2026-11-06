> **Nota:** guia escrito antes da reorganização; caminhos e imports podem estar desatualizados. A estrutura atual está em [AGENTS.md](../../AGENTS.md).

# Arquitetura do Sistema de Componentes

## Diagrama do Fluxo de Trabalho

```
┌─────────────────────────────────────────────────────────────────┐
│                    USUÁRIO NA INTERFACE                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│            Clica no Botão (ex: "Inserir Tomada")                │
│                                                                 │
│  Exemplo: InsertComponent, Tugs, Equipaments, etc.             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│         ComponentInserter.insert_component()                    │
│                                                                 │
│  • Valida documento FreeCAD ativo                              │
│  • Obtém caminho da pasta de componentes                       │
│  • Cria instância de ComponentSelectorDialog                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│       DIALOG: ComponentSelectorDialog()                         │
│                                                                 │
│  ╔════════════════════════════════════════════════════════════╗ │
│  ║ Selecionar Componente              [X]                    ║ │
│  ╠════════════════════════════════════════════════════════════╣ │
│  ║ Buscar: [________________]                                ║ │
│  ╠════════════════════════════════════════════════════════════╣ │
│  ║  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      ║ │
│  ║  │ 📦      │  │ 📦      │  │ 🖼️      │  │         │      ║ │
│  ║  │ Tomada  │  │Lâmpada  │  │ (Preview)  │         │      ║ │
│  ║  └─────────┘  └─────────┘  └─────────┘  │         │      ║ │
│  ║                                          │ Scrollar │    ║ │
│  ║  ... mais componentes ...                │         │      ║ │
│  ║                                          └─────────┘      ║ │
│  ╠════════════════════════════════════════════════════════════╣ │
│  ║ Selecionado: Tomada.FCStd                                 ║ │
│  ║                         [Cancelar] [OK]                   ║ │
│  ╚════════════════════════════════════════════════════════════╝ │
│                                                                 │
│  Funcionalidades:                                               │
│  • Load de thumbnails (extraídos do arquivo FCStd)             │
│  • Busca em tempo real por nome                                │
│  • Signal de seleção para callbacks                            │
│  • Retorna: caminho completo do arquivo                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                         (OK clicked)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│    ComponentInserter.load_and_insert_component(filepath)        │
│                                                                 │
│  1️⃣  Abre arquivo FCStd em documento temporário                │
│      App.open("Componentes/Eletrica/Tomada.FCStd")            │
│                                                                 │
│  2️⃣  Identifica objeto principal do componente                │
│      • Procura por grupos                                      │
│      • Procura por objetos com Shape                          │
│      • Fallback: primeiro objeto                              │
│                                                                 │
│  3️⃣  Copia para documento ativo                                │
│      doc.copyObject(component_obj)                            │
│                                                                 │
│  4️⃣  Fecha documento temporário                                │
│      App.closeDocument(temp_doc.Name)                         │
│                                                                 │
│  5️⃣  Recomputa o documento                                     │
│      doc.recompute()                                           │
│                                                                 │
│  6️⃣  Executa callback (se configurado)                        │
│      on_component_loaded(filepath, inserted_obj)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   ✅ COMPONENTE INSERIDO NO DOCUMENTO FREECAD                  │
│                                                                 │
│   Pronto para:                                                  │
│   • Visualização 3D                                            │
│   • Cálculos posteriores                                       │
│   • Edição adicional                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Estrutura de Classes

```
┌─────────────────────────────────────────────────────────────────┐
│                      UI/dialogs/                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ComponentSelectorDialog (QtWidgets.QDialog)                   │
│  ├─ __init__(components_path, title, parent)                  │
│  ├─ initUI()                                                   │
│  ├─ load_components()                                          │
│  ├─ on_component_selected(filepath)                           │
│  ├─ on_search_text_changed(text)                              │
│  ├─ get_selected_component() → Optional[str]                  │
│  └─ [Signal] component_selected(filepath)                     │
│                                                                 │
│  ComponentCard (QtWidgets.QWidget)  ◄─ Usado por Dialog       │
│  ├─ __init__(filename, filepath, parent)                      │
│  ├─ initUI()                                                   │
│  ├─ load_thumbnail()                                           │
│  ├─ mousePressEvent()                                          │
│  ├─ set_selected(selected)                                    │
│  └─ [Signal] clicked()                                        │
│                                                                 │
│  ComponentInserter                                             │
│  ├─ __init__(folder, callback, parent)                        │
│  ├─ insert_component() → bool                                 │
│  ├─ load_and_insert_component(filepath) → bool                │
│  ├─ insert_component_with_placement(filepath) → bool          │
│  ├─ insert_multiple_components(filepaths) → int               │
│  └─ _get_main_component_object(doc)                          │
│                                                                 │
│  ComponentInsertionMode                                        │
│  ├─ __init__(component_filepath)                              │
│  ├─ start()     # Ativa modo mouse                            │
│  └─ stop()      # Desativa                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Padrão de Reutilização

### Para Qualquer Funcionalidade (Cabos, Infraestrutura, etc.)

```python
# 1. SIMPLES: Apenas seleção
dialog = ComponentSelectorDialog(
    components_path="Componentes/Cabos",
    title="Selecionar Cabo"
)
if dialog.exec_() == QtWidgets.QDialog.Accepted:
    selected = dialog.get_selected_component()
    # Fazer algo com selected


# 2. INTERMEDIÁRIO: Seleção + Lógica Customizada
inserter = ComponentInserter(
    components_folder="Componentes/Cabos",
    on_component_loaded=lambda path, obj: print(f"Carregou: {obj.Label}")
)
success = inserter.insert_component()


# 3. AVANÇADO: Estender com classe customizada
class CableSelector(ComponentSelectorDialog):
    def __init__(self, parent=None):
        super().__init__(
            components_path="Componentes/Cabos",
            title="Selecione um Cabo",
            parent=parent
        )
    
    def get_cable_properties(self):
        filepath = self.get_selected_component()
        # Ler propriedades especiais...
        return properties
```

---

## Casos de Uso Suportados

### ✅ Caso 1: Inserir Componente Único
```python
inserter = ComponentInserter("Componentes/Eletrica")
inserter.insert_component()
```

### ✅ Caso 2: Inserir com Callback
```python
def after_insert(filepath, obj):
    print(f"Inseriu: {obj.Label}")

inserter = ComponentInserter(
    "Componentes/Eletrica",
    on_component_loaded=after_insert
)
inserter.insert_component()
```

### ✅ Caso 3: Integrar com Cálculo
```python
# Ver: examples_cable_calculation.py

workflow = CableCalculationWorkflow()
workflow.start_workflow()
# → Seleciona → Calcula → Mostra resultado
```

### ✅ Caso 4: Inserir Múltiplos
```python
inserter = ComponentInserter("Componentes")
files = [
    "Componentes/Eletrica/Tomada.FCStd",
    "Componentes/Eletrica/Lampada.FCStd"
]
count = inserter.insert_multiple_components(files)
```

### ✅ Caso 5: Extender para Domínios Específicos
```python
class BarramentoSelector(ComponentSelectorDialog):
    def __init__(self):
        super().__init__("Componentes/Barramento")

class InfraestruturaSelector(ComponentSelectorDialog):
    def __init__(self):
        super().__init__("Componentes/Infraestrutura")
```

---

## Fluxo de Dados

```
┌─────────────────────┐
│  Pasta de Arquivos  │ (Componentes/Eletrica/*.FCStd)
│  .FCStd + .FCBak    │
└──────────┬──────────┘
           │ load_components()
           ▼
┌─────────────────────────────┐
│  ComponentSelectorDialog    │
│  ┌───────────────────────┐  │
│  │ ComponentCard[] Array │  │
│  ├─ thumbnail extracted  │  │
│  ├─ name display         │  │
│  ├─ click events         │  │
│  └─ selected signal      │  │
│                         │  │
│  Search Filter → shown  │  │
└──────────┬──────────────┘
           │ get_selected_component()
           │ returns: /path/to/Tomada.FCStd
           ▼
┌──────────────────────────────┐
│  ComponentInserter           │
│  load_and_insert_component() │
│                              │
│  1. App.open(filepath)       │
│     → temp_doc               │
│  2. Find main object         │
│  3. doc.copyObject()         │
│  4. App.closeDocument()      │
│  5. doc.recompute()          │
│  6. callback()               │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  FreeCAD Document (Ativo)    │
│  ├─ Tomada (inserted)        │
│  ├─ Lampada (inserted antes) │
│  └─ ... outros objects       │
│                              │
│  Objeto pronto para:         │
│  • Manipulação 3D            │
│  • Propriedades              │
│  • Cálculos                  │
│  • Exportação                │
└──────────────────────────────┘
```

---

## Integração com Comando FreeCAD

```python
# InsertComponent.py

class Tugs:  # Comando de inserir tomadas
    def Activated(self):
        inserter = ComponentInserter(
            "Componentes/Eletrica",
            on_component_loaded=self._on_loaded
        )
        inserter.insert_component()

Gui.addCommand("InsertTugs", Tugs())
# Agora aparece no menu/toolbar FreeCAD
```

---

## Próximas Extensões Possíveis

### 1. Modo Interativo com Mouse
```python
# Em desenvolvimento...
inserter.insert_component_with_placement()
# Usuário clica no viewport para posicionar
```

### 2. Filtro Avançado
```python
dialog.filter_by_property("material", "Cobre")
dialog.filter_by_size_range(1, 50)  # mm²
```

### 3. Importar de Múltiplas Pastas
```python
dialog = ComponentSelectorDialog(
    components_path=[
        "Componentes/Eletrica",
        "Componentes/Externos"
    ]
)
```

### 4. Metadados do Componente
```python
properties = ComponentMetadata.load(filepath)
print(properties.material)
print(properties.specifications)
```

---

## Arquivos de Referência

- **Implementação**: `UI/dialogs/ComponentSelectorDialog.py` (~450 linhas)
- **Implementação**: `UI/dialogs/ComponentInserter.py` (~200 linhas)
- **Documentação**: `UI/dialogs/README.md` (~900 linhas)
- **Exemplos**: `UI/dialogs/examples_cable_calculation.py` (~400 linhas)
- **Integração**: `InsertComponent.py` (modificado)

---

*Arquitetura documentada em 2026-04-08*
