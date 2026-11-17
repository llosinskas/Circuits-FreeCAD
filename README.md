# Circuits: bancada de projeto elétrico predial para o FreeCAD

Bancada **Engenharia** para o FreeCAD 1.1: do desenho dos pontos na planta até o quadro de cargas, o diagrama unifilar e a lista de materiais, sem sair do FreeCAD.

- Planta elétrica com símbolos de tomadas, iluminação, interruptores, pontos de energia e quadros, organizados por pavimento.
- Circuitos montados a partir dos pontos, com cabo, disjuntor, DR e equilíbrio de fases.
- Planilha de circuitos por quadro, diagrama unifilar e lista de componentes do quadro.
- Rede de eletrodutos ligada às caixas, com contagem de fios e lista de verticais.
- Quantitativo de materiais em CSV, XLSX e PDF.
- Cálculos prediais: demanda, luminotécnico, pressurização de escada e bomba de recalque.
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

O relatório e o quantitativo em PDF usam a biblioteca `reportlab`, que já vem no Python do FreeCAD. O XLSX e o CSV não dependem de nada.

## Um projeto do começo ao fim

1. **Projeto > Novo projeto** cria a estrutura do documento, a planilha *Parâmetros do projeto* e o pavimento *Térreo* (ou ativa o primeiro nível do BIM, se o projeto já tiver níveis). Confira os parâmetros em **Projeto > Parâmetros**: tensões, esquema de aterramento, isolação, temperatura e limites de queda.
2. **Projeto > Pavimento** ou **Nível do BIM** escolhe ou cria o pavimento em que você vai desenhar.
3. **Tomadas, Energia, Iluminação e Interruptores**: insira os pontos na planta. Cada símbolo vai sozinho para a pasta do tipo dele no pavimento ativo.
4. **Iluminação > Luminotécnico**: com um retângulo do ambiente selecionado, calcula e distribui as luminárias.
5. **Circuitos > Definir circuito** e **Ligar interruptor**: agrupe os pontos em circuitos e ligue cada interruptor às suas luminárias.
6. **Quadros**: coloque na planta o quadro de distribuição, o de comando e a medição. Com o quadro selecionado, **Dados do quadro > Planilha do quadro** cria os dados dele e a planilha de circuitos.
7. **Montar circuitos**: soma os pontos de cada circuito, dimensiona cabo e disjuntor pela NBR 5410 e grava na planilha de circuitos do quadro. Desenhe e conecte os eletrodutos antes (passo 8) para a queda de tensão e o agrupamento entrarem no cálculo.
8. **Infraestrutura > Eletroduto** e **Conectar às caixas**: desenhe a rede de eletrodutos e prenda-a nas caixas. Em áreas técnicas e prumadas, **Bandeja/leito** e **Suportes**.
9. **Componentes** e **Unifilar**: lista o que vai dentro de cada quadro e desenha o diagrama.
10. **Cálculos > Demanda**: grava a demanda do quadro, que aparece no unifilar.
11. **Documentos**: quantitativos, legenda, notas e relatório PDF.

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
| Quadros | Quadro de distribuição (QD), de comando (QC), de medição (QM), medição agrupada (CM) |

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
| Queda de tensão | Até o ponto mais distante, com as descidas, limitada pelo valor dos parâmetros (4 %) |
| Curto-circuito | S ≥ I·√t / k, só quando o tempo de atuação é preenchido nos parâmetros |
| Contatos indiretos | No esquema TN, o comprimento máximo para o disjuntor seccionar; acima dele, aviso para usar DR. No TT, DR em todos os circuitos |

O comprimento e o agrupamento vêm da rede de eletrodutos e só entram quando ela chega ao símbolo do quadro ligado à planilha. Sem rede, valem a seção mínima e a capacidade de condução.

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
- **Componentes:** disjuntor geral, DPS, disjuntores e DR dos circuitos, barramentos com o número de terminais e o tamanho da caixa em módulos DIN, com a reserva de circuitos da NBR 5410. A lista fica numa planilha `Componentes <quadro>`.

## Eletrodutos, fios e verticais

1. Desenhe os eletrodutos com **Eletrodutos > Eletroduto**. O snap do Draft pode prender no ponto de inserção de cada símbolo (a caixa).
2. Selecione as linhas e clique em **Conectar às caixas**. Elas viram eletrodutos (diâmetro e altura nas propriedades), vão para a pasta *Eletrodutos* do pavimento, e todo vértice ou trecho a até 30 cm de uma caixa é puxado para cima dela.
3. **Lista de verticais** cria a planilha *Verticais*, com a descida ou subida de cada caixa: altura do eletroduto, altura da caixa, comprimento e diâmetro.

Os fios são contados pelo caminho mais curto na rede, do quadro até os pontos de cada circuito:

- fase até pontos e interruptores; neutro e terra até os pontos;
- retorno do interruptor até as luminárias da mesma letra, e dois condutores a mais entre interruptores paralelos e intermediários;
- seção e fases pela planilha de circuitos do quadro;
- verticais e 30 cm de folga em cada caixa.

O botão **Fiação** desenha na planta os traços de fase, neutro e terra ao lado de cada ponto.

### Subidas, descidas e detalhes das verticais

- **Infraestrutura > Subidas e descidas** desenha na planta o símbolo de cada vertical, com o texto ao lado (`Ø3/4" desce 2,50 m`, `EL 200x50 sobe 0,50 m`):
  - eletroduto: círculo com seta; a seta aponta para o círculo quando desce, para fora quando sobe, e para os dois lados onde um eletroduto do teto encontra um do piso;
  - eletrocalha e leito: a seção da bandeja com a diagonal e a seta.
  
  Entram as descidas até as caixas, os encontros de eletrodutos em alturas diferentes e os trechos verticais das bandejas. Para não desenhar o símbolo em toda caixa, mude *Símbolo de descida em cada caixa* para `N` em **Projeto > Parâmetros**.
- **Infraestrutura > Detalhar verticais** desenha ao lado da planta um detalhe em elevação por tipo de vertical (V1, V2...): piso, laje, cotas de altura, trecho horizontal, caixa ou curvas verticais (CVE e CVI), a quantidade e onde ficam. Verticais iguais (mesmo diâmetro ou seção, sentido e alturas) dividem o mesmo detalhe.

O encontro de dois eletrodutos em alturas diferentes entra nos quantitativos como eletroduto vertical.

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
- **Relatório PDF:** quadros, demandas, materiais e imagens dos diagramas.

## Aterramento

O botão **Aterramento** da barra *Planta elétrica* reúne:

- **Haste de aterramento**, **Caixa de inspeção** e **BEP** (barramento de equipotencialização principal): símbolos na planta, guardados na pasta *Aterramento* do pavimento. A haste fica abaixo do piso no modelo 3D.
- **Condutor de aterramento:** desenhe o caminho do cabo com uma linha, selecione-a e escolha a seção (16 a 70 mm²). A linha fica verde, vai para a pasta *Aterramento* e o comprimento entra nos quantitativos como cabo de cobre nu.
- **Resistência de terra:** calcula a resistência de uma haste e de várias hastes em linha (fórmulas da IEEE 142) e o menor número de hastes que atinge a resistência desejada. Escolha o tipo de solo ou informe a resistividade medida.

## Cálculos prediais

| Cálculo | O que faz |
|---|---|
| Demanda | Aplica fatores de demanda residenciais aos circuitos e grava no quadro |
| Luminotécnico | Método dos lúmens: quantidade, malha e iluminância; distribui as luminárias no retângulo selecionado |
| Pressurização | Vazão de ar da escada (portas fechadas e abertas), ventilador e motor |
| Bomba de recalque | Vazão, tubo, altura manométrica e motor |
| Resistência de terra | Resistência das hastes em linha e número de hastes (no botão Aterramento) |

Os formulários mostram poucas perguntas, com listas de opções prontas; o resto fica em **Opções avançadas**. O resultado é recalculado a cada mudança, e os valores usados voltam na próxima vez. Pressurização e bomba podem inserir o ponto de força do motor na planta, para entrar nos circuitos.

## Barras de ferramentas

Os botões com seta (▾) abrem uma lista; o botão mostra o último item usado.

| Barra | Botões |
|---|---|
| Planta elétrica | Projeto ▾, Tomadas ▾, Energia ▾, Iluminação ▾, Comandos ▾, Circuitos ▾, Infraestrutura ▾, Aterramento ▾ |
| Quadros e documentos | Quadros ▾, Dados do quadro ▾, Montar circuitos, Componentes, Unifilar, Cálculos ▾, Documentos ▾ |
| Modelo e biblioteca | Modelo 3D ▾, Biblioteca ▾ |

As barras *Desenho*, *Modificador*, *Snap* e *Arquitetura* trazem as ferramentas do FreeCAD mais usadas em planta. Todos os comandos estão nos menus **Elétrica** e **Desenho 2D**. O texto embaixo dos ícones pode ser desligado pela preferência `LegendaBotoes` em `BaseApp/Preferences/Mod/Circuits`.

## Limitações

- **Dimensionamento:** o método de instalação é sempre B1 (eletroduto), porque as bandejas ainda não entram na rede dos circuitos. A capacidade de interrupção dos disjuntores não é verificada, e o curto-circuito só quando o tempo de atuação é informado (disjuntores limitadores: confira o I²t no catálogo). Tabelas transcritas da NBR 5410:2004, a conferir com a norma.
- **Fios e verticais:** dependem de a rede de eletrodutos estar conectada às caixas. Prumadas entre pavimentos ainda não entram.
- **Demanda:** fatores de guias residenciais, não conferidos com a fonte; cada concessionária tem a sua tabela, e a demanda do edifício inteiro não é calculada.
- **Aterramento:** resistividades de solo típicas e fórmulas para hastes em linha; meça o solo e confira o valor máximo com a NBR 5410 e a NBR 5419.
- **Pressurização, recalque e luminotécnico:** pré-dimensionamentos com parâmetros genéricos, a conferir com as normas, o Corpo de Bombeiros, o projeto hidráulico e os catálogos.
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
