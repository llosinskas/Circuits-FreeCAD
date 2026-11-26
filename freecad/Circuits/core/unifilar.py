"""Geometria de um circuito do diagrama unifilar, sem FreeCAD.

Cada circuito sai do barramento (x = 0) para a direita, numa linha horizontal:

    ──●⌒●──[DR]──┼┤││──────►  C1  Tomadas sala
      disjuntor   condutores

- **Disjuntor:** dois terminais (círculos) e o arco por cima, como o geral do
  quadro. Em cima, a proteção (``C16A``); embaixo, as fases (``R``).
- **DR:** retângulo interrompendo a linha, com ``DR`` dentro e a
  sensibilidade em cima (``30mA``).
- **Condutores:** traços sobre a linha na convenção da planta: terra com
  barra (┬), neutro com bandeira, um traço reto por fase. Em cima, a seção
  (``#2,5``); embaixo, a potência.
- **Seta** na ponta e, depois dela, o número e a descrição do circuito.

**DR por grupo** (coluna ``Grupo_DR``): os circuitos do grupo são desenhados juntos,
na posição do primeiro deles; um ramo sai do barramento, passa pelo DR do grupo e
chega a um sub-barramento vertical, de onde sai cada circuito, sem DR próprio:

    ──[DR]──┬──●⌒●──┼┤││──►  C1
     DR1    └──●⌒●──┼┤││──►  C2

Todas as medidas são múltiplos de ``h`` (a altura do texto do diagrama).
"""
from freecad.Circuits.core import quadro as regras_quadro

# Posições ao longo da linha, em alturas de texto.
X_DISJUNTOR = 1.0  # primeiro terminal
LARGURA_DISJUNTOR = 1.0
RAIO_TERMINAL = 0.08
X_DR = 2.8
LARGURA_DR = 1.3
ALTURA_DR = 0.9
X_CONDUTORES = 5.0
ALTURA_TRACO = 0.6  # altura dos traços dos condutores
PASSO_TRACO = 0.5  # distância entre os traços dos condutores
COMPRIMENTO = 8.5  # até a ponta da seta
TAMANHO_SETA = 0.35
ALTURA_TEXTO = 0.4  # textos do circuito, em alturas de texto do diagrama


def fases_do_circuito(circuito):
    """Fases ligadas ('R', 'RS', 'RST') pelas colunas Fase_R, Fase_S e Fase_T."""
    return "".join(f for f in "RST" if str(circuito.get(f"Fase_{f}", "")).strip().lower() in ("true", "s", "sim", "1"))


def _sim(valor, padrao=False):
    texto = str(valor).strip().lower()
    if not texto:
        return padrao
    return texto in ("true", "s", "sim", "1", "x")


def secao_texto(cabo):
    """'2.5' -> '#2,5 mm²'; vazio -> ''."""
    texto = str(cabo).strip().replace(".", ",")
    return f"#{texto} mm²" if texto else ""


def potencia_texto(potencia):
    """Potência com unidade: '1200' -> '1200 W'; vazio ou zero -> ''."""
    texto = str(potencia).strip()
    try:
        valor = float(texto.replace(",", "."))
    except ValueError:
        return texto
    return f"{valor:g} W" if valor > 0 else ""


def geometria(h, dr=False, fases=1, neutro=True, terra=True):
    """Primitivas do circuito, na origem do barramento.

    Args:
        h: altura do texto do diagrama [mm].
        dr: o circuito tem DR.
        fases: número de fases (1 a 3).
        neutro, terra: o circuito leva esses condutores.
    Returns:
        Dicionário com ``linhas`` [(x1, y1, x2, y2)], ``arcos`` [(cx, cy, raio,
        ângulo inicial, ângulo final) em graus], ``circulos`` [(cx, cy, raio)] e
        ``textos`` {nome: (x, y)}, os pontos de inserção dos textos.
    """
    linhas, arcos, circulos = [], [], []
    a = X_DISJUNTOR * h
    b = (X_DISJUNTOR + LARGURA_DISJUNTOR) * h
    r = RAIO_TERMINAL * h

    # Disjuntor: terminais e arco
    linhas.append((0.0, 0.0, a - r, 0.0))
    circulos += [(a, 0.0, r), (b, 0.0, r)]
    arcos.append(((a + b) / 2, 0.0, (b - a) / 2, 0.0, 180.0))
    x = b + r

    # DR: a linha é interrompida pelo retângulo
    if dr:
        e, d = X_DR * h, (X_DR + LARGURA_DR) * h
        meia = ALTURA_DR * h / 2
        linhas.append((x, 0.0, e, 0.0))
        linhas += [(e, -meia, d, -meia), (e, meia, d, meia), (e, -meia, e, meia), (d, -meia, d, meia)]
        x = d

    fim = COMPRIMENTO * h
    linhas.append((x, 0.0, fim, 0.0))

    # Condutores, um traço a cada PASSO_TRACO: terra (┬), neutro (bandeira) e as fases, como na planta
    base = X_CONDUTORES * h
    t, passo = ALTURA_TRACO * h, PASSO_TRACO * h
    xc = base
    if terra:
        linhas += [(xc, -t / 2, xc, t / 2), (xc - t / 3, t / 2, xc + t / 3, t / 2)]
        xc += passo
    if neutro:
        linhas += [(xc, -t / 2, xc, t / 2), (xc - t / 3, t / 2, xc, t / 2)]
        xc += passo
    for _ in range(max(1, min(3, int(fases)))):
        linhas.append((xc, -t / 2, xc, t / 2))
        xc += passo

    # Seta
    s = TAMANHO_SETA * h
    linhas += [(fim, 0.0, fim - s, s * 0.6), (fim, 0.0, fim - s, -s * 0.6)]

    meio_disjuntor = (a + b) / 2
    textos = {
        "protecao": (a - 0.2 * h, 0.75 * h),
        "fases": (meio_disjuntor - 0.2 * h, -0.8 * h),
        "dr": ((X_DR + 0.3) * h, -0.2 * h),
        "sensibilidade": (X_DR * h, ALTURA_DR * h / 2 + 0.25 * h),
        "secao": (base - 0.2 * h, 0.75 * h),
        "potencia": (base - 0.2 * h, -0.85 * h),
        "numero": (fim + 0.4 * h, 0.15 * h),
        "descricao": (fim + 0.4 * h, -0.6 * h),
    }
    return {"linhas": linhas, "arcos": arcos, "circulos": circulos, "textos": textos}


def textos(circuito):
    """Textos de um circuito lido de ``planilhas.ler_circuitos_completos``.

    Returns:
        {nome do ponto de inserção: texto}, só os não vazios.
    """
    disjuntor = str(circuito.get("Disjuntor", "")).strip()
    curva = str(circuito.get("Curva", "")).strip()
    corrente = str(circuito.get("Corrente", "")).strip()
    protecao = f"{curva}{disjuntor}A" if disjuntor else (f"{corrente}A" if corrente else "")
    dr = _sim(circuito.get("DR", "")) and not regras_quadro.grupo_dr(circuito)
    sensibilidade = regras_quadro.sensibilidade_texto(circuito.get("Corrente_DR", ""))
    resultado = {
        "protecao": protecao,
        "fases": fases_do_circuito(circuito),
        "dr": "DR" if dr else "",
        "sensibilidade": sensibilidade if dr else "",
        "secao": secao_texto(circuito.get("Cabo", "")),
        "potencia": potencia_texto(circuito.get("Potencia", "")),
        "numero": f"C{str(circuito.get('N_circuito', '')).strip()}",
        "descricao": str(circuito.get("Destino", "")).strip(),
    }
    return {chave: texto for chave, texto in resultado.items() if texto and texto != "C"}


X_DR_GRUPO = 1.0  # início do DR do grupo
X_SUB_BARRAMENTO = 3.8  # sub-barramento do grupo, de onde saem os circuitos


def blocos(circuitos):
    """Ordem do desenho: circuitos soltos e grupos de DR.

    O grupo fica na posição do primeiro circuito dele, com todos os circuitos do
    grupo em seguida, na ordem da planilha.

    Returns:
        [('circuito', circuito) ou ('grupo', nome, [circuitos])].
    """
    grupos, resultado = {}, []
    for c in circuitos:
        nome = regras_quadro.grupo_dr(c)
        if not nome:
            resultado.append(("circuito", c))
        elif nome in grupos:
            grupos[nome].append(c)
        else:
            grupos[nome] = [c]
            resultado.append(("grupo", nome, grupos[nome]))
    return resultado


def geometria_grupo_dr(h, passo, quantidade):
    """Ramo do DR do grupo, na origem do barramento (y = 0 é o primeiro circuito).

    Args:
        h: altura do texto [mm].
        passo: distância vertical entre os circuitos [mm].
        quantidade: circuitos do grupo.
    Returns:
        Como ``geometria``, mais ``inicio_circuitos``: x [mm] onde começam os
        circuitos do grupo (no sub-barramento), cada um em y = −i·passo.
    """
    e, d = X_DR_GRUPO * h, (X_DR_GRUPO + LARGURA_DR) * h
    meia = ALTURA_DR * h / 2
    sub = X_SUB_BARRAMENTO * h
    linhas = [(0.0, 0.0, e, 0.0),
              (e, -meia, d, -meia), (e, meia, d, meia), (e, -meia, e, meia), (d, -meia, d, meia),
              (d, 0.0, sub, 0.0)]
    if quantidade > 1:
        linhas.append((sub, 0.0, sub, -(quantidade - 1) * passo))
    textos = {
        "dr": ((X_DR_GRUPO + 0.3) * h, -0.2 * h),
        "nome": (e, -meia - 0.75 * h),
        "especificacao": (e - 0.7 * h, -meia - 1.4 * h),  # embaixo do nome: em cima fica o texto do DPS
    }
    circulos = [(sub, -i * passo, RAIO_TERMINAL * h) for i in range(quantidade)] if quantidade > 1 else []
    return {"linhas": linhas, "arcos": [], "circulos": circulos, "textos": textos, "inicio_circuitos": sub}


def textos_grupo_dr(nome, membros):
    """Textos do DR do grupo: 'DR', a especificação ('2P 40 A, 30mA') e o nome do grupo."""
    dr = regras_quadro.dr_do_grupo(membros)
    return {"dr": "DR", "especificacao": dr["especificacao"], "nome": nome}


def condutores_do_circuito(circuito):
    """(número de fases, neutro, terra) do circuito; sem fase marcada vale 1, e o terra vai sempre."""
    fases = len(fases_do_circuito(circuito)) or 1
    neutro = _sim(circuito.get("Neutro", ""), padrao=fases == 1)
    terra = _sim(circuito.get("Terra", ""), padrao=True)
    return fases, neutro, terra


# --- Gerador e transferência (QTA) -------------------------------------------

MAXIMO_CARGAS_LISTADAS = 8
Y_SAIDA_TRANSFERENCIA = -2.0  # altura da saída do QTA, em alturas de texto
Y_ENTRADA_QUADRO = 2.5  # entrada do diagrama do quadro (linha do disjuntor geral), em alturas de texto


def _senoide(cx, cy, raio):
    meio = raio / 3
    return [(cx - meio, cy, meio, 0.0, 180.0), (cx + meio, cy, meio, 180.0, 360.0)]


def _disjuntor(x, y, h):
    """Terminais e arco de um disjuntor de ``x`` a ``x + h``, como o geral do quadro."""
    r = RAIO_TERMINAL * h
    return ([(x, y, r), (x + h, y, r)], [(x + h / 2, y, h / 2, 0.0, 180.0)])


def transferencia(dados, cargas, h, destino=None, saida_ate=None):
    """Diagrama da entrada com gerador: rede e gerador, cada um com disjuntor, chegando
    ao quadro de transferência (QTA) por contatores intertravados (K1 e K2), e a
    saída para as cargas do gerador.

    Args:
        dados: {rótulo: valor} de ``core.functions.Predial.gerador.resumo``.
        cargas: descrições das cargas ligadas ao gerador.
        h: altura do texto do diagrama [mm].
        destino: quadro geral alimentado pelo QTA; com ele, a saída leva o nome do
            quadro em vez da lista de cargas.
        saida_ate: X [mm, neste sistema] onde a saída termina, na entrada do
            diagrama do quadro geral; a linha vai até lá, sem seta.
    Returns:
        Dicionário com ``linhas``, ``arcos`` e ``circulos`` (como ``geometria``),
        ``textos`` [(x, y, texto, altura)] e ``saida`` (x, y) do fim da saída. A
        entrada da rede fica na origem.
    """
    linhas, arcos, circulos, textos = [], [], [], []
    r = RAIO_TERMINAL * h
    texto = ALTURA_TEXTO * h
    y_rede, y_gerador, x_barra = 0.0, -4 * h, 9 * h
    for y in (y_rede, y_gerador):
        linhas.append((0.0, y, 2 * h - r, y))
        terminais, arco = _disjuntor(2 * h, y, h)
        circulos += terminais
        arcos += arco
        linhas.append((3 * h + r, y, 6 * h, y))
        linhas.append((6 * h, y, 7.1 * h, y + 0.5 * h))  # contato aberto do contator
        linhas.append((7.2 * h, y, x_barra, y))
    # Gerador: círculo com a senoide, ligado à linha do gerador
    raio = 0.9 * h
    circulos.append((-raio, y_gerador, raio))
    arcos += _senoide(-raio, y_gerador, raio)
    # Barra de saída do QTA e intertravamento mecânico (tracejado entre os contatos)
    linhas.append((x_barra, y_rede, x_barra, y_gerador))
    y = y_rede - 0.6 * h
    while y > y_gerador + 0.8 * h:
        linhas.append((6.6 * h, y, 6.6 * h, y - 0.25 * h))
        y -= 0.5 * h
    # Caixa do QTA
    x1, x2, y1, y2 = 5.4 * h, 9.8 * h, 1.3 * h, y_gerador - 0.8 * h
    linhas += [(x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1)]
    # Saída: até a entrada do quadro geral, ou para as cargas, com seta
    y_saida = Y_SAIDA_TRANSFERENCIA * h
    ligada = saida_ate is not None and saida_ate > x_barra + 2 * h
    fim = saida_ate if ligada else 15 * h
    linhas.append((x_barra, y_saida, fim, y_saida))
    if not ligada:
        s = TAMANHO_SETA * h
        linhas += [(fim, y_saida, fim - s, y_saida + 0.6 * s), (fim, y_saida, fim - s, y_saida - 0.6 * s)]

    disjuntor = str(dados.get("Disjuntor [A]", "")).strip()
    tensao = str(dados.get("Tensão [V]", "")).strip()
    kva = str(dados.get("Gerador [kVA]", "")).strip()
    kw = str(dados.get("Gerador [kW]", "")).strip()
    textos.append((-4.2 * h, -0.15 * h, f"Rede{f' {tensao} V' if tensao else ''}", texto))
    if disjuntor:
        textos += [(1.8 * h, y_rede + 0.75 * h, f"{disjuntor}A", texto),
                   (1.8 * h, y_gerador + 0.75 * h, f"{disjuntor}A", texto),
                   (5.5 * h, y1 + 0.3 * h, f"QTA {disjuntor} A", texto * 1.25)]
    else:
        textos.append((5.5 * h, y1 + 0.3 * h, "QTA", texto * 1.25))
    textos += [(7.3 * h, y_rede + 0.35 * h, "K1", texto), (7.3 * h, y_gerador + 0.35 * h, "K2", texto),
               (5.6 * h, y2 + 0.3 * h, "K1 e K2 intertravados", texto * 0.8)]
    if kva:
        textos.append((-2 * raio, y_gerador - raio - 0.7 * h, f"GMG {kva} kVA", texto * 1.25))
    if kw or tensao:
        detalhe = " · ".join(t for t in (f"{kw} kW" if kw else "", f"{tensao} V" if tensao else "") if t)
        textos.append((-2 * raio, y_gerador - raio - 1.4 * h, detalhe, texto))
    cabos = [(f"Fases: {dados['Cabos por fase']}" if dados.get("Cabos por fase") else ""),
             " · ".join(f"{nome}: {dados[chave]}" for nome, chave in (("N", "Neutro"), ("PE", "Proteção (PE)"))
                        if dados.get(chave)),
             str(dados.get("Cabo", "")).strip()]
    for indice, linha in enumerate(t for t in cabos if t):
        textos.append((2 * h, y2 - (0.8 + 0.6 * indice) * h, linha, texto))
    if destino:
        textos.append((x_barra + 0.8 * h, y_saida + 0.3 * h, f"Alimenta {destino}", texto * 1.25))
        return {"linhas": linhas, "arcos": arcos, "circulos": circulos, "textos": textos, "saida": (fim, y_saida)}
    textos.append((fim + 0.4 * h, y_saida + 0.15 * h, "Cargas do gerador", texto * 1.25))
    cargas = [str(c) for c in cargas if str(c).strip()]
    listadas = cargas[:MAXIMO_CARGAS_LISTADAS]
    if len(cargas) > len(listadas):
        listadas.append(f"e mais {len(cargas) - len(listadas)}")
    for indice, descricao in enumerate(listadas):
        textos.append((fim + 0.4 * h, y_saida - (0.6 + 0.55 * indice) * h, descricao, texto))
    return {"linhas": linhas, "arcos": arcos, "circulos": circulos, "textos": textos, "saida": (fim, y_saida)}
