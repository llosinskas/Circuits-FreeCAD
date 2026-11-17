# Plano das próximas etapas

Atualizado em 17/11/2026. Substitui a seção "Próximos 10 passos" de
[Revisao_e_Roadmap_Predial.md](Revisao_e_Roadmap_Predial.md), que fica como histórico.

## Onde estamos

A bancada já desenha a planta por pavimento (pontos, comandos, quadros, aterramento),
monta a rede de eletrodutos e de bandejas, conta fios, verticais, conexões e suportes,
monta os circuitos, gera a planilha e o unifilar de cada quadro e exporta quantitativos
em CSV, XLSX e PDF.

O que falta para virar um projeto completo, nesta ordem:

1. **Confirmar no FreeCAD real** o que só tem teste com o FreeCAD simulado.
2. **Fechar o unifilar** como folha de projeto: DR por grupo, quadro de cargas, balanço de fases.
3. **Parâmetros do projeto** num lugar só, lidos por todos os cálculos.
4. **Dimensionamento completo da NBR 5410**, usando o que a rede já sabe (comprimento, agrupamento, método).
5. **Infraestrutura pela ocupação:** diâmetro do eletroduto e largura da bandeja.
6. **Entrada de energia e alimentadores.**
7. **Quadro de comando e proteção**, começando pelas bombas.
8. **Folhas de projeto e memoriais.**

Cada etapa tem entradas, o que sai, onde fica no código e como é testada. Uma etapa só
começa quando a anterior passa no `smoke_gui.py`.

## Testes de especificação

As etapas 1 a 4 e 6 já têm testes escritos antes do código, em `tests/plano/`:

```bash
python -B -m unittest discover -s tests/plano -t .
```

| Arquivo | Módulo esperado | Testes |
|---|---|---|
| `test_pre_requisitos.py` | o que já existe e o plano reaproveita | 4, passam |
| `test_etapa1_quadro_de_cargas.py` | `core/quadro_cargas.py` | 14 |
| ~~`test_etapa2_parametros.py`~~ | `core/parametros.py` | pronta: em `tests/unit/test_parametros.py` |
| ~~`test_etapa3_nbr5410.py`~~ | `core/nbr5410.py`, `comprimento` e `agrupados` em `core/rede.py` | pronta: em `tests/unit/test_nbr5410.py` |
| `test_etapa4_ocupacao.py` | `core/ocupacao.py` | 8 |
| `test_etapa6_comando.py` | `core/comando.py` | 8 |

Enquanto o módulo não existe, cada teste falha (não dá erro) com "Etapa N: o módulo ...
ainda não existe". Ao implementar uma etapa, os testes dela passam a `tests/unit/`.
As etapas 0, 5 e 7 ficam sem teste de especificação: a 0 e a 7 dependem do FreeCAD
real, e a 5 da concessionária, que ainda não foi escolhida.

## O que a análise do plano mudou

- **Comprimento do circuito:** o `trajeto` de `core.rede` é só o trecho horizontal. A
  queda de tensão precisa somar as descidas até o quadro e até a caixa; a rede ganha a
  chave `comprimento` (Etapa 3).
- **Balanço e reservas já existem:** `core.circuitos.distribuir_fases` e
  `core.quadro.reserva_de_circuitos`. A Etapa 1 só os usa, sem gravar na planilha
  sem a confirmação do usuário.
- **Método de instalação em bandeja aberta:** é F com cabos unipolares e E com
  multipolar; a eletrocalha lisa (fechada) conta como B1.
- **Condutor isolado em bandeja aberta:** a norma não permite; nesse trajeto o cabo
  precisa ser 0,6/1 kV. A Etapa 3 avisa (`exige_cabo`), e os quantitativos vão precisar
  separar "Cabo flexível 750 V" de cabo 0,6/1 kV.
- **Tabela de temperatura com erro:** `core/tables/NBR5410/fator_correcao_temperatura_ar_livre.py`
  pula 30 °C e tem 0,96 em 40 °C para EPR (o certo é 0,91). A Etapa 3 usa tabelas novas, em
  dicionário, e as antigas em pandas saem.
- **Curto-circuito:** já existe uma fórmula com temperaturas em
  `core/functions/Cabo/limite_curto_circuito.py`; a Etapa 3 usa o k da tabela 30
  (S ≥ I·√t / k) e a antiga é removida para não haver duas respostas.
- **Ocupação da bandeja:** a NBR 5410 não dá uma taxa como a do eletroduto. Fica fora
  da Etapa 4 até decidirmos a regra (camada única pela largura ou catálogo do fabricante).

---

## Etapa 0: validar no FreeCAD real

**Por quê:** a lista "Problemas conhecidos" do AGENTS.md tem muita coisa testada só com o
FreeCAD simulado (níveis do BIM, pastas, bandejas, filtro de teclas, unifilar novo).
Corrigir isso agora é mais barato que descobrir no meio de um projeto.

- Rodar `tests/gui/smoke_gui.py` no FreeCAD 1.1 e guardar o retrato JSON como referência.
- Corrigir o que falhar, com teste unitário que reproduza o erro.
- Fazer um projeto pequeno à mão (casa térrea com 2 pavimentos): inserir pontos, circuitos,
  quadro, unifilar, eletrodutos, bandeja, quantitativos.
- Tirar de "Problemas conhecidos" o que foi confirmado.

**Pronto quando:** `errors` vazio no JSON e o projeto de exemplo salvo em `docs/exemplos/`.

---

## Etapa 1: unifilar como folha de projeto

O desenho de cada circuito já tem disjuntor com terminais e arco, DR, traços dos
condutores, seção, potência, fases e descrição (`core/unifilar.py`). Falta:

| Item | Entrada | Saída |
|---|---|---|
| DR geral ou DR por grupo de circuitos | Coluna `Grupo DR` na planilha de circuitos | Um DR desenhado antes de um sub-barramento com os circuitos do grupo; o DR por circuito continua possível |
| Disjuntor geral com DR (IDR) | Dado do quadro | Símbolo de IDR na entrada |
| Quadro de cargas ao lado do diagrama | Planilha de circuitos | Tabela: circuito, descrição, potência por fase (R, S, T), corrente, disjuntor, cabo; total e desequilíbrio |
| Balanço de fases | Potência e número de fases de cada circuito | Sugestão de fases que minimiza o desequilíbrio, gravada na planilha só se o usuário aceitar |
| Reserva | Número de circuitos | Linhas "Reserva" no diagrama e no quadro de cargas, pela regra de reserva que `core/quadro.py` já aplica |
| Trifilar (opcional) | Mesmos dados | Diagrama com um traço por condutor |

- **Código:** `core/unifilar.py` (geometria), `core/quadro.py` (balanço, reservas),
  `services/unifilar.py`.
- **Testes:** geometria do DR por grupo; balanço com casos conhecidos (ex.: 3 circuitos de
  1500 W em 220/127 V); quadro de cargas somando por fase.

---

## Etapa 2: parâmetros do projeto (pronta)

Feita como planilha (`services/parametros.py`, botão **Projeto > Parâmetros**), não como
formulário: a planilha guarda os valores no próprio projeto e é editada como as outras.

Hoje cada cálculo tem os próprios valores fixos (127 V, PVC, 30 °C, método B1). Proposta:
uma planilha **Parâmetros do projeto** (propriedade `parametros_do_projeto`), criada pelo
**Novo projeto** e lida por `services/parametros.py`, com valores padrão quando faltar algo.

| Grupo | Parâmetros |
|---|---|
| Fornecimento | Concessionária, tensão fase-neutro e fase-fase, sistema (monofásico, bifásico, trifásico), corrente de curto no ponto de entrega ou potência e impedância do transformador |
| Aterramento | Esquema (TN-S, TN-C-S, TT), resistência de aterramento |
| Condutores | Material (cobre, alumínio), isolação (PVC 70 °C, EPR ou XLPE 90 °C), temperatura ambiente e do solo |
| Limites | Queda de tensão nos circuitos terminais (4 %) e total (7 %) |
| Padrões | Curva dos disjuntores por tipo de circuito, sensibilidade do DR, reserva de circuitos |

- O formulário segue as regras de `core/formularios.py` (até 4 campos básicos, o resto avançado).
- **Testes:** leitura com campos faltando; todos os cálculos recebem os parâmetros pelo mesmo caminho.

---

## Etapa 3: dimensionamento completo pela NBR 5410 (pronta, com pendências)

Feito em `core/nbr5410.py` e ligado ao **Montar circuitos**. Ficaram para depois: o método
pelo trajeto (as bandejas ainda não entram na rede dos circuitos, então vale B1), a tabela 39
(método F), a capacidade de interrupção dos disjuntores, a impedância do alimentador no curto
e a remoção das tabelas antigas em pandas e de `Cabo.py`. O curto só é verificado quando o
tempo de atuação é informado, porque o I²t dos disjuntores limitadores é bem menor que I²·t.

Usar o que a rede já calcula para fechar os 6 critérios de cada circuito:

| Critério | De onde vem o dado |
|---|---|
| Seção mínima (tabela 47) | Tipo do circuito (iluminação, força) |
| Capacidade de condução com FCT e FCA (tabelas 36 a 45) | Método de instalação pelo trajeto: eletroduto ou eletrocalha lisa → B1; eletrocalha perfurada e leito → F (cabos unipolares) ou E (multipolar); agrupamento = maior número de circuitos num trecho do trajeto; temperatura dos parâmetros |
| Queda de tensão | Comprimento do circuito na rede, com as descidas (`comprimento`, a criar em `core.rede`) |
| Sobrecarga (Ib ≤ In ≤ Iz) | Já existe |
| Curto-circuito (S ≥ I·√t / k) e capacidade de interrupção | Icc dos parâmetros, reduzida pela impedância do alimentador |
| Contatos indiretos (Zs·Ia ≤ U0 no TN; DR no TT) | Esquema de aterramento e comprimento |

- O resultado vai para a planilha de circuitos, com uma coluna "Critério determinante".
- **Código:** `core/functions/Cabo/` (refazer `Cabo.py`, hoje com erros), `core/tables/NBR5410/`
  (corrigir as tabelas com colunas desiguais e a temperatura que pula 30 °C), `core/circuitos.py`.
- **Testes:** exemplos resolvidos de livro (Cotrim, Mamede) para cada critério; tirar o
  `expectedFailure` de `test_queda_tensao.py`.

---

## Etapa 4: infraestrutura pela ocupação

| Item | Regra | Saída |
|---|---|---|
| Diâmetro do eletroduto por trecho | Taxa de ocupação: 53 % com 1 cabo, 31 % com 2, 40 % com 3 ou mais | Propriedade `Diametro` sugerida em cada trecho, com aviso quando o desenhado é menor |
| Largura da bandeja | Regra a definir (a NBR 5410 não dá uma taxa como a do eletroduto) | `Largura` sugerida e aviso |
| Fios por trecho | Já calculado pela rede | Identificação na planta (`#2,5 F+N+T` no trecho) |

- **Código:** `core/rede.py`, `core/bandejas.py`, `core/tables/eletrodutos.py` (diâmetro externo dos cabos).

---

## Etapa 5: entrada de energia e alimentadores

- **Demanda do edifício:** diversidade entre unidades pela tabela da concessionária escolhida
  nos parâmetros (começar por uma; as outras entram como tabela de dados).
- **Categoria de atendimento e padrão de entrada:** disjuntor, ramal e medição pela demanda.
- **Alimentadores:** do medidor ao QD e do QGBT aos QDs, dimensionados como na Etapa 3, com a
  queda acumulada (7 % no total).
- **Saída:** linha "Alimentador" na planilha do quadro e no unifilar.
- **Pendência sua:** qual concessionária usar primeiro.

---

## Etapa 6: quadro de comando e proteção

Começar pelas bombas, porque o recalque e a pressurização já calculam o motor.

**Entradas** (planilha **Cargas do quadro de comando**, uma linha por motor):
potência (cv ou kW), tensão, partida (direta, estrela-triângulo, soft-starter, inversor),
regime, tensão de comando (24 Vcc ou 220 Vca), modo manual/automático, intertravamentos
(boias, alternância entre bombas, detector de fumaça da pressurização), sinalizações.

**Saídas:**

1. **Dimensionamento por motor** (NBR IEC 60947-4-1): disjuntor-motor com a faixa de ajuste,
   contator em AC-3, relé térmico e cabo. Estrela-triângulo: K1 e K2 com 0,58·In, K3 com
   0,33·In, relé com 0,58·In. Soft-starter e inversor pela corrente e pelo regime.
2. **Diagrama de força** multifilar.
3. **Diagrama de comando** a partir de blocos prontos: liga/desliga com selo, boia, alternância,
   falha de bomba, sinaleiros. Cada bloco é uma função pura que devolve a geometria, como em
   `core/unifilar.py`.
4. **Régua de bornes** numerada e identificação dos condutores e dispositivos (Q1, K1, F1, S1, H1).
5. **Layout da placa e da porta:** trilho DIN, canaletas, tamanho do painel e soma das perdas
   em W para escolher ventilação e grau de proteção (NBR IEC 61439).
6. **Lista de materiais** do painel, que entra nos quantitativos.

- **Código previsto:** `core/comando.py` (dimensionamento), `core/diagramas_comando.py`
  (blocos), `services/quadro_comando.py`, comandos novos no grupo *Quadros*.
- **Testes:** dimensionamento de um motor de 5 cv em 380 V nas quatro partidas; blocos de
  comando sem linhas soltas (toda ponta ligada a um borne ou a outro elemento).
- **Pendência sua:** fabricante de referência para as faixas de disjuntor-motor e contator
  (até lá, tabela genérica marcada "conferir com o catálogo").

---

## Etapa 7: folhas de projeto e memoriais

- Folhas do TechDraw em A1/A3 com carimbo: planta de cada pavimento, unifilares, quadro de
  cargas, legenda, notas, detalhes de bandeja e de quadro de comando.
- Memorial descritivo e memorial de cálculo em PDF, a partir dos mesmos dados (cada
  critério da Etapa 3 com a conta mostrada).
- Exportação em DXF e PDF.

---

## Ordem sugerida e tamanho

| Etapa | Depende de | Tamanho |
|---|---|---|
| 0. Validação no FreeCAD | — | pequeno, mas precisa do FreeCAD na sua máquina |
| 1. Unifilar como folha | 0 | médio |
| 2. Parâmetros do projeto | 0 | pequeno |
| 3. NBR 5410 completa | 2 | grande |
| 4. Ocupação | 3 | médio |
| 5. Entrada e alimentadores | 2, 3 | médio |
| 6. Quadro de comando | 2 | grande |
| 7. Folhas e memoriais | 1, 3 | médio |

As etapas 1 e 2 podem andar juntas. A 6 é independente da 3 a 5 e pode ser antecipada se
o quadro de comando for a prioridade.

## Decisões que dependem de você

1. Concessionária da Etapa 5.
2. Fabricante de referência para disjuntores, DR, contatores e disjuntores-motores.
3. Se o DR geral (IDR) deve ser o padrão nos quadros residenciais ou o DR por circuito.
4. Formato e carimbo das folhas (A1 ou A3, logotipo, campos).
