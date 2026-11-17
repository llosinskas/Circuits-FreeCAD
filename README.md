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

1. **Projeto > Novo projeto** cria a estrutura do documento e o pavimento *Térreo* (ou ativa o primeiro nível do BIM, se o projeto já tiver níveis).
2. **Projeto > Pavimento** ou **Nível do BIM** escolhe ou cria o pavimento em que você vai desenhar.
3. **Tomadas, Energia, Iluminação e Interruptores**: insira os pontos na planta. Cada símbolo vai sozinho para a pasta do tipo dele no pavimento ativo.
4. **Iluminação > Luminotécnico**: com um retângulo do ambiente selecionado, calcula e distribui as luminárias.
5. **Circuitos > Definir circuito** e **Ligar interruptor**: agrupe os pontos em circuitos e ligue cada interruptor às suas luminárias.
6. **Quadros**: coloque na planta o quadro de distribuição, o de comando e a medição. Com o quadro selecionado, **Dados do quadro > Planilha do quadro** cria os dados dele e a planilha de circuitos.
7. **Montar circuitos**: soma os pontos de cada circuito, escolhe cabo e disjuntor e grava na planilha de circuitos do quadro.
8. **Eletrodutos > Eletroduto** e **Conectar às caixas**: desenhe a rede de eletrodutos e prenda-a nas caixas.
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
| Eletrodutos | Caixa de passagem (além das ferramentas de eletroduto) |
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
| **R** | Gira 90° |
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

**Montar circuitos** preenche essa planilha a partir da planta, mas ela também pode ser preenchida à mão. O Unifilar e os Componentes calculam o que ficar em branco e respeitam o que foi digitado.

### Unifilar e componentes

- **Unifilar:** um diagrama por quadro, com medidor (quando a origem do quadro é uma medição), disjuntor geral, DPS, barramentos de fases, neutro e terra, e, em cada circuito, disjuntor, DR, fases, cabo e potência.
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
| Planta elétrica | Projeto ▾, Tomadas ▾, Energia ▾, Iluminação ▾, Comandos ▾, Circuitos ▾, Eletrodutos ▾, Aterramento ▾ |
| Quadros e documentos | Quadros ▾, Dados do quadro ▾, Montar circuitos, Componentes, Unifilar, Cálculos ▾, Documentos ▾ |
| Modelo e biblioteca | Modelo 3D ▾, Biblioteca ▾ |

As barras *Desenho*, *Modificador*, *Snap* e *Arquitetura* trazem as ferramentas do FreeCAD mais usadas em planta. Todos os comandos estão nos menus **Elétrica** e **Desenho 2D**. O texto embaixo dos ícones pode ser desligado pela preferência `LegendaBotoes` em `BaseApp/Preferences/Mod/Circuits`.

## Limitações

- **Dimensionamento simplificado:** cabo e disjuntor só pela capacidade de condução (cobre, PVC, eletroduto embutido) e pela coordenação com o disjuntor. Queda de tensão, agrupamento, temperatura e curto-circuito não são verificados.
- **Fios e verticais:** dependem de a rede de eletrodutos estar conectada às caixas. Prumadas entre pavimentos ainda não entram.
- **Demanda:** fatores de guias residenciais, não conferidos com a fonte; cada concessionária tem a sua tabela, e a demanda do edifício inteiro não é calculada.
- **Aterramento:** resistividades de solo típicas e fórmulas para hastes em linha; meça o solo e confira o valor máximo com a NBR 5410 e a NBR 5419.
- **Pressurização, recalque e luminotécnico:** pré-dimensionamentos com parâmetros genéricos, a conferir com as normas, o Corpo de Bombeiros, o projeto hidráulico e os catálogos.
- **Padrões:** pontos em 127 V (220 V para chuveiro, ar-condicionado e ponto de força); DR marcado em todos os circuitos de tomadas e de uso específico.
- **Símbolos:** convenção da bancada, não cópia de uma norma.
- **Eletrocalhas:** ainda não implementadas.

A lista completa está em "Problemas conhecidos" do [AGENTS.md](AGENTS.md), e o plano de evolução em [docs/Revisao_e_Roadmap_Predial.md](docs/Revisao_e_Roadmap_Predial.md).

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
