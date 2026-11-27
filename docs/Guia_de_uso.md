# Guia de uso da bancada Circuits

Este guia mostra, passo a passo, como fazer o projeto elétrico de uma casa na bancada **Engenharia** do FreeCAD: da planta com os pontos até as folhas finais com o diagrama unifilar, o quadro de cargas e a lista de materiais. Cada etapa diz qual botão usar, o que preencher e o que conferir.

O [README](../README.md) descreve cada ferramenta em detalhe. Aqui o foco é a ordem de trabalho.

## Sumário

1. [Antes de começar](#1-antes-de-começar)
2. [Criar o projeto e os pavimentos](#2-criar-o-projeto-e-os-pavimentos)
3. [Colocar os pontos na planta](#3-colocar-os-pontos-na-planta)
4. [Circuitos e comandos](#4-circuitos-e-comandos)
5. [Eletrodutos e eletrocalhas](#5-eletrodutos-e-eletrocalhas)
6. [Quadro: planilhas e dimensionamento](#6-quadro-planilhas-e-dimensionamento)
7. [DR por grupo de circuitos](#7-dr-por-grupo-de-circuitos)
8. [Fases, quadro de cargas e componentes](#8-fases-quadro-de-cargas-e-componentes)
9. [Diagramas: unifilar e multifilar](#9-diagramas-unifilar-e-multifilar)
10. [Cálculos](#10-cálculos)
11. [Documentos e folhas finais](#11-documentos-e-folhas-finais)
12. [Problemas comuns](#12-problemas-comuns)

---

## 1. Antes de começar

- Use o **FreeCAD 1.1** ou mais novo e escolha a bancada **Engenharia** na lista de bancadas.
- As barras próprias da bancada são três: **Planta elétrica**, **Quadros e documentos** e **Modelo e biblioteca**. Os botões com seta (▾) abrem uma lista; o botão mostra o último comando usado.
- Todo comando também está no menu **Elétrica**.
- Na primeira ativação, a bancada pode pedir para instalar a biblioteca `reportlab` (para os PDFs). Aceite, ou instale depois pelo botão do relatório.
- Se você atualizou a bancada com o FreeCAD aberto, use **Elétrica > Outros > Reiniciar Bancada**.

> **Dica:** salve o projeto (`.FCStd`) logo no começo. Algumas funções, como o link para os componentes da biblioteca, precisam do arquivo salvo.

## 2. Criar o projeto e os pavimentos

1. **Projeto ▾ > Novo projeto.** Abre o formulário do projeto, em quatro abas:
   - **Identificação:** nome do projeto, obra/endereço, cliente, responsável técnico, CREA/CFT e desenhista (vão para o carimbo das folhas) e o tipo de edificação (residencial unifamiliar, multifamiliar, comercial ou industrial). Trocar o tipo sugere os pavimentos, as tensões, o fornecimento e o curto na entrada.
   - **Edificação e pavimentos:** quantos subsolos, quantos andares acima do térreo, se tem cobertura, o piso a piso do térreo e dos andares e a cota do térreo. A tabela embaixo mostra os pavimentos que serão criados (Subsolo 1, Térreo, 1º Pavimento... Cobertura), com a cota e o piso a piso, e deixa mudar nomes e cotas. Marque **Criar como níveis da bancada BIM** para os pavimentos virarem andares no IFC.
   - **Fornecimento de energia:** concessionária, sistema de tensões (127/220 V, 220/380 V...), monofásico, bifásico ou trifásico, curto-circuito na entrada, esquema de aterramento e resistência de terra.
   - **Condutores e proteção:** cobre ou alumínio, isolação, temperatura ambiente, curvas dos disjuntores e sensibilidade do DR.

   Embaixo aparece o resumo do que será criado. **Criar projeto** cria a estrutura do documento (sem documento aberto, um novo com o nome do projeto), os pavimentos, com o Térreo ativo, e a planilha *Parâmetros do projeto* já preenchida. Clicar de novo no botão num projeto existente abre o formulário preenchido para editar (os pavimentos que saírem da lista não são apagados). Se o arquivo já tiver níveis da bancada BIM, eles aparecem na tabela e mantêm a cota deles.
2. **Projeto ▾ > Parâmetros.** Abre a planilha de parâmetros, com os valores do formulário e os outros (limites de queda, tempo de curto...). Edite só a coluna *Valor*; em branco vale o padrão. Confira principalmente:
   - tensões fase-neutro e fase-fase (127/220 V ou 220/380 V);
   - esquema de aterramento (TN-S, TN-C-S ou TT);
   - isolação dos cabos e temperatura ambiente;
   - queda de tensão máxima;
   - sensibilidade do DR (30 mA).
3. **Projeto ▾ > Pavimento.** Escolhe o pavimento ativo ou cria um novo, com a cota do piso e a altura de piso a piso. Para usar os níveis do BIM, **Projeto ▾ > Nível do BIM**.

Tudo o que você inserir vai para a pasta do pavimento ativo, separado por tipo (*Tomadas*, *Iluminação*, *Interruptores*, *Quadros e medição*, *Eletrodutos*...).

**Planta de arquitetura:** desenhe ou importe a arquitetura antes (paredes, portas e espaços da bancada BIM, ou um DWG/DXF importado). Os pontos são desenhados por cima dela.

## 3. Colocar os pontos na planta

### Manualmente

Escolha o símbolo nos grupos **Tomadas ▾**, **Energia ▾**, **Iluminação ▾**, **Comandos ▾** ou **Quadros ▾**. O símbolo acompanha o cursor:

| Tecla | O que faz |
|---|---|
| Clique | Fixa o símbolo e já traz o próximo |
| R / Shift+R | Gira 90° / 45° |
| Espaço (ou A) | Alinha com o símbolo mais próximo |
| L | Liga ou desliga o alinhamento automático |
| ESC | Termina |

Cada ponto já vem com potência, tensão, ligação (F+N, F+F, 3F) e altura de montagem. Para mudar, selecione e edite no painel de propriedades.

### Automaticamente, por ambiente

1. **Projeto ▾ > Ambientes** transforma cada espaço do BIM (ou cada retângulo/polilinha fechada selecionada) em um ambiente com nome, tipo, área e perímetro.
2. **Projeto ▾ > Pontos automáticos** mostra uma prévia por ambiente com as tomadas pela NBR 5410 (9.5.2), as luminárias pelo luminotécnico, o interruptor junto da porta e, se você pedir, chuveiro e ar-condicionado. Responda as perguntas do lado (porta, pia, chuveiro, ar-condicionado, lâmpada) e confirme.

Os pontos automáticos saem **sem circuito**: o passo seguinte é definir os circuitos.

### O quadro

Coloque o quadro de distribuição com **Quadros ▾ > Quadro de distribuição**. A sigla (QD1, QD2...) fica na propriedade `Descricao`.

## 4. Circuitos e comandos

1. Selecione os pontos de um circuito e clique em **Circuitos ▾ > Definir circuito**. A bancada sugere o próximo número livre; informe também o quadro, se o projeto tiver mais de um.
2. Selecione um interruptor e as luminárias que ele acende e clique em **Circuitos ▾ > Ligar interruptor**. Eles recebem a mesma letra (a, b, c...). Para interruptores paralelos, selecione os dois junto com as luminárias.
3. **Circuitos ▾ > Identificar pontos** escreve ao lado de cada símbolo o circuito, a letra e a potência (`C1 · a · 100 VA`) e os condutores que chegam à caixa (`#2,5 F+N+T`).

> **Regra prática:** separe iluminação e tomadas em circuitos diferentes, e dê um circuito próprio a cada equipamento acima de 10 A (chuveiro, forno, ar-condicionado), como pede a NBR 5410.

## 5. Eletrodutos e eletrocalhas

### Eletrodutos

1. Com nada selecionado, **Infraestrutura ▾ > Eletroduto** abre a ferramenta de linha. Desenhe do quadro até as caixas. O **snap de ligação** prende a ponta direto na caixa do símbolo quando o cursor passa sobre ele.
2. Selecione as linhas desenhadas e clique de novo em **Eletroduto**. Escolha diâmetro, tipo (flexível ou rígido), material, instalação e altura. A bancada:
   - junta as pontas próximas e prende os vértices nas caixas;
   - cria caixas de passagem nas derivações embutidas;
   - escreve o diâmetro (`Ø3/4"`) e as siglas das curvas e conduletes.
3. Para um trecho em outra altura (por exemplo, descer do teto para o piso), use **Infraestrutura ▾ > Mudar altura** no trecho ou no vértice. A descida, as curvas, o símbolo na planta e o 3D se atualizam sozinhos.

### Eletrocalhas e leitos

Desenhe o trajeto com linhas, selecione e clique em **Infraestrutura ▾ > Bandeja/leito**. A bancada faz as curvas, tês, cruzetas e reduções, desenha em linha dupla e gera o 3D. **Infraestrutura ▾ > Suportes** coloca os suportes. Um eletroduto que termina na borda da eletrocalha vira uma saída (`SH` ou `SV`).

### Conferências

- **Infraestrutura ▾ > Rota do circuito:** mostra e seleciona por onde passa o cabo de cada circuito.
- **Infraestrutura ▾ > Ocupação eletrodutos:** confere a taxa de ocupação (53/31/40 %) e oferece aumentar os eletrodutos pequenos.
- **Circuitos ▾ > Fios por trecho:** escreve os fios de cada eletroduto na planta (`C1 #2,5 F+N+T`).

### Descida até as caixas

Desenhe o eletroduto no teto (2,80 m, por exemplo) até o símbolo da tomada, mesmo que ela esteja a 0,30 m. A bancada liga os dois por uma descida:

- no 3D (**Modelo 3D ▾ > Modelo 3D completo**), o tubo faz a curva de 90° na ponta e desce até o topo da caixa; o eletroduto do piso sobe até a base dela;
- se o eletroduto só passa sobre a caixa e continua, a descida sai dele sem curva;
- no rígido, cada curva entra nos quantitativos como *Curva 90° vertical*, e o comprimento vertical entra nos metros de eletroduto;
- **Infraestrutura ▾ > Editar descidas** lista também essas descidas (*Até a caixa de …*), onde dá para mudar a altura do eletroduto.

Depois de mudar a altura de um símbolo, gere o Modelo 3D de novo.

Desenhe a rede **antes** de montar os circuitos: assim o comprimento (queda de tensão) e o agrupamento entram no dimensionamento dos cabos.

## 6. Quadro: planilhas e dimensionamento

1. Selecione o símbolo do quadro na planta e clique em **Dados do quadro ▾ > Planilha do quadro**. Preencha os dados: tensão, número de fases, disjuntor geral, DPS, neutro e terra. A bancada cria também a planilha de circuitos do quadro.
2. Clique em **Montar circuitos**. Para cada circuito, ele soma os pontos, escolhe o disjuntor e o menor cabo que atende à NBR 5410 (seção mínima, capacidade de condução, queda de tensão e, se configurado, curto-circuito) e grava uma linha na planilha *Circuitos_<quadro>*. A coluna *Critério* diz o que decidiu o cabo.
3. Abra a planilha com **Dados do quadro ▾ > Circuitos do quadro** e confira. Você pode editar qualquer linha à mão: o que for digitado é respeitado, e o que ficar em branco (corrente, cabo, disjuntor) é calculado no unifilar e nos componentes.

Colunas da planilha de circuitos:

| Coluna | Conteúdo |
|---|---|
| A, B | Circuito e descrição |
| C, D | Potência [W] e tensão [V] |
| E | Fases: `R`, `RS`, `RST` (`R*` prende na fase) |
| F a I | Corrente, cabo, disjuntor e curva (podem ficar em branco) |
| J, K | DR (S/N) e sensibilidade |
| L, M | Neutro e terra (S/N) |
| N a P | Comprimento, queda e critério (preenchidos pelo Montar circuitos) |
| **Q** | **Grupo do DR** (veja a seção 7) |

## 7. DR por grupo de circuitos

Em vez de um DR por circuito, é comum proteger vários circuitos com **um DR só**: por exemplo, um DR para as tomadas da área molhada e outro para as tomadas dos quartos. A bancada faz isso pela coluna **Q – Grupo do DR** da planilha de circuitos.

### Como usar

1. Abra a planilha de circuitos do quadro (**Dados do quadro ▾ > Circuitos do quadro**).
2. Na coluna **Q**, escreva o **mesmo nome** em todos os circuitos que ficam sob o mesmo DR. Exemplo:

   | Circuito | Descrição | Fases | DR | Grupo do DR |
   |---|---|---|---|---|
   | 1 | Iluminação | R | N | |
   | 2 | Tomadas sala | S | S | **DR1** |
   | 3 | Tomadas cozinha | T | S | **DR1** |
   | 4 | Chuveiro | RS | S | |
   | 5 | Tomadas banheiro | S | S | **DR1** |
   | 6 | Tomadas quartos | R | N | **DR2** |
   | 7 | Lavanderia | T | N | **DR2** |

3. Gere o diagrama: **Diagramas ▾ > Unifilar**.

### O que a bancada faz com isso

| Situação na planilha | Resultado |
|---|---|
| Nome na coluna Q | O circuito fica sob o DR do grupo, mesmo com a coluna DR em `N`. Ele não tem DR próprio. |
| Coluna Q vazia e DR = `S` | DR só do circuito, como antes (no exemplo, o chuveiro). |
| Coluna Q vazia e DR = `N` | Sem DR (no exemplo, a iluminação). |

**No unifilar,** os circuitos do grupo são desenhados juntos, na posição do primeiro deles: um ramo sai do barramento, passa pelo DR do grupo e chega a um **sub-barramento** vertical, de onde sai cada circuito com o seu disjuntor e sem DR próprio. Embaixo do DR ficam o nome do grupo (`DR1`) e a especificação (`4P 25 A, 30mA`). Os circuitos 2, 3 e 5 do exemplo aparecem um embaixo do outro, mesmo que na planilha estejam separados.

```
 barramento
     │
     ├──[DR]──┬──●⌒●──┼┤││──►  C2 Tomadas sala
     │  DR1   ├──●⌒●──┼┤││──►  C3 Tomadas cozinha
     │        └──●⌒●──┼┤││──►  C5 Tomadas banheiro
     │
     ├──●⌒●──[DR]──┼┤││──►  C4 Chuveiro   (DR próprio)
```

**Especificação do DR do grupo:**

- **Polos:** bipolar (2P) se todos os circuitos do grupo estão na mesma fase; tetrapolar (4P) se estão em fases diferentes.
- **Corrente nominal:** a corrente comercial (25, 40, 63, 80, 100 ou 125 A) igual ou acima do maior destes valores: a soma das correntes dos circuitos do grupo na fase mais carregada e o maior disjuntor do grupo.
- **Sensibilidade:** a da coluna K do primeiro circuito que a tiver; senão, 30 mA.

**No multifilar,** cada circuito do grupo mostra o DR com o nome do grupo (`DR1`), porque os condutores de todos eles passam pelo mesmo DR.

**Nos componentes do quadro** (botão **Componentes**), o grupo conta um DR só, com essa especificação, e os circuitos dele não contam DR próprio. O tamanho da caixa em módulos DIN já considera isso.

**No quadro de cargas** (seção 8), a tabela lista os DRs do quadro e os circuitos de cada um.

### Dicas

- Use nomes curtos: `DR1`, `DR2`, `IDR-A`. Maiúsculas e minúsculas contam como nomes diferentes.
- O **Montar circuitos** não apaga a coluna Q: você pode montar de novo à vontade.
- Para tirar um circuito do grupo, apague o nome na coluna Q e, se ele precisar de DR próprio, ponha `S` na coluna J.
- Agrupe circuitos de um mesmo tipo de área (molhada, quartos, externa). Um DR com muitos circuitos soma as correntes de fuga e pode desarmar sem defeito.
- Para um DR geral na entrada do quadro, use o **IDR** (abaixo) em vez de um grupo com todos os circuitos.

### DR geral do quadro (IDR)

Para pôr um DR na entrada do quadro, que protege todos os circuitos:

1. Ao criar o quadro (**Dados do quadro ▾ > Planilha do quadro**), marque **Tem DR geral (IDR)** e escolha a sensibilidade (30 mA para pessoas; 100 a 500 mA para proteção contra incêndio).
2. Num quadro já criado, abra a planilha do quadro e ponha `S` na linha 3 da coluna **IDR** (coluna T). Se o título da coluna não aparecer, gere o Unifilar uma vez: ele escreve os títulos que faltam.
3. Gere o Unifilar.

O IDR aparece na entrada, depois do disjuntor geral e do DPS, com a especificação em cima: bipolar no quadro monofásico, tetrapolar nos outros, com corrente nominal igual ou acima da do disjuntor geral. O multifilar o desenha abraçando as fases e o neutro, e a lista de **Componentes** ganha o *Interruptor DR geral (IDR)*.

> O IDR não substitui os DRs dos circuitos de áreas molhadas quando você quer seletividade: com IDR e DR no mesmo circuito, use no IDR um modelo seletivo (tipo S) ou uma sensibilidade maior. A bancada não confere essa coordenação.

## 8. Fases, quadro de cargas e componentes

1. **Dados do quadro ▾ > Balancear fases:** redistribui os circuitos entre R, S e T para a carga ficar o mais igual possível. Mostra antes e depois e pergunta antes de gravar. Para prender um circuito numa fase, escreva `*` depois dela (`R*`).
2. **Dados do quadro ▾ > Quadro de cargas:** monta a planilha *Quadro de cargas* com a carga de cada circuito por fase, o total, o desequilíbrio, os DRs (inclusive os grupos) e os circuitos sem fase. Se faltarem as reservas da NBR 5410, oferece acrescentá-las.
3. **Componentes:** lista o que vai dentro do quadro (disjuntor geral, DPS, disjuntores, DRs, barramentos e a caixa em módulos DIN) na planilha *Componentes_<quadro>*.
4. **Modelo 3D ▾ > Quadro 3D:** desenha o quadro em 3D com os componentes montados: a caixa no tamanho comercial (12, 18 ou 24 módulos por fileira), os trilhos DIN, o disjuntor geral, os DPS, o IDR, cada DR seguido dos disjuntores dos circuitos dele, os disjuntores com a alavanca, o barramento de fases em cima, o neutro (azul) e o terra (verde) embaixo e a porta transparente. Selecione o símbolo do quadro na planta (ou a planilha dele); sem seleção, faz todos os quadros ligados a uma planilha. O **Modelo 3D completo** também desenha os quadros assim. Cada peça tem a especificação e os circuitos nas propriedades e as propriedades IFC (disjuntor e DR como `IfcProtectiveDevice`).

## 9. Diagramas: unifilar e multifilar

- **Diagramas ▾ > Unifilar** desenha um diagrama por quadro: entrada, medição (se houver), disjuntor geral, DPS, barramentos, os circuitos com disjuntor, DR, condutores, seção, potência e descrição, os grupos de DR (seção 7) e as barras de neutro e de terra.
- **Diagramas ▾ > Multifilar** desenha cada condutor separado, com os barramentos R, S, T, N e PE na vertical.
- Depois de mudar a planilha de circuitos, gere o diagrama de novo: ele é recriado no mesmo lugar.
- Os diagramas ficam na pasta do quadro (*Térreo > Quadros e medição*).

## 10. Cálculos

Todos ficam em **Cálculos ▾**. Os formulários mostram poucas perguntas, com listas prontas; o resto fica em **Opções avançadas**. O resultado é recalculado a cada mudança.

| Botão | Para quê |
|---|---|
| Demanda | Grava a potência instalada e a demanda no quadro (aparecem no unifilar) |
| Gerador diesel | Potência do gerador, disjuntor, cabos e tanque; desenha a transferência rede/gerador |
| Curto-circuito | Estudo pela IEC 60909: I″k3, pico, fase-terra e capacidade de interrupção por quadro |
| Fator de potência | Banco de capacitores em estágios e risco de ressonância |
| Partida de motor | Contatores, relé térmico e disjuntor-motor; insere o motor na planta |
| Pressurização, Bomba de recalque | Pré-dimensionamento do ventilador e da bomba |

### Centro de medição (Enel SP)

Fica em **Quadros ▾**, nesta ordem:

1. **Centro de medição** (primeiro clique): cria a planilha *Centro de medição* com os pavimentos do projeto. Num projeto só com o Térreo, as unidades ficam nele; com andares, o mais baixo fica sem unidades. Preencha por andar a cota do piso (B), as unidades (C), a demanda de cada unidade em A (D) e as fases (E).
2. **Centro de medição** (segundo clique): compara medição agrupada, descentralizada e busway, com o custo de cada uma. **Gravar na planilha** guarda os valores do formulário.
3. **Gerar centro de medição:** escolha *agrupada* ou *descentralizada*. As colunas de medição, o abrigo e, na descentralizada, o ramal de cada centro são criados na pasta *Busway e medição* do pavimento, ficam selecionados e a vista enquadra neles. Ponha antes um símbolo de **Medição agrupada** na planta para eles nascerem ali.
4. **Mural de medição:** com as colunas selecionadas (ou todas), desenha a elevação frontal cotada, como na norma: caixas numeradas com medidor, disjuntor e suporte L, CDPM com os barramentos, disjuntor geral e DPS, eletroduto de entrada, piso, cotas e notas. Leve-o para a prancha com **Inserir na folha**; ele também sai no relatório PDF.
5. **Coluna de medição:** insere uma coluna avulsa (clique na planta para posicionar) ou, com uma coluna selecionada, edita a quantidade de medidores, o modelo e o desenho 3D.
6. **Busway:** com o caminho do QDC ao shaft desenhado e selecionado.

No relatório, a seção *Centro de medição* mostra a solução que está desenhada (o busway, se houver; senão a gerada; senão a mais barata) e a seção *Busway* traz a queda de tensão trecho a trecho e as caixas MEC. Deixe desenhada só uma solução: com duas, o relatório avisa.

A **descentralizada** precisa de pelo menos 2 andares com unidades. Se todos caberiam num centro só (até 4 andares, o padrão de *Andares por centro*), eles são divididos em dois centros. Com *Andares por centro* = 0, ela fica de fora.

### Prumadas verticais

**Infraestrutura ▾ > Prumadas verticais** projeta as prumadas de energia, dados e telefonia, interfone e iluminação de emergência pelo shaft:

1. Crie antes os pavimentos (e, se quiser, a planilha do centro de medição: as unidades de cada andar vêm dela).
2. Clique no botão, marque os sistemas, confira a tabela de andares e as quantidades por unidade e veja a prévia de cada trecho.
3. Confirme e clique na planta, no ponto do shaft. Cada pavimento recebe o símbolo das prumadas, com uma seta para cada apartamento (AP1, AP2, AP3...), e o esquema vertical fica ao lado, também com uma seta por apartamento em cada andar. Gire o objeto (tecla R na inserção, ou mudando a rotação dele) e os símbolos giram junto, com os textos sempre legíveis. Vistos de cima com todos os pavimentos à mostra, os símbolos dos andares ficam um em cima do outro: deixe visível só o pavimento que está desenhando.
4. Para mudar, selecione as prumadas e clique de novo no botão: o 3D, os símbolos e o esquema são refeitos.

O 3D mostra os eletrodutos e as caixas de passagem de cada andar; os materiais entram nos quantitativos e o relatório traz uma seção própria.

O luminotécnico fica em **Iluminação ▾ > Luminotécnico** (com o retângulo do ambiente selecionado), e a resistência de terra em **Aterramento ▾ > Resistência de terra**. Os dois entram no memorial do relatório: o luminotécnico guarda o cálculo no retângulo do ambiente, e a resistência de terra, ao clicar em **Gravar no projeto**, na planilha *Cálculo de aterramento*.

## 11. Documentos e folhas finais

1. **Documentos ▾ > Legenda** e **Notas:** desenham a legenda dos símbolos usados e as notas numeradas.
2. **Documentos ▾ > Quantitativos:** grava a lista de materiais em CSV, XLSX e PDF, no total e por pavimento.
3. **Modelo 3D ▾ > Modelo 3D completo:** gera as caixas, os eletrodutos e as eletrocalhas em 3D (necessário para os cortes).
4. **Folhas ▾ > Nova folha:** cria uma prancha (A0 a A4) com carimbo.
5. Selecione o que vai na prancha (o pavimento, o diagrama unifilar, a legenda, a planilha do quadro de cargas) e clique em **Folhas ▾ > Inserir na folha**. A escala é escolhida sozinha.
6. **Folhas ▾ > Corte na folha** e **Detalhe na folha:** a partir de uma linha ou de um círculo desenhados na planta.
7. **Folhas ▾ > Atualizar folhas** depois de qualquer mudança no projeto.

**Carimbo:** preencha uma vez, em **Projeto ▾ > Parâmetros**, as linhas *Carimbo: projeto, obra, cliente, desenho, responsável técnico e CREA/CFT*: elas aparecem em todas as folhas e mudam em todas quando você as muda. O conteúdo, a data e a revisão de cada folha ficam nas propriedades dela (grupo *Carimbo*). A numeração (01/03...) e a escala são automáticas. Também dá para editar o campo com dois cliques na própria folha: o texto vai para o parâmetro e para as outras folhas.
8. **Documentos ▾ > Relatório PDF:** o memorial descritivo e de cálculo completo, com capa, sumário, parâmetros e normas, previsão de cargas e luminotécnico por ambiente, quadro de cargas, demanda, cada circuito verificado passo a passo (fórmula e valores), DR, curto-circuito, gerador, centro de medição e busway (comparação de custos, solução adotada, alimentadores, queda trecho a trecho e caixas MEC), luminotécnico dos ambientes, aterramento (hastes, BEP, cabo de cobre nu e a resistência de terra com as contas), ocupação dos eletrodutos, avisos, materiais, diagramas e a vista 3D. Gere antes os diagramas e, se quiser essas seções, o estudo de curto, o gerador e a resistência de terra gravada. O que não atende sai em vermelho e é listado em *Avisos e limitações*.

Para imprimir, use os botões de exportação do TechDraw com a folha aberta.

**BIM e IFC:** todo objeto da bancada recebe a classe IFC e as propriedades para a exportação (veja no painel de propriedades, grupos *IFC* e *IFC Attributes*): a tomada é `IfcOutlet`, a luminária `IfcLightFixture`, o interruptor `IfcSwitchingDevice`, a caixa de passagem `IfcJunctionBox`, o quadro `IfcElectricDistributionBoard`, o eletroduto e a eletrocalha `IfcCableCarrierSegment`, o busway `IfcCableSegment`. As propriedades seguem os conjuntos do IFC4 (tensão, potência, fator de potência, polos, diâmetro, largura...) e o conjunto *Circuits_Eletrica* (circuito, quadro, comando, pavimento, altura de montagem); o `Tag` é o circuito (`QD1-C3`). Elas se atualizam sozinhas quando o objeto muda. **Modelo 3D ▾ > Propriedades BIM** grava tudo de uma vez (use em projetos antigos), e **Modelo 3D ▾ > Exportar IFC** grava o arquivo `.ifc`: gere antes o **Modelo 3D completo**, porque no IFC vão os sólidos (as caixas, os tubos, as eletrocalhas, os quadros); os símbolos 2D viram anotações. Para os pavimentos virarem andares no IFC, use níveis da bancada BIM.

## 12. Problemas comuns

| Sintoma | O que fazer |
|---|---|
| O comprimento ou a queda não aparecem na planilha de circuitos | A rede de eletrodutos não chega ao símbolo do quadro. Use **Conectar às caixas** e confira com **Rota do circuito**. |
| O grupo de DR não aparece no unifilar | Confira se o nome na coluna Q é exatamente igual (sem espaço a mais) e gere o unifilar de novo. |
| Um circuito do grupo continua com DR próprio | Gere o diagrama de novo: a coluna Q manda mais que a coluna J. |
| O símbolo entrou no pavimento errado | Ative o pavimento certo (**Projeto ▾ > Pavimento** ou duplo clique no nível do BIM) ou use **Mover para pavimento**. |
| O 3D dos eletrodutos não acompanha a mudança | Confira a preferência `AtualizarVerticais` ou use **Modelo 3D completo**. |
| A folha mostra a planta antiga | **Folhas ▾ > Atualizar folhas**. |
| Os diagramas ficaram brancos depois de abrir o projeto | Projetos gravados antes desta versão: **Documentos ▾ > Sketches em preto** uma vez e salve. |
| A descida até a tomada não aparece no 3D | Gere o **Modelo 3D**: ela sai junto com o tubo do eletroduto. |
| O centro de medição diz "Nenhum andar com unidades" | Preencha a coluna C (unidades) da planilha *Centro de medição*. |
| A medição descentralizada não aparece na lista | Precisa de 2 andares com unidades e *Andares por centro* maior que 0 (opções avançadas do Centro de medição). |
| A coluna de medição é criada mas não aparece (FreeCAD 1.1) | Corrigido nesta versão: o 1.1 lê a cor das peças de outro jeito e a coluna ficava transparente. Atualize a bancada e reabra o projeto: a cor é refeita ao abrir. |
| A coluna de medição se dividia em grupos de 4 caixas | Era a soma das unidades sem diversidade passando de 300 A. Agora cada agrupamento recebe até 30 caixas; informe a *Demanda total* do cálculo de demanda para o disjuntor geral e o ramal saírem certos. |
| Onde informo a demanda das colunas de medição? | No formulário da coluna, logo abaixo de *Medidores*: **Demanda total (diversificada)**, ou a **demanda média por unidade**, que calcula a total. |
| Não acho o centro de medição gerado | Ele fica na pasta *Busway e medição* do pavimento, sobre o símbolo de medição agrupada (ou na origem). Depois de gerar, os objetos ficam selecionados: use **Ver seleção**. |
| O PDF não é gerado | Falta a biblioteca `reportlab`: aceite a instalação que o botão oferece. |

> **Atenção:** os dimensionamentos são simplificados e usam tabelas e valores de catálogo genéricos. Confira os resultados com as normas (NBR 5410, NBR 5419) e com os catálogos dos fabricantes antes de usar em um projeto real. Veja a seção *Limitações* do [README](../README.md).
