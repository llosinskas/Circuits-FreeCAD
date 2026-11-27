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
from freecad.Circuits.core.functions.Predial import gerador as cabos_grandes

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
MAX_COLUNAS_POR_LADO = 6
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
    "chave_vertical": ("Chave seccionadora vertical com fusíveis NH, no QDC", 2200.0),
    "caixa_E": ("Caixa de medição tipo E", 650.0),
    "cdpm_E": ("CDPM das caixas E (300 × 500 mm)", 900.0),
    "indireta_IND300": ("Conjunto de medição indireta até 300 A (policarbonato)", 4800.0),
    "indireta_IND600": ("Conjunto de medição indireta em caixa M (300 a 600 A)", 7600.0),
    "caixa_K": ("Caixa de medição coletiva K (2 medições)", 1900.0),
    "caixa_L": ("Caixa de medição coletiva L (4 medições)", 2700.0),
    "caixa_H": ("Caixa de medição coletiva H (6 medições)", 3500.0),
    "caixa_M": ("Caixa de medição coletiva M (8 medições)", 4300.0),
    "caixa_N": ("Caixa de medição coletiva N (12 medições)", 5800.0),
    "caixa_O": ("Caixa de medição coletiva O (16 medições)", 8200.0),
    "caixa_barramentos": ("Caixa de barramentos com CDPI", 1800.0),
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


def capacidade_agrupamento(por_coluna=MAX_VERTICAL):
    """Caixas P que cabem num agrupamento com ``por_coluna`` caixas sobrepostas (até 6 colunas por lado, máx. 30)."""
    por_coluna = max(1, min(MAX_VERTICAL, int(por_coluna)))
    return min(MAX_POR_AGRUPAMENTO, 2 * MAX_COLUNAS_POR_LADO * por_coluna)


def distribuicao(caixas, por_coluna=MAX_VERTICAL):
    """(caixas à esquerda, à direita, caixas na vertical) de um agrupamento.

    Com 3 por coluna, 30 caixas ficam em 10 colunas de 3, 5 de cada lado da CDPM.
    """
    por_coluna = max(1, min(MAX_VERTICAL, int(por_coluna)))
    if caixas > capacidade_agrupamento(por_coluna):
        raise ValueError(f"Um agrupamento com {por_coluna} caixa(s) por coluna tem no máximo "
                         f"{capacidade_agrupamento(por_coluna)} caixas.")
    vertical = min(por_coluna, max(1, math.ceil(caixas / 2)))
    esquerda = math.ceil(caixas / 2)
    return esquerda, caixas - esquerda, vertical


def largura_agrupamento(caixas, cdpm, por_coluna=MAX_VERTICAL):
    esquerda, direita, vertical = distribuicao(caixas, por_coluna)
    colunas = math.ceil(esquerda / vertical) + math.ceil(direita / vertical)
    return colunas * CAIXA_P_MM[0] + CDPM[cdpm][2]


def agrupamentos(caixas, corrente_por_caixa, por_coluna=MAX_VERTICAL, cdpm=None):
    """Agrupamentos de caixas P: [{'modelo': 'P', 'caixas', 'corrente', 'cdpm', 'largura_mm'}].

    Reparte as caixas igualmente no menor número de agrupamentos em que todos cabem
    (``capacidade_agrupamento`` e a corrente da CDPM). ``cdpm`` força o tipo, se couber.
    """
    if caixas <= 0:
        return []
    capacidade = capacidade_agrupamento(por_coluna)
    for quantidade in range(max(1, math.ceil(caixas / capacidade)), caixas + 1):
        divisao = [caixas // quantidade + (1 if i < caixas % quantidade else 0) for i in range(quantidade)]
        grupos = []
        for n in divisao:
            corrente = n * corrente_por_caixa
            tipo = tipo_cdpm(n, corrente)
            if cdpm in CDPM and tipo is not None and n <= CDPM[cdpm][0] and corrente <= CDPM[cdpm][1] + 1e-9:
                tipo = cdpm
            if tipo is None:
                break
            grupos.append({"modelo": "P", "caixas": n, "corrente": corrente, "cdpm": tipo,
                           "largura_mm": largura_agrupamento(n, tipo, por_coluna)})
        else:
            return grupos
    raise ValueError(f"Caixa P com {corrente_por_caixa:.0f} A não cabe em nenhuma CDPM (máximo 300 A).")


# --- caixas metálicas coletivas da Enel SP (Tabela 22, Desenhos 24 a 29) -------------------------------

# modelo -> (medições, largura, altura, colunas de medidores, linhas, altura da base ao piso [mm])
CAIXAS_METALICAS = {
    "K": (2, 600.0, 500.0, 2, 1, 1200.0),
    "L": (4, 600.0, 900.0, 2, 2, 750.0),
    "H": (6, 600.0, 1300.0, 2, 3, 575.0),
    "M": (8, 1200.0, 900.0, 4, 2, 750.0),
    "N": (12, 1200.0, 1300.0, 4, 3, 550.0),
    "O": (16, 1200.0, 2100.0, 4, 4, 175.0),
}
PROFUNDIDADE_METALICA_MM = 250.0
CORRENTE_MAX_COLETIVA = 300.0  # por caixa coletiva: ramal único de até 240 mm² PVC / 185 mm² EPR (nota 5)
ALTURA_CAIXA_BARRAMENTOS_MM = 300.0  # Desenho 32 (aproximada); a O já traz os barramentos embaixo
ALTURA_CDPI_MM = 250.0  # caixa dos disjuntores das unidades em cima (Desenho 20); a O já traz a CDPI
# Caixa E (Desenho 22): 1 medição bi ou trifásica até 100 A, aço ou policarbonato; medidor em cima
# (390 mm) e disjuntor e DPS embaixo; até 4 caixas com uma CDPM de 300 x 500 x 250 mm (7.19.2), com
# proteção geral até 125 A e ramal de até 50 mm².
CAIXA_E_MM = (350.0, 250.0, 560.0)  # largura, profundidade, altura
COMPARTIMENTO_MEDIDOR_E_MM = 390.0
ALTURA_BASE_E_MM = 1200.0  # 1100 a 1300 mm
CDPM_E_MM = (300.0, 250.0, 500.0)
MAX_CAIXAS_E = 4
CORRENTE_MAX_CDPM_E = 125.0
SECAO_MAX_RAMAL_E = 50

# Medição indireta (7.17.2, só Enel SP): TCs, bloco de aferição e medidor da Enel; chave seccionadora
# sob carga sem fusíveis antes dos TCs; condutores de 2,5 mm² do TC ao medidor (o cliente deixa).
# modelo -> (corrente máxima [A], rótulo, largura, altura, profundidade, base [mm])
INDIRETAS = {
    "IND300": (300.0, "Indireta em policarbonato (Tabela 27, 8.34)", 1300.0, 1120.0, 240.0, 550.0),
    "IND600": (600.0, "Indireta em caixa M (nota 7)", 1200.0, 900.0, 250.0, 750.0),
}
MODULO_INDIRETA_MM = (370.0, 560.0, 370.0)  # larguras dos módulos de baixo do 8.34; em cima, só o do meio
CHAVES_SECCIONADORAS = [125, 160, 250, 400, 630]
DISJUNTORES_GERAL_INDIRETA = [125, 150, 160, 175, 200, 225, 250, 300, 350, 400, 500, 630]
TCS = [150, 200, 300, 400, 600, 800]  # corrente primária dos TCs [A] (escolha da Enel; referência)

MODELOS = (["Automático", "P (policarbonato)", "Caixa E"] + [f"Caixa {m}" for m in CAIXAS_METALICAS]
           + ["Indireta"])
DISJUNTORES_UNIDADE = [32, 40, 50, 63, 70, 80, 90, 100]
DISJUNTORES_GERAL = [40, 50, 63, 70, 80, 100, 125, 150, 160, 175, 200, 225, 250, 300]
# Tabela 23: barra de cobre pintada (largura x espessura [mm]) -> corrente [A]
BARRAS = [((15, 3), 187), ((20, 3), 237), ((25, 3), 287), ((20, 5), 319), ((30, 3), 337), ((25, 5), 384),
          ((40, 3), 435), ((30, 5), 447), ((20, 10), 497), ((40, 5), 573), ((30, 10), 676), ((40, 10), 850)]
COMPRIMENTO_RAMAL_DISTRIBUICAO_M = 10.0  # do QDC ao agrupamento, padrão


def caixas_metalicas(medicoes, corrente_por_medicao, modelo=None):
    """Caixas coletivas metálicas: [{'modelo', 'medicoes', 'corrente', 'largura_mm'}].

    Menor número de caixas em que todas cabem (medições e ``CORRENTE_MAX_COLETIVA``),
    cada uma do menor modelo que comporta a parte dela; ``modelo`` força K a O.
    """
    if medicoes <= 0:
        return []
    modelos = [modelo] if modelo in CAIXAS_METALICAS else list(CAIXAS_METALICAS)
    for quantidade in range(1, medicoes + 1):
        divisao = [medicoes // quantidade + (1 if i < medicoes % quantidade else 0) for i in range(quantidade)]
        caixas = []
        for n in divisao:
            corrente = n * corrente_por_medicao
            escolhido = next((m for m in modelos if n <= CAIXAS_METALICAS[m][0]), None)
            if escolhido is None or corrente > CORRENTE_MAX_COLETIVA + 1e-9:
                break
            caixas.append({"modelo": escolhido, "medicoes": n, "caixas": n, "corrente": corrente,
                           "cdpm": f"Caixa {escolhido}", "largura_mm": CAIXAS_METALICAS[escolhido][1]})
        else:
            return caixas
    raise ValueError(f"Medição de {corrente_por_medicao:.0f} A não cabe numa caixa coletiva (máximo "
                     f"{CORRENTE_MAX_COLETIVA:.0f} A por caixa).")


def barramento(corrente, minimo=None):
    """Menor barra de cobre pintada da Tabela 23 que conduz a corrente, não menor que ``minimo`` (mm × mm)."""
    area_minima = minimo[0] * minimo[1] if minimo else 0
    for (largura, espessura), amperes in BARRAS:
        if amperes >= corrente - 1e-9 and largura * espessura >= area_minima:
            return f"{largura}x{espessura} mm"
    return None


QUEDA_RAMAL_DISTRIBUICAO = 1.0  # % do QDC ao conjunto de medição (escolha do projeto)


def ramal_de_distribuicao(corrente, comprimento, tensao, paralelos=1):
    """Seção [mm²] do ramal de distribuição principal (3 fases e neutro, EPR, método B1) que conduz a
    corrente e fica na queda ``QUEDA_RAMAL_DISTRIBUICAO``; com ``paralelos`` circuitos iguais (fator de
    agrupamento da NBR 5410), cada um leva a parte dele. None se nem 300 mm² atende."""
    parte = corrente / paralelos
    fator = nbr5410.fca(paralelos) if paralelos > 1 else 1.0
    for secao in cabos_grandes.SECOES:
        if cabos_grandes.capacidade(secao, "B1", "EPR") * fator < parte - 1e-9:
            continue
        if nbr5410.queda_tensao(parte, comprimento, secao, tensao, 3,
                                fator_potencia=FATOR_POTENCIA) <= QUEDA_RAMAL_DISTRIBUICAO + 1e-9:
            return secao
    return None


def grupos_e(medicoes, corrente_por_medicao):
    """Grupos de caixas E com CDPM: [{'modelo': 'E', 'medicoes', 'caixas', 'corrente', 'cdpm', 'largura_mm'}].

    Até ``MAX_CAIXAS_E`` caixas e ``CORRENTE_MAX_CDPM_E`` por CDPM; uma caixa sozinha dispensa a CDPM.
    """
    if medicoes <= 0:
        return []
    for quantidade in range(max(1, math.ceil(medicoes / MAX_CAIXAS_E)), medicoes + 1):
        divisao = [medicoes // quantidade + (1 if i < medicoes % quantidade else 0) for i in range(quantidade)]
        if all(n * corrente_por_medicao <= CORRENTE_MAX_CDPM_E + 1e-9 or n == 1 for n in divisao):
            return [{"modelo": "E", "medicoes": n, "caixas": n, "corrente": n * corrente_por_medicao,
                     "cdpm": "Caixas E" if n == 1 else "Caixas E com CDPM",
                     "largura_mm": n * CAIXA_E_MM[0] + (CDPM_E_MM[0] if n > 1 else 0.0)} for n in divisao]
    return []


def medicao_indireta(demanda_a, tensao=220.0, comprimento_ramal=COMPRIMENTO_RAMAL_DISTRIBUICAO_M):
    """Conjunto de medição indireta de uma unidade (7.17.2), ou None acima de 600 A (TCs na cabine).

    Até 300 A, o agrupamento de policarbonato do 8.34 (chave seccionadora, caixa dos TCs, proteção
    geral e, em cima, medidor e bloco de aferição); de 300 a 600 A, a caixa M (nota 7), com dois
    circuitos de entrada (nota 8).
    """
    modelo = next((m for m, dados in INDIRETAS.items() if demanda_a <= dados[0] + 1e-9), None)
    if modelo is None:
        return None
    paralelos = 2 if modelo == "IND600" else 1
    largura = INDIRETAS[modelo][2]
    disjuntor = comercial(DISJUNTORES_GERAL_INDIRETA, demanda_a)
    secao = ramal_de_distribuicao(disjuntor, comprimento_ramal, tensao, paralelos)
    return {"modelo": modelo, "medicoes": 1, "caixas": 1, "corrente": float(demanda_a),
            "cdpm": INDIRETAS[modelo][1], "largura_mm": largura, "disjuntor_geral": disjuntor,
            "chave": comercial(CHAVES_SECCIONADORAS, disjuntor), "tc": f"{comercial(TCS, demanda_a)}/5 A",
            "barramento": None, "ramal": secao, "paralelos": paralelos}


def escolher_modelo(demanda_a, fases, modelo="Automático", medidores=1):
    """'P', 'E', um modelo de ``CAIXAS_METALICAS`` ou 'indireta', com os avisos da escolha.

    Automático: acima de 100 A, indireta; mono e bifásicas, caixa P; trifásicas, caixas E (até 4
    medições e 125 A na CDPM) ou, acima disso, caixas coletivas metálicas.
    """
    avisos = []
    if demanda_a > CORRENTE_MAX_P or modelo == "Indireta":
        if demanda_a <= CORRENTE_MAX_P:
            avisos.append(f"{demanda_a:.0f} A cabe na medição direta (até {CORRENTE_MAX_P:.0f} A); a indireta foi "
                          "escolhida à mão")
        elif demanda_a <= 200.0:
            avisos.append("de 101 a 200 A a Enel admite medição direta com cabo até 95 mm² (7.17.1, nota)")
        return "indireta", avisos
    if modelo.startswith("Caixa "):
        escolhido = modelo.split()[1]
        if escolhido == "E" and fases == 1:
            avisos.append("a caixa E é para unidades bi e trifásicas (Tabela 22, nota 2)")
        return escolhido, avisos
    if modelo.startswith("P"):
        if fases == 3:
            avisos.append("a caixa P é só para unidades mono e bifásicas (Tabela 22, nota 2)")
        return "P", avisos
    if fases <= 2:
        return "P", avisos
    if medidores <= MAX_CAIXAS_E and medidores * demanda_a <= CORRENTE_MAX_CDPM_E + 1e-9:
        return "E", avisos
    return "N", avisos


def dimensionar_colunas(medidores, demanda_a=63.0, fases=2, por_coluna=MAX_VERTICAL, modelo="Automático",
                        cdpm=None, demanda_total_a=0.0, tensao=220.0,
                        comprimento_ramal=COMPRIMENTO_RAMAL_DISTRIBUICAO_M):
    """Dimensiona o centro de medição convencional de medição direta.

    Escolhe a caixa (P em agrupamento modular para mono e bifásicas até 100 A; caixas
    metálicas K a O para trifásicas; medição indireta acima de 100 A), reparte as
    medições em conjuntos e dimensiona, em cada um, o disjuntor geral, o barramento
    (Tabela 23, com o mínimo da Tabela 28 na CDPM) e o ramal de distribuição principal
    (NBR 5410, 3 fases e neutro; até 185 mm² no agrupamento de caixas P, 240 mm² nas
    metálicas), além do disjuntor de cada unidade.

    Args:
        medidores: medições diretas. demanda_a: demanda de cada unidade [A].
        por_coluna: caixas P sobrepostas (1 a 3; Tabela 29).
        modelo: de ``MODELOS``. cdpm: força o tipo de CDPM (Tabela 28).
        demanda_total_a: demanda do conjunto todo [A] (0 = soma das unidades).
    Returns:
        {'modelo' ('P', 'metalica' ou None), 'conjuntos', 'corrente', 'disjuntor_unidade', 'por_coluna', 'avisos'}.
    """
    medidores, fases = int(medidores), int(fases)
    escolhido, avisos = escolher_modelo(float(demanda_a), fases, modelo, medidores)
    total = float(demanda_total_a) if demanda_total_a else medidores * float(demanda_a)
    resultado = {"modelo": None, "conjuntos": [], "corrente": total, "por_coluna": int(por_coluna),
                 "disjuntor_unidade": comercial(DISJUNTORES_UNIDADE, float(demanda_a)), "avisos": avisos}
    if medidores <= 0:
        return resultado
    if escolhido == "indireta":
        conjunto = medicao_indireta(float(demanda_a), tensao, comprimento_ramal)
        resultado["disjuntor_unidade"] = None
        if conjunto is None:
            avisos.append(f"{float(demanda_a):.0f} A passa dos 600 A da caixa M: TCs na cabine de barramentos e "
                          "medidor na caixa A4 ou conforme a Enel (7.17.2)")
            return resultado
        resultado["modelo"] = "indireta"
        resultado["conjuntos"] = [dict(conjunto) for _ in range(medidores)]
        if conjunto["ramal"] is None:
            avisos.append(f"{conjunto['cdpm']}: ramal de distribuição acima de 300 mm²")
        avisos.append("medição indireta: TCs, bloco de aferição e medidor fornecidos pela Enel; chave seccionadora "
                      "sob carga sem fusíveis antes dos TCs e condutores de 2,5 mm² do TC ao medidor (7.17.2)")
        return resultado
    por_medidor = total / medidores
    if escolhido == "P":
        conjuntos = agrupamentos(medidores, por_medidor, por_coluna, cdpm)
        resultado["modelo"], limite = "P", 185
    elif escolhido == "E":
        conjuntos = grupos_e(medidores, por_medidor)
        resultado["modelo"], limite = "E", SECAO_MAX_RAMAL_E
        if len(conjuntos) > 1:
            avisos.append(f"{len(conjuntos)} grupos de caixas E: preveja QDC ou caixa de barramentos para eles")
    else:
        conjuntos = caixas_metalicas(medidores, por_medidor, None if modelo == "Automático" else escolhido)
        resultado["modelo"], limite = "metalica", 240
    for c in conjuntos:
        c["disjuntor_geral"] = comercial(DISJUNTORES_GERAL, c["corrente"])
        minimo = BARRA_CDPM.get(c["cdpm"]) if escolhido == "P" else None
        c["barramento"] = barramento(c["disjuntor_geral"] or c["corrente"], minimo)
        c["ramal"] = ramal_de_distribuicao(c["disjuntor_geral"] or c["corrente"], comprimento_ramal, tensao)
        if c["ramal"] is None or c["ramal"] > limite:
            avisos.append(f"{c['cdpm']}: ramal de distribuição acima de {limite} mm²; divida o conjunto")
    if len(conjuntos) > 1 and escolhido == "P":
        avisos.append(f"{len(conjuntos)} agrupamentos: centro de medição abrigado em alvenaria obrigatório")
    if escolhido not in ("P", "E") and (len(conjuntos) > 1 or medidores > 4):
        avisos.append("caixa de barramentos obrigatória sob as caixas coletivas (7.19.4)")
    resultado["conjuntos"] = conjuntos
    return resultado


def _cabo_da_unidade(demanda_a, fases, comprimento, tensao):
    n_fases = 3 if fases == 3 else 1
    tensao_circuito = tensao if fases >= 2 else tensao / math.sqrt(3)
    if demanda_a > nbr5410.DISJUNTORES[-1]:  # unidade grande (medição indireta): cabos de 16 a 300 mm²
        disjuntor = comercial(DISJUNTORES_GERAL_INDIRETA, demanda_a) or demanda_a
        for secao in cabos_grandes.SECOES:
            if cabos_grandes.capacidade(secao, "B1", "EPR") < disjuntor - 1e-9:
                continue
            queda_unidade = nbr5410.queda_tensao(demanda_a, comprimento, secao, tensao_circuito, n_fases,
                                                 fator_potencia=FATOR_POTENCIA)
            if queda_unidade <= QUEDA_ALIMENTADOR_UNIDADE + 1e-9:
                return secao, {"queda": round(queda_unidade, 2), "disjuntor": disjuntor}
        raise ValueError(f"nenhum cabo até 300 mm² atende {demanda_a:.0f} A em {comprimento:.0f} m")
    resultado = nbr5410.dimensionar_circuito(demanda_a, "TUE", comprimento, tensao_circuito, n_fases,
                                             queda_max=QUEDA_ALIMENTADOR_UNIDADE, fator_potencia=FATOR_POTENCIA)
    return max(SECAO_MIN_UNIDADE, resultado["secao"]), resultado


# profundidade da caixa e largura da folha da porta aberta a 90° [mm], por modelo de conjunto
PORTA_E_FUNDO = {"P": (CAIXA_P_MM[1], CAIXA_P_MM[0]), "E": (CAIXA_E_MM[1], CAIXA_E_MM[0]),
                 "IND300": (240.0, 560.0), "IND600": (250.0, 600.0)}


def _conjuntos(lista, total, tensao):
    """Conjuntos de medição das unidades da ``lista`` com a corrente ``total`` repartida pelo peso delas.

    As diretas (até 100 A) vão juntas para ``dimensionar_colunas``; cada andar com unidades acima
    de 100 A ganha os conjuntos indiretos dele.

    Returns:
        (conjuntos, modelo das diretas, disjuntor das unidades diretas, avisos).
    """
    avisos, conjuntos = [], []
    diretas = [a for a in lista if a["demanda_a"] <= CORRENTE_MAX_P]
    soma = sum(a["unidades"] * a["demanda_a"] for a in lista) or 1.0
    modelo, disjuntor = None, None
    if diretas:
        corrente_diretas = total * sum(a["unidades"] * a["demanda_a"] for a in diretas) / soma
        colunas = dimensionar_colunas(sum(a["unidades"] for a in diretas), max(a["demanda_a"] for a in diretas),
                                      max(a["fases"] for a in diretas), demanda_total_a=corrente_diretas,
                                      tensao=tensao)
        conjuntos += colunas["conjuntos"]
        avisos += colunas["avisos"]
        modelo, disjuntor = colunas["modelo"], colunas["disjuntor_unidade"]
    for a in lista:
        if a["demanda_a"] > CORRENTE_MAX_P:
            indireta = dimensionar_colunas(a["unidades"], a["demanda_a"], a["fases"], tensao=tensao)
            conjuntos += indireta["conjuntos"]
            avisos += [f"{a['nome']}: {texto}" for texto in indireta["avisos"]]
    return conjuntos, modelo, disjuntor, avisos


def abrigo_do_centro(conjuntos):
    """Dimensões do centro de medição abrigado [m, m²]: os conjuntos numa parede, a porta aberta e a circulação."""
    comprimento_mm = (sum(g["largura_mm"] for g in conjuntos) + FOLGA_ENTRE_AGRUPAMENTOS_MM * max(0, len(conjuntos) - 1)
                      + 2 * MARGEM_LATERAL_MM)
    fundos = [PORTA_E_FUNDO.get(g.get("modelo", "P"), (PROFUNDIDADE_METALICA_MM, 600.0)) for g in conjuntos] or \
        [PORTA_E_FUNDO["P"]]
    profundidade_mm = max(f + p for f, p in fundos) + max(FOLGA_PORTA_ABERTA_MM, CIRCULACAO_MM)
    return {"comprimento": comprimento_mm / 1000.0, "profundidade": profundidade_mm / 1000.0,
            "area": comprimento_mm * profundidade_mm / 1e6}


def _alimentadores(lista, cota_centro, horizontal, tensao, comprimento_no_andar):
    """Alimentador de cada unidade, do centro de medição (na ``cota_centro``) ao quadro dela."""
    avisos, alimentadores, cabo, eletroduto = [], [], 0.0, 0.0
    for a in lista:
        comprimento = horizontal + abs(a["cota"] - cota_centro) + comprimento_no_andar
        try:
            secao, calculo = _cabo_da_unidade(a["demanda_a"], a["fases"], comprimento, tensao)
        except ValueError as erro:
            raise ValueError(f"{a['nome']}: {erro}") from erro
        if secao > SECAO_MAX_UNIDADE and a["demanda_a"] <= CORRENTE_MAX_P:
            avisos.append(f"{a['nome']}: alimentador de {secao} mm² acima dos {SECAO_MAX_UNIDADE} mm² do borne do "
                          "medidor")
        condutores = a["fases"] + 1  # fases e neutro
        secao_pe = nbr5410.secao_protecao(secao)
        cabo += a["unidades"] * comprimento * (condutores * secao + secao_pe)
        eletroduto += a["unidades"] * comprimento
        alimentadores.append({"andar": a["nome"], "unidades": a["unidades"], "secao": secao, "pe": secao_pe,
                              "condutores": condutores, "comprimento": comprimento, "queda": calculo["queda"],
                              "disjuntor": calculo["disjuntor"]})
    return alimentadores, cabo, eletroduto, avisos


def convencional(andares, tensao=220.0, distancia_horizontal=15.0, demanda_total_a=0.0,
                 comprimento_no_andar=COMPRIMENTO_NO_ANDAR_M):
    """Medição agrupada num único centro de medição, no piso de cota 0 (o térreo).

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
    total = sum(corrente_dos_andares(lista, demanda_total_a))
    grupos, modelo, disjuntor, avisos = _conjuntos(lista, total, tensao)
    alimentadores, cabo, eletroduto, mais = _alimentadores(lista, 0.0, distancia_horizontal, tensao,
                                                           comprimento_no_andar)
    qdc, circuitos, _ = entrada(total)
    return {"solucao": "convencional", "agrupamentos": grupos, "modelo": modelo,
            "caixas": sum(a["unidades"] for a in lista), "corrente": total, "disjuntor_unidade": disjuntor,
            "abrigo": abrigo_do_centro(grupos), "alimentadores": alimentadores, "cabo_mm2_m": cabo,
            "eletroduto_m": eletroduto, "qdc": qdc, "ramal": circuitos, "avisos": avisos + mais}


# --- medição descentralizada: um centro de medição a cada grupo de andares ---------------------------

ANDARES_POR_CENTRO = 4
DISTANCIA_CENTRO_INDEPENDENTE_M = 15.0  # 7.18.2: acima disso, QDC ou CPG no centro e chave na entrada
CHAVES_VERTICAIS = [160, 250, 400, 630]  # chaves seccionadoras verticais com fusíveis NH no QDC (Tabela 46)
MAX_PARALELOS_RAMAL = 4


def grupos_de_andares(lista, andares_por_centro=ANDARES_POR_CENTRO):
    """Andares com unidades, de baixo para cima, em grupos seguidos de até ``andares_por_centro``."""
    n = max(1, int(andares_por_centro))
    ordenados = sorted(lista, key=lambda a: a["cota"])
    return [ordenados[i:i + n] for i in range(0, len(ordenados), n)]


def descentralizado(andares, tensao=220.0, distancia_horizontal=15.0, demanda_total_a=0.0,
                    andares_por_centro=ANDARES_POR_CENTRO, comprimento_no_andar=COMPRIMENTO_NO_ANDAR_M):
    """Medição convencional descentralizada: um centro (quadro) de medição a cada grupo de andares.

    Cada centro fica no andar de baixo do grupo e é alimentado do QDC da entrada por um ramal de
    distribuição próprio (3 fases e neutro, com circuitos em paralelo se preciso), protegido por
    uma chave seccionadora vertical com fusíveis no QDC. Se o ramal passa de 15 m, o centro é
    independente (7.18.2): leva QDC ou CPG próprio para receber o ramal. Os alimentadores das
    unidades vão só do centro ao andar delas.

    Returns:
        dict com ``centros`` (cada um: ``andares``, ``andar`` e ``cota`` do centro, ``unidades``,
        ``corrente``, ``conjuntos``, ``abrigo``, ``alimentadores``, ``ramal`` {seção, paralelos,
        comprimento}, ``chave``, ``qdc_local``), ``cabo_mm2_m``, ``eletroduto_m``,
        ``ramais_mm2_m``, ``qdc``, ``ramal``, ``corrente``, ``caixas`` e ``avisos``.
    """
    lista = _com_unidades(andares)
    if not lista:
        raise ValueError("Nenhum andar com unidades.")
    correntes = dict(zip((id(a) for a in lista), corrente_dos_andares(lista, demanda_total_a)))
    total = sum(correntes.values())
    avisos, centros = [], []
    cabo = eletroduto = ramais = 0.0
    for numero, grupo in enumerate(grupos_de_andares(lista, andares_por_centro), start=1):
        base = grupo[0]
        corrente = sum(correntes[id(a)] for a in grupo)
        conjuntos, _, _, mais = _conjuntos(grupo, corrente, tensao)
        avisos += [f"Centro {numero}: {texto}" for texto in mais]
        alimentadores, c, e, mais = _alimentadores(grupo, base["cota"], 0.0, tensao, comprimento_no_andar)
        avisos += [f"Centro {numero}: {texto}" for texto in mais]
        comprimento = distancia_horizontal + abs(base["cota"])
        chave = comercial(CHAVES_VERTICAIS, corrente)
        protecao = chave or comercial(DISJUNTORES_GERAL_INDIRETA, corrente) or corrente
        secao, paralelos = None, 1
        for paralelos in range(1, MAX_PARALELOS_RAMAL + 1):
            secao = ramal_de_distribuicao(protecao, comprimento, tensao, paralelos)
            if secao is not None:
                break
        if secao is None:
            avisos.append(f"Centro {numero}: nenhum ramal de até {MAX_PARALELOS_RAMAL} × 300 mm² atende "
                          f"{corrente:.0f} A; use menos andares por centro")
        if chave is None:
            avisos.append(f"Centro {numero}: {corrente:.0f} A passa da maior chave vertical ({CHAVES_VERTICAIS[-1]} A): "
                          "use disjuntor na cabine de barramentos")
        independente = comprimento > DISTANCIA_CENTRO_INDEPENDENTE_M
        qdc_local = entrada(corrente)[0] if independente else None
        cabo += c
        eletroduto += e + comprimento * paralelos
        ramais += 4 * (secao or 0) * paralelos * comprimento + nbr5410.secao_protecao(secao or 16) * comprimento
        centros.append({"numero": numero, "andares": [a["nome"] for a in grupo], "andar": base["nome"],
                        "cota": base["cota"], "unidades": sum(a["unidades"] for a in grupo), "corrente": corrente,
                        "conjuntos": conjuntos, "abrigo": abrigo_do_centro(conjuntos),
                        "alimentadores": alimentadores, "chave": chave, "qdc_local": qdc_local,
                        "ramal": {"secao": secao, "paralelos": paralelos, "comprimento": comprimento}})
    qdc, circuitos, _ = entrada(total)
    if len(centros) > 1:
        avisos.append(f"{len(centros)} centros de medição: cada um com chave vertical e fusíveis no QDC da entrada "
                      "(7.18.2); confirme com a Enel a medição fora do térreo")
    return {"solucao": "descentralizado", "centros": centros, "corrente": total,
            "caixas": sum(a["unidades"] for a in lista), "cabo_mm2_m": cabo, "eletroduto_m": eletroduto,
            "ramais_mm2_m": ramais, "qdc": qdc, "ramal": circuitos, "avisos": avisos}


# --- geração no desenho ----------------------------------------------------------------------------

SOLUCOES_DESENHAVEIS = ("convencional", "descentralizado")


def _valores_das_colunas(grupo, correntes, tensao):
    """Entradas dos objetos de colunas de medição de um grupo de andares: as diretas juntas e um
    objeto indireto por andar com unidades acima de 100 A."""
    objetos = []
    diretas = [a for a in grupo if a["demanda_a"] <= CORRENTE_MAX_P]
    if diretas:
        objetos.append(("diretas", {"Medidores": sum(a["unidades"] for a in diretas),
                                    "DemandaPorMedidor": max(a["demanda_a"] for a in diretas),
                                    "Fases": max(a["fases"] for a in diretas),
                                    "DemandaTotal": round(sum(correntes[id(a)] for a in diretas), 1),
                                    "Tensao": float(tensao)}))
    for a in grupo:
        if a["demanda_a"] > CORRENTE_MAX_P:
            objetos.append((f"indireta {a['nome']}", {"Medidores": a["unidades"], "DemandaPorMedidor": a["demanda_a"],
                                                      "Fases": a["fases"], "Modelo": "Indireta",
                                                      "Tensao": float(tensao)}))
    return objetos


def _largura(conjuntos):
    return sum(g["largura_mm"] for g in conjuntos) + FOLGA_ENTRE_AGRUPAMENTOS_MM * max(0, len(conjuntos) - 1)


def plano_de_geracao(andares, solucao="convencional", tensao=220.0, distancia_horizontal=15.0,
                     demanda_total_a=0.0, andares_por_centro=ANDARES_POR_CENTRO):
    """O que desenhar para a solução: um item por centro de medição.

    Returns:
        [{'numero', 'andar' (onde fica), 'cota' [m], 'andares' atendidos, 'objetos': [{'chave', 'valores'
          (entradas do objeto ``ColunaMedicao``), 'x' (meio dele em relação ao meio do centro) [mm]}],
          'abrigo' {'largura', 'profundidade', 'y0' [mm], 'area' [m²]}, 'ramal' (só no descentralizado)}].
        As caixas têm a frente em y = 0 e o fundo para +y; o abrigo vai de ``y0`` ao fundo.
    """
    if solucao not in SOLUCOES_DESENHAVEIS:
        raise ValueError("Só a medição agrupada e a descentralizada são desenhadas aqui; o busway é desenhado "
                         "pelo botão Busway, a partir do caminho do QDC ao shaft.")
    lista = _com_unidades(andares)
    if not lista:
        raise ValueError("Nenhum andar com unidades.")
    correntes = dict(zip((id(a) for a in lista), corrente_dos_andares(lista, demanda_total_a)))
    if solucao == "convencional":
        grupos, ramais = [sorted(lista, key=lambda a: a["cota"])], [None]
        cotas = [0.0]
    else:
        grupos = grupos_de_andares(lista, andares_por_centro)
        resultado = descentralizado(andares, tensao, distancia_horizontal, demanda_total_a, andares_por_centro)
        ramais = [dict(c["ramal"], chave=c["chave"], qdc_local=c["qdc_local"], corrente=c["corrente"])
                  for c in resultado["centros"]]
        cotas = [g[0]["cota"] for g in grupos]
    centros = []
    for numero, (grupo, ramal, cota) in enumerate(zip(grupos, ramais, cotas), start=1):
        objetos, todos = [], []
        for chave, valores in _valores_das_colunas(grupo, correntes, tensao):
            dados = dimensionar_colunas(valores["Medidores"], valores["DemandaPorMedidor"], valores["Fases"],
                                        modelo=valores.get("Modelo", "Automático"),
                                        demanda_total_a=valores.get("DemandaTotal", 0.0), tensao=tensao)
            objetos.append({"chave": chave, "valores": valores, "largura": _largura(dados["conjuntos"])})
            todos += dados["conjuntos"]
        total = sum(o["largura"] for o in objetos) + FOLGA_ENTRE_AGRUPAMENTOS_MM * max(0, len(objetos) - 1)
        x = -total / 2.0
        for o in objetos:
            o["x"] = x + o["largura"] / 2.0
            x += o["largura"] + FOLGA_ENTRE_AGRUPAMENTOS_MM
        abrigo = abrigo_do_centro(todos)
        fundo = max([PORTA_E_FUNDO.get(g.get("modelo", "P"), (PROFUNDIDADE_METALICA_MM, 0.0))[0] for g in todos]
                    or [CAIXA_P_MM[1]])
        centros.append({"numero": numero, "andar": grupo[0]["nome"] if solucao == "descentralizado" else None,
                        "cota": cota, "andares": [a["nome"] for a in grupo], "objetos": objetos, "ramal": ramal,
                        "abrigo": {"largura": abrigo["comprimento"] * 1000.0,
                                   "profundidade": abrigo["profundidade"] * 1000.0,
                                   "y0": fundo - abrigo["profundidade"] * 1000.0, "fundo": fundo,
                                   "area": abrigo["area"]}})
    return centros


# --- busway -------------------------------------------------------------------------------------

def caixas_mec(unidades, corrente, demanda_unidade=0.0):
    """Caixas MEC de um andar: [{'tipo', 'medicoes', 'corrente', 'disjuntor', 'indireta'}] (Tabela 30).

    Unidades acima de 100 A têm medição indireta, uma por caixa (7.21.2): MEC IV até 160 A e
    MEC VI de 160 a 300 A; acima de 300 A, consultar a Enel (MEC XII ou XVI com área própria).
    """
    if unidades <= 0:
        return []
    if demanda_unidade > CORRENTE_MAX_P:
        tipo = "MEC IV" if demanda_unidade <= 160.0 else "MEC VI" if demanda_unidade <= 300.0 else "MEC XII"
        return [{"tipo": tipo, "medicoes": 1, "corrente": corrente / unidades, "indireta": True,
                 "disjuntor": comercial(DISJUNTORES_MEC, max(63.0, demanda_unidade))} for _ in range(unidades)]
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
                          "caixas": caixas_mec(a["unidades"], corrente, a["demanda_a"])})

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


def _itens_dos_conjuntos(itens, precos, conjuntos):
    for g in conjuntos:
        if g.get("modelo", "P") == "P":
            _item(itens, precos, "caixa_p", g["caixas"])
            _item(itens, precos, f"cdpm_{g['cdpm']}", 1)
        elif g["modelo"] == "E":
            _item(itens, precos, "caixa_E", g["caixas"])
            if g["caixas"] > 1:
                _item(itens, precos, "cdpm_E", 1)
        elif g["modelo"] in INDIRETAS:
            _item(itens, precos, f"indireta_{g['modelo']}", 1)
        else:
            _item(itens, precos, f"caixa_{g['modelo']}", 1)
            if g["modelo"] != "O":
                _item(itens, precos, "caixa_barramentos", 1)


def orcamento(resultado, precos=None):
    """Estimativa de custo da solução: {'itens', 'material', 'mao_de_obra', 'total'} [R$]."""
    precos = dict(precos_padrao(), **(precos or {}))
    itens = []
    if resultado["solucao"] == "convencional":
        _itens_dos_conjuntos(itens, precos, resultado["agrupamentos"])
        _item(itens, precos, "cabo_mm2_m", round(resultado["cabo_mm2_m"]), "mm²·m")
        _item(itens, precos, "eletroduto_m", round(resultado["eletroduto_m"], 1), "m")
        _item(itens, precos, "abrigo_m2", round(resultado["abrigo"]["area"], 2), "m²")
    elif resultado["solucao"] == "descentralizado":
        for centro in resultado["centros"]:
            _itens_dos_conjuntos(itens, precos, centro["conjuntos"])
            _item(itens, precos, "abrigo_m2", round(centro["abrigo"]["area"], 2), "m²",
                  descricao=f"Centro de medição {centro['numero']} ({centro['andar']}), por m²")
            _item(itens, precos, "chave_vertical", 1)
            if centro["qdc_local"]:
                _item(itens, precos, f"qdc_{centro['qdc_local']}", 1,
                      descricao=f"{centro['qdc_local']} no centro {centro['numero']} (7.18.2)")
        _item(itens, precos, "cabo_mm2_m", round(resultado["cabo_mm2_m"] + resultado["ramais_mm2_m"]), "mm²·m",
              descricao="Cabos dos alimentadores e dos ramais de distribuição, por mm² × m")
        _item(itens, precos, "eletroduto_m", round(resultado["eletroduto_m"], 1), "m")
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
             demanda_total_a=0.0, altura_ultimo_pavimento=3.0, precos=None, andares_por_centro=ANDARES_POR_CENTRO):
    """As três soluções com o orçamento de cada uma e a recomendação pelo menor custo.

    ``andares_por_centro`` 0 deixa a medição descentralizada de fora.

    Returns:
        {'convencional', 'descentralizado' e 'busway': resultado ou None, 'erro_busway',
         'custos': {solução: orçamento}, 'recomendada', 'economia' [R$] para a segunda mais barata}.
    """
    conv = convencional(andares, tensao, distancia_horizontal, demanda_total_a)
    custos = {"convencional": orcamento(conv, precos)}
    desc = None
    if andares_por_centro and len(_com_unidades(andares)) > int(andares_por_centro):
        desc = descentralizado(andares, tensao, distancia_horizontal, demanda_total_a, andares_por_centro)
        custos["descentralizado"] = orcamento(desc, precos)
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
    recomendada = min(custos, key=lambda s: custos[s]["total"])
    outros = [custos[s]["total"] for s in custos if s != recomendada]
    economia = min(outros) - custos[recomendada]["total"] if outros else 0.0
    return {"convencional": conv, "descentralizado": desc, "busway": bus, "erro_busway": erro, "custos": custos,
            "recomendada": recomendada, "economia": economia}


NOMES = {"convencional": "Medição agrupada no térreo (caixas P ou coletivas)",
         "descentralizado": "Medição descentralizada (um centro a cada grupo de andares)",
         "busway": "Busway com medição centralizada"}


def _br(valor, casas=0):
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _linhas_dos_conjuntos(conjuntos, recuo):
    linhas = []
    for i, g in enumerate(conjuntos, start=1):
        if g.get("modelo") in INDIRETAS:
            linhas.append(f"{recuo}Conjunto {i}: {g['cdpm']}, {_br(g['corrente'])} A, chave seccionadora {g['chave']} A, "
                          f"TC {g['tc']}, proteção geral {g['disjuntor_geral']} A, ramal "
                          f"{g.get('paralelos', 1)} × {g.get('ramal')} mm²")
            continue
        caixa = f"{g['caixas']} caixas P, {g['cdpm']}" if g.get("modelo", "P") == "P" else \
            f"{g['cdpm']} com {g['caixas']} medição(ões)"
        linhas.append(f"{recuo}Conjunto {i}: {caixa}, {_br(g['corrente'])} A, disjuntor geral {g.get('disjuntor_geral')} A, "
                      f"barramento {g.get('barramento')}, ramal {g.get('ramal')} mm², "
                      f"{_br(g['largura_mm'])} mm de largura")
    return linhas


def relatorio(r):
    """Texto da comparação, para mostrar ao usuário."""
    conv, bus = r["convencional"], r["busway"]
    linhas = [f"Corrente de demanda total: {_br(conv['corrente'])} A · {conv['caixas']} medições · "
              f"entrada {conv['qdc']} com {conv['ramal']} circuito(s) de 4 × 240 mm²", "",
              f"1) {NOMES['convencional']}"]
    linhas += _linhas_dos_conjuntos(conv["agrupamentos"], "   ")
    ab = conv["abrigo"]
    linhas.append(f"   Centro de medição: {_br(ab['comprimento'], 2)} × {_br(ab['profundidade'], 2)} m = "
                  f"{_br(ab['area'], 1)} m²")
    for a in conv["alimentadores"]:
        linhas.append(f"   {a['andar']}: {a['unidades']} × ({a['condutores']} × {a['secao']} + PE {a['pe']}) mm², "
                      f"{_br(a['comprimento'], 1)} m, queda {_br(a['queda'], 2)} %")
    linhas.append(f"   Custo estimado: R$ {_br(r['custos']['convencional']['total'])}")
    desc = r.get("descentralizado")
    if desc:
        linhas += ["", f"2) {NOMES['descentralizado']}"]
        for centro in desc["centros"]:
            ramal = centro["ramal"]
            linhas.append(f"   Centro {centro['numero']} no {centro['andar']} ({', '.join(centro['andares'])}): "
                          f"{centro['unidades']} medições, {_br(centro['corrente'])} A, chave vertical "
                          f"{centro['chave']} A no QDC, ramal {ramal['paralelos']} × 4 × {ramal['secao']} mm² com "
                          f"{_br(ramal['comprimento'], 1)} m" + (f", {centro['qdc_local']} no centro"
                                                                if centro["qdc_local"] else ""))
            linhas += _linhas_dos_conjuntos(centro["conjuntos"], "      ")
            ab = centro["abrigo"]
            linhas.append(f"      Abrigo: {_br(ab['comprimento'], 2)} × {_br(ab['profundidade'], 2)} m")
        linhas.append(f"   Custo estimado: R$ {_br(r['custos']['descentralizado']['total'])}")
    linhas += ["", f"{3 if desc else 2}) {NOMES['busway']}"]
    if bus is None:
        linhas.append(f"   Não atende: {r['erro_busway']}")
    else:
        for i, linha in enumerate(bus["linhas"], start=1):
            linhas.append(f"   Linha {i}: busway {linha['nominal']} A (k {str(linha['k']).replace('.', ',')}), "
                          f"{_br(linha['comprimento'], 1)} m, demanda {_br(linha['corrente'])} A, queda "
                          f"{_br(linha['queda'], 2)} % até {linha['andares'][-1]}")
        for a in bus["andares"]:
            caixas = " + ".join(f"{c['tipo']} ({c['medicoes']} med.{', indireta' if c.get('indireta') else ''}, "
                                f"disj. {c['disjuntor']} A)" for c in a["caixas"])
            linhas.append(f"   {a['andar']}: {caixas}")
        m = bus["materiais"]
        linhas.append(f"   Shaft mínimo: {_br(bus['shaft']['largura'])} × {_br(bus['shaft']['profundidade'])} mm; "
                      f"{m['emendas']} emendas, {m['suportes']} suportes, {m['corta_fogo']} barreiras corta-fogo")
        linhas.append(f"   Custo estimado: R$ {_br(r['custos']['busway']['total'])}")
    linhas += ["", f"Recomendada pelo custo: {NOMES[r['recomendada']]}"
               + (f" (R$ {_br(r['economia'])} a menos)" if r["economia"] else "")]
    avisos = conv["avisos"] + (desc["avisos"] if desc else []) + (bus["avisos"] if bus else [])
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
    if r.get("descentralizado"):
        linhas += [("Centros descentralizados", str(len(r["descentralizado"]["centros"]))),
                   ("Custo descentralizado [R$]", _br(r["custos"]["descentralizado"]["total"]))]
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

POSICOES_CDPM = ("Centro", "Esquerda", "Direita")
SAIDAS_ELETRODUTO = ("Fundo", "Topo", "Base")


def _resolver_caixa_p(caixa_p_mm):
    if not caixa_p_mm:
        return CAIXA_P_MM
    return tuple(
        float(v) if v is not None and float(v) > 0 else padrao
        for v, padrao in zip(caixa_p_mm, CAIXA_P_MM)
    )


def _centralizar_x(pecas):
    xs = [p[1][0] for p in pecas] + [p[1][0] + p[2][0] for p in pecas]
    meio = (min(xs) + max(xs)) / 2.0
    return [(rotulo, (x - meio, y, z), dims) for rotulo, (x, y, z), dims in pecas]


def coluna_de_medicao(caixas, cdpm=None, por_coluna=MAX_VERTICAL, posicao_cdpm="Centro",
                      altura_base_mm=0.0, caixa_p_mm=None):
    """Caixas de um agrupamento em elevação, centradas em x = 0.

    O fundo das caixas fica na parede (y de 0 a +profundidade); a frente, em y = 0.

    Args:
        posicao_cdpm: ``"Centro"``, ``"Esquerda"`` ou ``"Direita"``.
        altura_base_mm: altura da base em relação ao piso [mm] (<= 0 usa a Tabela 29).
        caixa_p_mm: (largura, profundidade, altura) [mm] para sobrescrever ``CAIXA_P_MM`` (<= 0 mantém padrão).

    Returns:
        {'caixas': [(rótulo, (x, y, z), (dx, dy, dz))] mm, 'largura', 'altura', 'base', 'cdpm'}.
    """
    posicao_cdpm = posicao_cdpm or "Centro"
    if posicao_cdpm not in POSICOES_CDPM:
        raise ValueError(f"Posição da CDPM inválida: {posicao_cdpm}. Use {', '.join(POSICOES_CDPM)}.")
    esquerda, direita, vertical = distribuicao(caixas, por_coluna)
    cdpm = cdpm or tipo_cdpm(caixas, caixas * 63.0) or "Coluna MAX"
    largura_p, prof, altura_p = _resolver_caixa_p(caixa_p_mm)
    largura_cdpm = CDPM[cdpm][2]
    base = float(altura_base_mm) if altura_base_mm and float(altura_base_mm) > 0 else ALTURA_BASE_MM[vertical]
    if posicao_cdpm == "Centro":
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
    else:
        colunas = math.ceil(caixas / vertical) if caixas else 0
        x_cdpm = 0.0 if posicao_cdpm == "Esquerda" else colunas * largura_p
        x_caixas = largura_cdpm if posicao_cdpm == "Esquerda" else 0.0
        pecas = [("CDPM", (x_cdpm, 0.0, base), (largura_cdpm, prof, vertical * altura_p))]
        for i in range(caixas):
            coluna, linha = divmod(i, vertical)
            x = x_caixas + coluna * largura_p
            pecas.append((f"M{i + 1:02d}", (x, 0.0, base + (vertical - 1 - linha) * altura_p),
                          (largura_p, prof, altura_p)))
        pecas = _centralizar_x(pecas)
    xs = [p[1][0] for p in pecas] + [p[1][0] + p[2][0] for p in pecas]
    return {"caixas": pecas, "largura": max(xs) - min(xs), "altura": vertical * altura_p, "base": base,
            "cdpm": cdpm}


# Detalhes da coluna (Desenhos 23 a 26 e 55, ABNT NBR 15820, CT-68/CT-72): medidas [mm]
TAMPA_MM = 4.0  # tampa de policarbonato transparente
PAREDE_CAIXA_MM = 10.0  # espessura da carcaça oca (para ver o interior pela tampa transparente)
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
ALTURA_MIN_BASE_ENEL_MM = 300.0
ALTURA_MAX_TOPO_ENEL_MM = 1900.0

# Tipo de peça -> (cor RGB, transparência %)
CORES_DAS_PECAS = {
    "corpo": ((0.82, 0.84, 0.86), 0),
    "tampa": ((0.82, 0.92, 1.0), 70),
    "janelinha": ((0.72, 0.86, 0.98), 55),
    "cdpm": ((0.70, 0.72, 0.75), 0),
    "medidor": ((0.24, 0.26, 0.29), 0),
    "visor": ((0.62, 0.72, 0.64), 0),
    "borne": ((0.18, 0.19, 0.21), 0),
    "disjuntor": ((0.12, 0.12, 0.12), 0),
    "alavanca": ((0.78, 0.14, 0.14), 0),
    "barra": ((0.85, 0.5, 0.25), 0),
    "barra_r": ((0.08, 0.24, 0.58), 0),   # Enel SP: Fase R azul escuro
    "barra_s": ((0.95, 0.95, 0.95), 0),   # Enel SP: Fase S branco
    "barra_t": ((0.48, 0.20, 0.64), 0),   # Enel SP: Fase T violeta
    "barra_n": ((0.35, 0.68, 0.95), 0),   # Enel SP: Neutro azul claro
    "barra_pe": ((0.12, 0.58, 0.22), 0),  # Equipotencialização PE verde
    "isolador": ((0.68, 0.16, 0.14), 0),
    "dps": ((0.15, 0.35, 0.65), 0),
    "eletroduto": ((0.55, 0.55, 0.55), 0),
    "suporte": ((0.45, 0.48, 0.52), 0),
    "aviso": ((0.96, 0.80, 0.12), 0),
    "etiqueta": ((1.0, 1.0, 1.0), 0),
}
COR_DA_FASE = {"R": "barra_r", "S": "barra_s", "T": "barra_t", "N": "barra_n", "PE": "barra_pe"}


def _peca(pecas, tipo, rotulo, origem, dims, cor_tipo=None):
    pecas.append({
        "tipo": tipo,
        "cor_tipo": cor_tipo or tipo,
        "rotulo": rotulo,
        "forma": "caixa",
        "origem": origem,
        "dims": dims,
    })


def _caixa_oca(pecas, tipo, rotulo, origem, dims, espessura=PAREDE_CAIXA_MM, prefixo_paredes=None):
    """Invólucro oco (fundo, laterais, base e topo) sem sobreposição, aberto na frente (-y)."""
    x, y, z = origem
    dx, dy, dz = dims
    esp = min(float(espessura), dx / 4.0, dy / 4.0, dz / 4.0)
    if esp <= 0:
        _peca(pecas, tipo, rotulo, origem, dims)
        return
    pref = prefixo_paredes or rotulo
    _peca(pecas, tipo, rotulo, (x, y + dy - esp, z), (dx, esp, dz))
    _peca(pecas, tipo, f"{pref} lateral esquerda", (x, y, z), (esp, dy - esp, dz))
    _peca(pecas, tipo, f"{pref} lateral direita", (x + dx - esp, y, z), (esp, dy - esp, dz))
    _peca(pecas, tipo, f"{pref} fundo inferior", (x + esp, y, z), (dx - 2 * esp, dy - esp, esp))
    _peca(pecas, tipo, f"{pref} topo", (x + esp, y, z + dz - esp), (dx - 2 * esp, dy - esp, esp))


def _medidor_eletronico(pecas, rotulo, meio_x, y_fundo, z_base, largura=None, prof=None, altura=None):
    """Medidor eletrônico com placa de fundo, corpo, visor LCD e bloco de bornes inferior."""
    mx = largura or MEDIDOR_MM[0]
    my = prof or MEDIDOR_MM[1]
    mz = altura or MEDIDOR_MM[2]
    altura_bloco = min(22.0, mz * 0.14)
    altura_corpo = mz - altura_bloco
    _peca(pecas, "medidor", f"{rotulo} medidor", (meio_x - mx / 2.0, y_fundo - my, z_base + altura_bloco),
          (mx, my, altura_corpo))
    _peca(pecas, "visor", f"{rotulo} visor",
          (meio_x - mx * 0.34, y_fundo - my - 2.0, z_base + altura_bloco + altura_corpo * 0.55),
          (mx * 0.68, 2.0, altura_corpo * 0.28))
    _peca(pecas, "borne", f"{rotulo} bornes",
          (meio_x - mx * 0.42, y_fundo - my * 0.88, z_base),
          (mx * 0.84, my * 0.88, altura_bloco))


def _disjuntor_com_alavanca(pecas, rotulo, cx, y_fundo, z_base, dims, espessura_trilho=6.0):
    """Disjuntor montado sobre trilho DIN com alavanca frontal vermelha."""
    jx, jy, jz = dims
    _peca(pecas, "borne", f"{rotulo} trilho",
          (cx - jx * 0.75, y_fundo - espessura_trilho, z_base + jz * 0.3),
          (jx * 1.5, espessura_trilho, jz * 0.4))
    y_corpo = y_fundo - espessura_trilho - jy
    _peca(pecas, "disjuntor", rotulo, (cx - jx / 2.0, y_corpo, z_base), (jx, jy, jz))
    _peca(pecas, "alavanca", f"{rotulo} alavanca",
          (cx - jx * 0.32, y_corpo - 8.0, z_base + jz * 0.42),
          (jx * 0.64, 8.0, min(14.0, jz * 0.18)))


def _suporte_estrutural(pecas, x_min, x_max, y_fundo, z_base, z_topo):
    """Longarinas traseiras e montantes até o piso (pedestal/suporte de fixação Enel SP)."""
    largura = x_max - x_min
    if largura <= 0 or z_topo <= z_base:
        return
    y_trilho = y_fundo
    if z_topo - z_base > 240.0:
        for z_trilho, nome in ((z_base + 70.0, "Trilho suporte inferior"), (z_topo - 110.0, "Trilho suporte superior")):
            _peca(pecas, "suporte", nome, (x_min, y_trilho, z_trilho), (largura, 25.0, 40.0))
    z_col_topo = max(z_topo - 70.0, z_base + 60.0)
    pos_x = [x_min + 20.0, x_max - 60.0]
    if largura >= 1400.0:
        pos_x.append((x_min + x_max) / 2.0 - 20.0)
    for idx, px in enumerate(sorted(set(round(v, 1) for v in pos_x)), start=1):
        _peca(pecas, "suporte", f"Montante suporte {idx}", (px, y_trilho + 25.0, 0.0), (40.0, 40.0, z_col_topo))
        _peca(pecas, "suporte", f"Sapata suporte {idx}", (px - 40.0, y_trilho - 15.0, 0.0), (120.0, 120.0, 8.0))


def _tubo(pecas, rotulo, centro, raio, comprimento, eixo):
    pecas.append({"tipo": "eletroduto", "cor_tipo": "eletroduto", "rotulo": rotulo, "forma": "cilindro",
                  "origem": centro, "raio": raio, "comprimento": comprimento, "eixo": eixo})


def _tubo_saida(pecas, rotulo, x_tubo, y, dy, z, dz, z_inferior, saida_eletroduto):
    saida_eletroduto = saida_eletroduto or "Fundo"
    if saida_eletroduto not in SAIDAS_ELETRODUTO:
        raise ValueError(f"Saída do eletroduto inválida: {saida_eletroduto}. Use {', '.join(SAIDAS_ELETRODUTO)}.")
    raio = DIAMETRO_SAIDA_MM / 2.0
    if saida_eletroduto == "Fundo":
        _tubo(pecas, rotulo, (x_tubo, y + dy, z_inferior), raio, 100.0, (0.0, 1.0, 0.0))
    elif saida_eletroduto == "Topo":
        _tubo(pecas, rotulo, (x_tubo, y + dy / 2.0, z + dz), raio, 150.0, (0.0, 0.0, 1.0))
    elif z > 0:
        _tubo(pecas, rotulo, (x_tubo, y + dy / 2.0, max(0.0, z - 150.0)), raio, min(150.0, z), (0.0, 0.0, 1.0))


def pecas_da_coluna(caixas, cdpm=None, por_coluna=MAX_VERTICAL, posicao_cdpm="Centro",
                    altura_base_mm=0.0, caixa_p_mm=None, saida_eletroduto="Fundo", com_suporte=False):
    """Coluna detalhada no padrão Enel SP / ABNT NBR 15820:

    Cada caixa P tem carcaça oca, tampa transparente, janelinha de acesso ao disjuntor,
    divisória interna, medidor com visor LCD e bornes, disjuntor em trilho DIN com alavanca,
    etiqueta e eletroduto de saída. A CDPM tem carcaça oca, tampa transparente, aviso de
    segurança, barramentos R/S/T/N/PE nas cores da Enel sobre isoladores epóxi, disjuntor
    geral com alavanca, 4 módulos DPS, flange e eletroduto de entrada até o piso.
    """
    geral = coluna_de_medicao(caixas, cdpm, por_coluna, posicao_cdpm=posicao_cdpm,
                              altura_base_mm=altura_base_mm, caixa_p_mm=caixa_p_mm)
    pecas = []
    esp = PAREDE_CAIXA_MM
    for rotulo, (x, y, z), (dx, dy, dz) in geral["caixas"]:
        tipo_caixa = "cdpm" if rotulo == "CDPM" else "corpo"
        _caixa_oca(pecas, tipo_caixa, rotulo, (x, y + TAMPA_MM, z), (dx, dy - TAMPA_MM, dz), espessura=esp)
        _peca(pecas, "tampa", f"{rotulo} tampa", (x, y, z), (dx, TAMPA_MM, dz))
        meio = x + dx / 2.0
        y_fundo = y + dy - esp
        if rotulo == "CDPM":
            largura_barra, espessura = BARRA_CDPM[geral["cdpm"]]
            passo_b = min(largura_barra + 22.0, (dx - 2 * esp - 30.0) / 5.0)
            comprimento = min(COMPRIMENTO_BARRA_MM[geral["cdpm"]], dz * 0.36)
            topo = z + dz - esp - 35.0
            base_barras = topo - comprimento
            larg_isol = 4.2 * passo_b + largura_barra
            for k, zi in enumerate((base_barras + 25.0, topo - 35.0), start=1):
                _peca(pecas, "isolador", f"CDPM isolador {k}",
                      (meio - larg_isol / 2.0, y_fundo - 28.0, zi),
                      (larg_isol, 28.0, 22.0))
            for i, fase in enumerate(("R", "S", "T", "N", "PE")):
                bx = meio - 2 * passo_b + i * passo_b - largura_barra / 2.0
                _peca(pecas, "barra", f"Barra {fase}", (bx, y_fundo - 36.0, base_barras),
                      (largura_barra, espessura, comprimento), cor_tipo=COR_DA_FASE[fase])
            if dz >= 800.0:
                _peca(pecas, "cdpm", "CDPM divisória", (x + esp, y + TAMPA_MM + 8.0, base_barras - 20.0),
                      (dx - 2 * esp, dy - TAMPA_MM - esp - 8.0, 3.0))
            lx, ly, lz = DISJUNTOR_GERAL_MM
            lx = min(lx, dx - 2 * esp - 24.0)
            lz = min(lz, dz * 0.24)
            ly = min(ly, dy - TAMPA_MM - esp - 22.0)
            base_disjuntor = max(z + esp + 110.0, z + dz * 0.23) if dz >= 600.0 else z + esp + 65.0
            _disjuntor_com_alavanca(pecas, "Disjuntor geral", meio, y_fundo, base_disjuntor, (lx, ly, lz))
            px, py, pz = DPS_MM
            pz = min(pz, max(40.0, base_disjuntor - z - esp - 15.0))
            inicio = meio - DPS_POR_CDPM * px / 2.0
            _peca(pecas, "borne", "CDPM trilho DPS",
                  (inicio - 10.0, y_fundo - 6.0, z + esp + 18.0 + pz * 0.3),
                  (DPS_POR_CDPM * px + 20.0, 6.0, min(30.0, pz * 0.4)))
            for i in range(DPS_POR_CDPM):
                _peca(pecas, "dps", f"DPS {i + 1}", (inicio + i * px, y_fundo - 6.0 - py, z + esp + 18.0),
                      (px, py, pz))
            _peca(pecas, "borne", "CDPM flange entrada", (meio - 55.0, y + dy / 2.0 - 55.0, z + esp),
                  (110.0, 110.0, 6.0))
            _peca(pecas, "etiqueta", "CDPM aviso", (meio - 55.0, y - 1.0, z + dz - 45.0),
                  (110.0, 1.0, 28.0), cor_tipo="aviso")
            if z > 0:
                _tubo(pecas, "Eletroduto de entrada", (meio, y + dy / 2.0, 0.0), DIAMETRO_ENTRADA_MM / 2.0, z,
                      (0.0, 0.0, 1.0))
            continue
        divisoria = z + dz * (1 - DIVISORIA)
        _peca(pecas, "corpo", f"{rotulo} divisória", (x + esp, y + TAMPA_MM + 6.0, divisoria),
              (dx - 2 * esp, dy - TAMPA_MM - esp - 6.0, 3.0))
        altura_sup = z + dz - esp - (divisoria + 3.0)
        mz = min(MEDIDOR_MM[2], max(80.0, altura_sup - 36.0))
        mx = min(MEDIDOR_MM[0], dx - 2 * esp - 20.0)
        my = min(MEDIDOR_MM[1], dy - TAMPA_MM - esp - 20.0)
        z_med = divisoria + 3.0 + max(10.0, (altura_sup - mz) / 2.0)
        _peca(pecas, "borne", f"{rotulo} suporte medidor",
              (meio - mx * 0.55, y_fundo - 5.0, z_med + 10.0), (mx * 1.1, 5.0, mz * 0.85))
        _medidor_eletronico(pecas, rotulo, meio, y_fundo - 5.0, z_med, mx, my, mz)

        jx, jy, jz = DISJUNTOR_UNIDADE_MM
        jz = min(jz, max(45.0, divisoria - z - esp - 20.0))
        jy = min(jy, dy - TAMPA_MM - esp - 20.0)
        z_disj = z + esp + max(8.0, (divisoria - z - esp - jz) / 2.0)
        _disjuntor_com_alavanca(pecas, f"{rotulo} disjuntor", meio, y_fundo, z_disj, (jx, jy, jz))
        if divisoria - z - esp > 30.0:
            _peca(pecas, "janelinha", f"{rotulo} janelinha",
                  (x + 22.0, y + TAMPA_MM + 1.0, z + esp + 12.0),
                  (max(20.0, dx - 44.0), 3.0, divisoria - z - esp - 24.0))
        _peca(pecas, "etiqueta", f"{rotulo} identificação", (meio - 40.0, y - 1.0, z + dz - 45.0), (80.0, 1.0, 28.0))
        _tubo_saida(pecas, f"{rotulo} eletroduto", x + dx * 0.3, y, dy, z, dz,
                    z + (divisoria - z) / 2.0, saida_eletroduto)

    if com_suporte and geral["caixas"]:
        xs = [p[1][0] for p in geral["caixas"]] + [p[1][0] + p[2][0] for p in geral["caixas"]]
        ys = [p[1][1] + p[2][1] for p in geral["caixas"]]
        zs = [p[1][2] for p in geral["caixas"]] + [p[1][2] + p[2][2] for p in geral["caixas"]]
        _suporte_estrutural(pecas, min(xs), max(xs), max(ys), min(zs), max(zs))
    return pecas


def pecas_da_caixa_metalica(modelo, medicoes=None, altura_base_mm=0.0, com_suporte=False):
    """Caixa coletiva metálica detalhada (Desenhos 24 a 29), com a frente em y = 0 e o meio em x = 0."""
    quantidade, largura, altura, colunas, linhas, base = CAIXAS_METALICAS[modelo]
    if altura_base_mm and float(altura_base_mm) > 0:
        base = float(altura_base_mm)
    medicoes = quantidade if medicoes is None else min(int(medicoes), quantidade)
    prof = PROFUNDIDADE_METALICA_MM
    esp = PAREDE_CAIXA_MM
    pecas = []
    x0 = -largura / 2.0
    interna = modelo == "O"
    z_medicao, h_medicao = base, altura
    if interna:  # O: barramentos embaixo (500 mm) e CDPI em cima (325 mm)
        z_medicao, h_medicao = base + 500.0, altura - 500.0 - 325.0
    _caixa_oca(pecas, "corpo", f"Caixa {modelo}", (x0, TAMPA_MM, base), (largura, prof - TAMPA_MM, altura), espessura=esp)
    _peca(pecas, "tampa", f"Caixa {modelo} porta", (x0, 0.0, base), (largura, TAMPA_MM, altura))
    passo_x, passo_z = largura / colunas, h_medicao / linhas
    mx, my, mz = MEDIDOR_MM
    for i in range(medicoes):
        coluna, linha = i % colunas, i // colunas
        cx = x0 + passo_x * (coluna + 0.5)
        cz = z_medicao + h_medicao - passo_z * (linha + 0.5)
        _medidor_eletronico(pecas, f"Caixa {modelo} {i + 1}", cx, prof - esp - 10.0, cz - mz / 2.0, mx, my, mz)
        # Mantém rótulo 'Caixa {modelo} medidor {i+1}' compatível com os testes de contagem
        for p in reversed(pecas):
            if p["tipo"] == "medidor":
                p["rotulo"] = f"Caixa {modelo} medidor {i + 1}"
                break
        _peca(pecas, "etiqueta", f"Caixa {modelo} identificação {i + 1}", (cx - 40.0, -1.0, cz + mz / 2.0 + 10.0),
              (80.0, 1.0, 25.0))
    # CDPI (disjuntores das unidades)
    z_cdpi = base + altura - 325.0 if interna else base + altura
    h_cdpi = 325.0 if interna else ALTURA_CDPI_MM
    if not interna:
        _caixa_oca(pecas, "corpo", f"CDPI {modelo}", (x0, TAMPA_MM, z_cdpi), (largura, prof - TAMPA_MM, h_cdpi), espessura=esp)
        _peca(pecas, "tampa", f"CDPI {modelo} porta", (x0, 0.0, z_cdpi), (largura, TAMPA_MM, h_cdpi))
    jx, jy, jz = DISJUNTOR_UNIDADE_MM
    passo = min(largura / max(1, medicoes), jx + 20.0)
    inicio = -passo * medicoes / 2.0
    for i in range(medicoes):
        _disjuntor_com_alavanca(
            pecas, f"CDPI {modelo} disjuntor {i + 1}",
            inicio + (i + 0.5) * passo, prof - esp - 5.0, z_cdpi + 80.0, (jx, jy, jz),
        )
        _tubo(pecas, f"CDPI {modelo} eletroduto {i + 1}", (inicio + (i + 0.5) * passo, prof / 2.0, z_cdpi + h_cdpi),
              DIAMETRO_SAIDA_MM / 2.0 * 0.8, 150.0, (0.0, 0.0, 1.0))
    # barramentos
    z_barra = base if interna else base - ALTURA_CAIXA_BARRAMENTOS_MM
    h_barra = 500.0 if interna else ALTURA_CAIXA_BARRAMENTOS_MM
    if not interna:
        _caixa_oca(pecas, "cdpm", f"Barramentos {modelo}", (x0, TAMPA_MM, z_barra),
                   (largura, prof - TAMPA_MM, h_barra), espessura=esp)
        _peca(pecas, "tampa", f"Barramentos {modelo} tampa", (x0, 0.0, z_barra), (largura, TAMPA_MM, h_barra))
    for j, fase in enumerate(("R", "S", "T", "N")):  # de cima para baixo (7.19.4)
        _peca(pecas, "barra", f"Barra {fase} {modelo}",
              (x0 + 60.0, prof - 60.0, z_barra + h_barra - 60.0 - j * (h_barra - 80.0) / 4.0),
              (largura - 120.0, 5.0, 25.0), cor_tipo=COR_DA_FASE[fase])
    if z_barra > 0:
        _tubo(pecas, f"Eletroduto de entrada {modelo}", (0.0, prof / 2.0, 0.0), DIAMETRO_ENTRADA_MM / 2.0, z_barra,
              (0.0, 0.0, 1.0))
    if com_suporte:
        _suporte_estrutural(pecas, x0, x0 + largura, prof, z_barra, z_cdpi + h_cdpi)
    return pecas


def _medidor_e_disjuntor(pecas, rotulo, meio, prof, z_medidor, z_disjuntor):
    mx, my, mz = MEDIDOR_MM
    _medidor_eletronico(pecas, rotulo, meio, prof - PAREDE_CAIXA_MM - 5.0, z_medidor - mz / 2.0, mx, my, mz)
    jx, jy, jz = DISJUNTOR_UNIDADE_MM
    _disjuntor_com_alavanca(pecas, f"{rotulo} disjuntor", meio - jx * 0.75, prof - PAREDE_CAIXA_MM - 5.0,
                            z_disjuntor - jz / 2.0, (jx * 1.5, jy, jz))


def pecas_do_grupo_e(caixas, posicao_cdpm="Centro", altura_base_mm=0.0, saida_eletroduto="Base", com_suporte=False):
    """Caixas E (Desenho 22) lado a lado, com a CDPM de 300 × 500 mm (centro, esquerda ou direita)."""
    posicao_cdpm = posicao_cdpm or "Centro"
    if posicao_cdpm not in POSICOES_CDPM:
        raise ValueError(f"Posição da CDPM inválida: {posicao_cdpm}. Use {', '.join(POSICOES_CDPM)}.")
    largura, prof, altura = CAIXA_E_MM
    base = float(altura_base_mm) if altura_base_mm and float(altura_base_mm) > 0 else ALTURA_BASE_E_MM
    com_cdpm = caixas > 1
    lc = CDPM_E_MM[0] if com_cdpm else 0.0
    esquerda = math.ceil(caixas / 2) if com_cdpm else caixas
    largura_total = caixas * largura + lc
    x0_total = -largura_total / 2.0
    esp = PAREDE_CAIXA_MM
    pecas = []
    for i in range(caixas):
        if posicao_cdpm == "Centro":
            if i < esquerda:
                x = -lc / 2.0 - (esquerda - i) * largura
            else:
                x = lc / 2.0 + (i - esquerda) * largura
        elif posicao_cdpm == "Esquerda":
            x = x0_total + lc + i * largura
        else:
            x = x0_total + i * largura
        rotulo = f"E{i + 1:02d}"
        _caixa_oca(pecas, "corpo", rotulo, (x, TAMPA_MM, base), (largura, prof - TAMPA_MM, altura), espessura=esp)
        _peca(pecas, "tampa", f"{rotulo} porta", (x, 0.0, base), (largura, TAMPA_MM, altura))
        divisoria = base + altura - COMPARTIMENTO_MEDIDOR_E_MM
        _peca(pecas, "corpo", f"{rotulo} divisória", (x + esp, TAMPA_MM + 6.0, divisoria),
              (largura - 2 * esp, prof - TAMPA_MM - esp - 6.0, 3.0))
        meio = x + largura / 2.0
        _medidor_e_disjuntor(pecas, rotulo, meio, prof, divisoria + COMPARTIMENTO_MEDIDOR_E_MM / 2.0,
                             base + (divisoria - base) / 2.0)
        px, py, pz = DPS_MM
        _peca(pecas, "dps", f"{rotulo} DPS", (meio + 25.0, prof - esp - 5.0 - py, base + 40.0), (px * 3, py, pz))
        _peca(pecas, "etiqueta", f"{rotulo} identificação", (meio - 40.0, -1.0, base + altura - 40.0),
              (80.0, 1.0, 25.0))
        _tubo_saida(pecas, f"{rotulo} eletroduto", meio - 80.0, 0.0, prof, base, altura,
                    base + (divisoria - base) / 2.0, saida_eletroduto)
    if com_cdpm:
        lc, pc, hc = CDPM_E_MM
        if posicao_cdpm == "Centro":
            x_cdpm = -lc / 2.0
        elif posicao_cdpm == "Esquerda":
            x_cdpm = x0_total
        else:
            x_cdpm = x0_total + caixas * largura
        z = base + altura - hc
        _caixa_oca(pecas, "cdpm", "CDPM", (x_cdpm, TAMPA_MM, z), (lc, pc - TAMPA_MM, hc), espessura=esp)
        _peca(pecas, "tampa", "CDPM tampa", (x_cdpm, 0.0, z), (lc, TAMPA_MM, hc))
        for j, fase in enumerate(("R", "S", "T", "N")):
            _peca(pecas, "barra", f"Barra {fase}", (x_cdpm + 40.0 + j * 50.0, pc - 40.0, z + hc - 220.0),
                  (15.0, 5.0, 200.0), cor_tipo=COR_DA_FASE[fase])
        lx, ly, lz = DISJUNTOR_GERAL_MM
        _disjuntor_com_alavanca(pecas, "Disjuntor geral", x_cdpm + lc / 2.0, pc - esp - 5.0, z + 60.0,
                                (lx, ly, lz * 0.8))
        if z > 0:
            _tubo(pecas, "Eletroduto de entrada", (x_cdpm + lc / 2.0, pc / 2.0, 0.0),
                  DIAMETRO_ENTRADA_MM / 2.0 * 0.6, z, (0.0, 0.0, 1.0))
    if com_suporte:
        _suporte_estrutural(pecas, x0_total, x0_total + largura_total, prof, base, base + altura)
    return pecas


def pecas_da_indireta(modelo, altura_base_mm=0.0, com_suporte=False):
    """Conjunto de medição indireta (7.17.2), frente em y = 0 e meio em x = 0."""
    _, _, largura, altura, prof, base = INDIRETAS[modelo]
    if altura_base_mm and float(altura_base_mm) > 0:
        base = float(altura_base_mm)
    esp = PAREDE_CAIXA_MM
    pecas = []
    mx, my, mz = MEDIDOR_MM
    if modelo == "IND300":
        l1, l2, l3 = MODULO_INDIRETA_MM
        h = altura / 2.0
        x = -largura / 2.0
        modulos = [("Módulo da chave", x, l1, base), ("Módulo dos TCs", x + l1, l2, base),
                   ("Módulo da proteção", x + l1 + l2, l3, base), ("Módulo do medidor", x + l1, l2, base + h)]
        for rotulo, mx0, ml, mz0 in modulos:
            _caixa_oca(pecas, "corpo", rotulo, (mx0, TAMPA_MM, mz0), (ml, prof - TAMPA_MM, h),
                       espessura=esp, prefixo_paredes=f"Carcaça {rotulo}")
            _peca(pecas, "tampa", f"{rotulo} tampa", (mx0, 0.0, mz0), (ml, TAMPA_MM, h))
        _disjuntor_com_alavanca(pecas, "Chave seccionadora sob carga", x + l1 / 2.0, prof - esp - 10.0,
                                base + 150.0, (150.0, 120.0, 260.0))
        _peca(pecas, "isolador", "Caixa dos TCs", (x + l1 + l2 / 2.0 - 110.0, prof - 140.0, base + 70.0),
              (220.0, 120.0, 420.0))
        for j, fase in enumerate(("R", "S", "T")):
            _peca(pecas, "barra", f"TC {fase}", (x + l1 + 110.0 + j * 130.0, prof - 150.0, base + 210.0),
                  (80.0, 90.0, 120.0), cor_tipo=COR_DA_FASE[fase])
        _disjuntor_com_alavanca(pecas, "Proteção geral", x + l1 + l2 + l3 / 2.0, prof - esp - 10.0,
                                base + 160.0, (140.0, 120.0, 240.0))
        _medidor_eletronico(pecas, "Medidor", 120.0, prof - esp - 10.0, base + h + 280.0, mx, my, mz)
        for p in reversed(pecas):
            if p["tipo"] == "medidor":
                p["rotulo"] = "Medidor"
                break
        _peca(pecas, "dps", "Bloco de aferição", (-mx / 2.0 - 120.0, prof - 55.0, base + h + 140.0),
              (190.0, 40.0, 70.0))
        if base > 0:
            _tubo(pecas, "Eletroduto de entrada", (x + l1 / 2.0, prof / 2.0, 0.0), DIAMETRO_ENTRADA_MM / 2.0, base,
                  (0.0, 0.0, 1.0))
        _tubo(pecas, "Eletroduto de saída", (x + l1 + l2 + l3 / 2.0, prof / 2.0, base + h), DIAMETRO_ENTRADA_MM / 2.0,
              300.0, (0.0, 0.0, 1.0))
    else:
        x = -largura / 2.0
        _caixa_oca(pecas, "corpo", "Caixa M", (x, TAMPA_MM, base), (largura, prof - TAMPA_MM, altura), espessura=esp)
        _peca(pecas, "tampa", "Caixa M porta", (x, 0.0, base), (largura, TAMPA_MM, altura))
        _disjuntor_com_alavanca(pecas, "Chave seca", x + 180.0, prof - esp - 10.0, base + 120.0, (200.0, 120.0, 320.0))
        for j in range(3):
            fase = ("R", "S", "T")[j]
            _peca(pecas, "barra", f"TC {fase}", (x + 380.0 + j * 140.0, prof - 120.0, base + 200.0),
                  (100.0, 100.0, 140.0), cor_tipo=COR_DA_FASE[fase])
        _disjuntor_com_alavanca(pecas, "Proteção geral", x + largura - 210.0, prof - esp - 10.0, base + 120.0,
                                (220.0, 130.0, 340.0))
        _medidor_eletronico(pecas, "Medidor", x + largura / 2.0, prof - esp - 10.0, base + altura - mz - 80.0, mx, my, mz)
        for p in reversed(pecas):
            if p["tipo"] == "medidor":
                p["rotulo"] = "Medidor"
                break
        _peca(pecas, "dps", "Bloco de aferição", (x + largura / 2.0 + 120.0, prof - 55.0, base + altura - 200.0),
              (190.0, 40.0, 70.0))
        if base > 0:
            for j, xe in enumerate((x + 180.0, x + 300.0)):  # dois circuitos de entrada (nota 8)
                _tubo(pecas, f"Eletroduto de entrada {j + 1}", (xe, prof / 2.0, 0.0), DIAMETRO_ENTRADA_MM / 2.0, base,
                      (0.0, 0.0, 1.0))
        _tubo(pecas, "Eletroduto de saída", (x + largura - 210.0, prof / 2.0, base + altura),
              DIAMETRO_ENTRADA_MM / 2.0, 300.0, (0.0, 0.0, 1.0))
    _peca(pecas, "etiqueta", "Identificação", (-40.0, -1.0, base + altura - 40.0), (80.0, 1.0, 25.0))
    if com_suporte:
        _suporte_estrutural(pecas, -largura / 2.0, largura / 2.0, prof, base, base + altura)
    return pecas


def pecas_do_centro(dimensionamento, posicao_cdpm="Centro", altura_base_mm=0.0, caixa_p_mm=None,
                    saida_eletroduto=None, folga_conjuntos_mm=None, com_suporte=False):
    """Todas as peças dos conjuntos de ``dimensionar_colunas``, lado a lado e centrados em x = 0."""
    conjuntos = dimensionamento["conjuntos"]
    if not conjuntos:
        return []
    por_coluna = dimensionamento.get("por_coluna", MAX_VERTICAL)
    folga = float(folga_conjuntos_mm) if folga_conjuntos_mm and float(folga_conjuntos_mm) > 0 else FOLGA_ENTRE_AGRUPAMENTOS_MM
    blocos = []
    for c in conjuntos:
        modelo = c.get("modelo", "P")
        if modelo == "P":
            pecas = pecas_da_coluna(
                c["caixas"], c["cdpm"], por_coluna,
                posicao_cdpm=posicao_cdpm, altura_base_mm=altura_base_mm,
                caixa_p_mm=caixa_p_mm, saida_eletroduto=saida_eletroduto or "Fundo",
                com_suporte=com_suporte,
            )
        elif modelo == "E":
            pecas = pecas_do_grupo_e(
                c["medicoes"], posicao_cdpm=posicao_cdpm,
                altura_base_mm=altura_base_mm, saida_eletroduto=saida_eletroduto or "Base",
                com_suporte=com_suporte,
            )
        elif modelo in INDIRETAS:
            pecas = pecas_da_indireta(modelo, altura_base_mm=altura_base_mm, com_suporte=com_suporte)
        else:
            pecas = pecas_da_caixa_metalica(modelo, c["medicoes"], altura_base_mm=altura_base_mm, com_suporte=com_suporte)
        xs = [p["origem"][0] for p in pecas if p["forma"] == "caixa"] + \
             [p["origem"][0] + p["dims"][0] for p in pecas if p["forma"] == "caixa"]
        blocos.append((pecas, min(xs), max(xs) - min(xs)))
    largura_total = sum(b[2] for b in blocos) + folga * (len(blocos) - 1)
    x = -largura_total / 2.0
    resultado = []
    for numero, (pecas, minimo, largura) in enumerate(blocos, start=1):
        deslocamento = x - minimo
        for p in pecas:
            nova = dict(p, rotulo=f"A{numero} {p['rotulo']}")
            ox, oy, oz = p["origem"]
            nova["origem"] = (ox + deslocamento, oy, oz)
            nova["conjunto"] = numero
            resultado.append(nova)
        x += largura + folga
    return resultado


def dimensoes_das_pecas(pecas):
    """Dimensões globais [mm] do envoltório das caixas: largura, profundidade, altura, base e topo."""
    caixas = [p for p in pecas if p.get("forma") == "caixa" and p.get("tipo") not in ("etiqueta", "suporte")]
    if not caixas:
        return {"largura_mm": 0.0, "profundidade_mm": 0.0, "altura_mm": 0.0, "base_mm": 0.0, "topo_mm": 0.0}
    xs = [p["origem"][0] for p in caixas] + [p["origem"][0] + p["dims"][0] for p in caixas]
    ys = [p["origem"][1] for p in caixas] + [p["origem"][1] + p["dims"][1] for p in caixas]
    zs = [p["origem"][2] for p in caixas] + [p["origem"][2] + p["dims"][2] for p in caixas]
    base_mm = round(min(zs), 1)
    topo_mm = round(max(zs), 1)
    return {
        "largura_mm": round(max(xs) - min(xs), 1),
        "profundidade_mm": round(max(ys) - min(ys), 1),
        "altura_mm": round(topo_mm - base_mm, 1),
        "base_mm": base_mm,
        "topo_mm": topo_mm,
    }


def avisos_layout_enel(dimensionamento, pecas, posicao_cdpm="Centro", altura_base_mm=0.0):
    """Verifica restrições ergonômicas e de montagem da Enel SP (0018 v2 / Tabela 29)."""
    if not pecas or not dimensionamento.get("conjuntos"):
        return []
    avisos = []
    dims = dimensoes_das_pecas(pecas)
    if 0.0 < dims["base_mm"] < ALTURA_MIN_BASE_ENEL_MM:
        avisos.append(f"Enel SP (Tabela 29): altura da base ({dims['base_mm']:g} mm) abaixo do mínimo de "
                      f"{ALTURA_MIN_BASE_ENEL_MM:g} mm do piso acabado")
    modelo = dimensionamento.get("modelo")
    if modelo == "P" and dims["topo_mm"] > ALTURA_MAX_TOPO_ENEL_MM:
        avisos.append(f"Enel SP (Tabela 29): topo das caixas P em {dims['topo_mm']:g} mm passa dos "
                      f"{ALTURA_MAX_TOPO_ENEL_MM:g} mm ergonômicos")
    if modelo == "P" and posicao_cdpm in ("Esquerda", "Direita"):
        por_coluna = max(1, int(dimensionamento.get("por_coluna", MAX_VERTICAL)))
        for c in dimensionamento["conjuntos"]:
            colunas = math.ceil(c["caixas"] / por_coluna)
            if colunas > MAX_COLUNAS_POR_LADO:
                avisos.append(f"Enel SP: CDPM na {posicao_cdpm.lower()} deixa {colunas} colunas de um único lado "
                              f"(máximo recomendado {MAX_COLUNAS_POR_LADO} por lado)")
                break
    return avisos


def resumo_coluna(dimensionamento, pecas=None, avisos_extras=()):
    """Resumo textual do dimensionamento e das dimensões globais para prévia no diálogo."""
    solucoes = {
        "P": "Caixas P em agrupamento modular",
        "E": "Caixas E com CDPM",
        "metalica": "Caixas coletivas metálicas",
        "indireta": "Medição indireta (TCs)",
    }
    solucao = solucoes.get(dimensionamento.get("modelo"), "Sem conjunto (veja os avisos)")
    linhas = [f"Solução: {solucao}", f"Corrente total: {_br(dimensionamento.get('corrente', 0.0), 1)} A"]
    if dimensionamento.get("disjuntor_unidade"):
        linhas.append(f"Disjuntor por unidade: {dimensionamento['disjuntor_unidade']} A")
    conjuntos = dimensionamento.get("conjuntos") or []
    if pecas is None and conjuntos:
        pecas = pecas_do_centro(dimensionamento)
    dims = dimensoes_das_pecas(pecas or [])
    if dims["largura_mm"] > 0:
        linhas.append(
            f"Dimensões totais: {_br(dims['largura_mm'])} × {_br(dims['profundidade_mm'])} × "
            f"{_br(dims['altura_mm'])} mm (base {_br(dims['base_mm'])} mm, topo {_br(dims['topo_mm'])} mm)"
        )
    if conjuntos:
        linhas.append("")
        linhas.append(f"Conjuntos ({len(conjuntos)}):")
        for i, c in enumerate(conjuntos, start=1):
            if c.get("modelo") in INDIRETAS:
                linhas.append(
                    f"  {i}. {c['cdpm']} · {_br(c['corrente'])} A · chave {c['chave']} A · "
                    f"TC {c['tc']} · disj. {c['disjuntor_geral']} A · ramal "
                    f"{c.get('paralelos', 1)} × {c['ramal']} mm²"
                )
            else:
                nome = f"{c['caixas']} caixas P ({c['cdpm']})" if c.get("modelo", "P") == "P" else \
                    (f"{c['medicoes']} caixa(s) E" if c.get("modelo") == "E" else f"{c['cdpm']} ({c['medicoes']} med.)")
                linhas.append(
                    f"  {i}. {nome} · {_br(c['corrente'])} A · geral {c['disjuntor_geral']} A · "
                    f"barra {c['barramento']} · ramal {c['ramal']} mm²"
                )
    avisos = list(dimensionamento.get("avisos") or []) + list(avisos_extras or ())
    if avisos:
        linhas.append("")
        linhas.append("Avisos:")
        for aviso in avisos:
            linhas.append(f"  - {aviso}")
    return "\n".join(linhas)


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
    """Materiais das colunas de medição: [{'caixas' (caixas P), 'cdpms': [tipos], 'metalicas': [modelos],
    'medicoes_metalicas'}] de cada conjunto inserido."""
    itens, cdpms, metalicas, indiretas = [], {}, {}, {}
    for c in colunas:
        for modelo in c.get("metalicas", []):
            metalicas[modelo] = metalicas.get(modelo, 0) + 1
        for modelo in c.get("indiretas", []):
            indiretas[modelo] = indiretas.get(modelo, 0) + 1
    caixas_e = sum(int(c.get("caixas_e", 0)) for c in colunas)
    cdpm_e = sum(int(c.get("cdpm_e", 0)) for c in colunas)
    medicoes_metalicas = sum(int(c.get("medicoes_metalicas", 0)) for c in colunas)
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
    for modelo in CAIXAS_METALICAS:
        if metalicas.get(modelo):
            _, largura, altura, *_ = CAIXAS_METALICAS[modelo]
            itens.append(_linha("Caixa de medição coletiva", f"tipo {modelo}, aço, {largura:g} × {altura:g} × "
                                f"{PROFUNDIDADE_METALICA_MM:g} mm", metalicas[modelo]))
    barramentos = sum(q for m, q in metalicas.items() if m != "O")
    if barramentos:
        itens.append(_linha("Caixa de barramentos e CDPI", "Desenhos 20 e 32", barramentos))
    if medicoes_metalicas:
        itens.append(_linha("Disjuntor da unidade", "DIN até 100 A, na CDPI", medicoes_metalicas))
    if caixas_e:
        itens.append(_linha("Caixa de medição tipo E", "350 × 560 × 250 mm", caixas_e))
        itens.append(_linha("Disjuntor da unidade", "tripolar até 100 A, na caixa E", caixas_e))
        itens.append(_linha("DPS", "classe II, na caixa E", caixas_e * 3))
    if cdpm_e:
        itens.append(_linha("CDPM das caixas E", "300 × 500 × 250 mm, até 125 A", cdpm_e))
    for modelo, (_, rotulo, *_r) in INDIRETAS.items():
        if indiretas.get(modelo):
            itens.append(_linha("Conjunto de medição indireta", rotulo, indiretas[modelo]))
            itens.append(_linha("Chave seccionadora sob carga sem fusíveis", "antes dos TCs", indiretas[modelo]))
            itens.append(_linha("Condutor de cobre 2,5 mm² (TC ao medidor)", "10 fios", round(
                indiretas[modelo] * 10 * 1.5, 1), "m"))
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
