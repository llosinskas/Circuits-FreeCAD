# ⚡ Bancada Engenharia

Uma bancada profissional para FreeCAD dedicada a projetos elétricos, com foco em se tornar o padrão de projeto elétrico e escalar para projetos de quadros de comando.

## 🎯 Visão Geral

A Bancada Engenharia fornece um conjunto completo de ferramentas para:
- **Design 3D** de instalações elétricas residenciais e comerciais
- **Cálculos elétricos** (cabos, barramento, aterramento, fator de potência)
- **Gestão de componentes** (tomadas, lâmpadas, equipamentos)
- **Documentação técnica** (diagramas, relatórios, listas de materiais)
- **Projetos executivos** completos e profissionais

## ✨ Funcionalidades Principais

### 1. **Sistema de Componentes** ✅ (Implementado)
Insira componentes 3D diretamente do arquivo:
- 📦 Biblioteca de componentes (Tomadas, Lâmpadas, Equipamentos, etc.)
- 🎨 Preview/Thumbnail dos componentes
- 🖱️ Seleção fácil com diálogo intuitivo
- ⚙️ Configuração por callback (reutilizável)
- 🌙 **Suporte a Tema Dark** (Ícones com contorno branco, detectados automaticamente)

**Como usar:**
```
Menu Bancada → Componentes → Inserir Componente
ou
Toolbar "Componentes" → Botão "Inserir Componente"
```

### 2. **Cálculos Elétricos** ⏳ (Em Desenvolvimento)
- Cálculo de seção mínima de cabo
- Cálculo de queda de tensão
- Verificação de corrente
- Cálculos de barramento
- Cálculos de infraestrutura
- Aterramento

### 3. **Diagramas e Documentação** ⏳ (Planejado)
- Diagrama Unifilar automático
- Diagrama Multifilar
- Lista de Materiais
- Planilha de Circuitos
- Relatórios executivos

### 4. **Infraestrutura** ⏳ (Planejado)
- Traçado de Eletrodutos
- Geração automática de caminhos
- Eletrocalhas
- Leitos

---

## 🚀 Começar Rapidinho

### Prérequisitos
- FreeCAD 1.1+
- Python 3.10+
- PySide (incluído no FreeCAD)

### Instalação
Já está incluída! Apenas:
1. Abra FreeCAD
2. Selecione a bancada **"Engenharia"** na barra de seleção
3. Pronto! ✓

### Primeiro Uso
1. Crie um novo documento: `File → New`
2. Ative a bancada: Selecione **"Engenharia"** no dropdown
3. Clique em **"Inserir Componente"** (Toolbar ou Menu)
4. Selecione um componente (ex: Tomada)
5. Clique OK
6. Componente inserido no projeto! 🎉

---

## 📚 Documentação Detalhada

### Sistema de Componentes
Para documentação completa sobre seleção e inserção de componentes:
👉 [docs/componentes/README.md](docs/componentes/README.md)

### Arquitetura
Para entender a arquitetura:
👉 [AGENTS.md](AGENTS.md)

### Quick Start
Para começar em 5 minutos:
👉 [docs/componentes/QUICKSTART.md](docs/componentes/QUICKSTART.md)

### Exemplos de Integração
Para ver exemplos com cálculos:
👉 [docs/componentes/examples_cable_calculation.py](docs/componentes/examples_cable_calculation.py)

---

## 🗂️ Estrutura do Projeto

```
Circuits/
├── AGENTS.md                  # Guia da arquitetura (para pessoas e IAs)
├── package.xml                # Metadados do Addon Manager
├── docs/                      # Guias e documentação do sistema de componentes
├── tests/
│   ├── unit/                  # Rodam sem FreeCAD
│   └── gui/                   # Regressão com o FreeCAD real
└── freecad/Circuits/
    ├── init_gui.py            # Registro da bancada, toolbars e menus
    ├── qt.py                  # Importação única do Qt
    ├── commands/              # Comandos do FreeCAD (botões)
    ├── UI/                    # Diálogos
    ├── services/              # Operações no documento
    ├── objects/               # Objetos FeaturePython
    ├── core/                  # Regras e tabelas puras, sem FreeCAD
    ├── Componentes/           # Biblioteca de modelos .FCStd
    └── Resources/             # Ícones, dados e arquivos .ui
```

Ver [AGENTS.md](AGENTS.md) para as regras de cada camada.

---

## 📖 Menu da Bancada

Ao ativar a bancada "Engenharia", você terá acesso a:

### Menu "Componentes"
- ✅ Inserir Componente
- ✅ Inserir Tomada
- ✅ Inserir Equipamento
- ⏳ Inserir Fiação
- ⏳ Inserir Eletroduto
- ⏳ Inserir Eletrocalha

### Menu "Novo Projeto"
- Criar novo projeto elétrico
- Adicionar spreadsheet
- Criar modelo

### Menu "Diagrama Unifilar"
- Gerar diagrama unifilar
- Gerar planilha de circuitos
- Adicionar circuito

### Menu "Quadro Elétrico"
- Criar novo quadro

### Menu "Relatórios"
- Gerar relatório

---

## 🔧 Configuração

### Pasta de Componentes
Os componentes estão em:
```
freecad/Circuits/Componentes/Eletrica/
├── Tomada.FCStd
├── Lampada.FCStd
├── Tomadas.FCStd
└── ...
```

**Para adicionar novo componente:**
1. Crie arquivo 3D no FreeCAD: `File → Save As → component.FCStd`
2. Adicione um thumbnail (salva automaticamente no formato correto)
3. Coloque em `freecad/Circuits/Componentes/Eletrica/`
4. Pronto! Aparecerá no seletor ao clicar no botão

---

## 💡 Exemplos de Uso

### Exemplo 1: Inserir uma Tomada
```
1. Menu → Componentes → Inserir Tomada
2. Diálogo abre com preview dos componentes
3. Clique em "Tomada"
4. Clique OK
5. Tomada inserida no projeto
```

### Exemplo 2: Integrar com Cálculo
```python
from freecad.Circuits.UI.dialogs import ComponentInserter

def meu_callback(filepath, objeto):
    print(f"Componente inserido: {objeto.Label}")
    # Executar cálculo aqui

inserter = ComponentInserter(
    "Componentes/Eletrica",
    on_component_loaded=meu_callback
)
inserter.insert_component()
```

Ver arquivo `docs/componentes/examples_cable_calculation.py` para 3 exemplos completos!

---

## 🗺️ Roadmap

### ✅ Concluído (v0.1)
- [x] Sistema de seleção e inserção de componentes
- [x] Preview com thumbnails
- [x] Integração com bancada
- [x] Documentação técnica

### ⏳ Próximo (v0.2)
- [ ] Modo posicionamento com mouse
- [ ] Cálculos de cabo básicos
- [ ] Filtros avançados de componentes
- [ ] Teste unitário

### 🚀 Futuro (v0.3+)
- [ ] Traçado automático de eletrodutos
- [ ] Geração de diagrama unifilar
- [ ] Cálculos completos (barramento, aterramento, FP)
- [ ] Relatórios automáticos
- [ ] Exportação (DWG, PDF)
- [ ] Integração com QEletrotech

---

## 🐛 Troubleshooting

### "Sistema de Componentes não aparece"
- Verifique pasta `freecad/Circuits/Componentes/Eletrica/`
- Arquivos devem ser `.FCStd` (não `.FCBak`)
- Recrie a pasta se necessário

### "Thumbnails vazios"
- Isso é normal, usa fallback de ícone genérico
- Para adicionar thumbnail: abra `.FCStd` no FreeCAD e re-salve

### "Erro ao inserir componente"
- Verifique se um documento está aberto
- Tente recarregar a bancada (Menu → Ferramentas → Reiniciar Bancada)

### "Bancada não aparece"
- Reinicie FreeCAD
- Verifique se o repositório está em `%APPDATA%\FreeCAD\v1-1\Mod\Circuits`

---

## 📝 Notas de Versão

### v0.2 (2026-04-08)


### v0.1 (2026-04-08)
- ✅ Implementação do sistema de componentes
- ✅ Diálogo com busca em tempo real
- ✅ Preview de thumbnails
- ✅ Integração com bancada FreeCAD
- ✅ Documentação técnica completa
- ✅ 3 exemplos de integração

---

## 👨‍💻 Desenvolvimento e Contribuição

### Para Desenvolvedores
A bancada foi estruturada para ser fácil de estender:

**Adicionar novo tipo de componente:**
1. Crie pasta em `Componentes/` (ex: `Componentes/Cabos/`)
2. Adicione arquivos `.FCStd`
3. Use `ComponentSelectorDialog` apontando para essa pasta

**Integrar com cálculos:**
```python
from freecad.Circuits.UI.dialogs import ComponentInserter

inserter = ComponentInserter(
    "sua/pasta/componentes",
    on_component_loaded=seus_calculos
)
```

Ver `docs/componentes/README.md` para API completa!

---

## 📞 Suporte

- Versão do FreeCAD: 1.1+
- Python: 3.10+
- Sistema: Windows, Linux, macOS
- Licença: (Defina sua licença)

---

## 🎓 Aprender Mais

- [Arquitetura da bancada](AGENTS.md)
- [Documentação técnica de Componentes](docs/componentes/README.md)
- [Quick Start em 5 minutos](docs/componentes/QUICKSTART.md)
- [Exemplos com cálculos](docs/componentes/examples_cable_calculation.py)

---

## 📅 Histórico

| Versão | Data | Alterações |
|--------|------|-----------|
| 0.1 | 2026-04-08 | Sistema de componentes implementado |
| 0.0 | 2026-03 | Inicial |

---

**Desenvolvido com ❤️ para ElectroAlpha**

*Última atualização: 2026-04-08*
