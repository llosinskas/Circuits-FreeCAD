# Bancada Engenharia (Circuits) para FreeCAD

Bancada para projetos elétricos prediais no FreeCAD: desenho dos pontos em planta, montagem dos circuitos, quadro de cargas e diagrama unifilar, com geração 3D e relatório em PDF.

O projeto está em desenvolvimento. A seção [Limitações](#limitações) diz o que ainda não deve ser usado em um projeto real sem conferência.

## O que a bancada faz

- **Planta 2D:** botões separados para tomadas, pontos de energia, iluminação e interruptores. Cada ponto tem símbolo próprio e dados elétricos (potência, tensão, circuito) editáveis.
- **Circuitos:** soma os pontos da planta por circuito, escolhe cabo e disjuntor, equilibra as fases e grava no quadro.
- **Diagrama unifilar:** gerado a partir da planilha de cada quadro, com disjuntor, fases, cabo, potência, DR e DPS.
- **Cálculos prediais:** demanda do quadro, pré-dimensionamento do ventilador de pressurização de escada e da bomba de recalque, com o motor elétrico de cada um.
- **Legenda:** desenha ao lado da planta a legenda dos símbolos usados.
- **Infraestrutura:** caminho de eletrodutos em planta e simbologia de fiação.
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
2. **Insira os pontos** pelos botões *Tomadas*, *Energia*, *Iluminação* e *Interruptores*. Depois do clique, o próximo ponto do mesmo tipo já vem no cursor. A tecla **R** gira 90° e **ESC** encerra.
3. **Defina o circuito** de cada ponto na propriedade `Circuito`. Pontos de uso específico, como o chuveiro, precisam de circuito exclusivo.
4. **Novo quadro** (barra *Quadros e documentos*): informe tensão, fases, disjuntor geral e DPS.
5. **Montar circuitos:** grava no quadro uma linha por circuito, com potência, corrente, cabo, disjuntor e fases. Use **Circuito** para acrescentar ou corrigir uma linha à mão.
6. **Unifilar:** gera o diagrama de cada quadro.
7. **Demanda** (botão *Cálculos*): calcula a demanda do quadro e grava na planilha; gere o unifilar de novo para mostrá-la.
8. **Legenda** e **Relatório PDF** (botão *Documentos*).

**Pressurização** e **Bomba de recalque** abrem um formulário, mostram o cálculo e, com o botão *Inserir motor na planta*, criam o ponto de força do motor para entrar nos circuitos.

Ao repetir **Montar circuitos**, as linhas com o mesmo número são atualizadas e as demais ficam como estão.

## Barras de ferramentas

As barras da bancada têm poucos botões. Os que têm uma seta (▾) abrem uma lista: o botão mostra o último item usado, e a seta mostra os outros.

| Barra | Botões |
|---|---|
| Planta elétrica | Projeto ▾, Tomadas ▾, Energia ▾, Iluminação ▾, Interruptores ▾, Eletrodutos ▾ |
| Quadros e documentos | Novo quadro, Montar circuitos, Circuito, Unifilar, Cálculos ▾, Documentos ▾ |
| Modelo e biblioteca | Modelo 3D ▾, Biblioteca ▾ |

| Botão com lista | Itens |
|---|---|
| Projeto | Novo projeto, Planilha de circuitos, Importar QET |
| Tomadas | Tomada baixa, média, alta, de piso, Tomada TUG |
| Energia | Chuveiro, Ar-condicionado, Ventilador, Ponto de força |
| Iluminação | Luz de teto, Arandela, Luminária tubular, Luz embutida, Luz de emergência |
| Interruptores | Simples, paralelo, intermediário |
| Eletrodutos | Eletroduto, Dividir trecho, Fiação |
| Cálculos | Demanda, Pressurização, Bomba de recalque |
| Documentos | Legenda, Relatório PDF |
| Modelo 3D | Caixas 3D, Eletrodutos 3D, Tomadas 3D |
| Biblioteca | Equipamento, Componente, Criar modelo, Importar modelo |

As barras *Desenho*, *Modificador*, *Snap* e *Arquitetura* trazem só as ferramentas do FreeCAD mais usadas em planta. Tudo continua nos menus: **Elétrica** tem todos os comandos da bancada (os antigos e o *Reiniciar Bancada* em *Outros*), e **Desenho 2D** tem todas as ferramentas nativas.

O texto embaixo de cada ícone pode ser desligado pela preferência `LegendaBotoes` em `BaseApp/Preferences/Mod/Circuits` (Ferramentas > Editar parâmetros).

## Limitações

- **Dimensionamento simplificado.** *Montar circuitos* verifica só a capacidade de condução (cabo de cobre com PVC, em eletroduto embutido) e a coordenação com o disjuntor. Não calcula queda de tensão, agrupamento, temperatura nem curto-circuito. Confira o resultado antes de usar.
- **Demanda:** usa fatores de guias de instalações residenciais, não conferidos com a fonte. Cada concessionária tem tabela própria, e a demanda do edifício inteiro (vários apartamentos) não é calculada.
- **Pressurização de escada e bomba de recalque:** são pré-dimensionamentos para estimar a carga elétrica. Os parâmetros precisam ser conferidos com a NBR 14880, o Corpo de Bombeiros e o projeto hidráulico. O disjuntor do motor não considera a corrente de partida.
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
