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

Todas as medidas são múltiplos de ``h`` (a altura do texto do diagrama).
"""
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
    dr = _sim(circuito.get("DR", ""))
    sensibilidade = str(circuito.get("Corrente_DR", "")).strip() or "30"
    resultado = {
        "protecao": protecao,
        "fases": fases_do_circuito(circuito),
        "dr": "DR" if dr else "",
        "sensibilidade": f"{sensibilidade}mA" if dr else "",
        "secao": secao_texto(circuito.get("Cabo", "")),
        "potencia": potencia_texto(circuito.get("Potencia", "")),
        "numero": f"C{str(circuito.get('N_circuito', '')).strip()}",
        "descricao": str(circuito.get("Destino", "")).strip(),
    }
    return {chave: texto for chave, texto in resultado.items() if texto and texto != "C"}


def condutores_do_circuito(circuito):
    """(número de fases, neutro, terra) do circuito; sem fase marcada vale 1, e o terra vai sempre."""
    fases = len(fases_do_circuito(circuito)) or 1
    neutro = _sim(circuito.get("Neutro", ""), padrao=fases == 1)
    terra = _sim(circuito.get("Terra", ""), padrao=True)
    return fases, neutro, terra
