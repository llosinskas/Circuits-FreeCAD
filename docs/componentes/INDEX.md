> **Nota:** guia escrito antes da reorganização; caminhos e imports podem estar desatualizados. A estrutura atual está em [AGENTS.md](../../AGENTS.md).

# 📚 Índice: Sistema de Componentes FreeCAD

## 🎯 Começar por Aqui

### Para Usuários Finais
1. **[QUICKSTART.md](QUICKSTART.md)** ⭐ **→ COMECE AQUI!**
   - Como usar o novo sistema em 5 minutos
   - Primeiros passos
   - Solução de problemas básicos

### Para Desenvolvedores
1. **[README.md](README.md)** → Documentação técnica completa
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** → Arquitetura e fluxos
3. **[examples_cable_calculation.py](examples_cable_calculation.py)** → Exemplos práticos

---

## 📖 Mapa Completo

### 1. QUICKSTART.md
**O que é**: Guia de 5 minutos  
**Quando usar**: Primeira vez usando o sistema  
**Contém**:
- Como abrir um componente
- Solução rápida de problemas
- Exemplos simples de código

### 2. README.md
**O que é**: Documentação técnica completa  
**Quando usar**: Implementando nova funcionalidade  
**Contém**:
- API completa de classes
- Exemplos de reutilização
- Padrões recomendados
- Troubleshooting detalhado
- Estrutura de pastas

### 3. ARCHITECTURE.md
**O que é**: Diagramas e explicação interna  
**Quando usar**: Entender como funciona internamente  
**Contém**:
- Fluxo visual (ASCII diagrams)
- Estrutura de classes
- Padrões de dados
- Casos de uso
- Extensões futuras

### 4. examples_cable_calculation.py
**O que é**: 3 exemplos práticos completos  
**Quando usar**: Implementando integração com cálculos  
**Contém**:
- SimpleCableSelector (básico)
- CableCalculationWorkflow (intermediário)
- CableInsertionAndCalculation (avançado)
- Padrão pronto para copiar/adaptar

---

## 🔍 Encontre Respostas Rápidas

| Pergunta | Resposta | Arquivo |
|----------|---------|---------|
| **Como uso?** | 5 minutos de guia | [QUICKSTART.md](QUICKSTART.md) |
| **Como estendo para cabos?** | Passo a passo | [README.md](README.md#exemplo-1-criar-função-para-seleção-de-cabos) |
| **Como integro com cálculo?** | 3 exemplos | [examples_cable_calculation.py](examples_cable_calculation.py) |
| **Qual é a arquitetura?** | Diagramas | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **API completa?** | Referência | [README.md](README.md#api-completa) |
| **Thumbnails não carregam** | Solução | [QUICKSTART.md](QUICKSTART.md#-solução-de-problemas) |
| **Como criar novo comando?** | Exemplo | [QUICKSTART.md](QUICKSTART.md#exemplo-completo-inserir-um-componente) |

---

## 🗂️ Estrutura de Código

```
UI/dialogs/
├── __init__.py                           ← Inicializador
├── ComponentSelectorDialog.py             ← Classe principal (dialog)
├── ComponentInserter.py                   ← Classe principal (insertor)
├── README.md                              ← Documentação técnica
├── ARCHITECTURE.md                        ← Diagramas e arquitetura
├── QUICKSTART.md                          ← Guia rápido
├── INDEX.md                               ← Este arquivo
└── examples_cable_calculation.py          ← Exemplos avançados
```

### Módulos Relacionados
- `InsertComponent.py` - Integração com comandos FreeCAD (modificado)
- `UI/Cards.py` - Componente de card (compatível)

---

## 🚀 Casos de Uso Comuns

### 1. Inserir um componente sem lógica adicional
```python
from UI.dialogs import ComponentInserter

inserter = ComponentInserter("Componentes/Eletrica")
inserter.insert_component()
```
→ Ver: [QUICKSTART.md - Primeira Utilização](QUICKSTART.md#-primeira-utilização)

### 2. Seleção com callback customizado
```python
inserter = ComponentInserter(
    "Componentes/Eletrica",
    on_component_loaded=meu_callback
)
```
→ Ver: [README.md - Exemplo 2](README.md#exemplo-2-integração-com-sistema-de-cálculo)

### 3. Integração com cálculos
```python
workflow = CableCalculationWorkflow()
workflow.start_workflow()
```
→ Ver: [examples_cable_calculation.py](examples_cable_calculation.py)

### 4. Extensão para novo domínio
```python
class MeuSelecionador(ComponentSelectorDialog):
    def __init__(self):
        super().__init__("Minha/Pasta")
```
→ Ver: [README.md - Estendendo](README.md#estendendo-para-outras-funcionalidades)

---

## 📊 Estatísticas

| Item | Valor |
|------|-------|
| **Linhas de Código** | ~1450 |
| **Linhas de Documentação** | ~2500 |
| **Exemplos Práticos** | 10+ |
| **Casos de Uso** | 5+ |
| **Classes Principais** | 4 |
| **Sinais (Signals)** | 2 |

---

## ✅ Checklist de Implementação

- [x] ComponentSelectorDialog implementado
- [x] ComponentInserter implementado
- [x] Integração com InsertComponent.py
- [x] Documentação técnica (README)
- [x] Documentação de arquitetura (ARCHITECTURE)
- [x] Guia rápido (QUICKSTART)
- [x] Exemplos avançados
- [x] Teste de importações
- [x] Índice de navegação (este arquivo)

---

## 🎓 Próximas Extensões (Sugerências)

### Curto Prazo
- [ ] Teste unitário para ComponentSelectorDialog
- [ ] Teste unitário para ComponentInserter
- [ ] Modo posicionamento com mouse

### Médio Prazo
- [ ] Filtra por tipo/categoria
- [ ] Suporte a múltiplas pastas em um diálogo
- [ ] Metadados de componentes (JSON sidecar)

### Longo Prazo
- [ ] UI em abas por categoria
- [ ] Sistema de favoritos
- [ ] Preview em 3D interativo
- [ ] Integração com sistema de cálculos

---

## 🔗 Referências Cruzadas

### ComponentSelectorDialog
- **Arquivo**: ComponentSelectorDialog.py
- **Documentação**: README.md - Seção ComponentSelectorDialog
- **Exemplos**: examples_cable_calculation.py - SimpleCableSelector
- **Arquitetura**: ARCHITECTURE.md - Classes Principais

### ComponentInserter
- **Arquivo**: ComponentInserter.py
- **Documentação**: README.md - Seção ComponentInserter
- **Exemplos**: examples_cable_calculation.py - Todos
- **Arquitetura**: ARCHITECTURE.md - Fluxo de Inserção

### Integração com FreeCAD
- **Arquivo**: InsertComponent.py
- **Documentação**: README.md - Seção Integração
- **Exemplos**: QUICKSTART.md - Exemplo Completo
- **Arquitetura**: ARCHITECTURE.md - Integração com Comando

---

## 📞 Suporte e Recursos

### Documentação
- **Técnica**: [README.md](README.md)
- **Visual**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Rápida**: [QUICKSTART.md](QUICKSTART.md)

### Exemplos de Código
- **Básico**: [examples_cable_calculation.py](examples_cable_calculation.py) - SimpleCableSelector
- **Intermediário**: [examples_cable_calculation.py](examples_cable_calculation.py) - CableCalculationWorkflow
- **Avançado**: [examples_cable_calculation.py](examples_cable_calculation.py) - CableInsertionAndCalculation

### Código-Fonte com Docstrings
- ComponentSelectorDialog.py - Bem documentado
- ComponentInserter.py - Bem documentado
- InsertComponent.py - Bem documentado

---

## 🎯 Guia de Navegação por Objetivo

### Objetivo: "Primeiro Uso"
1. [QUICKSTART.md](QUICKSTART.md) - 5 minutos
2. [QUICKSTART.md - Primeira Utilização](QUICKSTART.md#-primeira-utilização)
3. Pronto!

### Objetivo: "Adicionar Suporte a Cabos"
1. [README.md - Exemplo 1](README.md#exemplo-1-criar-função-para-seleção-de-cabos)
2. [examples_cable_calculation.py](examples_cable_calculation.py)
3. Adaptar para seu caso de uso

### Objetivo: "Entender a Arquitetura"
1. [ARCHITECTURE.md - Diagrama do Fluxo](ARCHITECTURE.md#diagrama-do-fluxo-de-trabalho)
2. [ARCHITECTURE.md - Estrutura de Classes](ARCHITECTURE.md#estrutura-de-classes)
3. [README.md - API Completa](README.md#api-completa)

### Objetivo: "Integrar com Cálculos"
1. [examples_cable_calculation.py - Exemplo 2](examples_cable_calculation.py#========================================================================)
2. [README.md - Integração com Sistema de Cálculo](README.md#exemplo-2-integração-com-sistema-de-cálculo)
3. Adaptar CableCalculationWorkflow

### Objetivo: "Estender a Outro Domínio"
1. [README.md - Estendendo](README.md#estendendo-para-outras-funcionalidades)
2. [ARCHITECTURE.md - Casos de Uso](ARCHITECTURE.md#casos-de-uso-suportados)
3. Criar sua classe customizada

---

## 📅 Histórico

- **2026-04-08**: Implementação completa do sistema
  - ComponentSelectorDialog criado
  - ComponentInserter criado
  - Documentação técnica
  - Exemplos práticos
  - Integração com FreeCAD

---

**Última atualização**: 2026-04-08

*Para começar agora mesmo, abra [QUICKSTART.md](QUICKSTART.md) →*
