# Circuits: bancada "Engenharia" para FreeCAD

Bancada (workbench) de projetos elétricos residenciais, industriais e comerciais, com biblioteca de componentes, diagrama unifilar, geração 3D, importação do QElectroTech e relatório PDF. Requer FreeCAD 1.1+ e Python 3.10+. Código e interface em português.

## Não quebre isto

Estes nomes ficam gravados fora do repositório. Mudá-los quebra projetos ou configurações dos usuários.

| Não mude | Por quê |
|---|---|
| `freecad.Circuits` (nome do pacote) | Prefixo de todos os módulos gravados nos `.FCStd`. |
| `objects/*.py` e os nomes das classes | O FreeCAD grava `módulo.Classe` de cada objeto FeaturePython no `.FCStd`. |
| `Componentes/` | Projetos guardam `App::Link` apontando para os arquivos desta pasta. |
| IDs de comando, inclusive com erro de grafia (`newProjetctEletrical`) | Barras personalizadas pelo usuário guardam o ID. |
| Classe `CircuitsWorkbench` | É a chave da bancada no FreeCAD. |

Não edite nem apague `.FCStd` sem pedido explícito: são binários do usuário. Os `.FCBak` são backups automáticos e o git os ignora.

## Mapa

```
Circuits/                        pasta dentro de Mod/, raiz do repositório
├── package.xml                  metadados do Addon Manager
├── tests/unit/                  testes sem FreeCAD
├── tests/gui/smoke_gui.py       regressão com o FreeCAD real
├── docs/                        guias antigos (podem estar desatualizados)
├── Planejamento.md              roadmap
└── freecad/Circuits/
    ├── __init__.py              caminhos e metadados (sem FreeCAD nem Qt)
    ├── init_gui.py              classe da bancada, toolbars e menus
    ├── qt.py                    único lugar que importa PySide
    ├── commands/                comandos do FreeCAD, finos
    ├── UI/                      diálogos Qt
    ├── services/                operações no documento, sem Qt
    ├── objects/                 objetos FeaturePython
    ├── core/                    regras e tabelas puras
    │   ├── functions/           cálculos (Cabo/, Barramento, Infraestrutura/)
    │   ├── tables/              tabelas NBR 5410, NBR 14039 e eletrodutos
    │   ├── planilha.py          layout das planilhas de quadro e circuitos
    │   ├── qet.py               leitura de condutores do QElectroTech
    │   └── simbologia.py        geometria dos símbolos
    ├── Componentes/Eletrica/    biblioteca de modelos .FCStd
    └── Resources/               Icons/, data/, UI/ (.ui), translations/
```

## Camadas

As dependências só apontam para baixo:

```
init_gui → commands → UI, services, objects → core
```

| Camada | Pode usar | Não pode usar |
|---|---|---|
| `core` | só Python, `pandas` nas tabelas | FreeCAD, Qt, qualquer outra camada |
| `services` | FreeCAD, FreeCADGui, `core` | Qt, `UI`, `commands` |
| `objects` | FreeCAD, `core` | Qt, `UI`, `commands` |
| `UI` | Qt via `qt.py`, FreeCAD, `services` | `commands` |
| `commands` | todas as anteriores | lógica de negócio ou geometria |

Regras gerais:

- **Qt:** sempre `from freecad.Circuits.qt import QtWidgets`.
- **Imports:** sempre pelo caminho completo `freecad.Circuits...`. Módulos de `Mod/*` entram no mesmo `sys.path`, e nomes soltos como `Tools`, `UI` ou `utils` podem resolver para outra bancada.
- **Registro:** `Gui.addCommand` só na última parte de um módulo de `commands/`.

`tests/unit/test_architecture.py` falha se alguma dessas regras for violada.

## Como o FreeCAD carrega a bancada

1. Na inicialização, o FreeCAD importa `freecad.Circuits.init_gui` de todo pacote em `freecad/`. Não existe `InitGui.py` na raiz.
2. `init_gui` registra a bancada e não importa os comandos, para não atrasar a abertura do FreeCAD.
3. Na primeira ativação, `Initialize` importa `commands/*`, que registram os comandos ao serem importados, e monta toolbars e menus.

## Comandos

| ID | Módulo em `commands/` | Faz o trabalho em |
|---|---|---|
| `newProjetctEletrical`, `newSpreadsheet`, `AddSpreadsheet`, `ListElements`, `CreateModel` | `new_project` | `services/documento`, `planilhas`, `biblioteca`; `UI/insert_circuit` |
| `NewQuadro` | `projeto_quadro` | `services/documento` |
| `ComponentEletric`, `Gerar3D`, `Cabo` | `projeto_eletrico` | `services/tomadas`, `cabos` |
| `InsertComponent`, `InsertEquipaments` | `insert_component` | `UI/dialogs/ComponentInserter` |
| `InsertTugs` | `insert_component` | `services/tomadas` |
| `InsertSwitch`, `InsertLighting`, `InsertOutlet` | `insert_component` | `objects/switch`, `lighting`, `outlet` |
| `InsertConduit` | `insert_component` | `Draft_Wire` nativo |
| `InsertWire`, `InsertCableTray` | `insert_component` | ainda não implementados: só exibem um aviso |
| `Generate3DConduits`, `Generate3DSwitches` | `generate_3d` | `services/eletrodutos`, `caixas_3d` |
| `GerarUnifilar`, `GerarPlanilha`, `AddCircuito` | `gerar_unifilar` | `services/unifilar`, `planilhas`; `UI/dialogs/quadro_dialogs` |
| `ImportQET`, `Add_Node` | `import_QEletrotech` | `services/qet_import`, `eletrodutos`; `core/qet` |
| `GenerateReport` | `reports` | `services/pdf_generator`; `UI/dialogs/report_dialog` |
| `GetSpaces`, `ReiniciarBancada` | `tools` | no próprio módulo |

## Como os dados ficam no documento

Os comandos se encontram pelos objetos do documento, não por estado em Python:

- **Tomada em Sketch:** propriedade `tipo == "tomada"`, além de `Fase`, `neutro`, `terra` e `altura_piso`.
- **Objetos FeaturePython:** `obj.Proxy.Type` vale `Switch`, `Lighting`, `Outlet` ou `ConduitPath`.
- **Quadro:** planilha `Spreadsheet::Sheet` com a propriedade `quadro`. A linha 3 tem os dados, com aliases iguais a `core.planilha.CABECALHO_QUADRO`, que são lidos pelo unifilar. Os circuitos ficam da linha 6 em diante, conforme `COLUNAS_CIRCUITO`.
- **Diagrama:** grupo `diagrama_<quadro>`, recriado a cada geração.
- **Caixas e tubos 3D:** objeto `<nome da origem>_3D`, substituído a cada geração.
- **Unidades:** comprimentos em mm no FreeCAD; correntes em A; seções em mm².

## Receitas

**Novo comando**
1. Coloque a lógica em `services/`, ou em `core/` se não precisar do FreeCAD.
2. Crie a classe em `commands/` com `Activated` e `GetResources`, usando `recursos()` e `documento_ou_aviso()` de `commands/_base.py`.
3. Registre no fim do módulo com `Gui.addCommand("MeuId", MinhaClasse())`.
4. Acrescente o ID em uma lista de `init_gui.py`. Se o módulo for novo, importe-o em `Initialize`.

**Novo cálculo ou tabela de norma:** função pura em `core/functions/` ou dados em `core/tables/`, com teste em `tests/unit/`. Documente unidades no docstring.

**Novo objeto FeaturePython:** siga `objects/switch.py` (classe com `Type`, ViewProvider e `create_*`). Depois de usado em projetos, o nome do módulo e da classe ficam congelados.

**Novo diálogo:** arquivo em `UI/dialogs/`, devolvendo os dados por um método como `get_dados()`. Quem grava no documento é o `service`, chamado pelo comando.

**Novo componente de biblioteca:** arquivo `.FCStd` em `Componentes/Eletrica/`, ou o comando `CreateModel`.

## Como verificar uma mudança

Execute sempre a partir da raiz do repositório. O Python do FreeCAD já tem `pandas` e `reportlab`, mas não tem `pytest`; os testes rodam com `unittest`.

**Testes unitários** (menos de 1 s):

```bash
"/c/Program Files/FreeCAD 1.1/bin/python.exe" -B -m unittest discover -s tests/unit -t .
```

**Regressão no FreeCAD real.** Sem janela e sem gravar na biblioteca, executa os comandos e grava um retrato JSON do documento. Para mudanças em `commands`, `services`, `objects` ou `UI`, gere um retrato antes e outro depois, e compare. Qualquer diferença precisa ser intencional.

```bash
QT_QPA_PLATFORM=offscreen CIRCUITS_SMOKE_OUT="C:/temp/depois.json" \
  "/c/Program Files/FreeCAD 1.1/bin/freecad.exe" \
  --user-cfg "C:/temp/u.cfg" --system-cfg "C:/temp/s.cfg" tests/gui/smoke_gui.py
```

- Use sempre `--user-cfg` e `--system-cfg` temporários, para não alterar as preferências do usuário.
- `errors` no JSON precisa estar vazio, e `extras` precisa estar sem traceback.
- A mensagem `resource deadlock would occur` no log já existia e não vem da bancada.
- No FreeCAD aberto, o botão **Reiniciar Bancada** recarrega o código sem fechar o programa.

## Ambiente nesta máquina

- O FreeCAD 1.1 lê `%APPDATA%\FreeCAD\v1-1\Mod\`. Esta cópia é a mais recente.
- `%APPDATA%\FreeCAD\Mod\eletroAlpha` é um clone antigo do mesmo repositório, e o FreeCAD 1.1 não o carrega. Não edite lá.
- `v1-1\Mod\Circuits-FreeCAD` é outra instalação, mais antiga, com a classe `Circuits` e também o nome "Engenharia". Ela registra os mesmos IDs de comando, e vale o último registro. Ao testar, ative a bancada pela chave `CircuitsWorkbench`.
- O `origin` deste clone é `llosinskas/eletroAlpha`, enquanto `package.xml` e `pyproject.toml` apontam para `llosinskas/Circuits-FreeCAD`.
- `venv/` é local e ignorada pelo git. O FreeCAD não a usa.

## Problemas conhecidos

Todos foram confirmados no código ou em execução e já existiam antes da reorganização, que preservou o comportamento. Corrija com teste, e atualize esta lista.

**Afetam o uso**
- `core/planilha.py`, `ultima_linha`: lê só o primeiro dígito da linha (`A12` conta como 1). Do 5º circuito em diante, o novo circuito sobrescreve a linha 10, e o unifilar só desenha até a linha 9.
- `services/pdf_generator.py`: procura diagramas com Label `"diagrama "`, mas o Label real é `diagrama_<quadro>`. O relatório sempre diz que não há diagrama.
- `services/planilhas.py`, `criar_planilha_quadro`: `doc.Spreadsheet(...)` não existe. Criar um quadro com nome repetido gera erro.
- `commands/gerar_unifilar.py`, `GerarPlanilha`: cancelar o diálogo não interrompe a criação da planilha.
- `UI/insert_circuit.py` (`AddSpreadsheet`): os botões e o movimento do mouse usam `self.label1` e `self.label2`, que não existem. O formulário também não grava dados.

**Cálculos e tabelas, ainda sem uso na interface**
- `core/functions/Barramento.py`: `Sec_tubular` gera `TypeError` (falta `*` em `math.pi(...)`) e não tem `return`. `Corrente_carga_maxima` usa `Qc*Qr-Qs`; conferir com a fonte, pois o balanço térmico sugere soma.
- `core/functions/Cabo/Cabo.py`: os métodos de `Material` comparam a classe com inteiros e geram `UnboundLocalError`; `temp_sobrecarga` está definido duas vezes, e a segunda deveria ser a de curto-circuito.
- `core/tables/tab_cabo_pvc_2_3.py` e `core/tables/NBR5410/fator_correcao_temperatura_enterrado.py`: colunas com tamanhos diferentes, a importação gera `ValueError`.
- `core/tables/*/fator_correcao_*`: a lista `TEMPERATURA` pula 30 °C. Conferir os valores com a norma.
- `core/functions/Infraestrutura/Eletroduto.py`: tabela `DISTANCIA_MAX_FIXACAO_ISOLANTE` não preenchida.
- `tests/unit/test_queda_tensao.py`: a fórmula devolve 6,78 mm² e o teste espera 10 mm², por isso está marcado como falha esperada. Falta decidir qual está certo.

**Projeto**
- `package.xml` e `pyproject.toml` declaram licença MIT, mas não há arquivo `LICENSE`.
- `scipy`, `sympy` e `matplotlib` são dependências obrigatórias, mas nenhum código as usa.
- Nunca usados: `UI/ListaPeca.py` e `UI/Cards.py` (rascunho com erros), `core/conexoes.py` e `Resources/UI/*.ui`.
- Traduções: `Resources/translations/` está vazia.
