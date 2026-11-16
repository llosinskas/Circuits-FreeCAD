# Revisão técnica e roadmap: bancada de elétrica predial

Data: 2026-11-16 · Base: commit `66c4db0` ("Reorganiza a bancada em camadas")

Este documento tem duas partes: (1) o que está errado ou frágil hoje, com evidência, e (2) o caminho para a bancada fazer um projeto elétrico predial completo, do levantamento de cargas às pranchas, conforme a NBR 5410.

---

## 1. Diagnóstico geral

**O que está bom**

- A reorganização em camadas (`core` → `services`/`objects`/`UI` → `commands`) está correta, e `test_architecture.py` a protege. É a base certa para crescer.
- O carregamento preguiçoso da bancada (`init_gui` sem importar comandos) e o `smoke_gui.py` com retrato JSON são práticas de bancada madura.
- `core/qet.py` e `core/simbologia.py` estão limpos, puros e testáveis.
- Os objetos `Switch`, `Lighting` e `Outlet` seguem o padrão FeaturePython correto (`_add_properties` idempotente, `dumps`/`loads`).

**O problema central: não existe um modelo de dados elétrico**

Hoje o "projeto" está espalhado em três representações que não conversam:

| Conceito | Onde vive hoje | Problema |
|---|---|---|
| Tomada | Sketch com `tipo == "tomada"`, **e** `Outlet` FeaturePython, **e** `App::Link` da biblioteca | Três modelos, cada comando enxerga um. A descida de eletroduto só acha a Sketch; o PDF conta as três separadas. |
| Circuito | Linha de planilha, valores gravados como texto (`'` na frente) | Não dá para calcular, validar ou ligar a pontos na planta. |
| Quadro | `Spreadsheet::Sheet` com propriedade `quadro` | Planilha é ótima como *visão*, ruim como *fonte da verdade*. |
| Grandezas | `Potencia = "600VA"` (string), `potencia = 100` em `PropertyPower` | Ver bug U1: unidades internas do FreeCAD. |

Sem um modelo `Ponto → Circuito → Quadro` ligado por propriedades `App::PropertyLink`, nenhuma das funções-chave de um software predial (quadro de cargas automático, balanceamento, dimensionamento, fiação por trecho, lista de materiais) é possível. **Esta é a decisão de arquitetura mais importante do roadmap** (Fase 0).

---

## 2. Bugs novos encontrados

> Atualização: B1, B2 e B3 foram corrigidos junto com os pontos elétricos em planta e o comando `MontarCircuitos`, assim como `ultima_linha`, o Label do diagrama no PDF, o quadro com nome repetido e o cancelamento do diálogo de quadro. Os demais continuam abertos.

Não constam em "Problemas conhecidos" do `AGENTS.md`. Todos verificados no código; os marcados com (exec.) foram executados aqui.

### Afetam o uso

| # | Onde | Problema |
|---|---|---|
| B1 | `commands/gerar_unifilar.py`, `AddCircuito` | `for quadro in quadros: adicionar_circuito(quadro, dados)` grava o circuito em **todos** os quadros do documento. Falta escolher o quadro de destino no diálogo. |
| B2 | `services/unifilar.py`, `gerar_diagramas` | Todos os quadros são desenhados na mesma origem `(0,0,0)`: com dois quadros os diagramas se sobrepõem. Também ficam no mesmo espaço 3D da planta. |
| B3 | `services/unifilar.py` | Remove o diagrama anterior por `getObject(f"diagrama_{Label}")`, mas cria com nome `"diagrama {Label}"`. Labels com acento ou caracteres especiais geram nome sanitizado diferente, e o diagrama antigo não é apagado (duplica). |
| B4 | `services/pdf_generator.py`, `_get_calculos_table` | Lê a **linha 2** (cabeçalhos) em vez da linha 3 (dados), então "Tensão" mostra o texto `tensao`. Além disso percorre **todas** as planilhas, não só as que têm `quadro`. |
| B5 | `services/eletrodutos.py`, `_descidas_para_tomadas` | Usa `listar_tomadas`, que só acha Sketches. Tomadas `Outlet` e interruptores não recebem descida. |
| U1 | `services/tomadas.py`, `_valores_padrao` | `sketch.potencia = 100` em `App::PropertyPower` e `sketch.Tensao = "220"` em `PropertyElectricPotential` usam a unidade **interna** do FreeCAD (mm·kg·s), em que 1 W = 10⁶ unidades. O valor gravado provavelmente é 100 µW e 0,22 mV. **Confirmar no FreeCAD** com `App.Units.Quantity(sketch.potencia).getUserPreferred()`; corrigir com `"100 W"` e `"220 V"`. |

### Cálculos

| # | Onde | Problema |
|---|---|---|
| C1 | `core/functions/Cabo/queda_tensao.py`, `queda_tensao_trifasico` | (exec.) `comprimento(resistencia+reatancia)` gera `TypeError: 'int' object is not callable` (falta `*`). O docstring diz R e X em mΩ/km, mas a fórmula com `/10` só fecha com **mΩ/m** e L em m (Mamede): ΔV% = √3·I·L·(R cosφ + X senφ) / (10·N·V). Erro de 1000×. |
| C2 | `tests/unit/test_queda_tensao.py` | **Resolve a pendência do AGENTS.md.** (exec.) A fórmula monofásica dá 7,25 mm² (a trifásica, 6,28). O "10 mm²" esperado é a **seção comercial** seguinte. As duas coisas estão certas; falta a função `secao_comercial(s)` (escala 1,5 · 2,5 · 4 · 6 · 10 · 16 …). O teste deve comparar `secao_comercial(calculada) == 10`. |
| C3 | `core/tables/NBR5410/fator_correcao_temperatura_ar_livre.py` | EPR/XLPE a 40 °C está **0,96**; a Tabela 40 da NBR 5410 dá **0,91**. O mesmo valor errado foi copiado para `NBR14039/fator_correcao_temp_ar_livre.py`. |
| C4 | `core/tables/NBR5410/fator_correcao_temperatura_enterrado.py` | A temperatura de referência no solo é **20 °C**, não 30 °C. A lista deveria ser `[10, 15, 25, 30, 35, …]` (pula 20). Os valores de EPR/XLPE já estão nessa ordem, então hoje 20 °C → 0,96 está deslocado. PVC correto: 1,10 · 1,05 · 0,95 · 0,89 · 0,84 · 0,77 · 0,71 · 0,63 · 0,55 · 0,45 (o arquivo repete 0,89, por isso 15 itens e o `ValueError` já conhecido). |
| C5 | `core/tables/tab_cabo_pvc_2_3.py`, `A1_3` | A coluna de 23 itens (o `ValueError` conhecido) é porque **falta 328 A em 300 mm²**, entre 286 e 390. |
| C6 | `core/functions/Cabo/Cabo.py`, `Metodos` | Comentário de `C` diz "enterrados no solo"; o método C é **cabo sobre parede**. Enterrado é D. (`tables/NBR5410/metodos.py` está certo.) |
| C7 | `core/functions/Cabo/corrente_partida_motor.py` | `corrente_grupo_motores` não calcula partida, só soma In·FS. Para alimentador de motores o critério usual é 1,25·In do maior + Σ demais. Renomear ou corrigir. |
| C8 | `objects/outlet.py` | `Potencia` é `PropertyString` ("600VA"), impossível de somar. Deve ser `App::PropertyPower` / VA numérico + `FatorPotencia`. |

### FreeCAD

| # | Onde | Problema |
|---|---|---|
| F1 | `objects/conduit_path.py` | `Type` é atributo de instância criado no `__init__`, sem `dumps`/`loads` (os outros objetos têm). Também não tem `onDocumentRestored` para migrar propriedades novas. Padronizar com `switch.py`. |
| F2 | Todos os comandos que alteram o documento | Nenhum usa `doc.openTransaction()`/`commitTransaction()`. Um "Gerar unifilar" vira dezenas de passos no Ctrl+Z, ou nenhum. |
| F3 | `unifilar`, `caixas_3d`, `eletrodutos` | Estratégia "apaga e recria" quebra qualquer referência externa (TechDraw, expressões, Links). Preferir atualizar o `Shape` do objeto existente. |
| F4 | `core/tables/*` | `pandas` só para guardar tabelas de 10 linhas: importação lenta, dependência pesada, e o erro de colunas só aparece no import. Dicionários/CSV + teste de consistência resolvem. |

---

## 3. Arquitetura-alvo

### 3.1 Modelo de dados (FeaturePython, links no documento)

```
Edificacao (App::DocumentObjectGroup + props)
└── Pavimento  ── referencia Arch::BuildingPart / nível
    └── Ambiente  ── link para Arch::Space (área, perímetro, tipo: banheiro, cozinha…)

PontoEletrico (base de Outlet, Lighting, Switch, Equipamento)
    Potencia [VA], FatorPotencia, Tensao, Fases, AlturaMontagem,
    Ambiente -> Ambiente, Circuito -> Circuito, IfcType

Circuito
    Numero, Tipo (ILUM, TUG, TUE, ALIM), Quadro -> Quadro,
    Pontos (calculado: quem aponta para mim), Fases atribuídas,
    Metodo, Material, Comprimento (do roteamento), ResultadoCalculo (JSON)

Quadro
    Origem -> Quadro (hierarquia: QGBT → QD), Tensao, Esquema (TN-S, TN-C-S, TT),
    Icc no ponto, Disjuntor geral, DPS, Barramento, Alimentador -> Circuito

TrechoInfra (eletroduto / eletrocalha)
    Wire base, Diametro, Material, Altura, Circuitos que passam (calculado)
```

- A planilha do quadro vira **saída** (quadro de cargas gerado), não entrada.
- Pontos que já existem como Sketch `tipo == "tomada"` ganham um migrador (comando "Converter tomadas antigas").
- Cada objeto declara `IfcType` (`IfcOutlet`, `IfcLightFixture`, `IfcSwitchingDevice`, `IfcElectricDistributionBoard`, `IfcCableCarrierSegment`, `IfcCableSegment`) para exportar IFC pela bancada BIM.
- Os nomes `objects/switch.py`, `lighting.py`, `outlet.py`, `conduit_path.py` e suas classes **ficam congelados**. Os novos objetos entram em módulos novos.

### 3.2 Motor de cálculo (`core/`, puro e testado)

Um pipeline por circuito, cada etapa uma função pura com teste contra exemplo resolvido (Mamede, Cotrim, Creder):

1. **Corrente de projeto** Ib (mono/bi/tri, motores).
2. **Capacidade de condução**: Tabelas 36–39 completas (Cu/Al, PVC/EPR/XLPE, 2 e 3 carregados, A1…G), fatores de temperatura (40), resistividade do solo (41), agrupamento (42–45).
3. **Seção mínima** (Tabela 47: 1,5 mm² iluminação, 2,5 mm² força).
4. **Queda de tensão** (limites 6.2.7: 4 % a partir do ponto de entrega + total 7 %) com R e X por seção.
5. **Proteção**: Ib ≤ In ≤ Iz e I2 ≤ 1,45·Iz; curvas B/C/D; escala comercial de disjuntores.
6. **Curto-circuito**: Icc no fim do circuito, seção mínima térmica (k²S² ≥ I²t), comprimento máximo para atuação.
7. **Neutro e PE** (Tabela 48 e 58), redução de neutro só com condições da 6.2.6.2.
8. **DR obrigatório** (5.1.3.2.2): banheiros, áreas externas, cozinhas, copas, lavanderias, garagens, e pontos em área molhada.
9. **Previsão de cargas** (9.5.2): iluminação 100 VA nos 6 m² iniciais + 60 VA a cada 4 m²; TUG por perímetro (1 a cada 5 m; cozinha/área de serviço 1 a cada 3,5 m, 600 VA nas 3 primeiras); mínimo por banheiro.
10. **Demanda** (fatores por tipo de carga, critério da concessionária configurável) e **balanceamento de fases** (heurística gulosa por maior carga + troca local; desequilíbrio alvo < 10 %).
11. **Eletroduto**: taxa de ocupação 53 % / 31 % / 40 % (1, 2, ≥3 cabos) e escolha do diâmetro comercial.

Saída: um objeto de resultado com cada critério, o valor que dominou e as violações, para a interface mostrar "seção 6 mm² definida por queda de tensão".

### 3.3 Uso correto do FreeCAD

- **Planta**: pontos inseridos com `Gui.Snapper` do Draft (snap em parede, em ponto, ortogonal) em vez de clique livre; símbolos como Shape 2D do próprio FeaturePython, com escala ligada à escala da prancha.
- **Arquitetura**: ler `Arch::Space` (área, perímetro, `SpaceType`) e `BuildingPart` (níveis). O comando `GetSpaces` já existe; virar a entrada da previsão de cargas. Importar IFC de arquitetura pelo BIM nativo.
- **Pranchas**: diagrama unifilar, quadro de cargas, legenda e plantas em **TechDraw** (DrawViewPart da planta 2D, DrawViewSpreadsheet ou DrawViewSymbol SVG para quadros), com carimbo ABNT. Nada de texto Draft solto no espaço 3D.
- **Undo**: toda alteração dentro de `openTransaction("Circuits: …")`.
- **Recompute reativo**: propriedades calculadas (`Comprimento`, `Corrente`, `Secao`) atualizadas em `execute`; o usuário muda a potência e o quadro de cargas muda sozinho.
- **Migração**: `onDocumentRestored` em cada objeto adiciona propriedades novas e converte formatos antigos.
- **Unidades**: só `App.Units.Quantity` com unidade explícita ("100 W", "220 V", "2800 mm").

---

## 4. Roadmap

Estimativas em semanas de uma pessoa. Cada fase termina com algo usável.

### Fase 0: Fundação (2–3 sem.)

Objetivo: parar de acumular dívida antes de construir em cima.

1. Corrigir B1–B5, U1, C1–C8, F1, e os itens "Afetam o uso" do AGENTS.md (`ultima_linha`, diagrama no PDF, `doc.Spreadsheet`, cancelar diálogo, `AddSpreadsheet`). Um teste por correção.
2. `secao_comercial()` e destravar `test_queda_tensao.py`.
3. Tabelas de `core/tables` para dicionários/CSV com teste de consistência (todas as colunas do mesmo tamanho, 30 °C = 1,00 no ar, 20 °C = 1,00 no solo). Remover `pandas`, `scipy`, `sympy`, `matplotlib` das dependências obrigatórias.
4. Transações em todos os comandos (F2).
5. CI no GitHub Actions: `unittest` + `ruff`; depois `FreeCADCmd` headless (AppImage Linux) rodando a parte não-GUI do smoke.
6. Arquivo `LICENSE` (MIT, como declarado).

### Fase 1: Modelo de dados e motor de cálculo (4–6 sem.)

1. Objetos `Circuito` e `Quadro` (seção 3.1), `PontoEletrico` como base; `Outlet`/`Lighting`/`Switch` ganham `Circuito`, `Potencia` numérica e `Ambiente` via `onDocumentRestored`.
2. Tabelas 36–48 completas em `core/tables/NBR5410/`.
3. Pipeline de dimensionamento (seção 3.2, itens 1–8) com testes contra exemplos de livro.
4. Painel de tarefas "Circuito": escolher pontos na seleção, ver o cálculo com o critério dominante e violações em vermelho.
5. Quadro de cargas gerado (planilha como visão) e balanceamento de fases.

**Entregável**: desenhar pontos, agrupar em circuitos, e ter o quadro de cargas dimensionado e balanceado.

### Fase 2: Planta e arquitetura (3–4 sem.)

1. Ambientes a partir de `Arch::Space`; previsão de cargas automática (9.5.2) com relatório de "mínimos da norma atendidos?".
2. Inserção com snap e rotação na parede, alinhada à face.
3. Anotação automática dos pontos (potência, circuito, comando: "100 VA · 3 · a").
4. Pavimentos (níveis do BIM) e filtro de visibilidade por pavimento.
5. Unificar a biblioteca `Componentes/` com os objetos paramétricos: o `.FCStd` vira só a aparência 3D (Link), o dado elétrico fica no FeaturePython.

### Fase 3: Infraestrutura e fiação (4–6 sem.) — o diferencial

1. Rede de eletrodutos como **grafo** (nós = caixas e pontos, arestas = trechos), montada de Draft Wires/ConduitPath com tolerância de conexão.
2. Roteamento de cada circuito do quadro até seus pontos (caminho mínimo no grafo); comprimento real alimenta a queda de tensão.
3. Por trecho: quais circuitos passam, quantos condutores, fator de agrupamento real, taxa de ocupação e diâmetro mínimo.
4. Simbologia de fiação na planta gerada automaticamente (fase/neutro/retorno/terra, com número do circuito) — o código em `services/cabos.py` já desenha os traços.
5. Caixas de passagem, curvas, luvas; eletrocalhas e leitos (`InsertCableTray`, hoje só aviso); descidas para **todos** os pontos (B5).
6. 3D atualizado no lugar (F3), com cortes para compatibilização.

### Fase 4: Quadros e entrada de energia (3 sem.)

1. Hierarquia de quadros (QGBT → QDs), dimensionamento de alimentadores com demanda.
2. Padrão de entrada configurável por concessionária (tabela de categorias de atendimento em CSV, editável pelo usuário).
3. Diagrama unifilar automático em TechDraw (um por quadro, sem sobreposição — B2), com DR, DPS, barramentos.
4. Diagrama de montagem do quadro (vista frontal com módulos DIN) e QElectroTech como exportação além de importação.

### Fase 5: Documentação do projeto (3 sem.)

1. Pranchas TechDraw com carimbo ABNT: plantas por pavimento, unifilares, quadros de cargas, legenda, detalhes.
2. Memorial descritivo e de cálculo em PDF (o `pdf_generator` com ReportLab é a base), lendo o modelo e não as planilhas.
3. Lista de materiais completa: cabos por seção **e cor**, eletrodutos por diâmetro (m), curvas, luvas, caixas, disjuntores, DR, DPS, quadros. Exportar CSV/ODS.
4. Exportação IFC (via `IfcType`) e DXF.

### Fase 6: Complementares (contínuo)

- SPDA e aterramento (NBR 5419): malha, descidas, equipotencialização.
- Luminotécnico (NBR ISO/CIE 8995-1): método dos lúmens por ambiente sugerindo a quantidade de luminárias.
- Recarga de veículo elétrico (NBR 17019).
- Cabeamento estruturado/telecom (NBR 14565) e CFTV, reaproveitando a infraestrutura.
- Edifícios multifamiliares: prumadas, medição agrupada, demanda de edifício.
- Traduções (o `Resources/translations/` está vazio) e Addon Manager.

---

## 5. Próximos 10 passos

Em ordem, cada um com teste:

1. B1: `AddCircuito` com seleção do quadro de destino.
2. `ultima_linha` lendo o número inteiro (`re.search(r"\d+$", …)`).
3. `secao_comercial()` + `test_queda_tensao.py` sem `expectedFailure`.
4. C1: `queda_tensao_trifasico` (operador e unidade mΩ/m) com teste do exemplo do Mamede.
5. C3, C4, C5: tabelas corrigidas, convertidas para dicionário, com teste de consistência.
6. U1: unidades com `Quantity` explícita; confirmar no FreeCAD antes e depois.
7. B2, B3, B4: unifilar com deslocamento por quadro e nome estável; PDF lendo linha 3 só de quadros.
8. Transações nos comandos.
9. CI com `unittest` no GitHub Actions.
10. Especificar os objetos `Circuito` e `Quadro` (propriedades, migração das planilhas existentes) antes de escrever código da Fase 1.
