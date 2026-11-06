> **Nota:** guia escrito antes da reorganização; caminhos e imports podem estar desatualizados. A estrutura atual está em [AGENTS.md](../../AGENTS.md).

# Quick Start: Sistema de Componentes

## 📋 Sumário
- ⏱️ **5 minutos**: Primeiro uso
- 📚 **Documentação completa**: Ver `README.md`
- 🏗️ **Arquitetura**: Ver `ARCHITECTURE.md`
- 🎓 **Exemplos avançados**: Ver `examples_cable_calculation.py`

---

## ✨ O Que Foi Implementado?

Um sistema completo que permite:

1. **Clicar um botão** → Abre diálogo com lista de componentes
2. **Ver previews** → Thumbnails dos arquivos FreeCAD
3. **Selecionar** → Clica em um componente
4. **Inserir** → Clica OK e o componente é inserido no projeto
5. **Reutilizar** → Mesmas classes para cabos, infraestrutura, etc.

---

## 🚀 Primeira Utilização

### 1. Abra um Projeto no FreeCAD
```
File → New → Criar/Abrir um documento
```

### 2. Clique no Botão
```
Menu FreeCAD → Eletro → Inserir Componente
ou use Toolbar
```

### 3. Você Verá Este Diálogo

```
┌─────────────────────────────────────────┐
│ Selecionar Componente            [X]    │
├─────────────────────────────────────────┤
│ Buscar: [              ]                │
├─────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│ │ Tomada  │ │ Lampada │ │ Tomadas │    │
│ │ 📦      │ │ 📦      │ │ 📦      │    │
│ └─────────┘ └─────────┘ └─────────┘    │
├─────────────────────────────────────────┤
│ Selecionado: Nenhum                    │
│            [Cancelar]  [OK]             │
└─────────────────────────────────────────┘
```

### 4. Clique em Uma Tomada
- Fica **com borda verde**
- Mostra "Selecionado: Tomada.FCStd"
- Botão OK ativa

### 5. Clique OK
- Componente **inserido no projeto**
- Aparece na árvore de objetos do FreeCAD
- Pronto para usar!

---

## 💻 Para Desenvolvedores

### Usar em Seu Código

#### Opção 1: Simples (Apenas Seleção)
```python
from UI.dialogs import ComponentSelectorDialog

dialog = ComponentSelectorDialog("Componentes/Eletrica")
if dialog.exec_() == QtWidgets.QDialog.Accepted:
    filepath = dialog.get_selected_component()
    print(f"Selecionou: {filepath}")
```

#### Opção 2: Com Inserção
```python
from UI.dialogs import ComponentInserter

inserter = ComponentInserter("Componentes/Eletrica")
success = inserter.insert_component()
```

#### Opção 3: Com Callback
```python
def meu_callback(filepath, freecad_object):
    print(f"Inseriu: {freecad_object.Label}")
    # Sua lógica aqui...

inserter = ComponentInserter(
    "Componentes/Eletrica",
    on_component_loaded=meu_callback
)
inserter.insert_component()
```

#### Opção 4: Fluxo Completo (Seleção + Cálculo)
```python
from UI.dialogs.examples_cable_calculation import CableCalculationWorkflow

workflow = CableCalculationWorkflow()
workflow.start_workflow()
# Seleciona → Insere parâmetros → Calcula → Mostra resultado
```

---

## 📁 Estrutura de Pastas Usada

```
Componentes/
└── Eletrica/              ← Pasta atual
    ├── Tomada.FCStd
    ├── Lampada.FCStd
    └── Tomadas.FCStd
```

Para usar outras pastas, basta passar o caminho:
```python
dialog = ComponentSelectorDialog("Componentes/Cabos")  # Outra pasta
```

---

## ⚙️ Como Estender para Novas Funcionalidades

### Exemplo: Para Cálculo de Cabos

**Passo 1:** Criar pasta
```
Componentes/Cabos/
├── Cabo_2p5mm.FCStd
├── Cabo_4mm.FCStd
└── Cabo_6mm.FCStd
```

**Passo 2:** Criar função
```python
def calcular_cabo():
    """Seleciona cabo e calcula."""
    from UI.dialogs import ComponentSelectorDialog
    from core.functions.Cabo import calcular_bitola
    
    dialog = ComponentSelectorDialog(
        "Componentes/Cabos",
        title="Selecionar Cabo"
    )
    
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        filepath = dialog.get_selected_component()
        
        # Seu cálculo
        bitola = calcular_bitola(
            corrente=30,
            comprimento=50
        )
        
        print(f"Bitola mínima: {bitola} mm²")
```

**Passo 3:** Integrar com comando FreeCAD (ver `InsertComponent.py`)

---

## 🐛 Solução de Problemas

### "Nenhum arquivo de componente aparece"
- ✅ Verifique que a pasta `Componentes/Eletrica/` existe
- ✅ Confirme que tem arquivos `.FCStd` (não `.FCBak`)
- ✅ Verifique a estrutura:
  ```
  eletroAlpha/
  └── Componentes/
      └── Eletrica/
          ├── Lampada.FCStd
          ├── Tomada.FCStd
          └── ...
  ```

### "Thumbnails não carregam"
- Isso é normal, mostra ícone genérico 📦
- Ainda assim funciona (clique no card)
- Para adicionar thumbnail: abra .FCStd no FreeCAD, export thumbnail

### "Componente não insere"
- ✅ Verifique que um documento está aberto
- ✅ Veja a mensagem de erro exata
- ✅ Procure em `FreeCADGui.Console`

---

## 📚 Documentação Disponível

| Arquivo | Conteúdo |
|---------|----------|
| `README.md` | Guia técnico completo (API, padrões, boas práticas) |
| `ARCHITECTURE.md` | Diagramas, fluxos, estrutura interna |
| `examples_cable_calculation.py` | 3 exemplos práticos de integração |
| `ComponentSelectorDialog.py` | Código-fonte com docstrings |
| `ComponentInserter.py` | Código-fonte com docstrings |

---

## 🎯 Próximos Passos

### Curto Prazo (Você Pode Usar Agora)
- [x] Seletor básico de componentes
- [x] Inserção automática
- [x] Suporte a callbacks

### Médio Prazo
- [ ] Modo posicionamento com mouse
- [ ] Filtros avançados
- [ ] Múltiplas pastas em um diálogo

### Longo Prazo
- [ ] Metadados dos componentes
- [ ] Integração com cálculos
- [ ] Geração de relatórios

---

## 💡 Exemplo Completo: Inserir um Componente

```python
"""
Exemplo prático completo: Novo comando para inserir componentes nomeados
"""

import os
from pathlib import Path
from PySide2 import QtWidgets

import FreeCADGui as Gui
import FreeCAD as App

from UI.dialogs import ComponentInserter


class MinhaFuncionalidade:
    """Exemplo de como usar o selecionador."""
    
    def Activated(self):
        """Chamado quando usuário clica no botão/menu."""
        
        # Valida documento
        if not App.activeDocument():
            QtWidgets.QMessageBox.warning(
                None,
                "Erro",
                "Abra um documento FreeCAD primeiro."
            )
            return
        
        # Cria insertor
        base = Path(__file__).parent
        folder = str(base / "Componentes" / "Eletrica")
        
        inserter = ComponentInserter(
            components_folder=folder,
            on_component_loaded=self.on_insert_complete
        )
        
        # Executa
        inserter.insert_component()
    
    def on_insert_complete(self, filepath: str, freecad_obj):
        """Callback: chamado após inserir com sucesso."""
        print(f"✓ Componente inserido: {freecad_obj.Label}")
        
        # Aqui você pode:
        # - Ajustar propriedades
        # - Executar cálculos
        # - Mostrar diálogo de opções
        # - Etc.
    
    def GetResources(self):
        return {
            'MenuText': 'Minha Funcionalidade',
            'ToolTip': 'Insere componentes',
        }


# Registra no FreeCAD
Gui.addCommand("MinhaFuncionalidade", MinhaFuncionalidade())
```

---

## 📞 Suporte

Dúvidas? Veja:
1. `README.md` - Seção que mais se aproxima
2. `ARCHITECTURE.md` - Para entender fluxo interno
3. `examples_cable_calculation.py` - Exemplos reais
4. Código-fonte com docstrings (ao passar mouse no VS Code)

---

*Quick Start criado em 2026-04-08*
