"""Pré-dimensionamento de grupo motor-gerador diesel, sem FreeCAD.

Passos de ``dimensionar``:

1. cada carga: potência instalada (quantidade × potência), demanda pelo fator
   de demanda da carga e potência reativa pelo fator de potência;
2. o conjunto: soma das demandas dividida pelo **fator de diversidade**
   (≥ 1: soma das demandas individuais / demanda máxima do conjunto);
3. regime: a demanda máxima não passa do ``carregamento`` do gerador (80 % em
   emergência, 70 % em prime ou contínuo), nem em kVA nem em kW (o gerador é
   de fator de potência 0,8);
4. cargas não lineares (nobreak, eletrônica, inversores de frequência) contam
   ``FATOR_NAO_LINEAR`` vezes, por causa das harmônicas;
5. partida do maior motor: o afundamento de tensão ΔV = x″d·Sp / (Sg + x″d·Sp)
   não passa do admissível, ou seja, Sg ≥ x″d·Sp·(1 − ΔV)/ΔV, com Sp a
   potência de partida (``PARTIDAS`` × kVA do motor);
6. altitude e temperatura reduzem a potência do motor diesel (``reducao``);
7. o gerador comercial é o primeiro de ``GERADORES_KVA`` que atende os três critérios.

Depois: corrente nominal, disjuntor do gerador (Ib ≤ In), cabo de cobre por
fase (In ≤ Iz, com cabos em paralelo se passar de 300 mm², e queda de tensão
até o quadro de transferência), neutro, condutor de proteção (tabela 58 da
NBR 5410), corrente de curto estimada do gerador e o tanque de diesel.

ATENÇÃO: regras usuais de pré-dimensionamento, não de um fabricante. A redução
por altitude e temperatura, a reatância x″d, o consumo de diesel e o fator das
cargas não lineares variam de um modelo para outro: confirme com o catálogo
do gerador escolhido. As capacidades acima de 120 mm² são da NBR 5410
(tabelas 36 a 38), transcritas e a conferir.

Unidades: potências em kW, kVA ou cv, tensões em V, correntes em A, seções em
mm², comprimentos em m, altitude em m, temperatura em °C, consumo em L.
"""
import math

from freecad.Circuits.core import nbr5410
from freecad.Circuits.core.functions.Predial import motores

# Tipo de carga -> (fator de potência típico, é motor, é não linear)
TIPOS = {
    "Iluminação e tomadas": (0.92, False, False),
    "Resistiva (chuveiro, aquecedor, forno)": (1.00, False, False),
    "Motor (bomba, ventilador, compressor)": (0.85, True, False),
    "Ar-condicionado": (0.85, True, False),
    "Elevador": (0.80, True, False),
    "Nobreak (UPS)": (0.90, False, True),
    "Eletrônica e informática": (0.95, False, True),
    "Quadro (cargas mistas)": (0.92, False, False),
}
TIPO_PADRAO = "Quadro (cargas mistas)"
UNIDADES = ["kW", "kVA", "cv"]

# Partida -> potência de partida / potência do motor em funcionamento (kVA)
PARTIDAS = {
    "Direta": 6.0,
    "Estrela-triângulo": 2.0,
    "Chave compensadora": 2.6,
    "Soft-starter": 3.0,
    "Inversor de frequência": 1.0,
}
PARTIDA_PADRAO = "Direta"

FATOR_NAO_LINEAR = 1.5  # o gerador deve ter 1,5 vez o kVA das cargas não lineares
FATOR_POTENCIA_GERADOR = 0.8
REATANCIA_SUBTRANSITORIA = 0.15  # x″d [pu], típica de alternadores de grupos diesel
AFUNDAMENTO_ADMISSIVEL = 20.0  # % na partida do maior motor

# Regime -> carregamento máximo do gerador (fração da potência do regime)
REGIMES = {
    "Emergência (standby)": 0.80,
    "Prime (horário de ponta, sem rede)": 0.70,
    "Contínuo": 0.70,
}

# Redução da potência do motor diesel (aproximação; use a curva do fabricante)
ALTITUDE_SEM_REDUCAO = 1000.0  # m
REDUCAO_POR_100M = 0.01
TEMPERATURA_SEM_REDUCAO = 40.0  # °C
REDUCAO_POR_GRAU = 0.01

# Potências comerciais usuais de grupos geradores [kVA]
GERADORES_KVA = [12, 15, 20, 25, 30, 40, 50, 55, 60, 75, 80, 100, 115, 125, 150, 180, 200, 230, 250, 260, 300,
                 330, 360, 400, 450, 500, 550, 625, 700, 750, 800, 900, 1000, 1250, 1500, 1750, 2000, 2500]

# Disjuntores em caixa moldada e abertos [A]
DISJUNTORES = [16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 320, 400, 500, 630, 800, 1000, 1250,
               1600, 2000, 2500, 3200, 4000]

TENSOES = {"380/220 V": 380.0, "220/127 V": 220.0, "440/254 V": 440.0}

# Método de instalação do cabo do gerador -> (método da NBR 5410, descrição)
INSTALACOES = {
    "Eletroduto aparente ou embutido (B1)": "B1",
    "Eletrocalha perfurada ou leito (E)": "E",
    "Fixado em parede ou bandeja lisa (C)": "C",
    "Enterrado em eletroduto (D)": "D",
}
ISOLACOES = ["EPR ou XLPE (90 °C)", "PVC (70 °C)"]

# Capacidade [A] de cobre, 3 condutores carregados, a 30 °C (20 °C no solo), sem agrupamento.
SECOES = [16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]
CAPACIDADE = {
    ("PVC", "B1"): [68, 89, 110, 134, 171, 207, 239, 275, 314, 370, 426],
    ("PVC", "C"): [76, 96, 119, 144, 184, 223, 259, 299, 341, 403, 464],
    ("PVC", "D"): [67, 86, 103, 122, 151, 179, 203, 230, 258, 297, 336],
    ("PVC", "E"): [80, 101, 126, 153, 196, 238, 276, 319, 364, 430, 497],
    ("EPR", "B1"): [88, 117, 144, 175, 222, 269, 312, 358, 408, 481, 553],
    ("EPR", "C"): [96, 119, 147, 179, 229, 278, 322, 371, 424, 500, 576],
    ("EPR", "D"): [80, 104, 125, 148, 183, 216, 246, 278, 312, 361, 408],
    ("EPR", "E"): [100, 127, 158, 192, 246, 298, 346, 399, 456, 538, 621],
}
MAXIMO_PARALELO = 8
QUEDA_MAXIMA = 2.0  # % do gerador ao quadro de transferência

CONSUMO_ESPECIFICO = 0.27  # L/kWh, diesel, perto da carga nominal
AUTONOMIA_PADRAO = 8.0  # h
MARGEM_TANQUE = 1.1  # volume morto e dilatação


def _numero(valor, padrao=None):
    if valor is None or str(valor).strip() == "":
        return padrao
    try:
        return float(str(valor).strip().replace(",", "."))
    except ValueError:
        return padrao


def carga(descricao, tipo=TIPO_PADRAO, quantidade=1, potencia=0.0, unidade="kW", fator_potencia=None,
          fator_demanda=None, partida=None, no_gerador=True):
    """Normaliza uma carga da planilha.

    Campos em branco valem: tipo ``TIPO_PADRAO``, quantidade 1, fator de
    potência típico do tipo, fator de demanda 1, partida direta nos motores.

    Returns:
        dict com ``descricao``, ``tipo``, ``quantidade``, ``kw`` e ``kva`` (de
        uma unidade, em funcionamento), ``fator_potencia``, ``fator_demanda``,
        ``motor``, ``nao_linear``, ``partida`` e ``no_gerador``.
    Raises:
        ValueError: tipo, unidade ou partida desconhecidos, ou números fora da faixa.
    """
    tipo = str(tipo or "").strip() or TIPO_PADRAO
    if tipo not in TIPOS:
        raise ValueError(f"{descricao}: tipo '{tipo}' desconhecido. Use um de: {', '.join(TIPOS)}.")
    fp_tipico, motor, nao_linear = TIPOS[tipo]
    unidade = str(unidade or "").strip() or "kW"
    if unidade not in UNIDADES:
        raise ValueError(f"{descricao}: unidade '{unidade}' desconhecida. Use kW, kVA ou cv.")
    quantidade = _numero(quantidade, 1.0)
    potencia = _numero(potencia, 0.0)
    fp = _numero(fator_potencia, fp_tipico if unidade != "cv" else motores.FATOR_POTENCIA_TIPICO)
    fd = _numero(fator_demanda, 1.0)
    if quantidade <= 0 or potencia < 0:
        raise ValueError(f"{descricao}: quantidade e potência precisam ser positivas.")
    if not 0.1 <= fp <= 1.0:
        raise ValueError(f"{descricao}: fator de potência {fp:g} fora de 0,1 a 1.")
    if not 0.0 <= fd <= 1.0:
        raise ValueError(f"{descricao}: fator de demanda {fd:g} fora de 0 a 1.")
    partida = str(partida or "").strip()
    motor = motor or unidade == "cv"
    if motor:
        partida = partida or PARTIDA_PADRAO
        if partida not in PARTIDAS:
            raise ValueError(f"{descricao}: partida '{partida}' desconhecida. Use uma de: {', '.join(PARTIDAS)}.")
        nao_linear = nao_linear or partida == "Inversor de frequência"
    else:
        partida = ""

    if unidade == "cv":
        kw, _ = motores.potencia_eletrica(potencia, fator_potencia=fp)
    elif unidade == "kVA":
        kw = potencia * fp
    else:
        kw = potencia
    if isinstance(no_gerador, str):
        no_gerador = no_gerador.strip().upper()[:1] not in ("N", "F", "0")
    return {
        "descricao": str(descricao), "tipo": tipo, "quantidade": quantidade, "kw": kw, "kva": kw / fp,
        "fator_potencia": fp, "fator_demanda": fd, "motor": motor, "nao_linear": nao_linear,
        "partida": partida, "no_gerador": bool(no_gerador),
    }


def reducao(altitude=0.0, temperatura=TEMPERATURA_SEM_REDUCAO):
    """Fração da potência nominal disponível no local (1 = sem redução)."""
    perda = REDUCAO_POR_100M * max(0.0, float(altitude) - ALTITUDE_SEM_REDUCAO) / 100.0
    perda += REDUCAO_POR_GRAU * max(0.0, float(temperatura) - TEMPERATURA_SEM_REDUCAO)
    return max(0.3, 1.0 - perda)


def gerador_comercial(kva):
    """Menor gerador da lista com potência ≥ ``kva``."""
    for potencia in GERADORES_KVA:
        if potencia >= kva - 1e-9:
            return potencia
    raise ValueError(f"Potência de {kva:.0f} kVA acima do maior gerador da lista ({GERADORES_KVA[-1]} kVA). "
                     "Divida as cargas em mais de um gerador ou use geradores em paralelo.")


def disjuntor(corrente):
    """Menor disjuntor comercial com In ≥ corrente."""
    for nominal in DISJUNTORES:
        if nominal >= corrente - 1e-9:
            return nominal
    raise ValueError(f"Corrente de {corrente:.0f} A acima do maior disjuntor da lista ({DISJUNTORES[-1]} A).")


def _isolacao(isolacao):
    return "PVC" if str(isolacao).upper().startswith("PVC") else "EPR"


def capacidade(secao, metodo="B1", isolacao="EPR"):
    """Capacidade [A] do cabo de cobre com 3 condutores carregados, a 30 °C, sem agrupamento."""
    chave = (_isolacao(isolacao), "E" if metodo == "F" else metodo)
    if chave not in CAPACIDADE:
        raise ValueError(f"Sem tabela para {chave[0]}, método {metodo}.")
    return CAPACIDADE[chave][SECOES.index(secao)]


def condutor_protecao(secao_fase):
    """Seção do condutor de proteção pela tabela 58 da NBR 5410 [mm²] (``nbr5410.secao_protecao``)."""
    return nbr5410.secao_protecao(secao_fase)


def cabo(corrente_disjuntor, corrente_projeto, comprimento, tensao, metodo="B1", isolacao="EPR", temperatura=30.0,
         queda_max=QUEDA_MAXIMA):
    """Menor arranjo (cabos por fase, seção) com In ≤ Iz e queda dentro do limite.

    Com cabos em paralelo, cada conjunto conta como um circuito no fator de
    agrupamento (tabela 42, em feixe: conservador para eletrocalha e leito).

    Returns:
        dict com ``paralelos``, ``secao``, ``iz`` (do conjunto) [A], ``queda`` [%],
        ``fator`` (FCT·FCA) e ``criterio`` ('capacidade' ou 'queda_tensao').
    """
    fct = nbr5410.fct(temperatura, "EPR" if _isolacao(isolacao) == "EPR" else "PVC")
    for paralelos in range(1, MAXIMO_PARALELO + 1):
        fator = fct * nbr5410.fca(paralelos)
        cabem = [s for s in SECOES if capacidade(s, metodo, isolacao) * fator * paralelos >= corrente_disjuntor]
        for secao in cabem:
            queda = nbr5410.queda_tensao(corrente_projeto / paralelos, comprimento, secao, tensao, 3)
            if queda <= queda_max:
                iz = capacidade(secao, metodo, isolacao) * fator * paralelos
                return {"paralelos": paralelos, "secao": secao, "iz": round(iz, 1), "queda": round(queda, 2),
                        "fator": round(fator, 3), "criterio": "capacidade" if secao == cabem[0] else "queda_tensao"}
    raise ValueError(f"Nenhum arranjo de até {MAXIMO_PARALELO} cabos de {SECOES[-1]} mm² por fase atende "
                     f"{corrente_disjuntor:.0f} A com queda de até {queda_max:g} %.")


def dimensionar(cargas, tensao=380.0, fator_diversidade=1.0, carregamento=REGIMES["Emergência (standby)"],
                comprimento=30.0, metodo="B1", isolacao="EPR", temperatura_cabo=30.0, queda_max=QUEDA_MAXIMA,
                afundamento=AFUNDAMENTO_ADMISSIVEL, reatancia=REATANCIA_SUBTRANSITORIA, altitude=0.0,
                temperatura_local=TEMPERATURA_SEM_REDUCAO, autonomia=AUTONOMIA_PADRAO,
                consumo_especifico=CONSUMO_ESPECIFICO):
    """Gerador, disjuntor, cabos e tanque para as cargas.

    Args:
        cargas: dicionários de ``carga``; as com ``no_gerador`` falso ficam de fora.
        tensao: tensão entre fases [V].
        fator_diversidade: soma das demandas / demanda máxima do conjunto (≥ 1).
        carregamento: fração máxima da potência do gerador usada pela demanda.
        comprimento: do gerador ao quadro de transferência [m].
        afundamento: afundamento de tensão admissível na partida do maior motor [%].
        reatancia: reatância subtransitória x″d do alternador [pu].
    Returns:
        dict com as cargas, as somas, os três critérios de potência, o gerador
        e os dados do cabo, do disjuntor e do tanque.
    Raises:
        ValueError: sem cargas no gerador ou dados fora da faixa.
    """
    usadas = [c for c in cargas if c["no_gerador"] and c["kw"] > 0]
    if not usadas:
        raise ValueError("Nenhuma carga no gerador. Preencha a planilha de cargas (coluna I = S).")
    if fator_diversidade < 1.0:
        raise ValueError("O fator de diversidade é a soma das demandas dividida pela demanda máxima: use 1 ou mais.")
    if not 0.1 <= carregamento <= 1.0:
        raise ValueError("O carregamento do gerador fica entre 0,1 e 1.")
    if not 1.0 <= afundamento <= 50.0:
        raise ValueError("O afundamento admissível fica entre 1 e 50 %.")

    linhas = []
    for c in usadas:
        instalada = c["kw"] * c["quantidade"]
        demanda = instalada * c["fator_demanda"]
        reativa = demanda * math.tan(math.acos(c["fator_potencia"]))
        linhas.append(dict(c, instalada_kw=instalada, demanda_kw=demanda, demanda_kvar=reativa,
                           demanda_kva=math.hypot(demanda, reativa)))

    instalada_kw = sum(l["instalada_kw"] for l in linhas)
    soma_demandas_kw = sum(l["demanda_kw"] for l in linhas)
    demanda_kw = soma_demandas_kw / fator_diversidade
    demanda_kvar = sum(l["demanda_kvar"] for l in linhas) / fator_diversidade
    demanda_kva = math.hypot(demanda_kw, demanda_kvar)
    nao_linear_kva = sum(l["demanda_kva"] for l in linhas if l["nao_linear"]) / fator_diversidade
    fp_medio = demanda_kw / demanda_kva if demanda_kva else 1.0

    disponivel = reducao(altitude, temperatura_local)
    equivalente = demanda_kva + (FATOR_NAO_LINEAR - 1.0) * nao_linear_kva
    criterios = {
        "demanda_kva": equivalente / carregamento / disponivel,
        "demanda_kw": demanda_kw / (FATOR_POTENCIA_GERADOR * carregamento) / disponivel,
    }
    motores_ = [l for l in linhas if l["motor"]]
    maior = max(motores_, key=lambda l: l["kva"] * PARTIDAS[l["partida"]], default=None)
    partida_kva = maior["kva"] * PARTIDAS[maior["partida"]] if maior else 0.0
    if maior:
        dv = afundamento / 100.0
        criterios["partida_motor"] = reatancia * partida_kva * (1.0 - dv) / dv / disponivel
    decisivo = max(criterios, key=criterios.get)
    necessario = criterios[decisivo]
    gerador = gerador_comercial(necessario)

    corrente = gerador * 1000.0 / (math.sqrt(3) * tensao)
    protecao = disjuntor(corrente)
    condutor = cabo(protecao, corrente, comprimento, tensao, metodo, isolacao, temperatura_cabo, queda_max)
    afundamento_real = (100.0 * reatancia * partida_kva / (gerador * disponivel + reatancia * partida_kva)
                        if maior else 0.0)
    consumo = demanda_kw * consumo_especifico
    return {
        "cargas": linhas,
        "instalada_kw": instalada_kw,
        "soma_demandas_kw": soma_demandas_kw,
        "fator_diversidade": fator_diversidade,
        "demanda_kw": demanda_kw,
        "demanda_kvar": demanda_kvar,
        "demanda_kva": demanda_kva,
        "fator_potencia": fp_medio,
        "nao_linear_kva": nao_linear_kva,
        "maior_motor": maior,
        "partida_kva": partida_kva,
        "carregamento": carregamento,
        "reducao": disponivel,
        "criterios": criterios,
        "criterio": decisivo,
        "necessario_kva": necessario,
        "gerador_kva": gerador,
        "gerador_kw": gerador * FATOR_POTENCIA_GERADOR,
        "carregamento_real": demanda_kva / (gerador * disponivel),
        "afundamento": afundamento_real,
        "tensao": tensao,
        "corrente": corrente,
        "disjuntor": protecao,
        "cabo": condutor,
        "metodo": metodo,
        "isolacao": "PVC" if _isolacao(isolacao) == "PVC" else "EPR",
        "comprimento": comprimento,
        "neutro": condutor["secao"],
        "protecao": condutor_protecao(condutor["secao"]),
        "curto_ka": corrente / reatancia / 1000.0,
        "consumo_lh": consumo,
        "autonomia": autonomia,
        "tanque_l": math.ceil(consumo * autonomia * MARGEM_TANQUE / 10.0) * 10,
    }


_NOMES_CRITERIO = {
    "demanda_kva": "demanda em kVA",
    "demanda_kw": "demanda em kW (gerador com FP 0,8)",
    "partida_motor": "partida do maior motor",
}


def _br(valor, casas=1):
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def relatorio(r):
    """Texto do cálculo, para mostrar ao usuário."""
    linhas = ["CARGAS NO GERADOR"]
    for c in r["cargas"]:
        qtd = f"{c['quantidade']:g} x " if c["quantidade"] != 1 else ""
        extra = f", partida {c['partida'].lower()}" if c["motor"] else ""
        linhas.append(f"  {c['descricao']}: {qtd}{_br(c['kw'], 2)} kW, FP {_br(c['fator_potencia'], 2)}, "
                      f"FD {_br(c['fator_demanda'], 2)} → {_br(c['demanda_kw'], 2)} kW{extra}")
    linhas += [
        "",
        f"Potência instalada: {_br(r['instalada_kw'])} kW",
        f"Soma das demandas: {_br(r['soma_demandas_kw'])} kW ÷ diversidade {_br(r['fator_diversidade'], 2)}",
        f"Demanda máxima: {_br(r['demanda_kw'])} kW, {_br(r['demanda_kva'])} kVA (FP {_br(r['fator_potencia'], 2)})",
    ]
    if r["nao_linear_kva"]:
        linhas.append(f"Cargas não lineares: {_br(r['nao_linear_kva'])} kVA (contam {_br(FATOR_NAO_LINEAR)} vez)")
    if r["maior_motor"]:
        m = r["maior_motor"]
        linhas.append(f"Maior partida: {m['descricao']} ({m['partida'].lower()}), {_br(r['partida_kva'])} kVA")
    if r["reducao"] < 1.0:
        linhas.append(f"Redução por altitude e temperatura: potência disponível {r['reducao'] * 100:.0f} %")
    linhas += ["", "POTÊNCIA NECESSÁRIA"]
    for nome, valor in r["criterios"].items():
        marca = "  ← decide" if nome == r["criterio"] else ""
        linhas.append(f"  pela {_NOMES_CRITERIO[nome]}: {_br(valor)} kVA{marca}")
    linhas += [
        "",
        f"GERADOR: {r['gerador_kva']} kVA / {_br(r['gerador_kw'], 0)} kW, {r['tensao']:.0f} V, FP 0,8",
        f"  carregamento com a demanda máxima: {r['carregamento_real'] * 100:.0f} %"
        f" (limite {r['carregamento'] * 100:.0f} %)",
    ]
    if r["maior_motor"]:
        linhas.append(f"  afundamento na partida do maior motor: {_br(r['afundamento'])} %")
    cabo_ = r["cabo"]
    arranjo = f"{cabo_['paralelos']} x "
    linhas += [
        f"  corrente nominal: {_br(r['corrente'])} A",
        f"  curto-circuito nos terminais (estimado): {_br(r['curto_ka'], 1)} kA",
        "",
        f"DISJUNTOR DO GERADOR: {r['disjuntor']} A, tripolar",
        f"CABOS ({r['isolacao']}, método {r['metodo']}, {_br(r['comprimento'], 0)} m até a transferência):",
        f"  fases: {arranjo}{cabo_['secao']} mm² por fase (Iz {_br(cabo_['iz'])} A, queda {_br(cabo_['queda'], 2)} %,"
        f" definido pela {'queda de tensão' if cabo_['criterio'] == 'queda_tensao' else 'capacidade'})",
        f"  neutro: {arranjo}{r['neutro']} mm²",
        f"  proteção (PE): {arranjo}{r['protecao']} mm²",
        "",
        f"DIESEL: cerca de {_br(r['consumo_lh'])} L/h com a demanda máxima; tanque de {r['tanque_l']} L"
        f" para {r['autonomia']:g} h",
        "",
        "Pré-dimensionamento com regras usuais. Confirme a potência, a reatância e a redução no catálogo",
        "do fabricante, e o tanque com o Corpo de Bombeiros e a NBR 17505.",
    ]
    return "\n".join(linhas)


# --- planilha de cargas -----------------------------------------------------

LINHA_TITULOS = 2
PRIMEIRA_LINHA = 3
# (coluna, chave do argumento de ``carga``, título)
COLUNAS = [
    ("A", "descricao", "Descrição"),
    ("B", "tipo", "Tipo"),
    ("C", "quantidade", "Quantidade"),
    ("D", "potencia", "Potência (cada)"),
    ("E", "unidade", "Unidade (kW, kVA ou cv)"),
    ("F", "fator_potencia", "Fator de potência"),
    ("G", "fator_demanda", "Fator de demanda"),
    ("H", "partida", "Partida do motor"),
    ("I", "no_gerador", "No gerador (S/N)"),
]
AJUDA = ("Uma carga por linha. Em branco: quantidade 1, FP típico do tipo, demanda 1, partida direta. "
         "Tipos: " + "; ".join(TIPOS) + ". Partidas: " + "; ".join(PARTIDAS) + ".")
EXEMPLOS = [
    {"descricao": "Iluminação de emergência e áreas comuns", "tipo": "Iluminação e tomadas", "potencia": "5",
     "unidade": "kW", "fator_demanda": "1"},
    {"descricao": "Bomba de recalque", "tipo": "Motor (bomba, ventilador, compressor)", "quantidade": "2",
     "potencia": "5", "unidade": "cv", "fator_demanda": "0,5", "partida": "Direta"},
    {"descricao": "Elevador", "tipo": "Elevador", "potencia": "15", "unidade": "cv",
     "partida": "Inversor de frequência"},
    {"descricao": "Pressurização de escada", "tipo": "Motor (bomba, ventilador, compressor)", "potencia": "10",
     "unidade": "cv", "partida": "Soft-starter"},
]


def carga_da_linha(celulas):
    """Carga de uma linha da planilha (textos por chave de ``COLUNAS``)."""
    return carga(**{chave: celulas.get(chave, "") for _, chave, _ in COLUNAS})


def linhas_dos_quadros(quadros):
    """Uma linha da planilha por quadro do projeto.

    Args:
        quadros: [(nome, potência instalada [kW], demanda [kW] ou None)].
    Returns:
        Dicionários com as chaves de ``COLUNAS``; o fator de demanda é a
        demanda / instalada, quando a demanda do quadro já foi calculada.
    """
    linhas = []
    for nome, instalada, demanda in quadros:
        if not instalada:
            continue
        fd = min(1.0, demanda / instalada) if demanda else 1.0
        linhas.append({"descricao": nome, "tipo": TIPO_PADRAO, "quantidade": "1", "potencia": f"{instalada:g}",
                       "unidade": "kW", "fator_demanda": f"{fd:.2f}".replace(".", ","), "no_gerador": "S"})
    return linhas


def resumo(r):
    """[(rótulo, valor)] do resultado, gravados ao lado da planilha de cargas."""
    cabo_ = r["cabo"]
    return [
        ("Demanda máxima [kW]", f"{r['demanda_kw']:.1f}"),
        ("Demanda máxima [kVA]", f"{r['demanda_kva']:.1f}"),
        ("Gerador [kVA]", str(r["gerador_kva"])),
        ("Gerador [kW]", f"{r['gerador_kw']:.0f}"),
        ("Corrente nominal [A]", f"{r['corrente']:.1f}"),
        ("Disjuntor [A]", str(r["disjuntor"])),
        ("Cabos por fase", f"{cabo_['paralelos']} x {cabo_['secao']} mm²"),
        ("Neutro", f"{cabo_['paralelos']} x {r['neutro']} mm²"),
        ("Proteção (PE)", f"{cabo_['paralelos']} x {r['protecao']} mm²"),
        ("Queda de tensão [%]", f"{cabo_['queda']:.2f}"),
        ("Tanque de diesel [L]", str(r["tanque_l"])),
        ("Tensão [V]", f"{r['tensao']:.0f}"),
        ("Cabo", f"{r['isolacao']}, método {r['metodo']}, {r['comprimento']:.0f} m"),
    ]


def quadro_geral(quadros, siglas_qta=(), cargas=()):
    """Quadro alimentado pelo QTA, ligado ao diagrama da transferência.

    Args:
        quadros: [(nome do quadro, origem escrita na planilha do quadro)].
        siglas_qta: siglas (``Descricao``) dos símbolos de QTA da planta.
        cargas: descrições das cargas ligadas ao gerador.
    Returns:
        O nome do quadro cuja origem é o QTA (começa com "QTA" ou é a sigla de um
        QTA da planta); senão, o único quadro que está entre as cargas do gerador;
        senão None.
    """
    siglas = {str(s).strip().lower() for s in siglas_qta if str(s).strip()}
    for nome, origem in quadros:
        texto = str(origem).strip().lower()
        if texto and (texto.startswith("qta") or texto in siglas):
            return nome
    nas_cargas = {str(c).strip().lower() for c in cargas}
    candidatos = [nome for nome, _ in quadros if str(nome).strip().lower() in nas_cargas]
    return candidatos[0] if len(candidatos) == 1 else None
