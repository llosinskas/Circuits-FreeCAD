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
    │   ├── functions/           cálculos (Cabo/, Barramento, Infraestrutura/, Predial/)
    │   ├── tables/              tabelas NBR 5410, NBR 14039 e eletrodutos
    │   ├── simbolos.py          catálogo e geometria dos pontos elétricos
    │   ├── alinhamento.py       travas, alinhamento automático, alinhar e distribuir símbolos
    │   ├── pavimentos.py        pastas dos símbolos por tipo, nome e cota dos pavimentos
    │   ├── identificacao.py     letra de comando, próximo circuito e texto de anotação
    │   ├── formularios.py       campos dos formulários de cálculo: opções prontas, dicas, avançados
    │   ├── rede.py              rede de eletrodutos: encaixe nas caixas, roteamento, fios e verticais
    │   ├── quantitativos.py     soma dos materiais: pontos, caixas, interruptores, eletrodutos, quadros
    │   ├── exportar.py          gravação de tabelas em CSV e XLSX só com a biblioteca padrão
    │   ├── quadro.py            componentes do quadro: disjuntores, DR, DPS, barramentos, módulos
    │   ├── circuitos.py         circuitos a partir dos pontos: soma, cabo, disjuntor, fases
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
| `InsertSwitch`, `InsertSwitchParalelo`, `InsertSwitchIntermediario`, `InsertLighting`, `InsertOutlet` | `insert_component` | `objects/switch`, `lighting`, `outlet` |
| `Ponto_<símbolo>` (um por entrada de `core.simbolos.CATALOGO`) | `pontos` | `objects/ponto`; `core/simbolos` |
| `LegendaSimbolos` | `pontos` | `services/legenda` |
| `DefinirPavimento`, `AdicionarNivelBIM`, `MoverParaPavimento`, `AjustarCotas` | `pavimentos` | `services/pavimentos`; `core/pavimentos`; `UI/dialogs/pavimento_dialog` |
| `PlanilhaNotas`, `GerarNotas` | `pontos` | `services/notas`; `core/notas` |
| `DefinirCircuito`, `LigarInterruptor`, `IdentificarPontos` | `identificacao` | `services/identificacao`; `core/identificacao`; `UI/dialogs/circuito_dialog` |
| `PintarSketches` | `tools` | `services/estilo` |
| `AlinharPontos`, `DistribuirPontos`, `EscalaSimbolos` | `alinhar` | `services/alinhamento`, `escala`; `core/alinhamento` |
| `InsertConduit` | `insert_component` | `Draft_Wire` nativo |
| `ConectarEletrodutos`, `ListaVerticais` | `rede` | `services/rede`; `core/rede` |
| `InsertWire`, `InsertCableTray` | `insert_component` | ainda não implementados: só exibem um aviso |
| `Generate3DConduits`, `Generate3DSwitches` | `generate_3d` | `services/eletrodutos`, `caixas_3d` |
| `GerarPlanilha`, `CircuitosQuadro`, `MontarCircuitos`, `AddCircuito`, `ComponentesQuadro`, `GerarUnifilar` | `gerar_unifilar` | `services/planilhas`, `circuitos`, `unifilar`, `identificacao`; `core/circuitos`, `quadro`; `UI/dialogs/quadro_dialogs` |
| `ImportQET`, `Add_Node` | `import_QEletrotech` | `services/qet_import`, `eletrodutos`; `core/qet` |
| `CalcDemanda` | `calculos` | `services/circuitos`; `core/functions/Predial/demanda` |
| `CondutorAterramento`, `CalcAterramento` | `aterramento` | `services/aterramento`; `core/functions/Predial/aterramento`; `UI/dialogs/calculo_dialog` |
| `CalcPressurizacao`, `CalcRecalque` | `calculos` | `core/functions/Predial/pressurizacao`, `recalque`, `motores`; `UI/dialogs/calculo_dialog` |
| `DistribuirLuminarias` | `calculos` | `services/luminotecnico`; `core/functions/Predial/luminotecnico`; `UI/dialogs/calculo_dialog` |
| `GenerateReport` | `reports` | `services/pdf_generator`; `UI/dialogs/report_dialog` |
| `GerarQuantitativos` | `reports` | `services/quantitativos`; `core/quantitativos`, `exportar` |
| `GetSpaces`, `ReiniciarBancada` | `tools` | no próprio módulo |

## Barras e legendas

As barras ficam em `init_gui.py`. As três barras próprias são enxutas: os comandos parecidos ficam em **grupos**, botões com lista suspensa definidos em `GROUPS` e registrados por `commands/grupos.py`. O botão do grupo mostra o ícone do último comando usado; a seta abre os outros.

| Barra | Botões (▾ = grupo) |
|---|---|
| Planta elétrica | Projeto ▾, Tomadas ▾, Energia ▾, Iluminação ▾, Comandos ▾, Circuitos ▾, Eletrodutos ▾, Aterramento ▾ |
| Quadros e documentos | Quadros ▾, Dados do quadro ▾, `MontarCircuitos`, `ComponentesQuadro`, `GerarUnifilar` (nesta ordem de uso), Cálculos ▾, Documentos ▾ |
| Modelo e biblioteca | Modelo 3D ▾, Biblioteca ▾ |
| Desenho, Modificador, Snap, Arquitetura | só os comandos nativos de uso frequente em planta; *Modificador* termina com `AlinharPontos`, `DistribuirPontos` e `EscalaSimbolos` |

| Grupo | Comandos |
|---|---|
| `Grupo_Projeto` | `newProjetctEletrical`, `DefinirPavimento`, `AdicionarNivelBIM`, `MoverParaPavimento`, `AjustarCotas`, `newSpreadsheet`, `ImportQET` |
| `Grupo_Tomadas` | `Ponto_tomada_baixa`, `_media`, `_alta`, `_piso` |
| `Grupo_Energia` | `Ponto_chuveiro`, `_ar_condicionado`, `_ventilador`, `_ponto_forca`, `_campainha` |
| `Grupo_Iluminacao` | `Ponto_luz_teto`, `_arandela`, `_fluorescente`, `_embutida`, `_emergencia`; `DistribuirLuminarias` |
| `Grupo_Interruptores` (legenda "Comandos") | `InsertSwitch`, `InsertSwitchParalelo`, `InsertSwitchIntermediario`, `Ponto_botao_campainha`, `Ponto_fotocelula` |
| `Grupo_Aterramento` | `Ponto_haste_aterramento`, `_caixa_inspecao`, `_bep`; `CondutorAterramento`, `CalcAterramento` |
| `Grupo_Quadros` | `Ponto_quadro_distribuicao`, `_quadro_comando`, `_quadro_medicao`, `_medicao_agrupada` |
| `Grupo_DadosQuadro` | `GerarPlanilha`, `CircuitosQuadro`, `AddCircuito` |
| `Grupo_Circuitos` | `DefinirCircuito`, `LigarInterruptor`, `IdentificarPontos` |
| `Grupo_Infra` | `InsertConduit`, `Ponto_caixa_passagem`, `ConectarEletrodutos`, `Add_Node`, `ListaVerticais`, `Cabo` |
| `Grupo_Calculos` | `CalcDemanda`, `CalcPressurizacao`, `CalcRecalque` |
| `Grupo_Documentos` | `GerarQuantitativos`, `LegendaSimbolos`, `PlanilhaNotas`, `GerarNotas`, `PintarSketches`, `GenerateReport` |
| `Grupo_3D` | `Generate3DSwitches`, `Generate3DConduits`, `Gerar3D` |
| `Grupo_Biblioteca` | `InsertEquipaments`, `InsertComponent`, `CreateModel`, `ListElements` |

- **Menus:** todo comando da bancada está no menu **Elétrica**, e todo comando nativo, inclusive os que saíram das barras, no menu **Desenho 2D**.
- Só no menu **Elétrica > Outros**: `InsertTugs` (a tomada TUG em Sketch, substituída pelas tomadas novas), `InsertOutlet` e `InsertLighting` (substituídos pelos pontos novos), `ComponentEletric`, `InsertWire`, `InsertCableTray`, `AddSpreadsheet`, `NewQuadro`, `GetSpaces`, `ReiniciarBancada`.
- **Legenda:** o `MenuText` de cada comando aparece embaixo do ícone nas barras próprias. Mantenha-o curto (até 24 caracteres) e único; a explicação vai no `ToolTip`. A preferência booleana `LegendaBotoes` em `BaseApp/Preferences/Mod/Circuits` desliga as legendas.
- `tests/unit/test_toolbars.py` falha se um comando ficar fora do menu, se uma barra ou grupo citar um comando que não existe, se uma barra própria passar de 8 botões, se faltar um ícone ou se a legenda for longa ou repetida.

## Inserção de símbolos na planta

Todo símbolo 2D (pontos, interruptores, tomada TUG) é posicionado por `ComponentInsertionMode`, em `UI/dialogs/ComponentInserter.py`:

| Ação | Efeito |
|---|---|
| Clique | Fixa o símbolo. Pontos e interruptores repetem até ESC, mantendo circuito, rotação e trava. |
| R | Gira 90°. |
| Espaço (ou A) | Alinha com o símbolo mais próximo: trava no eixo em que já está mais perto, depois no outro eixo, depois solta. |
| L | Liga ou desliga o alinhamento automático, que puxa o símbolo para o X ou o Y de um vizinho a menos de 10 pixels. |
| ESC | Encerra e apaga o símbolo ainda não fixado. |

- Começar outro comando de inserção encerra o anterior.
- A lógica é pura (`core/alinhamento.py`) e as teclas são testadas com o FreeCAD simulado em `tests/unit/test_insercao.py`.
- Para símbolos já colocados: selecione-os e use **Alinhar** (atalho `A, L`; o primeiro selecionado é a referência) ou **Distribuir** (`A, D`).

## Como os dados ficam no documento

Os comandos se encontram pelos objetos do documento, não por estado em Python:

- **Pavimentos e pastas:** um pavimento é um **nível da bancada BIM** (`BuildingPart` com `IfcType == "Building Storey"`; cota = `Placement.Base.z`, altura = `Height`, ou 3000 mm se for 0) ou, na falta de níveis, um grupo criado pela bancada (Label = nome) com as propriedades `Elevacao` (cota do piso, mm), `AlturaPavimento` (piso a piso, mm) e `Ativo`. Só um é o ativo; o nível do BIM ganha a propriedade `Ativo` quando é ativado, e a bancada nunca altera a cota nem a altura dele. Com níveis do BIM no projeto, `Novo projeto` não cria o Térreo e ativa o mais baixo. `AdicionarNivelBIM` cria um nível com `Arch.makeBuildingPart()`, define `IfcType`, a cota e `Height`, coloca-o no edifício do BIM (objeto com `IfcType == "Building"`), se houver, e o ativa. Os grupos da bancada ficam dentro de `Pontos_eletricos`, se existir. Dentro dele, uma subpasta por tipo de símbolo, marcada pela propriedade `pasta` (`tomadas`, `energia`, `iluminacao`, `interruptores`, `quadros`), com o nome mostrado de `core.pavimentos.PASTAS`. Todo símbolo novo (pontos, interruptores, tomada TUG, motores e luminárias do luminotécnico) é criado na subpasta do tipo dele e **desenhado na cota do pavimento** (`ComponentInsertionMode(cota=...)`). O pavimento da inserção é escolhido por `pavimentos.pavimento_para_insercao`: o nível ativo da bancada BIM (`ActiveView.getActiveObject("Arch")`), senão o pavimento ou a pasta dele selecionados na árvore, senão o pavimento ativo; o escolhido passa a ser o ativo. O símbolo recebe a propriedade `Pavimento` com o nome. **Cota no desenho:** o símbolo 2D fica no Z do piso do pavimento (`core.pavimentos.cota_de_desenho`), e só o 3D usa a altura de montagem: caixa 3D em cota do piso + `Altura3D` (`core.pavimentos.cota_3d`, `services.pavimentos.cota_3d`; `Altura3D`, ou `altura_piso` na tomada em Sketch, é sempre relativa ao piso). `Ponto` e `Switch` guardam a cota do piso na propriedade só de leitura `CotaPiso`, preenchida por `pavimentos.ajustar_cota` ao arquivar ou mover, e o `onChanged` deles (`objects.ponto.acompanhar_cota`) move o símbolo quando `CotaPiso` muda; mudar `Altura3D` não move o símbolo (não age ao abrir o arquivo). Projetos antigos ficam como estão até usar `AjustarCotas`. `MoverParaPavimento` leva os símbolos à cota do piso do pavimento novo e desloca os eletrodutos pela diferença de cota; o eletroduto guardado numa pasta não muda de Z. Sem níveis do BIM, `Novo projeto` cria o `Térreo` e o ativa. O pavimento de um símbolo é o da pasta em que ele está; a propriedade `Pavimento` só vale se ele for tirado da pasta. As caixas 3D e os eletrodutos 3D somam a cota do pavimento à altura de montagem (`Altura3D` é sempre medida a partir do piso). Objetos que não são símbolos (eletrodutos, textos) não são arquivados. Se o FreeCAD recusar o nome repetido de uma subpasta (preferência `DuplicateLabels` desligada), ela se chama `<pavimento> - <tipo>`.
- **Cor dos Sketches:** todo Sketch criado pela bancada (tomada TUG, fiação, unifilar) nasce com `LineColor` e `PointColor` pretos (`services/estilo.py`), porque o branco padrão do FreeCAD some sobre o fundo claro. `PintarSketches` repinta os de projetos antigos.
- **Tomada em Sketch:** propriedade `tipo == "tomada"`, além de `Fase`, `neutro`, `terra` e `altura_piso`.
- **Objetos FeaturePython:** `obj.Proxy.Type` vale `Ponto`, `Switch`, `Lighting`, `Outlet` ou `ConduitPath`.
- **Ponto elétrico (`Ponto`):** a propriedade `Simbolo` é a chave de `core.simbolos.CATALOGO`. `Potencia` em VA, `FatorPotencia`, `Tensao`, `Ligacao` (`F+N`, `F+F`, `3F`), `Circuito` e `Quadro` (vazio vale para qualquer quadro). `MontarCircuitos` também lê `Outlet`, `Lighting` e as tomadas em Sketch.
- **Categorias sem carga** (`core.simbolos.SEM_CARGA`): `QUADRO`, `COMANDO` (botão de campainha e fotocélula), `PASSAGEM` (caixa de passagem) e `ATERRAMENTO` (haste, caixa de inspeção, BEP) não entram em `MontarCircuitos`, na demanda nem na fiação desenhada. `COMANDO` se comporta como interruptor: `LigarInterruptor` aceita o botão e a fotocélula, a rede os trata como `tipo="interruptor"` e a identificação mostra `F+R` (botão) e `F+N+R` (fotocélula). A campainha é `ENERGIA` com `tipo_circuito` ILUM, então é comandada como uma luminária. A caixa de passagem entra na rede como `tipo="passagem"` (nó sem circuito) e vai para a pasta `eletrodutos`; o aterramento fica fora da rede e vai para a pasta `aterramento`, com alturas negativas (abaixo do piso).
- **Condutor de aterramento:** linha (Draft Wire) com a propriedade `SecaoAterramento` (enum 16 a 70 mm²), marcada por `CondutorAterramento`, pintada de verde e guardada na pasta `aterramento`. Os quantitativos somam o comprimento por seção com `PERDA_CABO_ATERRAMENTO` e um conector haste-cabo por haste, no grupo "Aterramento".
- **Quadros na planta:** também são `Ponto`, com `Simbolo` de categoria `QUADRO` (`quadro_distribuicao`, `quadro_comando`, `quadro_medicao`, `medicao_agrupada`). Não são carga: `MontarCircuitos` e `CalcDemanda` os ignoram. `Descricao` guarda a sigla (QD1, QC, QM, CM), `Medidores` a quantidade de medidores (só nos de medição) e `Circuito`, vazio por padrão, o circuito que alimenta o quadro. `GerarPlanilha` com um símbolo de quadro selecionado cria a planilha para ele: copia a sigla para a identificação e grava o nome da planilha na propriedade `Planilha` do símbolo.
- **Componentes do quadro:** `ComponentesQuadro` lê a planilha do quadro e recria a planilha `Componentes_<nome do quadro>` (propriedade `componentes_de`) com item, especificação, quantidade e unidade.
- **Medição no unifilar:** o medidor é desenhado na entrada quando a `origem` do quadro é a sigla de um símbolo de medição da planta, ou começa com QM, CM ou "medi". O unifilar também identifica o barramento de fases e desenha as barras de neutro e de terra.
- **Escala dos símbolos:** `Ponto` e `Switch` têm a propriedade `Escala` (1 = normal), que multiplica `Tamanho` ou `RaioSimbolo`. A tomada em Sketch ganha `Escala` quando o comando `EscalaSimbolos` a redesenha. Sem seleção, o comando escala todos os símbolos e grava o valor em `EscalaSimbolos` (`BaseApp/Preferences/Mod/Circuits`), que é a escala dos próximos pontos. `Outlet` e `Lighting` antigos não têm escala.
- **Fiação:** `Cabo` desenha um Sketch de fiação por ponto (`Ponto`, `Outlet`, `Lighting` e tomada em Sketch; não em quadros nem interruptores), na pasta `fiacao` (*Fiação*) do pavimento do ponto (`pavimentos.pasta_do_pavimento`; fora de um pavimento, no grupo `Cabos`), com a propriedade `fiacao_de` = nome do ponto. Fases e neutro vêm de `Ligacao`; o tamanho acompanha o símbolo. Repetir o comando apaga a fiação anterior e redesenha.
- **Circuito e comando:** `DefinirCircuito` grava `Circuito` (e `Quadro`) nos pontos selecionados. `LigarInterruptor` grava a mesma letra em `Comando` no interruptor e nos pontos de luz selecionados, e copia para o interruptor o circuito da primeira luz. A ligação é só essa letra em comum; não há link entre os objetos.
- **Identificação:** um texto de duas linhas por símbolo, marcado pela propriedade `identificacao_de` (nome do símbolo) e guardado na pasta `circuitos` (*Circuitos*) do pavimento dele; os de símbolos fora de um pavimento, no grupo `Identificacao_pontos`. O texto fica na cota do símbolo e mostra circuito, comando e potência (`C1 · a · 100 VA`), e os cabos que chegam à caixa (`#2,5 F+N+T`; luminária comandada `R+N+T`; interruptor simples `F+R`, paralelo `F+2R`, intermediário `4R`). A seção vem da planilha de circuitos do quadro do ponto (`mapa_de_secoes`); sem ela, 1,5 mm² para iluminação e interruptores e 2,5 mm² para o resto. É recriado por `IdentificarPontos` e, se já existir, atualizado sozinho quando o circuito ou o comando mudam por esses comandos. Editar a propriedade à mão não atualiza o texto.
- **Quadro:** planilha `Spreadsheet::Sheet` com a propriedade `quadro`. A linha 3 tem os dados, com aliases iguais a `core.planilha.CABECALHO_QUADRO`, que são lidos pelo unifilar. Quando ligada a um símbolo de quadro (`vincular_planilha`), ela, a planilha de circuitos, a de componentes e o diagrama unifilar vão para a pasta do símbolo (`pavimentos.guardar_junto`), por exemplo *Térreo > Quadros e medição*.
- **Circuitos do quadro:** planilha própria, `Circuitos_<nome do quadro>`, ligada ao quadro pela propriedade `circuitos_de`. Linha 1: título e ajuda; linha 2: títulos das colunas; da linha 3 em diante, um circuito por linha, nas colunas de `core.planilha.PLANILHA_CIRCUITOS` (circuito, descrição, potência, tensão, fases como texto "RS", corrente, cabo, disjuntor, curva, DR, sensibilidade, neutro e terra; sim/não como S/N). É criada junto com o quadro e pode ser preenchida à mão. Tudo lê os circuitos por `planilhas.ler_circuitos(quadro)`, que devolve os dicionários com as chaves de `COLUNAS_CIRCUITO`; o unifilar e os componentes usam `ler_circuitos_completos`, que calcula corrente, cabo e disjuntor deixados em branco (`core.quadro.completar`) sem gravar na planilha.
- **Formato antigo:** quadros de versões anteriores guardam os circuitos na própria planilha do quadro, da linha 6 em diante (`COLUNAS_CIRCUITO`). Enquanto a planilha de circuitos não existe, eles são lidos de lá; quando ela é criada, são levados para ela e apagados da planilha do quadro.
- **Circuitos montados:** `MontarCircuitos` soma os pontos por `Circuito`, dimensiona e grava uma linha por circuito na planilha de circuitos do quadro. Uma linha com o mesmo número é atualizada no lugar; as outras ficam como estão.
- **Demanda:** `CalcDemanda` grava `potencia_instalada` e `potencia_demanda` (kW) na linha 3 do quadro, e o unifilar as mostra.
- **Motores calculados:** `CalcPressurizacao` e `CalcRecalque` podem inserir um `Ponto` do tipo `ponto_forca` com a potência aparente, a tensão e a ligação do motor; ele entra em `MontarCircuitos` como qualquer ponto.
- **Diagrama:** grupo com Label `diagrama_<quadro>` e propriedade `quadro_origem` com o nome da planilha, recriado a cada geração. Os diagramas são empilhados, um por quadro.
- **Legenda:** grupo `Legenda_simbolos`, recriado a cada geração na posição em que estava, com os símbolos do catálogo usados e os tipos de interruptor usados (`core.simbolos.INTERRUPTORES`, desenho de `geometria_interruptor`).
- **Luminotécnico:** `DistribuirLuminarias` usa o retângulo envolvente (plano XY) do objeto selecionado como ambiente e cria um `Ponto` de iluminação por posição da malha, com a propriedade `Ambiente` = nome desse objeto. Repetir o comando no mesmo objeto apaga os pontos com esse `Ambiente` e cria de novo.
- **Notas:** planilha com a propriedade `notas_do_projeto`, uma nota por linha na coluna A, da linha 3 em diante. `GerarNotas` recria o grupo `Notas_projeto` com o título e as notas numeradas, na posição em que estava ou embaixo da legenda.
- **Rede de eletrodutos:** um eletroduto é um `ConduitPath` ou um Draft Wire com `Diametro` e `Altura3D` (marcado por `ConectarEletrodutos` ou por `Generate3DConduits`). `ConectarEletrodutos` marca as linhas selecionadas (ou trata todos os eletrodutos), guarda-as na pasta `eletrodutos` do pavimento ativo, se ainda não estiverem num pavimento, e puxa vértices e trechos a até 300 mm de uma caixa para cima dela (`core.rede.encaixar`). Para o snap do Draft ao desenhar, `Ponto` e `Switch` têm um vértice no ponto de inserção. `core.rede.analisar` monta o grafo por pavimento (vértices a até 50 mm são o mesmo nó; ponta sobre um trecho vira derivação em T), liga cada caixa ao nó a até 50 mm (caixa no meio de um trecho, sem vértice, fica de fora), e roteia cada circuito pelo caminho mais curto a partir do quadro (`Quadro` do ponto, ou o quadro de distribuição/comando mais próximo pela rede). Seção e condutores vêm da planilha de circuitos do quadro ou, sem ela, dos pontos; o terra vai sempre. A vertical é a diferença entre a `Altura3D` do eletroduto e a altura da caixa, ambas em relação ao piso. `ListaVerticais` recria a planilha com a propriedade `lista_de_verticais`.
- **Quantitativos:** `GerarQuantitativos` lê o documento a cada clique (nada é gravado nele) e grava `<nome>.csv`, `<nome>.xlsx` e `<nome>.pdf` com o mesmo nome base escolhido. Entram: pontos (`Ponto`, por legenda, tensão e potência), quadros da planta, interruptores (por `Tipo`), `Outlet`, `Lighting` e tomadas em Sketch; uma caixa por ponto (`core.quantitativos.caixa_do_simbolo`); eletrodutos pelos objetos com `Diametro` (ConduitPath, ou Draft Wire já marcado, que tem `Altura3D`) e as verticais, com `PERDA_ELETRODUTO`; fios por seção e função (`core.rede`); e `core.quadro.componentes` de cada quadro. O XLSX tem as abas Quantitativo (total), Por pavimento, Verticais e Fiação por circuito; as três últimas também saem em `<nome>_pavimentos.csv`, `<nome>_verticais.csv` e `<nome>_circuitos.csv` e no PDF. O pavimento de cada item é o de `pavimentos.pavimento_do_objeto`; o do quadro é o da pasta da planilha ou do símbolo ligado a ela; os fios por pavimento vêm de `fios_por_pavimento` de `core.rede.juntar`. Fora de um pavimento, *Sem pavimento*. O CSV usa ponto e vírgula, vírgula decimal e UTF-8 com BOM; o XLSX é escrito por `core/exportar.py`, sem openpyxl; o PDF usa reportlab e, se faltar, os outros dois são gravados mesmo assim. A seção de materiais do relatório PDF (`GenerateReport`) usa o mesmo levantamento.
- **Caixas e tubos 3D:** objeto `<nome da origem>_3D`, substituído a cada geração e guardado por `pavimentos.guardar_3d` na subpasta 3D da pasta do elemento (grupo com a propriedade `pasta_3d` = chave da pasta, Label `<tipo> 3D`), por exemplo *Térreo > Tomadas > Tomadas 3D* e *Térreo > Eletrodutos > Eletrodutos 3D*. Objetos fora de um pavimento deixam o 3D na raiz (ou em `Equipamentos`, para a tomada em Sketch).
- **Unidades:** comprimentos em mm no FreeCAD; correntes em A; seções em mm².

## Receitas

**Novo comando**
1. Coloque a lógica em `services/`, ou em `core/` se não precisar do FreeCAD.
2. Crie a classe em `commands/` com `Activated` e `GetResources`, usando `recursos()` e `documento_ou_aviso()` de `commands/_base.py`.
3. Registre no fim do módulo com `Gui.addCommand("MeuId", MinhaClasse())`.
4. Acrescente o ID em uma lista de `init_gui.py`, de preferência a de um grupo existente (veja "Barras e legendas"). Se o módulo for novo, importe-o em `Initialize`.

**Novo cálculo ou tabela de norma:** função pura em `core/functions/` ou dados em `core/tables/`, com teste em `tests/unit/`. Documente unidades no docstring.

**Novo cálculo com formulário:** função `dimensionar(...)` e `relatorio(resultado)` em `core/functions/Predial/`, a lista de campos em `core/formularios.py` e um comando em `commands/calculos.py` que abre o `CalculoDialog`. As chaves dos campos são os nomes dos argumentos de `dimensionar`. Regras dos formulários, cobradas por `tests/unit/test_formularios.py`:
- no máximo 4 campos fora das opções avançadas (`"avancado": True` nos demais);
- todo campo tem `dica`; campos numéricos têm `minimo` e `maximo` do mesmo tipo do valor;
- onde houver valores típicos, ofereça uma lista com `preenche`, que preenche os campos avançados (veja `LAMPADAS`).

O `CalculoDialog` recalcula a cada mudança, guarda os valores usados em `BaseApp/Preferences/Mod/Circuits/Formularios/<chave>` e os traz de volta na próxima abertura; **Restaurar padrões** volta aos valores iniciais.

**Novo objeto FeaturePython:** siga `objects/switch.py` (classe com `Type`, ViewProvider e `create_*`). Depois de usado em projetos, o nome do módulo e da classe ficam congelados.

**Novo diálogo:** arquivo em `UI/dialogs/`, devolvendo os dados por um método como `get_dados()`. Quem grava no documento é o `service`, chamado pelo comando.

**Novo símbolo de ponto elétrico:** acrescente a entrada em `core.simbolos.CATALOGO` e o desenho em `_unitario`, rode `python tools/gerar_icones_simbolos.py` para gerar o ícone, e inclua `Ponto_<símbolo>` na lista de um grupo em `init_gui.py`. O comando é criado sozinho.

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
- No FreeCAD aberto, **Elétrica > Outros > Reiniciar Bancada** recarrega o código sem fechar o programa.

## Ambiente nesta máquina

- O FreeCAD 1.1 lê `%APPDATA%\FreeCAD\v1-1\Mod\`. Esta cópia é a mais recente.
- `%APPDATA%\FreeCAD\Mod\eletroAlpha` é um clone antigo do mesmo repositório, e o FreeCAD 1.1 não o carrega. Não edite lá.
- `v1-1\Mod\Circuits-FreeCAD` é outra instalação, mais antiga, com a classe `Circuits` e também o nome "Engenharia". Ela registra os mesmos IDs de comando, e vale o último registro. Ao testar, ative a bancada pela chave `CircuitsWorkbench`.
- O `origin` deste clone é `llosinskas/eletroAlpha`, enquanto `package.xml` e `pyproject.toml` apontam para `llosinskas/Circuits-FreeCAD`.
- `venv/` é local e ignorada pelo git. O FreeCAD não a usa.

## Problemas conhecidos

Todos foram confirmados no código ou em execução e já existiam antes da reorganização, que preservou o comportamento. Corrija com teste, e atualize esta lista.

**Afetam o uso**
- `UI/insert_circuit.py` (`AddSpreadsheet`): os botões e o movimento do mouse usam `self.label1` e `self.label2`, que não existem. O formulário também não grava dados.

- `core/circuitos.py`: o dimensionamento de `MontarCircuitos` só verifica capacidade de condução (método B1, PVC) e Ib ≤ In ≤ Iz. Não considera queda de tensão, agrupamento, temperatura nem curto-circuito.
- `core/functions/Predial/demanda.py`: fatores de demanda de guias de instalações residenciais, transcritos de memória e não conferidos com a fonte. Cada concessionária tem tabela própria. Não calcula a demanda do edifício (diversidade entre apartamentos).
- `core/functions/Predial/pressurizacao.py`: áreas de fresta, número de portas abertas e acréscimos (25 % não identificados; 15 % duto metálico, 25 % alvenaria) precisam ser conferidos com a edição vigente da NBR 14880 e com o Corpo de Bombeiros.
- `core/functions/Predial/recalque.py`: singularidades estimadas em 30 % do comprimento e rendimento da bomba de 50 % são suposições, editáveis só no código ou no formulário (rendimento).
- `core/formularios.py`, `LAMPADAS`: fluxo e potência das lâmpadas da lista são valores aproximados de mercado, não de um fabricante.
- `core/functions/Predial/luminotecnico.py`: o fator de utilização vem de uma curva genérica por índice do local, e as iluminâncias por ambiente são valores usuais, ambos não conferidos com a NBR ISO/CIE 8995-1 nem com catálogo. O ambiente é sempre tratado como retângulo reto.
- `core/functions/Predial/aterramento.py`: resistividades de solo típicas e λ = 2·(H_n − 1) como aproximação da tabela da IEEE 142 para hastes em linha; não calcula malha nem hastes em triângulo ou quadrado.
- `core/circuitos.py`, `dimensionar`: o disjuntor de motores é escolhido só pela corrente nominal, sem considerar a partida.
- `services/circuitos.py`, `_de_tomada_sketch`: lê potência e tensão das tomadas em Sketch pelo número bruto, porque elas são gravadas sem unidade. Falta confirmar no FreeCAD e migrar para grandezas com unidade.
- `core/quadro.py`: correntes comerciais de DR e de barramento, quantidade de DPS e módulos da caixa são regras gerais, não de um fabricante. O DR é sempre por circuito; não há DR geral nem agrupamento de circuitos em um DR.
- As pastas Circuitos e Fiação do pavimento, as planilhas e o diagrama do quadro na pasta do símbolo, o quantitativo por pavimento, as subpastas 3D dos elementos, campainha, fotocélula, caixa de passagem e o módulo de aterramento (símbolos, condutor de cobre nu, resistência de terra), a cota no desenho (símbolo no piso do pavimento, 3D na altura de montagem, `CotaPiso` e o `onChanged` dos objetos), a inserção no nível ativo do BIM, a identificação dos cabos, os interruptores na legenda, a rede de eletrodutos (Conectar às caixas, fios, verticais e o vértice de snap nos símbolos), o botão Quantitativos (leitura dos objetos reais e arquivos abertos no Excel/LibreOffice), a planilha de circuitos do quadro (criação, migração do formato antigo, leitura pelo unifilar), a criação de níveis do BIM (`Arch.makeBuildingPart` nunca foi chamado de verdade), os níveis do BIM como pavimentos (nunca testados com um BuildingPart real), a cor preta dos Sketches, os pavimentos e as pastas dos símbolos, o formulário de cálculo novo (opções avançadas, valores guardados, cálculo automático), o luminotécnico, as notas do projeto, a fiação em todos os pontos, a escala dos símbolos, os símbolos de quadro e medição, a lista de componentes do quadro, o medidor e os barramentos no unifilar, os botões de grupo (lista suspensa), as teclas da inserção (Espaço, R, L), os comandos Alinhar, Distribuir, Definir circuito, Ligar interruptor e Identificar pontos, os pontos novos, a legenda, `MontarCircuitos`, os cálculos prediais e as mudanças do unifilar têm teste unitário da lógica, mas ainda não foram executados no FreeCAD real: rode o `smoke_gui.py` e atualize este item.

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
