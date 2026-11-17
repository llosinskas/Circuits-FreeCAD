# Bancada Engenharia (Circuits) para FreeCAD

Bancada para projetos elétricos prediais no FreeCAD: desenho dos pontos em planta, montagem dos circuitos, quadro de cargas e diagrama unifilar, com geração 3D e relatório em PDF.

O projeto está em desenvolvimento. A seção [Limitações](#limitações) diz o que ainda não deve ser usado em um projeto real sem conferência.

## O que a bancada faz

- **Planta 2D:** botões separados para tomadas, pontos de energia, iluminação e interruptores. Cada ponto tem símbolo próprio e dados elétricos (potência, tensão, circuito) editáveis.
- **Quadros na planta:** símbolos de quadro de distribuição, quadro de comando, quadro de medição e medição agrupada.
- **Circuitos:** soma os pontos da planta por circuito, escolhe cabo e disjuntor, equilibra as fases e grava no quadro.
- **Diagrama unifilar:** gerado a partir da planilha de cada quadro, com medidor, disjuntor geral, DPS, barramentos de fases, neutro e terra, e disjuntor, DR, fases, cabo e potência de cada circuito.
- **Componentes do quadro:** lista de disjuntores, DR, DPS, barramentos e tamanho da caixa em módulos.
- **Cálculos prediais:** demanda do quadro, pré-dimensionamento do ventilador de pressurização de escada e da bomba de recalque, com o motor elétrico de cada um.
- **Luminotécnico:** calcula e distribui as luminárias dentro de um retângulo desenhado no ambiente.
- **Legenda:** desenha ao lado da planta a legenda dos símbolos usados.
- **Notas:** você escreve as notas do projeto numa planilha e um botão as desenha na planta.
- **Fiação:** um botão desenha os traços de fase, neutro e terra em todas as tomadas e pontos.
- **Escala dos símbolos:** cada símbolo tem uma escala, e um comando muda a de todos de uma vez.
- **Infraestrutura:** caminho de eletrodutos em planta.
- **Modelo 3D:** caixas dos pontos e tubos dos eletrodutos gerados a partir da planta.
- **Biblioteca:** componentes `.FCStd` inseridos como link, com busca e miniatura.
- **Relatório PDF** e importação de condutores do **QElectroTech**.

## Instalação

Requer FreeCAD 1.1 ou mais novo (Python 3.10+).

Clone o repositório dentro da pasta `Mod` do FreeCAD, com o nome `Circuits`. No Windows, pelo Git Bash:

```bash
cd "$APPDATA/FreeCAD/v1-1/Mod"
```

```bash
git clone -b master https://github.com/llosinskas/Circuits-FreeCAD.git Circuits
```

No Linux, a pasta é `~/.local/share/FreeCAD/v1-1/Mod`. Reinicie o FreeCAD e escolha a bancada **Engenharia**.

Para atualizar uma instalação existente:

```bash
cd "$APPDATA/FreeCAD/v1-1/Mod/Circuits"
```

```bash
git pull origin master
```

Depois use **Elétrica > Outros > Reiniciar Bancada** ou reabra o FreeCAD. Mantenha uma única cópia da bancada em `Mod`: duas cópias registram os mesmos comandos e uma substitui a outra.

## Passo a passo de um projeto

1. **Novo projeto** (botão *Projeto*): cria os grupos do documento.
2. **Insira os pontos** pelos botões *Tomadas*, *Energia*, *Iluminação* e *Interruptores*. Depois do clique, o próximo ponto do mesmo tipo já vem no cursor. Veja as teclas em [Inserir e alinhar símbolos](#inserir-e-alinhar-símbolos).
3. **Defina os circuitos** (botão *Circuitos*): selecione os pontos de um circuito e use **Definir circuito**. Pontos de uso específico, como o chuveiro, precisam de circuito exclusivo. Veja [Circuitos e interruptores](#circuitos-e-interruptores).
4. **Quadros** (barra *Quadros e documentos*): posicione na planta o quadro de distribuição, o de comando e a medição. Depois, com o símbolo do quadro selecionado, use **Dados do quadro > Planilha do quadro** e informe tensão, fases, disjuntor geral e DPS.
5. **Montar circuitos:** grava no quadro uma linha por circuito, com potência, corrente, cabo, disjuntor e fases. Use **Dados do quadro > Circuito** para acrescentar ou corrigir uma linha à mão.
6. **Componentes:** lista o que vai dentro do quadro.
7. **Unifilar:** gera o diagrama de cada quadro.
8. **Demanda** (botão *Cálculos*): calcula a demanda do quadro e grava na planilha; gere o unifilar de novo para mostrá-la.
9. **Legenda** e **Relatório PDF** (botão *Documentos*).

**Pressurização** e **Bomba de recalque** abrem um formulário (veja [Formulários de cálculo](#formulários-de-cálculo)), mostram o cálculo e, com o botão *Inserir motor na planta*, criam o ponto de força do motor para entrar nos circuitos.

Ao repetir **Montar circuitos**, as linhas com o mesmo número são atualizadas e as demais ficam como estão.

## Inserir e alinhar símbolos

Enquanto um símbolo acompanha o cursor:

| Tecla | Efeito |
|---|---|
| Clique | Fixa o símbolo e já traz o próximo do mesmo tipo |
| **Espaço** | Alinha com o símbolo mais próximo: primeiro em um eixo, de novo no outro, de novo solta |
| **R** | Gira 90° |
| **L** | Liga ou desliga o alinhamento automático |
| **ESC** | Encerra |

O alinhamento automático puxa o símbolo para a mesma vertical ou horizontal de um vizinho quando ele chega perto. A trava do Espaço vale para os próximos símbolos da sequência, o que facilita fazer uma fileira.

Para símbolos já colocados, selecione-os com Ctrl + clique e use **Alinhar** (coloca em linha com o primeiro selecionado) ou **Distribuir** (iguala o espaço entre eles), no fim da barra *Modificador* ou em **Elétrica > Alinhar símbolos**.

## Quadros e medição na planta

O botão **Quadros** insere quatro símbolos, do mesmo jeito que os outros pontos:

| Símbolo | Sigla inicial | Uso |
|---|---|---|
| Quadro distribuição | QD | Distribuição e proteção dos circuitos |
| Quadro de comando | QC | Comando e proteção de motores: bombas, pressurização, portões |
| Quadro de medição | QM | Caixa de medição individual |
| Medição agrupada | CM | Centro de medição com vários medidores |

Edite a sigla na propriedade `Descricao` (por exemplo QD1, QD2) e, na medição, a quantidade em `Medidores`. **Identificar pontos** escreve a sigla ao lado do símbolo, e **Caixas 3D** gera o volume de cada quadro. Os quadros não entram na soma de carga dos circuitos.

**Ligação com a planilha:** selecione o símbolo do quadro antes de abrir **Planilha do quadro**. A identificação já vem preenchida com a sigla, e o símbolo passa a guardar o nome da planilha.

**Medição no unifilar:** escreva no campo *Origem* do quadro a sigla da medição (QM ou CM, a mesma do símbolo). O unifilar desenha então o medidor na entrada.

### Componentes do quadro

O botão **Componentes** lê a planilha do quadro e monta a lista do que vai dentro dele:

- disjuntor geral (polos, corrente, curva e capacidade de interrupção);
- DPS, um por fase mais um para o neutro;
- disjuntores dos circuitos, agrupados por polos e corrente;
- interruptores DR dos circuitos que têm DR, bipolares ou tetrapolares;
- barramentos de fases, de neutro e de terra, com o número de terminais;
- caixa do quadro em módulos DIN, com a reserva de circuitos da NBR 5410.

A lista aparece na tela e fica gravada na planilha `Componentes <quadro>`. Os valores comerciais são gerais, não de um fabricante.

## Circuitos e interruptores

O botão **Circuitos** da barra *Planta elétrica* reúne três comandos:

- **Definir circuito:** selecione os pontos (Ctrl + clique) e escolha o número do circuito, existente ou novo, e opcionalmente o quadro. O comando já sugere o próximo número livre.
- **Ligar interruptor:** selecione um interruptor e os pontos de luz (ou ventilador) que ele comanda. Todos recebem a mesma letra de comando (a, b, c...) e o interruptor recebe o circuito da luz. Para interruptores paralelos, selecione os dois junto com as luzes.
- **Identificar pontos:** escreve ao lado de cada símbolo o circuito, a letra do comando e a potência, por exemplo `C1 · a · 100 VA`. Depois de criada, a identificação se atualiza quando você usa os dois comandos acima. Se mudar uma propriedade à mão, clique em *Identificar pontos* de novo.

## Fiação e escala dos símbolos

**Fiação** (botão *Eletrodutos > Fiação*) desenha, ao lado de cada tomada, ponto de energia e ponto de iluminação, os traços dos condutores: terra, neutro e uma, duas ou três fases, conforme a propriedade `Ligacao` do ponto. Clicar de novo apaga a fiação anterior e redesenha, então use depois de mudar os pontos. Quadros e interruptores não recebem fiação.

**Escala:** cada símbolo tem a propriedade `Escala` (1 = tamanho normal, 2 = dobro). Para mudar vários de uma vez, use **Escala dos símbolos**, no fim da barra *Modificador* ou em **Elétrica > Alinhar e escalar símbolos**:

- com símbolos selecionados, muda só eles;
- sem nada selecionado, muda todos os símbolos da planta, e os próximos que você inserir já nascem na nova escala.

A fiação e a identificação acompanham o tamanho do símbolo; gere-as de novo depois de mudar a escala.

## Luminotécnico

1. Desenhe um retângulo no contorno do ambiente, com a ferramenta de retângulo da barra *Desenho*, e selecione-o.
2. Abra **Iluminação > Luminotécnico** e responda quatro perguntas: tipo de ambiente, lâmpada ou luminária (de uma lista pronta), circuito e pé-direito. O resultado aparece na hora: número de luminárias, malha e iluminância resultante.
3. **Distribuir luminárias** as coloca dentro do retângulo, com o mesmo espaçamento entre elas e metade até as paredes.

Repetir o comando no mesmo retângulo troca as luminárias anteriores pelas novas. Em **Opções avançadas** dá para informar o fluxo luminoso e a potência de uma luminária fora da lista, a iluminância personalizada, a altura do plano de trabalho e o fator de utilização do catálogo.

## Formulários de cálculo

Luminotécnico, Pressurização e Bomba de recalque usam o mesmo tipo de formulário:

- poucas perguntas à vista, com listas de opções prontas;
- **Opções avançadas**, fechadas no início, para quem tem os dados do catálogo ou do projeto;
- uma dica em cada campo, ao parar o mouse sobre ele;
- o resultado é recalculado a cada mudança;
- os valores usados ficam guardados e voltam na próxima vez; **Restaurar padrões** volta aos iniciais.

## Notas do projeto

1. **Documentos > Planilha de notas** abre a planilha `Notas`, criada na primeira vez com três exemplos. Escreva uma nota por linha na coluna A, a partir da linha 3.
2. **Documentos > Notas** desenha na planta o quadro "NOTAS", com as notas numeradas, embaixo da legenda. Notas longas são quebradas em várias linhas.

Depois de editar a planilha, clique em **Notas** de novo para atualizar. O quadro fica onde você o deixou, se tiver movido.

## Barras de ferramentas

As barras da bancada têm poucos botões. Os que têm uma seta (▾) abrem uma lista: o botão mostra o último item usado, e a seta mostra os outros.

| Barra | Botões |
|---|---|
| Planta elétrica | Projeto ▾, Tomadas ▾, Energia ▾, Iluminação ▾, Interruptores ▾, Circuitos ▾, Eletrodutos ▾ |
| Quadros e documentos | Quadros ▾, Dados do quadro ▾, Montar circuitos, Componentes, Unifilar, Cálculos ▾, Documentos ▾ |
| Modelo e biblioteca | Modelo 3D ▾, Biblioteca ▾ |

| Botão com lista | Itens |
|---|---|
| Projeto | Novo projeto, Planilha de circuitos, Importar QET |
| Tomadas | Tomada baixa, média, alta, de piso, Tomada TUG |
| Energia | Chuveiro, Ar-condicionado, Ventilador, Ponto de força |
| Iluminação | Luz de teto, Arandela, Luminária tubular, Luz embutida, Luz de emergência, Luminotécnico |
| Interruptores | Simples, paralelo, intermediário |
| Quadros | Quadro distribuição, Quadro de comando, Quadro de medição, Medição agrupada |
| Dados do quadro | Planilha do quadro, Circuito |
| Circuitos | Definir circuito, Ligar interruptor, Identificar pontos |
| Eletrodutos | Eletroduto, Dividir trecho, Fiação |
| Cálculos | Demanda, Pressurização, Bomba de recalque |
| Documentos | Legenda, Planilha de notas, Notas, Relatório PDF |
| Modelo 3D | Caixas 3D, Eletrodutos 3D, Tomadas 3D |
| Biblioteca | Equipamento, Componente, Criar modelo, Importar modelo |

As barras *Desenho*, *Modificador*, *Snap* e *Arquitetura* trazem só as ferramentas do FreeCAD mais usadas em planta. Tudo continua nos menus: **Elétrica** tem todos os comandos da bancada (os antigos e o *Reiniciar Bancada* em *Outros*), e **Desenho 2D** tem todas as ferramentas nativas.

O texto embaixo de cada ícone pode ser desligado pela preferência `LegendaBotoes` em `BaseApp/Preferences/Mod/Circuits` (Ferramentas > Editar parâmetros).

## Limitações

- **Dimensionamento simplificado.** *Montar circuitos* verifica só a capacidade de condução (cabo de cobre com PVC, em eletroduto embutido) e a coordenação com o disjuntor. Não calcula queda de tensão, agrupamento, temperatura nem curto-circuito. Confira o resultado antes de usar.
- **Demanda:** usa fatores de guias de instalações residenciais, não conferidos com a fonte. Cada concessionária tem tabela própria, e a demanda do edifício inteiro (vários apartamentos) não é calculada.
- **Pressurização de escada e bomba de recalque:** são pré-dimensionamentos para estimar a carga elétrica. Os parâmetros precisam ser conferidos com a NBR 14880, o Corpo de Bombeiros e o projeto hidráulico. O disjuntor do motor não considera a corrente de partida.
- **Luminotécnico:** usa um fator de utilização genérico e iluminâncias usuais por ambiente, não conferidos com a NBR ISO/CIE 8995-1 nem com catálogo. Vale para ambientes retangulares; um retângulo girado é tratado pelo retângulo reto que o contém.
- **DR** é marcado em todos os circuitos de tomadas e de uso específico, mais do que a NBR 5410 exige.
- **Tensão padrão** dos pontos é 127 V (220 V para chuveiro, ar-condicionado e ponto de força). Ajuste em cada ponto se a sua rede for diferente.
- **Símbolos** são convenção da bancada, não cópia de uma norma.
- **Fiação automática e eletrocalhas** ainda não existem: os botões só exibem um aviso.
- **Tabelas e cálculos** de `core/functions` e `core/tables` ainda não são usados pela interface, e alguns têm erros conhecidos.

A lista completa está em "Problemas conhecidos" do [AGENTS.md](AGENTS.md). O plano de evolução está em [docs/Revisao_e_Roadmap_Predial.md](docs/Revisao_e_Roadmap_Predial.md).

## Biblioteca de componentes

Os modelos ficam em `freecad/Circuits/Componentes/Eletrica/`. Para acrescentar um, use o botão **Criar modelo** ou salve um `.FCStd` nessa pasta. Não renomeie a pasta: os projetos guardam links para os arquivos dela.

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
    ├── core/              regras, símbolos e tabelas, sem FreeCAD
    ├── Componentes/       biblioteca .FCStd
    └── Resources/         ícones e dados
```

Testes unitários, a partir da raiz do repositório:

```bash
python -B -m unittest discover -s tests/unit -t .
```

O [AGENTS.md](AGENTS.md) explica as camadas, como criar um comando ou um símbolo novo e como rodar a regressão no FreeCAD real.

## Licença e autor

MIT, conforme `package.xml`; o arquivo `LICENSE` ainda não foi adicionado ao repositório.

Autor: Lucas Losinskas.
