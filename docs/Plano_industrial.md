# Plano: projeto industrial

Atualizado em 20/11/2026. Complementa o [Plano das próximas etapas](Plano_proximas_etapas.md),
que é residencial e predial. As etapas daqui levam o prefixo **I** e reaproveitam as de lá:
a Etapa 5 (alimentadores) vira a I1, e a Etapa 6 (quadro de comando) vira a I4.

## O que muda num projeto industrial

| Residencial / predial (o que a bancada já faz) | Industrial (o que falta) |
|---|---|
| Quadros soltos, cada um com a sua origem em texto | **Árvore de distribuição**: rede → transformador → QGBT → CCM, QDF, QDL → cargas |
| Circuitos terminais de tomadas e iluminação | **Motores**: partida, CCM, disjuntor-motor, queda na partida |
| Curto só para a seção do cabo (S ≥ I·√t / k), com o tempo informado à mão | **Estudo de curto-circuito** em cada barra: Ik3 máximo, pico, Ik1 mínimo |
| Disjuntor escolhido pela corrente | **Capacidade de interrupção**, **seletividade** e coordenograma |
| Entrada em baixa tensão | **Transformador e subestação** (NBR 14039) |
| Demanda pelos guias residenciais | **Demanda industrial** por fator de utilização e simultaneidade |
| — | **Correção do fator de potência** (banco de capacitores) |
| `core/functions/Barramento.py` com erro e sem uso | **Barramentos** do QGBT e do CCM (NBR IEC 61439) |

O que já serve sem mudança: eletrocalhas e leitos (com conexões, suportes e saídas),
`core/nbr5410.py` (capacidade, agrupamento, queda pelo anexo G, seccionamento, tabela 58),
`core/functions/Predial/motores.py` (corrente nominal pela potência), o gerador diesel com o
QTA, o aterramento, o luminotécnico (vale para galpão, com o pé-direito alto), o unifilar,
o multifilar e os quantitativos.

## Testes de especificação

Como no plano residencial, os testes vêm antes do código, em `tests/plano/`, e falham com
"Etapa I*n*: o módulo ... ainda não existe" até a etapa ser feita.

| Arquivo | Módulo esperado | Etapa |
|---|---|---|
| `test_industrial_curto.py` | `core/curto.py` | I2 |
| `test_industrial_fator_potencia.py` | `core/fator_potencia.py` | I6 |
| `test_etapa6_comando.py` (já existia) | `core/comando.py` | I4 |

---

## Etapa I1: árvore de distribuição e alimentadores

**Por quê:** o curto, a queda acumulada, a demanda e a seletividade andam pela árvore.
Hoje cada quadro só tem a `origem` em texto.

- **Entrada:** a `origem` da linha 3 de cada quadro (sigla do quadro de cima ou do
  transformador) e a nova coluna **Alimentador** (seção, paralelos, comprimento, método),
  preenchida pela rede de bandejas e eletrodutos quando o quadro de cima está ligado a ela.
- **Saída:** `core/distribuicao.py` com `arvore(quadros)` (pais e filhos, aviso de ciclo e de
  origem que não existe), `demanda_acumulada` e `queda_acumulada` (7 % no total, a soma que
  hoje falta: `queda_total_ok` existe e não é chamada). O alimentador é dimensionado por
  `nbr5410.dimensionar_circuito` com a demanda do quadro de baixo.
- **Símbolos novos:** `transformador` (categoria QUADRO, sigla TR1), `qgbt` e `ccm`.
- **Onde aparece:** linha "Alimentador" na planilha e no unifilar de cada quadro, e um
  **unifilar geral** (só quadros e alimentadores, um bloco por quadro).

## Etapa I2: estudo de curto-circuito (IEC 60909) (pronta)

**Feito:** `core/curto.py` e o botão **Curto-circuito** (planilha "Estudo de curto": barras, rede, transformador, cabos; I″k3, ip, I″k1 mínima e capacidade de interrupção; grava o curto em cada quadro e avisa do disjuntor geral fraco). Sem contribuição de motores e com o PE igual à fase.

**Método:** das impedâncias, em mΩ, referidas à baixa tensão.

| Elemento | Impedância |
|---|---|
| Rede (Scc da concessionária) | Z = c·U² / Scc, X = 0,995·Z, R = 0,1·X |
| Transformador | Z = uk·U² / S, R = Pcu·U² / S², X = √(Z² − R²), vezes KT = 0,95·cmáx / (1 + 0,6·xT) |
| Cabo | R = ρ20·L / (S·n) com ρ20 = 1/54 Ω·mm²/m no cobre (1/34 no alumínio); X = 0,08 mΩ/m dividido pelos paralelos |
| Barramento | pelo catálogo; sem dado, 0,15 mΩ/m |
| Motores | contribuição pela corrente de rotor bloqueado quando a soma deles passa de 1 % do Ik sem motores |

**Resultados por barra:** Ik3 máximo = c·U / (√3·|Z|) com cmáx = 1,05; pico
ip = κ·√2·Ik3 com κ = 1,02 + 0,98·e^(−3R/X); Ik1 mínimo fase-terra com cmín = 0,95 e o
cabo a 80 °C (ou 160 °C no fim do curto), que vai para o seccionamento automático no TN.

**Onde é usado:**

1. Capacidade de interrupção: o disjuntor de cada quadro precisa de Icu ≥ Ik3 da barra
   (`capacidade_interrupcao` dá o valor comercial). Fecha o "capacidade de interrupção do
   disjuntor não verificada" dos problemas conhecidos.
2. O `tempo_curto` informado à mão nos parâmetros passa a ser o tempo do disjuntor para o
   Ik3 da barra (da curva da Etapa I7), e S ≥ I·√t / k usa o Ik3 calculado.
3. Barramento: esforço pela corrente de pico e Icw pelo Ik3.

- **Código:** `core/curto.py` (puro), `services/curto.py` (lê a árvore e grava a planilha
  **Estudo de curto-circuito**, propriedade `curto_circuito`, uma linha por barra),
  comando `CalcCurto` ("Curto-circuito").
- **Entrada nova nos parâmetros do projeto:** Scc da concessionária (MVA) no ponto de
  entrega, ou a impedância informada por ela.
- **Testes:** `tests/plano/test_industrial_curto.py`: rede de 500 MVA + transformador de
  1000 kVA, 5 %, 10,5 kW de perdas no cobre, 380 V dá cerca de 31,5 kA no QGBT
  (κ ≈ 1,54, ip ≈ 68,7 kA), e 2 × 240 mm² com 50 m até o CCM baixa para cerca de 23,6 kA.

## Etapa I3: transformador e subestação

- **Transformador:** potência pela demanda acumulada do QGBT, com a reserva dos parâmetros,
  na lista comercial (75 a 2500 kVA); uk, perdas e corrente nominal de tabela genérica
  ("conferir com o fabricante"), que alimentam a Etapa I2.
- **Média tensão (NBR 14039):** cabo de MT pelas tabelas que já existem em
  `core/tables/NBR14039`, chave e fusível HH ou disjuntor com relé 50/51 pelo
  `demanda_kva` e pela corrente de magnetização (8 a 12 × In por 0,1 s).
- **Malha de aterramento** da subestação: hoje o `aterramento.py` só calcula hastes em
  linha; a malha (NBR 15751, tensões de passo e de toque) é uma subetapa.
- **Pendência sua:** subestação abrigada, ao tempo ou só cabine de medição.

## Etapa I4: motores e CCM

É a Etapa 6 do plano residencial (quadro de comando), com o que a indústria acrescenta:

- **Planilha "Motores do CCM"**, uma linha por motor: potência (cv/kW), tensão, partida
  (direta, estrela-triângulo, soft-starter, inversor), fator de serviço, regime, carga
  acionada, comando (24 Vcc ou 220 Vca). Os `Ponto` de motor (`ponto_forca`) da planta
  entram nela, como o recalque e a pressurização já fazem.
- **Dimensionamento por motor:** disjuntor-motor pela faixa de ajuste e com o magnético
  acima da corrente de partida (resolve "disjuntor de motores só pela corrente nominal" dos
  problemas conhecidos), contatores em AC-3, relé térmico, cabo pela corrente nominal × fator
  de serviço e **queda na partida** até 10 % no motor (com a corrente de rotor bloqueado e o
  fator de potência de partida, cerca de 0,3).
- **Saídas:** diagramas de força e de comando por blocos, régua de bornes, layout da porta e
  da placa, perdas em W para a ventilação do painel, lista de materiais nos quantitativos.
- **Testes:** os de `test_etapa6_comando.py`, mais a queda na partida e o magnético.

## Etapa I5: demanda industrial

- Potência instalada por quadro e, pela árvore, fator de utilização por tipo de carga
  (motor, resistência, iluminação, tomada) e fator de simultaneidade por grupo de motores
  (tabelas usuais, editáveis na planilha).
- Saída: demanda de cada quadro e do QGBT em kW e kVA, que dimensiona alimentadores (I1),
  transformador (I3) e banco de capacitores (I6). Substitui o `CalcDemanda` residencial
  nos quadros marcados como industriais (parâmetro `tipo_instalacao`).

## Etapa I6: correção do fator de potência (pronta)

**Feito:** `core/fator_potencia.py` e o formulário **Fator de potência** (kvar, estágios, corrente de projeto e risco de ressonância).

- Q = P·(tg φ1 − tg φ2), com o FP de referência de 0,92 (ANEEL).
- Banco automático em estágios comerciais (com o menor estágio para a carga mínima), ou fixo
  no transformador para a magnetização (cerca de 5 % da potência dele).
- Cabo e proteção do banco pela corrente nominal × 1,35 (sobretensão e harmônicas).
- Aviso de ressonância quando houver inversores: frequência de ressonância
  fr = f·√(Scc / Q) perto da 5ª ou da 7ª harmônica pede reator de dessintonia.
- **Testes:** `tests/plano/test_industrial_fator_potencia.py`.
- **Código:** `core/fator_potencia.py`, comando `CalcFatorPotencia` no grupo Cálculos e
  símbolo `banco_capacitores` no QGBT.

## Etapa I7: seletividade e coordenograma

- Curvas tempo-corrente: disjuntores IEC 60898 (B, C, D) com a faixa do térmico e do
  magnético, IEC 60947-2 ajustáveis (L, S, I), fusíveis gG e aM por tabelas genéricas.
- Verificações entre o disjuntor de cada quadro e os de baixo: amperimétrica (o magnético
  de cima acima do Ik3 da barra de baixo) e cronológica (atraso do S); aviso quando não há
  seletividade, com a corrente até onde ela vale.
- **Coordenograma** em papel log-log como Sketch (no padrão do unifilar), com as curvas do
  ramo, o Ik3 de cada barra e a curva de dano do cabo (I²t = k²S²), e na página do PDF.

## Etapa I8: barramentos

- Corrigir `core/functions/Barramento.py` (os erros estão nos problemas conhecidos) ou
  trocar por `core/barramento.py` com: seção pela corrente e temperatura, esforço
  eletrodinâmico pela corrente de pico (I2) e o vão dos isoladores, suportabilidade térmica
  por Icw e o tempo.
- Saída: barramento de cobre (barras × espessura × largura) na lista do quadro.

## Etapa I9: folhas e memoriais industriais

Entra na Etapa 7 do plano residencial: unifilar geral, estudo de curto (tabela por barra),
coordenogramas, quadro de cargas dos CCMs, memorial de cálculo com as contas mostradas.

---

## Ordem sugerida

| Etapa | Depende de | Tamanho |
|---|---|---|
| I1. Árvore e alimentadores | Etapa 3 (pronta) | médio |
| I2. Curto-circuito | I1 (a conta pura não depende: pode começar já) | médio |
| I3. Transformador e subestação | I1, I2, I5 | grande |
| I4. Motores e CCM | I1 | grande |
| I5. Demanda industrial | I1 | pequeno |
| I6. Fator de potência | I5 | pequeno |
| I7. Seletividade | I2 | grande |
| I8. Barramentos | I2 | pequeno |
| I9. Folhas | I1 a I8 | médio |

Proposta: **I2 (só a conta) → I1 → I2 no documento → I4 → I5 → I6 → I7 → I3 → I8 → I9**.
O curto e a capacidade de interrupção são o que falta de mais grave hoje: um quadro perto do
transformador com disjuntor de 6 kA não é avisado.

## Na interface

Uma barra nova, **Industrial**, com até 8 botões: Transformador ▾ (símbolo, dimensionar),
Árvore de distribuição, Curto-circuito, Motores do CCM ▾, Seletividade, Fator de potência,
Barramento, Unifilar geral. Os símbolos `transformador`, `qgbt`, `ccm` e
`banco_capacitores` entram no grupo Quadros.

## Decisões que dependem de você

1. **Tensões:** 380/220 V, 220/127 V ou 440 V no secundário? Média tensão de 13,8 kV ou 23,1 kV?
2. **Scc da concessionária:** valor fixo nos parâmetros, ou a impedância informada no
   parecer de acesso?
3. **Subestação:** abrigada, ao tempo (poste ou plataforma) ou só entrada em BT?
4. **Fabricante de referência** para disjuntores (Icu, curvas LSI), disjuntores-motores,
   contatores e capacitores, ou tabelas genéricas marcadas "conferir"?
5. **Contribuição dos motores** no curto: incluir desde a I2 ou só na I4?
6. **Seletividade:** basta o aviso e a tabela, ou quer o coordenograma desenhado já na
   primeira versão?
