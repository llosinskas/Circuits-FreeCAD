"""Centro de medição coletivo pela Enel SP: medição agrupada (caixas P) × busway com medição centralizada.

Base: especificação técnica Enel 0018 (GRI-EDBR-CNC-GRI-0018 / CNC-NDBR-DBR-25-1580-EDBR,
versão 2, 08/09/2025), "Fornecimento em tensão secundária até 1 kV – Conexão coletiva".

**Medição agrupada convencional** (7.18 e 7.20): todas as medições num centro de
medição no térreo, em agrupamentos modulares de caixas de policarbonato tipo P
(260 × 520 × 190 mm, Desenho 23), com a CDPM (disjuntor geral, barramentos e DPS)
no meio. Por agrupamento: até 30 caixas, no máximo 3 sobrepostas e 6 de cada lado
da CDPM, até 300 A (Tabela 28: coluna simples até 12 medições e 250 A, coluna dupla
de 13 a 30 e 250 A, coluna MAX até 30 e 300 A). Cada caixa P atende até 100 A,
mono ou bifásica; os cabos de cada unidade sobem do centro de medição até o andar
(10 a 35 mm² no borne do medidor). Mais de um agrupamento exige centro de medição
abrigado em alvenaria (porta 800 × 2100, 600 mm livres além da porta aberta e
1,00 m de circulação).

**Busway com medição eletrônica centralizada** (7.14, 7.21 e 7.22.8 a 7.22.15):
barramento blindado na prumada, com caixas MEC em cada andar (Tabela 30: MEC II até
2 medições e 200 A, IV até 4 e 300 A, VI até 6 e 300 A, IX até 9 e 400 A, XII até
12 e 400 A), alimentadas por plug-in com disjuntor de 63 a 400 A. É opção do
cliente, que paga a diferença de custo para o padrão convencional. Queda de tensão
do ponto de conexão à última medição, trecho a trecho com a carga concentrada
(Tabela 42): ΔV = k·L·I / 100, com k = √3/10·(R·cos φ + X·sen φ) em V/(100 m·A),
R e X em mΩ/m; limite de 2 % (uso residencial) ou 1 % (comercial ou misto), Tabela 41.
Sem atender, outra linha de busway (Desenho 56, seq. 4). Suportes a cada 1,5 m no
máximo (elementos de 3 m), barreira corta-fogo em cada laje, IP 54.

Nota sobre o exemplo da norma (7.22.15): o k de 0,00250 V/(100 m·A) dado para o cabo
de 185 mm² é cerca de dez vezes menor que o da fórmula da própria Tabela 42
(√3/10·Z ≈ 0,025 para 185 mm² de cobre); aqui o k dos cabos vem da fórmula.

ATENÇÃO: os **k** e as **medidas** dos busways e das caixas MEC são valores típicos de
catálogo, e os **preços** (``PRECOS``) são de referência: confirme com o fabricante
homologado e com cotações. A demanda de cada unidade e a do edifício vêm do cálculo
de demanda (não estão nesta norma).

Unidades: comprimentos em m (geometria em mm), correntes em A, tensões em V,
potências em kVA, preços em R$.
"""
import math

from freecad.Circuits.core import nbr5410

# --- tensões e limites ---------------------------------------------------------------------

TENSOES = {"127/220 V (estrela)": 220.0, "220/380 V (estrela)": 380.0, "120/240 V (delta, centro)": 240.0}
USOS = {"Residencial (queda até 2 %)": 2.0, "Comercial ou misto (queda até 1 %)": 1.0}  # Tabela 41
QUEDA_ALIMENTADOR_UNIDADE = 2.0  # % do centro de medição ao quadro da unidade (escolha do projeto)
FATOR_POTENCIA = 0.92  # da carga, para a queda nos cabos

# --- medição agrupada convencional (caixas P) ------------------------------------------------

CAIXA_P_MM = (260.0, 190.0, 520.0)  # largura, profundidade, altura (Desenho 23)
MAX_POR_AGRUPAMENTO = 30
MAX_VERTICAL = 3
MAX_POR_LADO = 18  # 6 colunas de 3 caixas de cada lado da CDPM
CORRENTE_MAX_P = 100.0  # demanda individual na caixa P
SECAO_MIN_UNIDADE, SECAO_MAX_UNIDADE = 10, 35  # mm², borne do medidor
# Tabela 28: tipo -> (até medições, corrente máxima [A], largura [mm], barramento)
CDPM = {
    "Coluna simples": (12, 250.0, 260.0, "20x5 mm"),
    "Coluna dupla": (30, 250.0, 520.0, "25x5 mm"),
    "Coluna MAX": (30, 300.0, 470.0, "25x5 mm"),
}
# Tabela 29: caixas na vertical -> altura da base do agrupamento ao piso [mm], dentro da faixa
ALTURA_BASE_MM = {1: 1200.0, 2: 700.0, 3: 320.0}  # com 3, o topo fica abaixo de 1,90 m
FOLGA_ENTRE_AGRUPAMENTOS_MM = 100.0
CIRCULACAO_MM = 1000.0  # 7.18.2
FOLGA_PORTA_ABERTA_MM = 600.0
MARGEM_LATERAL_MM = 300.0
COMPRIMENTO_NO_ANDAR_M = 10.0  # da prumada ao quadro da unidade

# --- medição centralizada (busway) --------------------------------------------------------------

# Tabela 30: tipo -> (até medições, corrente máxima [A], largura, profundidade, altura [mm] aproximadas)
MEC = {
    "MEC II": (2, 200.0, 600.0, 250.0, 900.0),
    "MEC IV": (4, 300.0, 700.0, 250.0, 1000.0),
    "MEC VI": (6, 300.0, 800.0, 250.0, 1100.0),
    "MEC IX": (9, 400.0, 1000.0, 250.0, 1100.0),
    "MEC XII": (12, 400.0, 1250.0, 250.0, 1100.0),
}
DISJUNTORES_MEC = [63, 80, 100, 125, 160, 200, 250, 320, 400]  # 7.21.2: de 63 a 400 A
ALTURA_MEC_MM = 450.0  # base da MEC VI, IX e XII: 400 a 500 mm (MEC II e IV: 600 a 800)
ALTURA_DERIVACAO_MM = 850.0  # caixa de derivação: 600 a 1100 mm
# Corrente nominal do busway [A] -> k típico [V/(100 m·A)] (cobre, carga concentrada, cos φ de ensaio)
K_BUSWAY = {
    160: 0.069, 250: 0.043, 400: 0.026, 500: 0.01615, 630: 0.0135, 800: 0.0115, 1000: 0.0098, 1250: 0.0083,
    1600: 0.0066, 2000: 0.0053, 2500: 0.0043, 3200: 0.0034, 4000: 0.0027, 5000: 0.0022,
}
CORRENTES_BUSWAY = sorted(K_BUSWAY)
MAX_LINHAS_BUSWAY = 4
ELEMENTO_RETO_M = 3.0
VAO_SUPORTE_M = 1.5  # 7.22.10, com elementos de até 3 m
# Desenho 75 (barra espaçada): até a corrente -> (profundidade C mínima, largura do shaft com MEC II/IV/VI) [mm]
SHAFT = [(400, 100.0, 800.0), (800, 110.0, 800.0), (1600, 130.0, 900.0), (2500, 160.0, 1000.0),
         (5000, 170.0, 1100.0)]
LARGURA_SHAFT_MEC = {"MEC IX": 1050.0, "MEC XII": 1300.0}
# Seção aproximada do busway [mm]: até a corrente -> (largura, profundidade)
SECAO_BUSWAY_MM = [(400, 130.0, 100.0), (800, 140.0, 110.0), (1600, 200.0, 130.0), (2500, 300.0, 160.0),
                   (5000, 420.0, 170.0)]

# --- entrada (comum às duas soluções) -----------------------------------------------------------

# Tabela 32: QDC -> corrente máxima [A]; circuito de entrada de 4 × 240 mm² para cada 300 A
QDC = [("QDC 5", 300.0), ("QDC 10", 600.0), ("QDC 15", 1400.0), ("QDC 21", 2800.0)]
CABINE = "Cabine de barramentos"  # acima do QDC 21 (7.22.4: obrigatória acima de 1000 kVA)
SECAO_RAMAL = 240.0
CORRENTE_POR_CIRCUITO_RAMAL = 300.0
REATANCIA_CABO = 0.08  # mΩ/m

# --- preços de referência (R$) -------------------------------------------------------------------

PRECOS = {
    "caixa_p": ("Caixa de medição tipo P", 420.0),
    "cdpm_Coluna simples": ("CDPM coluna simples", 2800.0),
    "cdpm_Coluna dupla": ("CDPM coluna dupla", 4500.0),
    "cdpm_Coluna MAX": ("CDPM coluna MAX", 6500.0),
    "cabo_mm2_m": ("Cabo de cobre 750 V, por mm² × m", 1.05),
    "eletroduto_m": ("Eletroduto de cada alimentador, por m", 18.0),
    "abrigo_m2": ("Centro de medição abrigado em alvenaria, por m²", 3500.0),
    "mec_MEC II": ("Caixa MEC II", 2200.0),
    "mec_MEC IV": ("Caixa MEC IV", 3200.0),
    "mec_MEC VI": ("Caixa MEC VI", 4300.0),
    "mec_MEC IX": ("Caixa MEC IX", 6200.0),
    "mec_MEC XII": ("Caixa MEC XII", 7800.0),
    "plugin": ("Plug-in com disjuntor (derivação)", 2600.0),
    "busway_m_160": ("Busway 160 A, por m", 950.0),
    "busway_m_250": ("Busway 250 A, por m", 1150.0),
    "busway_m_400": ("Busway 400 A, por m", 1500.0),
    "busway_m_500": ("Busway 500 A, por m", 1800.0),
    "busway_m_630": ("Busway 630 A, por m", 2100.0),
    "busway_m_800": ("Busway 800 A, por m", 2600.0),
    "busway_m_1000": ("Busway 1000 A, por m", 3100.0),
    "busway_m_1250": ("Busway 1250 A, por m", 3800.0),
    "busway_m_1600": ("Busway 1600 A, por m", 4600.0),
    "busway_m_2000": ("Busway 2000 A, por m", 5600.0),
    "busway_m_2500": ("Busway 2500 A, por m", 7000.0),
    "busway_m_3200": ("Busway 3200 A, por m", 8800.0),
    "busway_m_4000": ("Busway 4000 A, por m", 11000.0),
    "busway_m_5000": ("Busway 5000 A, por m", 13500.0),
    "busway_acessorio": ("Cotovelo, flange ou tampa final (× preço do metro)", 1.5),
    "corta_fogo": ("Barreira corta-fogo na laje", 650.0),
    "suporte_busway": ("Suporte do busway", 120.0),
    "concentradora": ("Caixa concentradora CL-II", 3500.0),
    "comunicacao_m": ("Cabo de comunicação, por m", 8.0),
    "onus_medicao": ("Ônus da medição eletrônica, por unidade", 350.0),
    "qdc_QDC 5": ("QDC 5", 9000.0),
    "qdc_QDC 10": ("QDC 10", 14000.0),
    "qdc_QDC 15": ("QDC 15", 22000.0),
    "qdc_QDC 21": ("QDC 21", 35000.0),
    "qdc_Cabine de barramentos": ("Cabine de barramentos", 90000.0),
    "mao_de_obra": ("Mão de obra (fração do material)", 0.30),
}


def precos_padrao():
    """{chave: valor} dos preços de referência."""
    return {chave: valor for chave, (_, valor) in PRECOS.items()}


# --- entrada de dados ---------------------------------------------------------------------------

def andar(nome, cota, unidades, demanda_a=63.0, fases=2):
    """Um pavimento com unidades consumidoras.

    Args:
        cota: do piso, em relação ao piso do centro de medição [m].
        unidades: unidades consumidoras do andar.
        demanda_a: corrente de demanda de cada unidade [A].
        fases: 1, 2 ou 3.
    """
    unidades, fases = int(unidades), int(fases)
    if unidades < 0 or demanda_a < 0:
        raise ValueError(f"{nome}: unidades e demanda não podem ser negativas.")
    if fases not in (1, 2, 3):
        raise ValueError(f"{nome}: fases deve ser 1, 2 ou 3.")
    return {"nome": str(nome), "cota": float(cota), "unidades": unidades, "demanda_a": float(demanda_a),
            "fases": fases}


def _com_unidades(andares):
    return sorted((a for a in andares if a["unidades"] > 0), key=lambda a: a["cota"])


def corrente_dos_andares(andares, demanda_total_a=0.0):
    """Corrente de demanda de cada andar [A], na ordem de ``andares``.

    Sem ``demanda_total_a``, é a soma das unidades; com ela (do cálculo de demanda
    do edifício, que já tem a diversidade), é repartida pelo peso de cada andar.
    """
    somas = [a["unidades"] * a["demanda_a"] for a in andares]
    total = sum(somas)
    if not demanda_total_a or total <= 0:
        return somas
    return [s * float(demanda_total_a) / total for s in somas]


def comercial(lista, valor):
    """Primeiro valor da lista ≥ ``valor``, ou None."""
    return next((v for v in lista if v >= valor - 1e-9), None)


def k_cabo(secao, paralelos=1, fator_potencia=FATOR_POTENCIA, material="cobre"):
    """k de cabos trifásicos [V/(100 m·A)] pela Tabela 42: √3/10·(R·cos φ + X·sen φ) / paralelos."""
    r = 1000.0 * nbr5410.RESISTIVIDADE_QUEDA[material] / float(secao)  # mΩ/m
    seno = math.sqrt(max(0.0, 1 - fator_potencia ** 2))
    return math.sqrt(3) / 10.0 * (r * fator_potencia + REATANCIA_CABO * seno) / int(paralelos)


def queda(k, comprimento, corrente, tensao):
    """Queda de tensão trifásica [V, %] de um trecho (Tabela 42): ΔV = k·L·I/100."""
    volts = float(k) * float(comprimento) * float(corrente) / 100.0
    return volts, 100.0 * volts / float(tensao)


def entrada(corrente):
    """QDC e ramal de entrada pela corrente total: (QDC, circuitos de 4 × 240 mm², k do ramal)."""
    qdc = next((nome for nome, maximo in QDC if corrente <= maximo), CABINE)
    circuitos = max(1, math.ceil(corrente / CORRENTE_POR_CIRCUITO_RAMAL - 1e-9))
    return qdc, circuitos, k_cabo(SECAO_RAMAL, circuitos)


# --- medição agrupada convencional -----------------------------------------------------------------

def tipo_cdpm(caixas, corrente):
    """Tipo da CDPM (Tabela 28) para as caixas e a corrente do agrupamento, ou None se não cabe."""
    for nome, (maximo, amperes, _, _) in CDPM.items():
        if caixas <= maximo and corrente <= amperes + 1e-9:
            return nome
    return None


def distribuicao(caixas):
    """(caixas à esquerda, à direita, caixas na vertical) de um agrupamento."""
    if caixas > MAX_POR_AGRUPAMENTO:
        raise ValueError(f"Um agrupamento tem no máximo {MAX_POR_AGRUPAMENTO} caixas.")
    vertical = min(MAX_VERTICAL, max(1, math.ceil(caixas / 2)))
    esquerda = math.ceil(caixas / 2)
    return esquerda, caixas - esquerda, vertical


def largura_agrupamento(caixas, cdpm):
    esquerda, direita, vertical = distribuicao(caixas)
    colunas = math.ceil(esquerda / vertical) + math.ceil(direita / vertical)
    return colunas * CAIXA_P_MM[0] + CDPM[cdpm][2]


def agrupamentos(caixas, corrente_por_caixa):
    """Agrupamentos de caixas P: [{'caixas', 'corrente', 'cdpm', 'largura_mm'}].

    Reparte as caixas igualmente no menor número de agrupamentos em que todos cabem
    (até 30 caixas e a corrente da CDPM).
    """
    if caixas <= 0:
        return []
    for quantidade in range(1, caixas + 1):
        divisao = [caixas // quantidade + (1 if i < caixas % quantidade else 0) for i in range(quantidade)]
        grupos = []
        for n in divisao:
            corrente = n * corrente_por_caixa
            cdpm = tipo_cdpm(n, corrente)
            if cdpm is None:
                break
            grupos.append({"caixas": n, "corrente": corrente, "cdpm": cdpm,
                           "largura_mm": largura_agrupamento(n, cdpm)})
        else:
            return grupos
    raise ValueError(f"Caixa P com {corrente_por_caixa:.0f} A não cabe em nenhuma CDPM (máximo 300 A).")


def _cabo_da_unidade(demanda_a, fases, comprimento, tensao):
    n_fases = 3 if fases == 3 else 1
    tensao_circuito = tensao if fases >= 2 else tensao / math.sqrt(3)
    resultado = nbr5410.dimensionar_circuito(demanda_a, "TUE", comprimento, tensao_circuito, n_fases,
                                             queda_max=QUEDA_ALIMENTADOR_UNIDADE, fator_potencia=FATOR_POTENCIA)
    return max(SECAO_MIN_UNIDADE, resultado["secao"]), resultado


def convencional(andares, tensao=220.0, distancia_horizontal=15.0, demanda_total_a=0.0,
                 comprimento_no_andar=COMPRIMENTO_NO_ANDAR_M):
    """Medição agrupada com caixas P num centro de medição no térreo.

    Args:
        andares: de ``andar``; a cota é medida do piso do centro de medição.
        distancia_horizontal: do centro de medição à base da prumada dos alimentadores [m].
        comprimento_no_andar: da prumada ao quadro da unidade [m].
    Returns:
        dict com ``agrupamentos``, ``caixas``, ``corrente``, ``abrigo`` (comprimento,
        profundidade [m], área [m²]), ``alimentadores`` (por andar: seção, condutores,
        comprimento), ``cabo_mm2_m``, ``eletroduto_m``, ``qdc``, ``ramal`` e ``avisos``.
    """
    lista = _com_unidades(andares)
    if not lista:
        raise ValueError("Nenhum andar com unidades.")
    avisos = []
    correntes = corrente_dos_andares(lista, demanda_total_a)
    total = sum(correntes)
    caixas = sum(a["unidades"] for a in lista)
    maior = max(a["demanda_a"] for a in lista)
    if maior > CORRENTE_MAX_P:
        avisos.append(f"unidade de {maior:.0f} A: a caixa P vai até {CORRENTE_MAX_P:.0f} A (use caixa N, M ou "
                      "medição indireta para ela)")
    if any(a["fases"] == 3 for a in lista):
        avisos.append("unidades trifásicas: a caixa P é só para mono e bifásicas")
    grupos = agrupamentos(caixas, min(total / caixas, CORRENTE_MAX_P))
    if len(grupos) > 1:
        avisos.append(f"{len(grupos)} agrupamentos: centro de medição abrigado em alvenaria obrigatório")

    comprimento_mm = (sum(g["largura_mm"] for g in grupos) + FOLGA_ENTRE_AGRUPAMENTOS_MM * (len(grupos) - 1)
                      + 2 * MARGEM_LATERAL_MM)
    profundidade_mm = CAIXA_P_MM[1] + CAIXA_P_MM[0] + max(FOLGA_PORTA_ABERTA_MM, CIRCULACAO_MM)
    abrigo = {"comprimento": comprimento_mm / 1000.0, "profundidade": profundidade_mm / 1000.0,
              "area": comprimento_mm * profundidade_mm / 1e6}

    alimentadores, cabo, eletroduto = [], 0.0, 0.0
    for a in lista:
        comprimento = distancia_horizontal + max(0.0, a["cota"]) + comprimento_no_andar
        try:
            secao, calculo = _cabo_da_unidade(a["demanda_a"], a["fases"], comprimento, tensao)
        except ValueError as erro:
            raise ValueError(f"{a['nome']}: {erro}") from erro
        if secao > SECAO_MAX_UNIDADE:
            avisos.append(f"{a['nome']}: alimentador de {secao} mm² acima dos {SECAO_MAX_UNIDADE} mm² do borne do "
                          "medidor")
        condutores = a["fases"] + 1  # fases e neutro
        secao_pe = nbr5410.secao_protecao(secao)
        mm2_m = a["unidades"] * comprimento * (condutores * secao + secao_pe)
        cabo += mm2_m
        eletroduto += a["unidades"] * comprimento
        alimentadores.append({"andar": a["nome"], "unidades": a["unidades"], "secao": secao, "pe": secao_pe,
                              "condutores": condutores, "comprimento": comprimento, "queda": calculo["queda"],
                              "disjuntor": calculo["disjuntor"]})
    qdc, circuitos, _ = entrada(total)
    return {"solucao": "convencional", "agrupamentos": grupos, "caixas": caixas, "corrente": total,
            "abrigo": abrigo, "alimentadores": alimentadores, "cabo_mm2_m": cabo, "eletroduto_m": eletroduto,
            "qdc": qdc, "ramal": circuitos, "avisos": avisos}


# --- busway -------------------------------------------------------------------------------------

def caixas_mec(unidades, corrente):
    """Caixas MEC de um andar: [{'tipo', 'medicoes', 'corrente', 'disjuntor'}] (Tabela 30)."""
    if unidades <= 0:
        return []
    for quantidade in range(1, unidades + 1):
        divisao = [unidades // quantidade + (1 if i < unidades % quantidade else 0) for i in range(quantidade)]
        caixas = []
        for n in divisao:
            amperes = corrente * n / unidades
            tipo = next((t for t, (maximo, limite, *_r) in MEC.items() if n <= maximo and amperes <= limite + 1e-9),
                        None)
            if tipo is None:
                break
            caixas.append({"tipo": tipo, "medicoes": n, "corrente": amperes,
                           "disjuntor": comercial(DISJUNTORES_MEC, max(63.0, amperes))})
        else:
            return caixas
    raise ValueError(f"{unidades} unidades com {corrente:.0f} A não cabem em caixas MEC (máximo 400 A por caixa).")


def _linhas_contiguas(correntes, n):
    """Divide os andares (de baixo para cima) em ``n`` grupos seguidos de corrente parecida."""
    total = sum(correntes)
    grupos, atual, soma = [], [], 0.0
    for indice, corrente in enumerate(correntes):
        atual.append(indice)
        soma += corrente
        restantes = len(correntes) - indice - 1
        if len(grupos) < n - 1 and soma >= total * (len(grupos) + 1) / n - 1e-9 and restantes >= n - len(grupos) - 1:
            grupos.append(atual)
            atual = []
    if atual:
        grupos.append(atual)
    return grupos


def _trechos(andares_da_linha, correntes, distancia_horizontal, altura_derivacao):
    """Trechos de uma linha: [(comprimento [m], corrente [A], até)] do QDC à última derivação."""
    trechos, posicao = [], 0.0
    restante = sum(correntes)
    primeiro = True
    for a, corrente in zip(andares_da_linha, correntes):
        destino = a["cota"] + altura_derivacao
        comprimento = (distancia_horizontal if primeiro else 0.0) + max(0.0, destino - posicao)
        trechos.append((comprimento, restante, a["nome"]))
        restante -= corrente
        posicao = destino
        primeiro = False
    return trechos


def _dimensionar_linha(andares_da_linha, correntes, tensao, limite, distancia_horizontal, k_ramal_vt):
    trechos = _trechos(andares_da_linha, correntes, distancia_horizontal, ALTURA_DERIVACAO_MM / 1000.0)
    corrente = trechos[0][1]
    for nominal in CORRENTES_BUSWAY:
        if nominal < corrente - 1e-9:
            continue
        k = K_BUSWAY[nominal]
        volts = k_ramal_vt + sum(queda(k, l, i, tensao)[0] for l, i, _ in trechos)
        if 100.0 * volts / tensao <= limite + 1e-9:
            return {"corrente": corrente, "nominal": nominal, "k": k, "trechos": trechos,
                    "queda_v": volts, "queda": 100.0 * volts / tensao}
    return None


def busway(andares, tensao=220.0, uso=2.0, distancia_horizontal=15.0, comprimento_ramal=0.0,
           demanda_total_a=0.0, altura_ultimo_pavimento=3.0):
    """Busway na prumada com caixas MEC por andar.

    Args:
        uso: queda máxima [%] da Tabela 41 (2 residencial, 1 comercial/misto).
        distancia_horizontal: do QDC à base da prumada (busway horizontal) [m].
        comprimento_ramal: do ponto de conexão ao QDC [m]; entra na queda.
        altura_ultimo_pavimento: piso a piso do último andar [m], até a tampa final.
    Returns:
        dict com ``linhas`` (busway de cada linha: corrente nominal, k, trechos, queda,
        andares atendidos), ``andares`` (caixas MEC de cada andar), ``materiais``,
        ``shaft`` [mm], ``qdc``, ``ramal``, ``corrente`` e ``avisos``.
    """
    lista = _com_unidades(andares)
    if not lista:
        raise ValueError("Nenhum andar com unidades.")
    avisos = []
    correntes = corrente_dos_andares(lista, demanda_total_a)
    total = sum(correntes)
    qdc, circuitos, k_ramal = entrada(total)
    volts_ramal = queda(k_ramal, comprimento_ramal, total, tensao)[0]

    escolha = None
    for n in range(1, min(MAX_LINHAS_BUSWAY, len(lista)) + 1):
        linhas = []
        for grupo in _linhas_contiguas(correntes, n):
            linha = _dimensionar_linha([lista[i] for i in grupo], [correntes[i] for i in grupo], tensao, uso,
                                       distancia_horizontal, volts_ramal)
            if linha is None:
                break
            linha["andares"] = [lista[i]["nome"] for i in grupo]
            linhas.append(linha)
        else:
            escolha = linhas
            break
    if escolha is None:
        raise ValueError(f"Nem com {MAX_LINHAS_BUSWAY} linhas de busway a queda fica até {uso:g} %: reveja a "
                         "demanda, a distância horizontal ou o k do fabricante.")
    if len(escolha) > 1:
        avisos.append(f"{len(escolha)} linhas de busway para a queda ficar até {uso:g} % (Desenho 56, seq. 4)")

    por_andar = []
    for a, corrente in zip(lista, correntes):
        if a["demanda_a"] > CORRENTE_MAX_P:
            avisos.append(f"{a['nome']}: unidade de {a['demanda_a']:.0f} A é medição indireta (MEC IV até 160 A, "
                          "MEC VI até 300 A)")
        por_andar.append({"andar": a["nome"], "cota": a["cota"], "unidades": a["unidades"], "corrente": corrente,
                          "caixas": caixas_mec(a["unidades"], corrente)})

    topo = lista[-1]["cota"] + altura_ultimo_pavimento
    materiais = {"metros": {}, "cotovelos": 0, "flanges": 0, "tampas": 0, "emendas": 0, "suportes": 0,
                 "corta_fogo": 0, "plugins": 0}
    nomes_por_linha = []
    for linha in escolha:
        vertical = topo - 0.0 if linha is escolha[-1] else max(
            a["cota"] for a in lista if a["nome"] in linha["andares"]) + ALTURA_DERIVACAO_MM / 1000.0 + 0.5
        comprimento = distancia_horizontal + vertical
        materiais["metros"][linha["nominal"]] = materiais["metros"].get(linha["nominal"], 0.0) + comprimento
        materiais["cotovelos"] += 1
        materiais["flanges"] += 1
        materiais["tampas"] += 1
        materiais["emendas"] += max(0, math.ceil(comprimento / ELEMENTO_RETO_M - 1e-9) - 1)
        materiais["suportes"] += math.ceil(comprimento / VAO_SUPORTE_M - 1e-9)
        materiais["corta_fogo"] += sum(1 for a in lista if 0.0 < a["cota"] <= vertical)
        linha["comprimento"] = comprimento
        nomes_por_linha.append(set(linha["andares"]))
    materiais["plugins"] = sum(len(a["caixas"]) for a in por_andar)
    materiais["mec"] = {}
    for a in por_andar:
        for caixa in a["caixas"]:
            materiais["mec"][caixa["tipo"]] = materiais["mec"].get(caixa["tipo"], 0) + 1
    materiais["comunicacao_m"] = topo + distancia_horizontal
    maior = max(linha["nominal"] for linha in escolha)
    c, largura = next((c, l) for limite, c, l in SHAFT if maior <= limite)
    tipos = [c["tipo"] for a in por_andar for c in a["caixas"]]
    largura = max([largura] + [LARGURA_SHAFT_MEC.get(t, 0.0) for t in tipos])
    shaft = {"largura": largura * (1 if len(escolha) == 1 else 1.6), "profundidade": c + 250.0 + 50.0}
    return {"solucao": "busway", "linhas": escolha, "andares": por_andar, "materiais": materiais, "shaft": shaft,
            "qdc": qdc, "ramal": circuitos, "corrente": total, "unidades": sum(a["unidades"] for a in lista),
            "topo": topo, "avisos": avisos}


# --- custos -------------------------------------------------------------------------------------

def _item(itens, precos, chave, quantidade, unidade="un", multiplicador=1.0, descricao=None):
    if quantidade <= 0:
        return
    unitario = float(precos.get(chave, PRECOS.get(chave, ("", 0.0))[1])) * multiplicador
    nome = descricao or PRECOS.get(chave, (chave, 0))[0]
    itens.append({"descricao": nome, "quantidade": quantidade, "unidade": unidade, "unitario": unitario,
                  "total": quantidade * unitario})


def orcamento(resultado, precos=None):
    """Estimativa de custo da solução: {'itens', 'material', 'mao_de_obra', 'total'} [R$]."""
    precos = dict(precos_padrao(), **(precos or {}))
    itens = []
    if resultado["solucao"] == "convencional":
        _item(itens, precos, "caixa_p", resultado["caixas"])
        for g in resultado["agrupamentos"]:
            _item(itens, precos, f"cdpm_{g['cdpm']}", 1)
        _item(itens, precos, "cabo_mm2_m", round(resultado["cabo_mm2_m"]), "mm²·m")
        _item(itens, precos, "eletroduto_m", round(resultado["eletroduto_m"], 1), "m")
        _item(itens, precos, "abrigo_m2", round(resultado["abrigo"]["area"], 2), "m²")
    else:
        m = resultado["materiais"]
        for nominal, metros in sorted(m["metros"].items()):
            _item(itens, precos, f"busway_m_{nominal}", round(metros, 1), "m")
        maior = max(m["metros"]) if m["metros"] else 0
        metro = float(precos.get(f"busway_m_{maior}", 0.0))
        acessorios = m["cotovelos"] + m["flanges"] + m["tampas"]
        _item(itens, precos, "busway_acessorio", acessorios, multiplicador=metro,
              descricao="Cotovelos, flanges e tampas finais do busway")
        for tipo, quantidade in sorted(m["mec"].items()):
            _item(itens, precos, f"mec_{tipo}", quantidade)
        _item(itens, precos, "plugin", m["plugins"])
        _item(itens, precos, "corta_fogo", m["corta_fogo"])
        _item(itens, precos, "suporte_busway", m["suportes"])
        _item(itens, precos, "concentradora", 1)
        _item(itens, precos, "comunicacao_m", round(m["comunicacao_m"], 1), "m")
        _item(itens, precos, "onus_medicao", resultado["unidades"])
    _item(itens, precos, f"qdc_{resultado['qdc']}", 1)
    material = sum(i["total"] for i in itens)
    mao = material * float(precos.get("mao_de_obra", 0.0))
    return {"itens": itens, "material": material, "mao_de_obra": mao, "total": material + mao}


def comparar(andares, tensao=220.0, uso=2.0, distancia_horizontal=15.0, comprimento_ramal=0.0,
             demanda_total_a=0.0, altura_ultimo_pavimento=3.0, precos=None):
    """As duas soluções com o orçamento de cada uma e a recomendação.

    Returns:
        {'convencional', 'busway': resultado ou None, 'erro_busway', 'custos': {solução: orçamento},
         'recomendada', 'economia' [R$]}.
    """
    conv = convencional(andares, tensao, distancia_horizontal, demanda_total_a)
    custos = {"convencional": orcamento(conv, precos)}
    bus, erro = None, ""
    try:
        bus = busway(andares, tensao, uso, distancia_horizontal, comprimento_ramal, demanda_total_a,
                     altura_ultimo_pavimento)
        custos["busway"] = orcamento(bus, precos)
    except ValueError as e:
        erro = str(e)
    if not demanda_total_a and conv["caixas"] > 1:
        conv["avisos"].insert(0, "sem a demanda do edifício, as unidades foram somadas sem diversidade: informe a "
                                 "demanda do cálculo de demanda para não superdimensionar")
    if bus is None:
        recomendada = "convencional"
    else:
        recomendada = min(custos, key=lambda s: custos[s]["total"])
    outros = [s for s in custos if s != recomendada]
    economia = custos[outros[0]]["total"] - custos[recomendada]["total"] if outros else 0.0
    return {"convencional": conv, "busway": bus, "erro_busway": erro, "custos": custos, "recomendada": recomendada,
            "economia": economia}


NOMES = {"convencional": "Medição agrupada (caixas P no térreo)", "busway": "Busway com medição centralizada"}


def _br(valor, casas=0):
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def relatorio(r):
    """Texto da comparação, para mostrar ao usuário."""
    conv, bus = r["convencional"], r["busway"]
    linhas = [f"Corrente de demanda total: {_br(conv['corrente'])} A · {conv['caixas']} medições · "
              f"entrada {conv['qdc']} com {conv['ramal']} circuito(s) de 4 × 240 mm²", "",
              f"1) {NOMES['convencional']}"]
    for i, g in enumerate(conv["agrupamentos"], start=1):
        linhas.append(f"   Agrupamento {i}: {g['caixas']} caixas P, {g['cdpm']}, {_br(g['corrente'])} A, "
                      f"{_br(g['largura_mm'])} mm de largura")
    ab = conv["abrigo"]
    linhas.append(f"   Centro de medição: {_br(ab['comprimento'], 2)} × {_br(ab['profundidade'], 2)} m = "
                  f"{_br(ab['area'], 1)} m²")
    for a in conv["alimentadores"]:
        linhas.append(f"   {a['andar']}: {a['unidades']} × ({a['condutores']} × {a['secao']} + PE {a['pe']}) mm², "
                      f"{_br(a['comprimento'], 1)} m, queda {_br(a['queda'], 2)} %")
    linhas.append(f"   Custo estimado: R$ {_br(r['custos']['convencional']['total'])}")
    linhas += ["", f"2) {NOMES['busway']}"]
    if bus is None:
        linhas.append(f"   Não atende: {r['erro_busway']}")
    else:
        for i, linha in enumerate(bus["linhas"], start=1):
            linhas.append(f"   Linha {i}: busway {linha['nominal']} A (k {str(linha['k']).replace('.', ',')}), "
                          f"{_br(linha['comprimento'], 1)} m, demanda {_br(linha['corrente'])} A, queda "
                          f"{_br(linha['queda'], 2)} % até {linha['andares'][-1]}")
        for a in bus["andares"]:
            caixas = " + ".join(f"{c['tipo']} ({c['medicoes']} med., disj. {c['disjuntor']} A)" for c in a["caixas"])
            linhas.append(f"   {a['andar']}: {caixas}")
        m = bus["materiais"]
        linhas.append(f"   Shaft mínimo: {_br(bus['shaft']['largura'])} × {_br(bus['shaft']['profundidade'])} mm; "
                      f"{m['emendas']} emendas, {m['suportes']} suportes, {m['corta_fogo']} barreiras corta-fogo")
        linhas.append(f"   Custo estimado: R$ {_br(r['custos']['busway']['total'])}")
    linhas += ["", f"Recomendada pelo custo: {NOMES[r['recomendada']]}"
               + (f" (R$ {_br(r['economia'])} a menos)" if r["economia"] else "")]
    avisos = conv["avisos"] + (bus["avisos"] if bus else [])
    if avisos:
        linhas += ["", "Avisos:"] + [f" - {a}" for a in avisos]
    linhas += ["", "Preços de referência (edite na planilha) e k/medidas típicos: confirme com o fabricante "
               "homologado e com a Enel."]
    return "\n".join(linhas)


def resumo(r):
    """[(rótulo, valor)] para gravar na planilha."""
    linhas = [("Recomendada", NOMES[r["recomendada"]]),
              ("Corrente total [A]", _br(r["convencional"]["corrente"])),
              ("Entrada", f"{r['convencional']['qdc']}, {r['convencional']['ramal']} × 4 × 240 mm²"),
              ("Agrupamentos (caixas P)", str(len(r["convencional"]["agrupamentos"]))),
              ("Centro de medição [m²]", _br(r["convencional"]["abrigo"]["area"], 1)),
              ("Custo convencional [R$]", _br(r["custos"]["convencional"]["total"]))]
    if r["busway"]:
        linhas += [("Busway", " + ".join(f"{l['nominal']} A" for l in r["busway"]["linhas"])),
                   ("Queda no busway [%]", " / ".join(_br(l["queda"], 2) for l in r["busway"]["linhas"])),
                   ("Custo busway [R$]", _br(r["custos"]["busway"]["total"]))]
    return linhas


# --- planilha -----------------------------------------------------------------------------------

LINHA_TITULOS, PRIMEIRA_LINHA = 2, 3
COLUNAS = [("A", "nome", "Pavimento"), ("B", "cota", "Cota do piso [m]"), ("C", "unidades", "Unidades"),
           ("D", "demanda_a", "Demanda por unidade [A]"), ("E", "fases", "Fases (1, 2 ou 3)")]
COLUNA_PRECO_CHAVE, COLUNA_PRECO_ROTULO, COLUNA_PRECO_VALOR = "G", "H", "I"
COLUNA_RESULTADO_ROTULO, COLUNA_RESULTADO_VALOR = "K", "L"
AJUDA = ("Um pavimento por linha (cota em relação ao piso do centro de medição). Demanda por unidade: do cálculo "
         "de demanda. Preços nas colunas G a I: edite com as suas cotações.")
UNIDADES_PADRAO, DEMANDA_PADRAO, FASES_PADRAO = 4, 63.0, 2


def andar_da_linha(celulas):
    """Andar a partir das células de texto da planilha (vírgula decimal aceita)."""
    def numero(chave, padrao):
        texto = str(celulas.get(chave, "")).strip().replace(",", ".")
        if not texto:
            return padrao
        try:
            return float(texto)
        except ValueError as erro:
            raise ValueError(f"valor inválido em '{chave}': {celulas.get(chave)}") from erro
    return andar(celulas.get("nome") or "Pavimento", numero("cota", 0.0), int(numero("unidades", 0)),
                 numero("demanda_a", DEMANDA_PADRAO), int(numero("fases", FASES_PADRAO)))


def linhas_dos_pavimentos(pavimentos, cota_base=None):
    """Linhas iniciais da planilha a partir de [(nome, cota do piso [m])]: o mais baixo fica sem unidades."""
    if not pavimentos:
        return [{"nome": f"{i}º pavimento", "cota": 3.0 * i, "unidades": UNIDADES_PADRAO} for i in range(1, 5)]
    ordenados = sorted(pavimentos, key=lambda p: p[1])
    base = ordenados[0][1] if cota_base is None else cota_base
    return [{"nome": nome, "cota": round(cota - base, 2), "unidades": 0 if i == 0 else UNIDADES_PADRAO}
            for i, (nome, cota) in enumerate(ordenados)]


# --- geometria: coluna de medição (agrupamento) ----------------------------------------------------------

def coluna_de_medicao(caixas, cdpm=None):
    """Caixas de um agrupamento em elevação, a partir do meio da base da CDPM no piso.

    O fundo das caixas fica na parede (y de 0 a +profundidade); a frente, em y = 0.

    Returns:
        {'caixas': [(rótulo, (x, y, z), (dx, dy, dz))] mm, 'largura', 'altura', 'base', 'cdpm'}.
    """
    esquerda, direita, vertical = distribuicao(caixas)
    cdpm = cdpm or tipo_cdpm(caixas, caixas * 63.0) or "Coluna MAX"
    largura_p, prof, altura_p = CAIXA_P_MM
    largura_cdpm = CDPM[cdpm][2]
    base = ALTURA_BASE_MM[vertical]
    pecas = [("CDPM", (-largura_cdpm / 2, 0.0, base), (largura_cdpm, prof, vertical * altura_p))]
    numero = 1
    for lado, quantidade in ((-1, esquerda), (1, direita)):
        for i in range(quantidade):
            coluna, linha = divmod(i, vertical)
            x0 = largura_cdpm / 2 + coluna * largura_p
            x = x0 if lado > 0 else -x0 - largura_p
            pecas.append((f"M{numero:02d}", (x, 0.0, base + (vertical - 1 - linha) * altura_p),
                          (largura_p, prof, altura_p)))
            numero += 1
    xs = [p[1][0] for p in pecas] + [p[1][0] + p[2][0] for p in pecas]
    return {"caixas": pecas, "largura": max(xs) - min(xs), "altura": vertical * altura_p, "base": base,
            "cdpm": cdpm}


# Detalhes da coluna (Desenhos 23 a 26 e 55): medidas aproximadas [mm]
TAMPA_MM = 4.0  # tampa de policarbonato transparente
DIVISORIA = 0.62  # fração da altura da caixa P acima da divisória (medição em cima, proteção embaixo)
MEDIDOR_MM = (130.0, 60.0, 190.0)  # largura, profundidade, altura
DISJUNTOR_UNIDADE_MM = (36.0, 70.0, 90.0)  # bipolar DIN até 100 A
DISJUNTOR_GERAL_MM = (105.0, 90.0, 160.0)  # tripolar, até 300 A
DPS_MM = (18.0, 65.0, 90.0)
BARRA_CDPM = {"Coluna simples": (20.0, 5.0), "Coluna dupla": (25.0, 5.0), "Coluna MAX": (25.0, 5.0)}  # Tabela 28
COMPRIMENTO_BARRA_MM = {"Coluna simples": 600.0, "Coluna dupla": 600.0, "Coluna MAX": 600.0}
DIAMETRO_SAIDA_MM = 40.0  # eletroduto do ramal alimentador de cada unidade, pelo fundo da caixa
DIAMETRO_ENTRADA_MM = 100.0  # eletroduto do ramal de entrada, por baixo da CDPM
DPS_POR_CDPM = 4  # 3 fases e neutro

# Tipo de peça -> (cor RGB, transparência %)
CORES_DAS_PECAS = {
    "corpo": ((0.82, 0.84, 0.86), 0), "tampa": ((0.75, 0.88, 1.0), 70), "cdpm": ((0.70, 0.71, 0.74), 0),
    "medidor": ((0.25, 0.27, 0.30), 0), "disjuntor": ((0.12, 0.12, 0.12), 0), "barra": ((0.85, 0.5, 0.25), 0),
    "dps": ((0.15, 0.35, 0.65), 0), "eletroduto": ((0.55, 0.55, 0.55), 0), "etiqueta": ((1.0, 1.0, 1.0), 0),
}


def _peca(pecas, tipo, rotulo, origem, dims):
    pecas.append({"tipo": tipo, "rotulo": rotulo, "forma": "caixa", "origem": origem, "dims": dims})


def _tubo(pecas, rotulo, centro, raio, comprimento, eixo):
    pecas.append({"tipo": "eletroduto", "rotulo": rotulo, "forma": "cilindro", "origem": centro, "raio": raio,
                  "comprimento": comprimento, "eixo": eixo})


def pecas_da_coluna(caixas, cdpm=None):
    """Coluna detalhada: cada caixa P com corpo, tampa transparente, divisória, medidor, disjuntor,
    etiqueta e eletroduto de saída pelo fundo; a CDPM com corpo, tampa, barramentos R, S, T, N e PE,
    disjuntor geral, DPS e o eletroduto de entrada até o piso.

    Mesma origem e orientação de ``coluna_de_medicao`` (frente em y = 0, fundo na parede, em +y).

    Returns:
        [{'tipo' (chave de ``CORES_DAS_PECAS``), 'rotulo', 'forma': 'caixa' com 'origem' e 'dims',
          ou 'cilindro' com 'origem' (centro da base), 'raio', 'comprimento' e 'eixo'}] em mm.
    """
    geral = coluna_de_medicao(caixas, cdpm)
    pecas = []
    for rotulo, (x, y, z), (dx, dy, dz) in geral["caixas"]:
        _peca(pecas, "cdpm" if rotulo == "CDPM" else "corpo", rotulo, (x, y + TAMPA_MM, z), (dx, dy - TAMPA_MM, dz))
        _peca(pecas, "tampa", f"{rotulo} tampa", (x, y, z), (dx, TAMPA_MM, dz))
        meio = x + dx / 2.0
        if rotulo == "CDPM":
            largura_barra, espessura = BARRA_CDPM[geral["cdpm"]]
            comprimento = min(COMPRIMENTO_BARRA_MM[geral["cdpm"]], dz * 0.45)
            topo = z + dz - 60.0
            for i, fase in enumerate(("R", "S", "T", "N", "PE")):
                bx = meio - 2 * (largura_barra + 25.0) + i * (largura_barra + 25.0) - largura_barra / 2.0
                _peca(pecas, "barra", f"Barra {fase}", (bx, y + dy - 40.0, topo - comprimento),
                      (largura_barra, espessura, comprimento))
            lx, ly, lz = DISJUNTOR_GERAL_MM
            base_disjuntor = z + dz * 0.25
            _peca(pecas, "disjuntor", "Disjuntor geral", (meio - lx / 2.0, y + dy - 15.0 - ly, base_disjuntor),
                  (lx, ly, lz))
            px, py, pz = DPS_MM
            inicio = meio - DPS_POR_CDPM * px / 2.0
            for i in range(DPS_POR_CDPM):
                _peca(pecas, "dps", f"DPS {i + 1}", (inicio + i * px, y + dy - 15.0 - py, z + 60.0), (px, py, pz))
            _tubo(pecas, "Eletroduto de entrada", (meio, y + dy / 2.0, 0.0), DIAMETRO_ENTRADA_MM / 2.0, z,
                  (0.0, 0.0, 1.0))
            continue
        divisoria = z + dz * (1 - DIVISORIA)
        _peca(pecas, "corpo", f"{rotulo} divisória", (x + 5.0, y + TAMPA_MM, divisoria), (dx - 10.0, dy - 20.0, 3.0))
        mx, my, mz = MEDIDOR_MM
        _peca(pecas, "medidor", f"{rotulo} medidor", (meio - mx / 2.0, y + dy - 15.0 - my,
                                                      divisoria + (z + dz - divisoria - mz) / 2.0), (mx, my, mz))
        jx, jy, jz = DISJUNTOR_UNIDADE_MM
        _peca(pecas, "disjuntor", f"{rotulo} disjuntor", (meio - jx / 2.0, y + dy - 15.0 - jy,
                                                          z + (divisoria - z - jz) / 2.0), (jx, jy, jz))
        _peca(pecas, "etiqueta", f"{rotulo} identificação", (meio - 40.0, y - 1.0, z + dz - 45.0), (80.0, 1.0, 30.0))
        _tubo(pecas, f"{rotulo} eletroduto", (x + dx * 0.3, y + dy, z + (divisoria - z) / 2.0),
              DIAMETRO_SAIDA_MM / 2.0, 100.0, (0.0, 1.0, 0.0))
    return pecas


# --- quantitativos --------------------------------------------------------------------------------

GRUPO = "Busway e medição"


def _linha(item, especificacao, quantidade, unidade="un"):
    return {"item": item, "especificacao": especificacao, "quantidade": quantidade, "unidade": unidade,
            "grupo": GRUPO}


def materiais_do_busway(trechos):
    """Materiais das linhas de busway desenhadas.

    Args:
        trechos: [{'nominal' [A], 'horizontal' [m], 'vertical' [m], 'cotovelos', 'lajes'}], um por linha.
    Returns:
        itens no formato de ``core.quadro.componentes`` (grupo "Busway e medição").
    """
    itens = []
    for t in trechos:
        espec = f"{t['nominal']} A, cobre, IP 54"
        comprimento = float(t.get("horizontal", 0.0)) + float(t.get("vertical", 0.0))
        itens.append(_linha("Busway (barramento blindado)", espec, round(comprimento, 2), "m"))
        itens.append(_linha("Cotovelo de busway", espec, int(t.get("cotovelos", 0))))
        itens.append(_linha("Flange de ligação ao QDC", espec, 1))
        itens.append(_linha("Tampa final de busway", espec, 1))
        emendas = max(0, math.ceil(comprimento / ELEMENTO_RETO_M - 1e-9) - 1) + int(t.get("cotovelos", 0))
        itens.append(_linha("Emenda (junção) de busway", espec, emendas))
        itens.append(_linha("Suporte de busway", f"vão até {VAO_SUPORTE_M:g} m",
                            math.ceil(comprimento / VAO_SUPORTE_M - 1e-9)))
        itens.append(_linha("Barreira corta-fogo", espec, int(t.get("lajes", 0))))
        fitas = math.ceil(float(t.get("horizontal", 0.0)) / 12.0 - 1e-9) + 1  # 7.22.11: a cada 10 a 15 m
        itens.append(_linha("Fita de advertência", "\"Barramento Blindado – Cuidado Risco de Choque\"", fitas))
    return [i for i in itens if i["quantidade"]]


def materiais_das_caixas_mec(tipos):
    """Caixas MEC, plug-ins com disjuntor e placas de comunicação de uma lista de tipos ('MEC IV', ...)."""
    itens, contagem = [], {}
    for tipo in tipos:
        contagem[tipo] = contagem.get(tipo, 0) + 1
    for tipo in MEC:
        if contagem.get(tipo):
            itens.append(_linha("Caixa de medição centralizada", tipo, contagem[tipo]))
    if tipos:
        itens.append(_linha("Plug-in com disjuntor (derivação)", "63 a 400 A", len(tipos)))
        placas = sum(2 if t in ("MEC IX", "MEC XII") else 1 for t in tipos)  # 7.21.2
        itens.append(_linha("Placa de comunicação", "", placas))
    return itens


def materiais_das_colunas(colunas):
    """Materiais das colunas de medição: [{'caixas', 'cdpms': [tipos]}] de cada conjunto inserido."""
    itens, cdpms = [], {}
    caixas = sum(int(c.get("caixas", 0)) for c in colunas)
    for c in colunas:
        for tipo in c.get("cdpms", []):
            cdpms[tipo] = cdpms.get(tipo, 0) + 1
    if caixas:
        itens.append(_linha("Caixa de medição tipo P", "policarbonato, 260 × 520 × 190 mm", caixas))
        itens.append(_linha("Disjuntor da unidade", "bipolar DIN até 100 A", caixas))
    for tipo in CDPM:
        if cdpms.get(tipo):
            itens.append(_linha("CDPM", tipo, cdpms[tipo]))
            barra = "x".join(f"{v:g}" for v in BARRA_CDPM[tipo])
            itens.append(_linha("Barramento de cobre", f"{barra} mm", round(
                cdpms[tipo] * 5 * COMPRIMENTO_BARRA_MM[tipo] / 1000.0, 2), "m"))
    total = sum(cdpms.values())
    if total:
        itens.append(_linha("DPS", "classe II, 3 fases e neutro", total * DPS_POR_CDPM))
    return itens


# --- geometria: busway ------------------------------------------------------------------------------

def secao_busway(nominal):
    """(largura, profundidade) aproximadas do invólucro [mm]."""
    return next((l, p) for limite, l, p in SECAO_BUSWAY_MM if nominal <= limite)


def emendas_e_suportes(comprimento_mm):
    """Posições [mm] das emendas (a cada 3 m) e dos suportes (a cada 1,5 m, fora das emendas)."""
    passo = ELEMENTO_RETO_M * 1000.0
    emendas = [passo * i for i in range(1, math.ceil(comprimento_mm / passo - 1e-9))]
    suportes, s = [], VAO_SUPORTE_M * 1000.0 / 2
    while s < comprimento_mm:
        if all(abs(s - e) > 150.0 for e in emendas):
            suportes.append(s)
        s += VAO_SUPORTE_M * 1000.0
    return emendas, suportes
