# Circuits: bancada de projeto elétrico predial para o FreeCAD

Bancada **Engenharia** para o FreeCAD 1.1: do desenho dos pontos na planta até o quadro de cargas, o diagrama unifilar e a lista de materiais, sem sair do FreeCAD.

- Planta elétrica com símbolos de tomadas, iluminação, interruptores, pontos de energia e quadros, organizados por pavimento.
- Circuitos montados a partir dos pontos, com cabo, disjuntor, DR e equilíbrio de fases.
- Planilha de circuitos por quadro, diagrama unifilar e lista de componentes do quadro.
- Rede de eletrodutos ligada às caixas, com contagem de fios e lista de verticais.
- Quantitativo de materiais em CSV, XLSX e PDF.
- Cálculos prediais: demanda, gerador diesel, luminotécnico, pressurização de escada e bomba de recalque.
- Integração com os níveis da bancada BIM e geração 3D de caixas e eletrodutos.

> **Estado do projeto:** em desenvolvimento. A lógica tem testes automáticos, mas boa parte das funções novas ainda não foi validada no FreeCAD por um usuário. Os dimensionamentos são simplificados: leia [Limitações](#limitações) antes de usar um resultado em projeto real.

## Instalação

Requer **FreeCAD 1.1** ou mais novo.

Clone o repositório na pasta `Mod` do FreeCAD, com o nome `Circuits`. No Windows, pelo Git Bash:

```bash
cd "$APPDATA/FreeCAD/v1-1/Mod"
```

```bash
git clone -b master https://github.com/llosinskas/Circuits-FreeCAD.git Circuits
```

No Linux, a pasta costuma ser `~/.local/share/FreeCAD/v1-1/Mod`. Reabra o FreeCAD e escolha a bancada **Engenharia**.

Para atualizar:

```bash
cd "$APPDATA/FreeCAD/v1-1/Mod/Circuits"
```

```bash
git pull origin master
```

Depois use **Elétrica > Outros > Reiniciar Bancada** ou reabra o FreeCAD. Mantenha uma única cópia da bancada em `Mod`: duas cópias registram os mesmos comandos e uma substitui a outra.

O relatório e o quantitativo em PDF usam a biblioteca `reportlab`. Pelo **Addon Manager**, o FreeCAD pede para instalá-la junto com a bancada. Instalando pelo `git clone`, a bancada confere ao ser ativada e, se faltar, pergunta se pode instalar com o pip do FreeCAD, na mesma pasta que o Addon Manager usa (`AdditionalPythonPackages`). O botão **Não perguntar de novo** desliga a pergunta, mas o botão do relatório ainda oferece a instalação. Se o pip falhar (sem internet, por exemplo), a mensagem mostra o comando para rodar no terminal. O XLSX e o CSV não dependem de nada.

## Um projeto do começo ao fim

1. **Projeto > Novo projeto** cria a estrutura do documento, a planilha *Parâmetros do projeto* e o pavimento *Térreo* (ou ativa o primeiro nível do BIM, se o projeto já tiver níveis). Confira os parâmetros em **Projeto > Parâmetros**: tensões, esquema de aterramento, isolação, temperatura e limites de queda.
2. **Projeto > Pavimento** ou **Nível do BIM** escolhe ou cria o pavimento em que você vai desenhar.
3. **Tomadas, Energia, Iluminação e Interruptores**: insira os pontos na planta. Cada símbolo vai sozinho para a pasta do tipo dele no pavimento ativo.
4. **Iluminação > Luminotécnico**: com um retângulo do ambiente selecionado, calcula e distribui as luminárias.
5. **Circuitos > Definir circuito** e **Ligar interruptor**: agrupe os pontos em circuitos e ligue cada interruptor às suas luminárias.
6. **Quadros**: coloque na planta o quadro de distribuição, o de comando e a medição. Com o quadro selecionado, **Dados do quadro > Planilha do quadro** cria os dados dele e a planilha de circuitos.
7. **Montar circuitos**: soma os pontos de cada circuito, dimensiona cabo e disjuntor pela NBR 5410 e grava na planilha de circuitos do quadro. Desenhe e conecte os eletrodutos antes (passo 8) para a queda de tensão e o agrupamento entrarem no cálculo.
8. **Infraestrutura > Eletroduto** e **Conectar às caixas**: desenhe a rede de eletrodutos e prenda-a nas caixas. Em áreas técnicas e prumadas, **Bandeja/leito** e **Suportes**. Depois dos circuitos, **Ocupação eletrodutos** confere o diâmetro de cada eletroduto pelos cabos que passam nele, e **Rota do circuito** mostra o caminho de cada cabo até o quadro.
9. **Componentes** e **Unifilar**: lista o que vai dentro de cada quadro e desenha o diagrama.
10. **Cálculos > Demanda**: grava a demanda do quadro, que aparece no unifilar.
11. **Documentos**: quantitativos, legenda, notas e relatório PDF.
12. **Folhas**: monte as pranchas finais com carimbo, planta, diagramas, cortes e detalhes (veja "Folhas de desenho").

## Planta elétrica

### Pontos e símbolos

| Botão | Símbolos |
|---|---|
| Tomadas | Tomada baixa, média, alta, de piso |
| Energia | Chuveiro, ar-condicionado, ventilador, ponto de força, campainha |
| Iluminação | Luz de teto, arandela, luminária tubular, luz embutida, luz de emergência |
| Comandos | Interruptor simples, paralelo, intermediário, botão de campainha, fotocélula |
| Infraestrutura | Caixa de passagem (além das ferramentas de eletroduto, bandeja e suportes) |
| Aterramento | Haste de aterramento, caixa de inspeção, BEP |
| Quadros | Quadro de distribuição (QD), de comando (QC), de medição (QM), medição agrupada (CM), grupo gerador (GMG) e quadro de transferência (QTA) |

- **Campainha:** o botão de campainha funciona como um interruptor: selecione o botão e a campainha e use **Ligar interruptor**. A **fotocélula** também: ligue-a às luminárias que ela acende ao anoitecer.
- **Caixa de passagem:** é um nó da rede de eletrodutos, encaixado por **Conectar às caixas**; não tem carga nem circuito.
- A **tomada TUG antiga** saiu da barra; use as tomadas baixa, média, alta e de piso. Ela continua em **Elétrica > Outros**, e as já desenhadas continuam funcionando.

Cada ponto já nasce com potência, tensão, ligação (F+N, F+F ou 3F), altura de montagem e circuito, editáveis no painel de propriedades. Os quadros guardam a sigla em `Descricao` e, na medição, a quantidade de medidores em `Medidores`; eles não entram na soma de carga.

Enquanto um símbolo acompanha o cursor:

| Tecla | Efeito |
|---|---|
| Clique | Fixa o símbolo e já traz o próximo do mesmo tipo |
| **Espaço** (ou A) | Alinha com o símbolo mais próximo: um eixo, o outro eixo, solta |
| **R** | Gira 90° (**Shift+R**, 45°); os próximos símbolos da sequência já vêm girados |
| **L** | Liga ou desliga o alinhamento automático com os vizinhos |
| **ESC** | Encerra |

Para símbolos já colocados, selecione-os e use **Alinhar**, **Distribuir** ou **Escala dos símbolos**, no fim da barra *Modificador*. Sem seleção, a escala vale para todos os símbolos e para os próximos.

### Ambientes e pontos automáticos

1. **Projeto ▾ > Ambientes** transforma em polilinha cada espaço da bancada BIM (**Arquitetura > Espaço**) ou, com uma seleção, cada retângulo, polilinha ou face fechada selecionada. A polilinha vai para a pasta *Ambientes* do pavimento, com nome, tipo (sugerido pelo nome: "Cozinha 01" vira Cozinha, "WC" vira Banheiro), área e perímetro. Se o tipo vier errado, corrija na propriedade *TipoAmbiente*.
2. **Projeto ▾ > Pontos automáticos** mostra antes uma prévia por ambiente, com o tipo (que dá para trocar ali), portas, tomadas, potências, iluminação e equipamentos, e só gera os pontos se você confirmar. Ao lado da tabela, para o ambiente selecionado, ele pergunta:
   - **Porta:** as portas do projeto (BIM), a parede dela (com a posição em % da parede) ou "Sem porta". As paredes aparecem pelo lado na planta, por exemplo *Parede 2 – da direita, 3,00 m*.
   - **Pia / bancada** (cozinha, copa, área de serviço, lavanderia): as tomadas de 600 VA vão acima dela, no mínimo duas (NBR 5410 9.5.2.2.1 b). **Lavatório** (banheiro): a tomada de 600 VA junto a ele.
   - **Chuveiro** (banheiro), com a potência: no canto mais longe da porta.
   - **Ar-condicionado** (sala, dormitório, escritório), pela capacidade: na parede mais comprida sem porta.
   - Embaixo, para todos: a lâmpada e o pé-direito do **luminotécnico**, que sempre calcula as luminárias.

   Pelo mínimo da NBR 5410 (9.5.2):

| Ambiente | Tomadas (TUG) | Potência |
|---|---|---|
| Cozinha, copa, área de serviço, lavanderia | 1 a cada 3,5 m de perímetro | 600 VA nas 3 primeiras (2, se forem mais de 6), 100 VA nas outras; as de 600 VA ficam a meia altura |
| Banheiro | 1, junto ao lavatório | 600 VA, a meia altura |
| Sala e dormitório | 1 a cada 5 m de perímetro | 100 VA |
| Varanda | 1 | 100 VA |
| Demais | 1 até 6 m²; acima, 1 a cada 5 m | 100 VA |

- **Tomadas:** espaçadas pelo perímetro, fora das portas, a pelo menos 30 cm dos cantos e do interruptor, viradas para dentro.
- **Interruptor:** a 15 cm do batente da porta (as portas são as do BIM). Sem porta, fica no primeiro canto e a prévia avisa.
- **Luminárias:** sempre pelo luminotécnico (método dos lúmens), com a iluminância mantida do tipo (sala e dormitório 150 lx, cozinha, área de serviço e banheiro 200 lx, escritório 500 lx no plano de 0,75 m; corredor e varanda 100 lx e garagem 75 lx no piso), numa malha dentro do ambiente (também em L) com espaçamento de no máximo 1,5 × a altura útil. Cada ponto entra no circuito com o maior entre a potência da lâmpada e a parte dele na carga mínima da NBR 5410 (100 VA até 6 m² e mais 60 VA a cada 4 m² inteiros). Todas saem ligadas ao interruptor pela mesma letra.
- Os pontos saem **sem circuito**: use **Circuitos ▾ > Definir circuito**. Repetir o comando no mesmo ambiente substitui os pontos gerados antes por ele; os que você inseriu à mão ficam.

### Centro de medição Enel SP: busway ou medição agrupada

Pela especificação Enel 0018 (conexão coletiva, versão 2 de 2025), no grupo **Quadros ▾**:

1. **Centro de medição**: no primeiro clique cria a planilha *Centro de medição* com os pavimentos do projeto. Preencha unidades, demanda por unidade (A) e fases de cada andar, e troque os preços de referência (colunas G a I) pelas suas cotações. No segundo clique, informe a tensão, o uso (queda de 2 % residencial ou 1 % comercial), a distância do QDC à prumada e a demanda do edifício. A janela compara:
   - **Medição agrupada**: agrupamentos de caixas P com a CDPM (até 30 caixas e 300 A cada), o tamanho do centro de medição abrigado e o cabo de cada unidade do térreo até o andar.
   - **Busway com medição centralizada**: corrente nominal do barramento blindado, queda trecho a trecho pela fórmula da Enel (outra linha se não atender), caixas MEC por andar, shaft mínimo, emendas, suportes e barreiras corta-fogo.
   - **Medição descentralizada**: um centro (quadro) de medição a cada grupo de andares (4 por padrão, nas opções avançadas), no andar de baixo do grupo, cada um com o seu ramal de distribuição a partir do QDC, chave vertical com fusíveis no QDC e, a mais de 15 m da entrada, QDC próprio (item 7.18.2). Os cabos das unidades ficam curtos.
   - O custo estimado de cada uma e a recomendada pelo menor custo. O resultado fica gravado na planilha.
   - **Gerar centro de medição** desenha a solução escolhida (agrupada ou descentralizada): as colunas paramétricas de cada centro, o contorno do abrigo com a área e, no descentralizado, o ramal de cada centro, nos pavimentos certos. Rodar de novo, depois de mudar a planilha, recria tudo e mantém no lugar o que você moveu. Os novos ficam sobre o símbolo de medição agrupada do pavimento, se houver.
2. **Coluna de medição**: insere as colunas de medição **paramétricas**. Pelas medições, demanda e fases, escolhe a caixa: P em agrupamento modular (mono e bifásicas até 100 A; até 3 por coluna e 30 por agrupamento, como 10 colunas de 3 com a CDPM no meio) caixas E com CDPM (até 4 trifásicas e 125 A) ou as caixas metálicas K, L, H, M, N e O (mais trifásicas); acima de 100 A, medição indireta no padrão Enel SP: até 300 A no agrupamento de policarbonato (chave seccionadora, caixa dos TCs, proteção geral, medidor e bloco de aferição) e de 300 a 600 A na caixa M, com dois circuitos de entrada. Em cada conjunto, dimensiona o disjuntor geral, o barramento (Tabela 23) e o ramal de distribuição, e o disjuntor de cada unidade. Nas propriedades do objeto dá para mudar medidores, medidores por coluna, demanda, fases, modelo da caixa e CDPM: o dimensionamento e o 3D detalhado (tampas transparentes, medidores, disjuntores, barramentos, DPS, CDPI, caixa de barramentos e eletrodutos) se refazem. Você posiciona com o mouse.
3. **Busway**: desenhe com Linha ou Polilinha o caminho do QDC até o shaft, selecione e clique. O caminho vira busway e, do último ponto, sobe a prumada pelos andares com os plug-ins e as caixas MEC, em 3D, e um texto por andar na pasta *Busway e medição*.

O busway, as caixas MEC e as colunas entram nos **Quantitativos**, no grupo *Busway e medição* (metros por corrente, cotovelos, emendas, suportes, corta-fogo, fitas, caixas MEC, plug-ins, caixas P, CDPM, barramentos, DPS), por pavimento.

Os k e as medidas dos busways e das caixas MEC e os preços são valores típicos: confirme com o fabricante homologado e com a Enel.

### Pavimentos

Cada pavimento é uma pasta com os símbolos separados por tipo:

```
Pontos_eletricos
├── Térreo
│   ├── Tomadas
│   │   └── Tomadas 3D        (caixas geradas pelo Modelo 3D)
│   ├── Pontos de energia
│   ├── Iluminação
│   ├── Interruptores
│   ├── Quadros e medição     (símbolos, planilhas do quadro e diagrama unifilar)
│   ├── Eletrodutos
│   ├── Bandejas e leitos     (bandejas, conexões e suportes)
│   ├── Circuitos             (textos de identificação dos pontos)
│   └── Fiação                (traços de fase, neutro e terra)
└── 1º Pavimento
    └── ...
```

- **Níveis do BIM:** se o projeto tem níveis da bancada BIM, eles são os pavimentos, e as pastas ficam dentro do próprio nível. A cota vem do nível; a bancada não altera níveis do BIM.
- **Onde o símbolo entra:** no nível ativo da bancada BIM (o que você ativou com duplo clique), ou no pavimento selecionado na árvore, ou no pavimento ativo.
- **Altura no desenho:** o símbolo 2D fica no plano do piso do pavimento, então todos os símbolos de um pavimento estão no mesmo Z. A altura de montagem (`Altura3D`), sempre medida a partir do piso, só vale para o 3D: uma tomada alta tem 2,00 m em qualquer pavimento; no pavimento de cota 3,00 m o símbolo fica em Z 3,00 m e a caixa 3D em 5,00 m.
- **Projeto > Ajustar cotas** recoloca todos os símbolos no piso do pavimento deles; use uma vez em projetos feitos antes desta regra.
- **Projeto > Pavimento** escolhe o pavimento ativo ou cria um novo, com cota e altura de piso a piso, e sugere o próximo.
- **Projeto > Nível do BIM** cria um nível da bancada BIM e o ativa.
- **Projeto > Mover para pavimento** leva os símbolos selecionados para outro pavimento, já na cota do piso dele.

As caixas e os eletrodutos 3D somam a cota do pavimento à altura de montagem e ficam numa subpasta 3D dentro da pasta do elemento, por exemplo *Térreo > Tomadas > Tomadas 3D*.

**Modelo 3D > Modelo 3D completo** gera ou refaz todo o 3D num clique: as caixas de todos os símbolos, os tubos de todos os eletrodutos, as eletrocalhas com curvas, tês e reduções, e os suportes. Os botões separados (caixas, eletrodutos, tomadas TUG antigas) continuam no mesmo grupo.

A caixa 3D da **tomada de parede** fica atrás do ponto de inserção, dentro da parede: insira a tomada com o traço encostado na face da parede e o triângulo apontando para o ambiente (gire com **R**), e a caixa entra na parede com a largura ao longo dela. A **tomada de piso** tem a caixa embaixo do piso. Os outros símbolos continuam com a caixa centrada no ponto.

Tudo o que é gerado a partir dos símbolos fica no pavimento deles: a identificação vai para a pasta *Circuitos*, a fiação para *Fiação*, e as planilhas do quadro (dados, circuitos e componentes) e o diagrama unifilar ficam junto do símbolo do quadro, em *Quadros e medição*. O que está fora de um pavimento continua nos grupos da raiz.

### Circuitos e interruptores

- **Definir circuito:** dá o mesmo circuito (e, se quiser, o quadro) aos pontos selecionados; sugere o próximo número livre.
- **Ligar interruptor:** dá a mesma letra de comando (a, b, c...) ao interruptor e às luminárias selecionadas. Para paralelos, selecione os dois interruptores junto.
- **Identificar pontos:** escreve ao lado de cada símbolo duas linhas: o circuito, a letra e a potência (`C1 · a · 100 VA`) e os cabos que chegam à caixa, com a seção e os condutores (`#2,5 F+N+T`). F é fase, N neutro, T terra e R retorno: uma luminária comandada recebe `R+N+T`, um interruptor simples `F+R` e um paralelo `F+2R`. A seção vem da planilha de circuitos do quadro.

## Quadros e unifilar

### Planilha de circuitos

Cada quadro tem uma planilha de dados (tensão, fases, disjuntor geral, DPS) e uma planilha de circuitos, aberta por **Dados do quadro > Circuitos do quadro**, com um circuito por linha:

| Coluna | Conteúdo |
|---|---|
| Circuito, Descrição | Identificação |
| Potência [W], Tensão [V] | Carga do circuito |
| Fases (R, S, T) | `R`, `RS` ou `RST` |
| Corrente, Cabo, Disjuntor, Curva | Podem ficar em branco |
| DR, Sensibilidade, Neutro, Terra | `S` ou `N` |
| Comprimento [m], Queda de tensão [%], Critério determinante | Preenchidos pelo Montar circuitos |

**Montar circuitos** preenche essa planilha a partir da planta, mas ela também pode ser preenchida à mão. O Unifilar e os Componentes calculam o que ficar em branco e respeitam o que foi digitado.

### Dimensionamento pela NBR 5410

O **Montar circuitos** escolhe o disjuntor (Ib ≤ In) e o menor cabo que atende a todos os critérios, e escreve na planilha qual deles decidiu:

| Critério | Como é verificado |
|---|---|
| Seção mínima | 1,5 mm² na iluminação, 2,5 mm² nos outros (tabela 47) |
| Capacidade de condução | Iz corrigida pela temperatura dos parâmetros (tabela 40) e pelo número de circuitos no trecho mais cheio do trajeto (tabela 42), com In ≤ Iz |
| Queda de tensão | Até o ponto mais distante, com as descidas, limitada pelo valor dos parâmetros (4 %). Fórmula do anexo G da IEC 60364-5-52: resistividade do condutor quente (0,0225 Ω·mm²/m no cobre, 0,036 no alumínio), fator de potência do circuito e reatância de 0,08 mΩ/m |
| Curto-circuito | S ≥ I·√t / k, só quando o tempo de atuação é preenchido nos parâmetros |
| Contatos indiretos | No esquema TN, o comprimento máximo para o disjuntor seccionar, com o condutor de proteção da tabela 58 (igual à fase até 16 mm², 16 mm² até 35 mm², metade acima); acima dele, aviso para usar DR. No TT, DR em todos os circuitos |

O comprimento e o agrupamento vêm da rede de eletrodutos e só entram quando ela chega ao símbolo do quadro ligado à planilha. Sem rede, valem a seção mínima e a capacidade de condução. A sobrecarga (I2 ≤ 1,45·Iz) fica atendida com Ib ≤ In ≤ Iz e disjuntores da NBR NM 60898.

O cabo que o Unifilar e os Componentes calculam para as linhas digitadas com corrente, cabo ou disjuntor em branco usa o mesmo cálculo, com os parâmetros do projeto e, se preenchida, a coluna *Comprimento* da linha.

### Balanceamento de fases

**Dados do quadro ▾ > Balancear fases** redistribui os circuitos da planilha de circuitos entre as fases do quadro (R, S e T, ou só R e S num quadro bifásico) para a carga ficar o mais igual possível:

- Mostra a potência e a corrente de cada fase antes e depois, o desequilíbrio ((maior − menor) / maior; o usual é até 10 %) e os circuitos que mudam de fase, e pergunta antes de gravar.
- Circuitos bifásicos dividem a potência entre as duas fases; trifásicos não mudam.
- Para prender um circuito numa fase, escreva `*` depois dela na coluna *Fases* (ex.: `R*`).
- Sem potência na linha, usa corrente × tensão.
- O **Montar circuitos** usa o mesmo método ao distribuir as fases dos circuitos novos.

Depois de gravar, gere o Unifilar de novo para atualizar as fases no diagrama.

**Projeto > Parâmetros** abre a planilha *Parâmetros do projeto*. Edite a coluna *Valor*; em branco vale o padrão:

| Parâmetro | Padrão |
|---|---|
| Tensão fase-neutro e fase-fase | 127 V e 220 V |
| Esquema de aterramento | TN-S (TN-C-S e TT também) |
| Material e isolação | Cobre, PVC (EPR e XLPE também) |
| Temperatura ambiente | 30 °C |
| Queda máxima nos terminais e total | 4 % e 7 % |
| Curva dos disjuntores | B na iluminação, C nas tomadas e no uso específico |
| Sensibilidade do DR | 30 mA |
| Corrente de curto na entrada e tempo de atuação | 5 kA e 0 (0 não verifica o curto) |

### Unifilar e componentes

- **Unifilar:** um diagrama por quadro, com medidor (quando a origem do quadro é uma medição), disjuntor geral, DPS, barramentos de fases, neutro e terra, e, em cada circuito, o disjuntor com os terminais e o arco, a proteção (`C16A`) e as fases, o DR com a sensibilidade, os traços de terra, neutro e fases, a seção (`#2,5 mm²`), a potência, o número e a descrição.
- **Multifilar:** o botão **Multifilar**, no grupo **Diagramas ▾** junto com o Unifilar, desenha um diagrama por quadro, na vertical, com cada condutor separado: os barramentos R, S, T (conforme o número de fases do quadro), N e PE descem lado a lado, e cada circuito sai deles para a direita, um embaixo do outro, com um condutor por fase, o neutro e o terra. Cada fase tem um polo do disjuntor (os polos de um mesmo disjuntor ligados por tracejado), o DR abraça as fases e o neutro, e o terra segue direto. Cada circuito termina num retângulo com o número e a descrição; em cima dos condutores ficam a proteção, a sensibilidade do DR, a seção e a potência. A entrada vem por cima, pelo disjuntor geral. Os multifilares ficam à direita dos unifilares e, se você os mover, voltam no mesmo lugar ao gerar de novo.
- **Gerador e transferência:** se o projeto tiver o gerador calculado (planilha *Cargas do gerador* com o resultado gravado), o Unifilar também desenha, à esquerda dos quadros, a entrada com gerador: rede e gerador, cada um com disjuntor, os contatores K1 e K2 intertravados do QTA, a saída para as cargas do gerador e os dados do gerador e dos cabos. O botão Gerador diesel redesenha esse diagrama ao gravar o resultado. Se você mover o diagrama, ele é recriado no mesmo lugar.
- **Ligação ao quadro geral:** a saída do QTA vai até a entrada do diagrama do quadro geral, na mesma altura, com o texto "Alimenta QGBT". O quadro geral é o que tem a origem começando com **QTA** (ou igual à sigla do símbolo de QTA da planta) na planilha do quadro; sem isso, o único quadro que está entre as cargas do gerador. Gere o Unifilar para refazer a ligação depois de mudar os quadros.
- **Componentes:** disjuntor geral, DPS, disjuntores e DR dos circuitos, barramentos com o número de terminais e o tamanho da caixa em módulos DIN, com a reserva de circuitos da NBR 5410. A lista fica numa planilha `Componentes <quadro>`.

## Eletrodutos, fios e verticais

1. Desenhe os eletrodutos com **Infraestrutura > Eletroduto** (sem nada selecionado, abre a ferramenta de linha). O snap do Draft pode prender no ponto de inserção de cada símbolo (a caixa).
2. Selecione as linhas e clique de novo em **Eletroduto**. No formulário, escolha diâmetro, tipo (flexível ou rígido), material (PVC ou aço), instalação (teto ou parede, piso ou aparente) e altura. A bancada, como nas eletrocalhas:
   - guarda as linhas na pasta *Eletrodutos* do pavimento e deixa tracejado o eletroduto do piso;
   - junta a ponta solta a até 30 cm de outro eletroduto (no vértice, ou no meio do trecho, como derivação) e puxa para a caixa os vértices a até 30 cm dela;
   - cria uma **caixa de passagem** em cada derivação embutida sem caixa; no aparente, a derivação leva condulete;
   - escreve o diâmetro (`Ø3/4"`) em cada eletroduto e a sigla das curvas e conduletes (C90, C45, CT, CX), e avisa das pontas soltas.

   **Conectar às caixas** continua servindo para encaixar nas caixas os eletrodutos já marcados, todos de uma vez.

   | Peça | Quando |
   |---|---|
   | Curva 90° / 45° | rígido mudando de direção (o flexível só dobra) |
   | Luva | rígido entre barras de 3 m e em trechos alinhados |
   | Bucha e arruela | cada rígido que entra numa caixa |
   | Condulete T / X | derivação aparente sem caixa |
   | Abraçadeira tipo D | aparente, a cada 1,5 m e na ponta de cada trecho |

   Todas entram nos quantitativos, no total e por pavimento. No 3D, o rígido faz a curva com raio de 3 diâmetros.
3. **Lista de verticais** cria a planilha *Verticais*, com a descida ou subida de cada caixa: altura do eletroduto, altura da caixa, comprimento e diâmetro.

Os fios são contados pelo caminho mais curto na rede, do quadro até os pontos de cada circuito:

- fase até pontos e interruptores; neutro e terra até os pontos;
- retorno do interruptor até as luminárias da mesma letra, e dois condutores a mais entre interruptores paralelos e intermediários;
- seção e fases pela planilha de circuitos do quadro;
- verticais e 30 cm de folga em cada caixa.

O botão **Fiação** desenha na planta os traços de fase, neutro e terra ao lado de cada ponto.

### Rota dos cabos e diâmetro dos eletrodutos

- **Infraestrutura > Rota do circuito** segue o cabo de cada circuito do quadro até os pontos, pelos eletrodutos e pelas eletrocalhas (a ponta do eletroduto que chega na borda de uma eletrocalha entra nela), seleciona tudo por onde ele passa e mostra o caminho de cada ponto (`QD1 → Eletroduto 3 → calha Bandeja → Eletroduto 7 → T4`). Selecione pontos (o circuito deles), um quadro (todos os circuitos dele) ou um eletroduto (os circuitos que passam nele); sem seleção, escolha o circuito numa lista.
- **Infraestrutura > Ocupação eletrodutos** conta os condutores de cada trecho (fases, neutro, terra e retornos de todos os circuitos que passam ali) e confere o diâmetro pela taxa de ocupação da NBR 5410 (6.2.11.1.6): no máximo 53 % da seção interna com um cabo, 31 % com dois e 40 % com três ou mais. Vale o trecho mais cheio de cada eletroduto. Grava a planilha *Ocupação dos eletrodutos* (desenhado, cabos, condutores, circuitos, área, ocupação, sugerido) e oferece aumentar os eletrodutos pequenos para o diâmetro sugerido, refazendo os rótulos `Ø`; se você recusar, eles ficam selecionados. O flexível corrugado tem seção livre menor que o rígido.
- Nas eletrocalhas a norma não dá uma taxa: a planilha mostra a área ocupada sobre a seção útil (largura × aba) e a largura de uma camada única de cabos, com 40 % só como referência.
- **Circuitos > Fios por trecho** escreve ao lado de cada eletroduto (do lado oposto ao `Ø`) os fios que passam nele, uma linha por circuito: `C1 #2,5 F+N+T`, `C3 #1,5 F+2R`; na eletrocalha, os circuitos e o total de cabos. Trechos do mesmo eletroduto com os mesmos fios levam um texto só. Os textos vão para a pasta *Fiação* do pavimento; repetir o comando apaga e escreve de novo.

### Subidas, descidas e detalhes das verticais

- **Infraestrutura > Subidas e descidas** desenha na planta o símbolo de cada vertical, com o texto ao lado (`Ø3/4" desce 2,50 m`, `EL 200x50 sobe 0,50 m`):
  - eletroduto: círculo com seta; a seta aponta para o círculo quando desce, para fora quando sobe, e para os dois lados onde um eletroduto do teto encontra um do piso;
  - eletrocalha e leito: a seção da bandeja com a diagonal e a seta.
  
  Entram as descidas até as caixas, os encontros de eletrodutos em alturas diferentes e os trechos verticais das bandejas. Para não desenhar o símbolo em toda caixa, mude *Símbolo de descida em cada caixa* para `N` em **Projeto > Parâmetros**.
- **Infraestrutura > Detalhar verticais** desenha ao lado da planta um detalhe em elevação por tipo de vertical (V1, V2...): piso, laje, cotas de altura, trecho horizontal, caixa ou curvas verticais em arco (CVE e CVI; raio de 6 diâmetros no eletroduto e igual à largura na eletrocalha), a quantidade e onde ficam. Verticais iguais (mesmo diâmetro ou seção, sentido e alturas) dividem o mesmo detalhe.

O encontro de dois eletrodutos em alturas diferentes entra nos quantitativos como eletroduto vertical.

### Descidas entre eletrodutos de alturas diferentes

Ligue no mesmo ponto da planta dois eletrodutos com alturas diferentes (por exemplo, um no teto e outro no piso) e marque-os com o botão **Eletroduto**. A bancada faz a descida sozinha:

- **3D:** cada eletroduto que termina no ponto faz uma curva de 90° até a vertical, e o tubo horizontal é encurtado pelo raio da curva. O raio é de 3 diâmetros no rígido (curva pré-fabricada) e maior no flexível, reduzido se a vertical ou o trecho forem curtos. Se o 3D dos eletrodutos já existe, ele é refeito; se não, só a descida aparece.
- **Planta:** o símbolo de subida ou descida é desenhado no ponto.
- **Quantitativos:** a vertical entra como eletroduto, e cada curva do rígido como "Curva 90° vertical".

Para mudar uma descida depois, use **Infraestrutura ▾ > Editar descidas**. A tabela mostra cada descida (pavimento, posição, eletrodutos e diâmetro) com a altura de cima e a de baixo, que você pode mudar. Clicar numa linha seleciona os eletrodutos dela. Na coluna *Ligação*, **Caixa de passagem** troca as curvas por uma caixa no ponto. Mudar a altura muda o eletroduto inteiro, inclusive a outra ponta dele. O 3D e os símbolos que já existiam são refeitos.

### Prumadas entre pavimentos (pelo teto ou pelo piso)

Para levar um eletroduto ou uma eletrocalha de um pavimento a outro, desenhe o trecho de cada pavimento normalmente e deixe uma **ponta solta no mesmo ponto em planta** nos dois (a até 10 cm; use o snap). No eletroduto, ponta solta é a que não chega a uma caixa; na eletrocalha, a ponta que seria terminal. A bancada liga as duas pontas como prumada, com a vertical calculada pelas cotas dos pavimentos e pelas alturas de cada trecho, e trata cada pavimento assim:

| Onde | Eletroduto | Eletrocalha | Texto |
|---|---|---|---|
| No pavimento (sobe ou desce até a caixa, teto ↔ piso) | círculo com seta | seção com uma diagonal e seta | `Ø3/4" desce 2,50 m` |
| Pavimento de baixo: sai pelo **teto** | círculo duplo, seta saindo | seção com X, seta saindo | `Ø1" sobe ao 1º Pavimento 3,20 m` |
| Pavimento de cima: entra pelo **piso** | círculo duplo, seta entrando | seção com X, seta entrando | `Ø1" desce ao Térreo 3,20 m` |
| Pavimentos do meio: só **passa** | círculo duplo, seta atravessando | seção com X, seta atravessando | `Ø1" passa (Térreo → 2º Pavimento)` |

- **Legenda:** ganha uma linha para cada um desses casos que aparece no projeto.
- **Detalhar verticais:** desenha a prumada uma vez, com os pisos de todos os pavimentos que ela atravessa.
- **Quantitativo:** conta a prumada uma vez, no pavimento de baixo: eletroduto vertical; na eletrocalha, metros, curvas verticais, emendas e suportes de parede. A ponta da eletrocalha que vira prumada deixa de contar terminal.
- **Modelo 3D completo:** desenha a prumada atravessando a laje.
- **Avisos:** o Eletroduto deixa de avisar "ponta solta" para as pontas que são prumada.

## Bandejas e leitos

1. Desenhe o trajeto com linhas (o botão **Bandeja/leito** sem nada selecionado abre a ferramenta de linha). Um ramal que sai do meio de outra bandeja é desenhado com a ponta sobre ela.
2. Selecione as linhas e clique em **Infraestrutura > Bandeja/leito**: escolha eletrocalha perfurada, lisa ou leito para cabos, largura, aba, altura de instalação (do piso à base) e tampa.
   - **Junções automáticas:** a ponta de uma bandeja a até 30 cm de outra é levada até ela: para o vértice mais próximo (vira curva ou cruzeta) ou, sem vértice perto, para o meio do trecho (vira tê). Não é preciso acertar o encontro com o snap.
   - **Cruzamentos:** duas bandejas na mesma altura que se cruzam viram cruzeta; em alturas diferentes, uma passa sob a outra.
3. A bancada guarda as linhas na pasta *Bandejas e leitos* do pavimento, desenha a bandeja em linha dupla na planta, gera o modelo 3D (fundo e abas, ou longarinas e travessas no leito) com as peças montadas, e escreve na planta a sigla de cada conexão. As curvas são em arco, com raio igual à largura da bandeja; os tês e as cruzetas têm o fundo quadrado na largura da principal, fechado nos lados sem ramal e dos dois lados de um ramal mais estreito. Os trechos retos são recortados para as peças encaixarem:

| Sigla | Peça | Quando |
|---|---|---|
| C90, C45 | Curva horizontal 90° ou 45° (outros ângulos com o valor medido) | dois trechos com mudança de direção |
| T | Tê horizontal | três trechos no mesmo nó, ou a ponta de um ramal sobre outra bandeja |
| X | Cruzeta horizontal | quatro trechos no mesmo nó |
| TF | Terminal de fechamento | ponta solta |
| R | Redução | trecho de seção menor que a bandeja principal do nó: mais estreito ou, na mesma largura, com aba mais baixa. Numa emenda ou depois de uma curva, é uma peça de 30 cm com as bordas inclinadas, na planta e no 3D; num tê, a boca do tê já sai na largura do ramal |
| CVE + CVI | Curvas verticais externa e interna 90°, com o trecho vertical entre elas | trecho em outra altura de instalação |

Para subir ou descer, desenhe os trechos com alturas diferentes e com as pontas no mesmo ponto: a bancada conta as duas curvas verticais, o trecho vertical (que entra nos metros e no 3D) e os suportes de parede dele. As siglas de um mesmo ponto aparecem juntas, por exemplo `T + R` ou `C90 + CVE + CVI`.

**Infraestrutura > Suportes** coloca um suporte suspenso a 50 cm de cada conexão e os intermediários com vão de até 1,5 m (eletrocalha) ou 2,0 m (leito). Cada suporte é um perfilado 38x38 sob a bandeja e dois tirantes de 3/8" até a laje (altura de piso a piso do pavimento); aparece como um traço na planta e no modelo 3D. Repetir o comando refaz os suportes.

Nos quantitativos, entram no total e em cada pavimento:

- *Bandejas e leitos*: metros por tipo e seção com 5 % de perdas (inclusive os verticais), curvas horizontais e verticais, tês, cruzetas, reduções, terminais, emendas e tampa;
- *Suportes*: suportes suspensos, perfilado, vergalhão roscado, chumbadores, porcas e arruelas, e os suportes de parede dos trechos verticais;
- *Fixação*: parafusos cabeça lentilha 1/4" x 5/8" com porca e arruela (8 por emenda, 4 por terminal, 2 por suporte de parede) e 2 grampos da bandeja no perfilado por suporte.


### Saídas de eletroduto nas eletrocalhas

Termine o eletroduto na eletrocalha (ou a até 30 cm dela) e marque-o com o botão **Eletroduto**; ou desenhe a eletrocalha depois, por cima das pontas. A bancada leva a ponta até a eletrocalha e cria a saída:

| Altura do eletroduto | Saída | Na planta |
|---|---|---|
| Entre a base e o topo da aba da eletrocalha | **Horizontal**, pela lateral: a ponta vai para a borda | ponto cheio e `SH Ø3/4"` |
| Abaixo (ou acima) da eletrocalha | **Vertical**, pelo fundo (ou por cima): o eletroduto faz curva de 90° e sobe até o fundo | ponto cheio e `SV Ø3/4"` |

- A saída entra nos quantitativos (grupo *Bandejas e leitos*, "Saída horizontal/vertical para eletroduto" com o diâmetro); no rígido, também bucha e arruela e, na vertical, a curva. A vertical soma nos metros de eletroduto.
- No 3D, cada saída ganha a peça: uma flange quadrada encostada na eletrocalha (na aba, do lado de fora, na horizontal; embaixo do fundo, na vertical) e a luva com anel por onde entra o eletroduto. A saída vertical aparece também com a curva e o tubo até o fundo da eletrocalha, e em **Editar descidas**.
- A ponta que chega à eletrocalha deixa de ser avisada como ponta solta.

## Folhas de desenho

Botão **Folhas ▾** (barra *Quadros e documentos*). As folhas são do TechDraw, com as margens da NBR 10068 e um carimbo editável (projeto, conteúdo, obra, cliente, desenho, responsável técnico, CREA/CFT, data, escala, folha e revisão). Para mudar um campo, dê dois cliques nele na folha.

1. **Nova folha**: escolha o formato (A0 a A4) e o conteúdo. O carimbo já vem com o nome do projeto, a data e os dados da última folha (obra, cliente, responsável); a numeração 01/03, 02/03... é refeita em todas.
2. **Inserir na folha**: selecione na árvore o que vai para a folha e clique. Um **pavimento** vira a planta baixa (sem o modelo 3D); o **diagrama unifilar**, o multifilar, a **legenda**, as **notas**, os **detalhes das verticais** ou qualquer grupo viram desenhos; uma **planilha** (circuitos, quadro de cargas, componentes) vira tabela. Selecione a folha junto para escolher em qual entra; senão vai para a última. A bancada escolhe a maior escala normalizada (1:20, 1:25, 1:50, 1:75, 1:100...) em que tudo cabe, arruma as vistas sem invadir o carimbo, põe o título com a escala embaixo de cada uma e escreve a escala no carimbo.
3. **Corte na folha**: desenhe na planta uma linha onde o corte passa, selecione e clique. Sai o corte do modelo 3D (gere o **Modelo 3D** antes), com a letra (Corte A-A) e as setas na planta. Quem olha fica à esquerda da linha, do primeiro para o segundo ponto, e olha para a direita dela.
4. **Detalhe na folha**: desenhe um círculo (ou retângulo) em volta do que quer ampliar, selecione e clique. Sai o detalhe D1, D2... da planta, recortado no retângulo em volta da forma, em pelo menos o dobro da escala da folha, e o nome dele aparece na planta.
5. **Organizar folha**: arruma de novo as vistas da folha, na escala que você escolher ou na maior que couber.
6. **Atualizar folhas**: depois de mudar o projeto, redesenha as plantas, diagramas e detalhes de todas as folhas no mesmo lugar e escala (os cortes e as tabelas o TechDraw atualiza sozinho).

Para imprimir ou exportar em PDF, use os botões do próprio TechDraw com a folha aberta.

## Documentação

### Quantitativos

**Documentos > Quantitativos** levanta os materiais do desenho e grava, com o mesmo nome:

- `Quantitativo_<projeto>.csv`, separado por ponto e vírgula, abre no Excel com os acentos certos;
- `Quantitativo_<projeto>.xlsx`, com as abas *Quantitativo* (total do projeto), *Por pavimento*, *Verticais* e *Fiação por circuito*;
- `Quantitativo_<projeto>.pdf`, com as mesmas tabelas, uma por pavimento, e os avisos;
- `_pavimentos.csv`, `_verticais.csv` e `_circuitos.csv`, com as tabelas auxiliares.

O quantitativo por pavimento soma em cada um os pontos, caixas, eletrodutos, verticais, fios, aterramento e os componentes dos quadros que estão nele; o que está fora de um pavimento aparece como *Sem pavimento*.

| Grupo | Como é contado |
|---|---|
| Pontos | Por tipo, tensão e potência |
| Interruptores | Simples, paralelo, intermediário, botão de campainha, fotocélula |
| Caixas | Uma por ponto: 4x2" na parede, octogonal 4x4" no teto, de piso; e as caixas de passagem |
| Eletrodutos | Trechos horizontais e verticais por diâmetro, com 10 % de perdas |
| Bandejas e leitos | Metros por tipo e seção, conexões, emendas e tampa |
| Suportes | Suporte suspenso por posição, com perfilado, tirantes até a laje e chumbadores |
| Fios e cabos | Metros por seção e função: fase, neutro, terra, retorno |
| Quadros | Símbolos de quadro e componentes de cada quadro |
| Aterramento | Hastes, caixas de inspeção, BEP, conectores haste-cabo e cabo de cobre nu por seção, com 10 % de perdas |

### Legenda, notas e relatório

- **Legenda:** desenha ao lado da planta os símbolos usados, inclusive os tipos de interruptor.
- **Planilha de notas** e **Notas:** escreva as notas numa planilha, uma por linha; o botão as desenha numeradas embaixo da legenda.
- **Sketches em preto:** os Sketches da bancada já nascem pretos; o botão repinta os de projetos antigos.
- **Relatório PDF:** quadros, demandas, materiais e os diagramas. Cada diagrama gerado (unifilar e multifilar de cada quadro e a transferência rede/gerador) sai numa página: na hora de capturar, a bancada mostra só aquele diagrama, vira a vista para o topo e enquadra nele, grava a imagem com fundo branco na proporção do desenho e depois devolve a vista e a visibilidade como estavam. Gere os diagramas antes do relatório.

## Aterramento

O botão **Aterramento** da barra *Planta elétrica* reúne:

- **Haste de aterramento**, **Caixa de inspeção** e **BEP** (barramento de equipotencialização principal): símbolos na planta, guardados na pasta *Aterramento* do pavimento. A haste fica abaixo do piso no modelo 3D.
- **Condutor de aterramento:** desenhe o caminho do cabo com uma linha, selecione-a e escolha a seção (16 a 70 mm²). A linha fica verde, vai para a pasta *Aterramento* e o comprimento entra nos quantitativos como cabo de cobre nu.
- **Resistência de terra:** calcula a resistência de uma haste e de várias hastes em linha (fórmulas da IEEE 142) e o menor número de hastes que atinge a resistência desejada. Escolha o tipo de solo ou informe a resistividade medida.

## Cálculos prediais

| Cálculo | O que faz |
|---|---|
| Demanda | Aplica fatores de demanda residenciais aos circuitos e grava no quadro |
| Gerador diesel | Potência do gerador pelas cargas, demanda, diversidade e partida do maior motor; disjuntor, cabos, neutro, PE e tanque de diesel |
| Luminotécnico | Método dos lúmens: quantidade, malha e iluminância; distribui as luminárias no retângulo selecionado |
| Pressurização | Vazão de ar da escada (portas fechadas e abertas), ventilador e motor |
| Bomba de recalque | Vazão, tubo, altura manométrica e motor |
| Resistência de terra | Resistência das hastes em linha e número de hastes (no botão Aterramento) |

### Gerador diesel

1. Clique em **Cálculos > Gerador diesel**. Na primeira vez, a bancada cria a planilha **Cargas do gerador**, com uma linha por quadro do projeto (a potência instalada e o fator de demanda vêm do botão Demanda; sem ele, da soma dos circuitos) ou, sem quadros, com cargas de exemplo.
2. Revise a planilha, uma carga por linha: descrição, tipo, quantidade, potência de cada uma, unidade (kW, kVA ou cv), fator de potência, fator de demanda, partida do motor e se vai no gerador (S/N). Em branco valem quantidade 1, o fator de potência típico do tipo, demanda 1 e partida direta. Ponha N nas cargas que não são essenciais.
3. Clique de novo. O formulário pede tensão, regime (emergência ou prime), fator de diversidade e comprimento do cabo até o quadro de transferência; o resto fica nas opções avançadas.

O gerador escolhido é o primeiro da lista comercial que atende os três critérios, e o relatório mostra qual decidiu:

| Critério | Conta |
|---|---|
| Demanda em kVA | soma das demandas ÷ diversidade, com as cargas não lineares (nobreak, eletrônica, inversores) valendo 1,5 vez, dividida pelo carregamento máximo (80 % em emergência, 70 % em prime) |
| Demanda em kW | o gerador é de FP 0,8: kW da demanda ÷ (0,8 × carregamento) |
| Partida do maior motor | afundamento de tensão ΔV = x″d·Sp/(Sg + x″d·Sp) até o admissível (20 %); Sp = kVA do motor × 6 (direta), 2 (estrela-triângulo), 2,6 (compensadora), 3 (soft-starter) ou 1 (inversor) |

A altitude acima de 1000 m e a temperatura da sala acima de 40 °C reduzem a potência disponível. Com o gerador, o cálculo dá a corrente nominal, o disjuntor, os cabos de cobre por fase (cabos em paralelo acima de 300 mm²; capacidade da NBR 5410 com temperatura e agrupamento, e queda até a transferência), neutro igual à fase, PE pela tabela 58, o curto estimado nos terminais e o tanque para a autonomia escolhida. **Gravar e gerar diagrama** escreve o resumo nas colunas K e L e desenha o diagrama da transferência rede/gerador (veja *Unifilar e componentes*). Para mostrar o gerador e o QTA na planta, use **Quadros ▾ > Grupo gerador** e **Quadro transferência**.

Os formulários mostram poucas perguntas, com listas de opções prontas; o resto fica em **Opções avançadas**. O resultado é recalculado a cada mudança, e os valores usados voltam na próxima vez. Pressurização e bomba podem inserir o ponto de força do motor na planta, para entrar nos circuitos.

## Biblioteca

**Biblioteca ▾ > Equipamento** (ou **Componente**) abre a biblioteca:

- À esquerda, as categorias (Tomadas, Interruptores, Iluminação, Quadros e proteção, Caixas, Equipamentos, Outros), com quantos itens cada uma tem. Em cima, a busca (por palavras, no nome e na descrição).
- No meio, os componentes com miniatura e nome legível ("Tomada alta 1 módulo 110 V"). Dois cliques inserem.
- À direita, a prévia maior, os detalhes e o modo: **Link** (acompanha a biblioteca; o projeto precisa estar salvo, senão a bancada oferece cópia) ou **Cópia** (independente).
- **Exemplos da bancada**, desenhados sem arquivo, com medidas típicas e potência: quadros de embutir e de sobrepor, caixas 4×2, 4×4 e octogonal, plafon, luminária tubular, arandela, ar-condicionado split, chuveiro, motor de 3 cv, motobomba, gerador diesel e transformador.

Cada componente inserido vira uma **pasta própria dentro de *<pavimento> > Equipamentos***, no piso do pavimento ativo (ou do selecionado na árvore). Depois clique na planta para posicioná-lo (R gira 90°). Os exemplos ficam na altura de montagem deles, a partir do piso.

## Barras de ferramentas

Os botões com seta (▾) abrem uma lista; o botão mostra o último item usado.

| Barra | Botões |
|---|---|
| Planta elétrica | Projeto ▾, Tomadas ▾, Energia ▾, Iluminação ▾, Comandos ▾, Circuitos ▾, Infraestrutura ▾, Aterramento ▾ |
| Quadros e documentos | Quadros ▾, Dados do quadro ▾, Montar circuitos, Componentes, Diagramas ▾ (Unifilar e Multifilar), Cálculos ▾, Documentos ▾, Folhas ▾ |
| Modelo e biblioteca | Modelo 3D ▾, Biblioteca ▾ |

As barras *Desenho*, *Modificador*, *Snap* e *Arquitetura* trazem as ferramentas do FreeCAD mais usadas em planta. O primeiro botão de *Desenho* é o **plano de trabalho** (`Draft_SelectPlane`): mostra o plano atual e troca para planta (topo), frente, lateral, a vista atual ou a face selecionada, para desenhar em elevação ou corte. Todos os comandos estão nos menus **Elétrica** e **Desenho 2D**. O texto embaixo dos ícones pode ser desligado pela preferência `LegendaBotoes` em `BaseApp/Preferences/Mod/Circuits`.

## Limitações

- **Dimensionamento:** o método de instalação é sempre B1 (eletroduto), porque as bandejas ainda não entram na rede dos circuitos. A capacidade de interrupção dos disjuntores não é verificada, e o curto-circuito só quando o tempo de atuação é informado (disjuntores limitadores: confira o I²t no catálogo). Tabelas transcritas da NBR 5410:2004, a conferir com a norma.
- **Folhas de desenho:** conferidas no FreeCAD 1.0.2 (folha exportada em PDF); falta conferir no 1.1. O detalhe é retangular e sai recortado no PDF, mas não no SVG exportado. As plantas e os diagramas na folha não se atualizam sozinhos: use **Atualizar folhas**.
- **Ocupação dos eletrodutos:** diâmetros internos dos eletrodutos e externos dos cabos (450/750 V, unipolares) aproximados, de catálogos de mercado; a rota é o caminho mais curto do quadro, não necessariamente o que você quer: confira com **Rota do circuito**.
- **Fios e verticais:** dependem de a rede de eletrodutos estar conectada às caixas. Os fios não são roteados pelas prumadas entre pavimentos (cada pavimento é calculado à parte).
- **Demanda:** fatores de guias residenciais, não conferidos com a fonte; cada concessionária tem a sua tabela, e a demanda do edifício inteiro não é calculada.
- **Aterramento:** resistividades de solo típicas e fórmulas para hastes em linha; meça o solo e confira o valor máximo com a NBR 5410 e a NBR 5419.
- **Gerador diesel:** pré-dimensionamento com valores típicos (x″d, redução por altitude e temperatura, consumo, fator das cargas não lineares, potências comerciais): confirme com o catálogo do fabricante. Não calcula a sequência de partida de vários motores, o paralelismo de geradores nem a transferência (QTA); a capacidade dos cabos acima de 120 mm² é da NBR 5410, a conferir.
- **Pressurização, recalque e luminotécnico:** pré-dimensionamentos com parâmetros genéricos, a conferir com as normas, o Corpo de Bombeiros, o projeto hidráulico e os catálogos. No luminotécnico, o fator de utilização vem de uma curva genérica (luminária direta, teto e paredes claros); com o do catálogo da luminária o resultado é o certo.
- **Padrões:** pontos em 127 V (220 V para chuveiro, ar-condicionado e ponto de força); DR marcado em todos os circuitos de tomadas e de uso específico.
- **Símbolos:** convenção da bancada, não cópia de uma norma.
- **Bandejas e leitos:** curvas verticais sempre de 90° e a altura de cada linha é única (para subir, divida em duas linhas); a redução tem sempre 30 cm e é concêntrica, e o tê é um quadrado na largura da principal, não o desenho do catálogo; o raio da curva é a largura da bandeja. Vão dos suportes, parafusos e materiais por regras usuais de catálogo, não de um fabricante.

A lista completa está em "Problemas conhecidos" do [AGENTS.md](AGENTS.md), e o plano das próximas etapas em [docs/Plano_proximas_etapas.md](docs/Plano_proximas_etapas.md).

## Desenvolvimento

```
Circuits/
├── AGENTS.md              arquitetura, regras e problemas conhecidos
├── docs/                  roadmap e guias
├── tests/unit/            testes sem FreeCAD
├── tests/gui/             regressão com o FreeCAD real
├── tools/                 gerador dos ícones dos símbolos
└── freecad/Circuits/
    ├── init_gui.py        bancada, barras e menus
    ├── commands/          comandos (botões)
    ├── UI/                diálogos
    ├── services/          operações no documento
    ├── objects/           objetos paramétricos
    ├── core/              regras, cálculos e tabelas, sem FreeCAD
    ├── Componentes/       biblioteca de modelos .FCStd
    └── Resources/         ícones e dados
```

Testes unitários, a partir da raiz do repositório:

```bash
python -B -m unittest discover -s tests/unit -t .
```

O [AGENTS.md](AGENTS.md) explica as camadas, como criar um comando, um símbolo ou um cálculo novo, e como rodar a regressão no FreeCAD real.

Os modelos da biblioteca ficam em `freecad/Circuits/Componentes/Eletrica/`. Não renomeie essa pasta: os projetos guardam links para os arquivos dela.

## Licença e autor

MIT, conforme `package.xml`; o arquivo `LICENSE` ainda não foi adicionado ao repositório.

Autor: Lucas Losinskas.
