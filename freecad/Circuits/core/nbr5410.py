"""Dimensionamento de circuitos pela NBR 5410:2004, sem FreeCAD.

Critérios verificados em ``dimensionar_circuito``:

1. seção mínima (tabela 47): 1,5 mm² na iluminação, 2,5 mm² nos outros circuitos;
2. capacidade de condução corrigida pela temperatura (tabela 40) e pelo
   agrupamento (tabela 42), com Ib ≤ In ≤ Iz;
3. queda de tensão até o ponto mais distante;
4. curto-circuito: S ≥ I·√t / k (k da tabela 30), quando a corrente de curto é dada.

``seccionamento_ok`` verifica o seccionamento automático no esquema TN
(contatos indiretos); com DR o circuito está protegido.

Tabelas de condutores de cobre, transcritas da norma; o método F usa os
valores do método E (conservador) até a tabela 39 ser transcrita.

Unidades: correntes em A, seções em mm², comprimentos em m, tensões em V,
quedas em %, temperaturas em °C, tempo em s.
"""
import math

SECOES = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120]
DISJUNTORES = [6, 10, 16, 20, 25, 32, 40, 50, 63, 70, 80, 100, 125]
SECAO_MINIMA = {"ILUM": 1.5}
SECAO_MINIMA_PADRAO = 2.5
RESISTIVIDADE_COBRE = 1 / 56  # Ω·mm²/m, em serviço
RESISTIVIDADE_COBRE_CURTO = 0.0225  # Ω·mm²/m, na temperatura de curto (seccionamento)
K_CURTO = {("cobre", "PVC"): 115, ("cobre", "EPR"): 143, ("cobre", "XLPE"): 143,
           ("aluminio", "PVC"): 76, ("aluminio", "EPR"): 94, ("aluminio", "XLPE"): 94}
MULTIPLO_DISPARO = {"B": 5, "C": 10, "D": 20}  # Ia / In, limite superior do disparo magnético
FATOR_TENSAO_SECCIONAMENTO = 0.8

# Capacidade [A] por (isolação, método, condutores carregados): uma por seção de SECOES.
_CAPACIDADE = {
    # tabela 36, PVC
    ("PVC", "A1", 2): [14.5, 19.5, 26, 34, 46, 61, 80, 99, 119, 151, 182, 210],
    ("PVC", "A1", 3): [13.5, 18, 24, 31, 42, 56, 73, 89, 108, 136, 164, 188],
    ("PVC", "B1", 2): [17.5, 24, 32, 41, 57, 76, 101, 125, 151, 192, 232, 269],
    ("PVC", "B1", 3): [15.5, 21, 28, 36, 50, 68, 89, 110, 134, 171, 207, 239],
    ("PVC", "B2", 2): [16.5, 23, 30, 38, 52, 69, 90, 111, 133, 168, 201, 232],
    ("PVC", "B2", 3): [15, 20, 27, 34, 46, 62, 80, 99, 118, 149, 179, 206],
    ("PVC", "C", 2): [19.5, 27, 36, 46, 63, 85, 112, 138, 168, 213, 258, 299],
    ("PVC", "C", 3): [17.5, 24, 32, 41, 57, 76, 96, 119, 144, 184, 223, 259],
    ("PVC", "D", 2): [22, 29, 38, 47, 63, 81, 104, 125, 148, 183, 216, 246],
    ("PVC", "D", 3): [18, 24, 31, 39, 52, 67, 86, 103, 122, 151, 179, 203],
    # tabela 38, PVC, cabo multipolar ao ar livre
    ("PVC", "E", 2): [22, 30, 40, 51, 70, 94, 119, 148, 180, 232, 282, 328],
    ("PVC", "E", 3): [18.5, 25, 34, 43, 60, 80, 101, 126, 153, 196, 238, 276],
    # tabela 37, EPR/XLPE
    ("EPR", "B1", 2): [23, 31, 42, 54, 75, 100, 133, 164, 198, 253, 306, 354],
    ("EPR", "B1", 3): [20, 28, 37, 48, 66, 88, 117, 144, 175, 222, 269, 312],
    ("EPR", "C", 2): [24, 33, 45, 58, 80, 107, 138, 171, 209, 269, 328, 382],
    ("EPR", "C", 3): [22, 30, 40, 52, 71, 96, 119, 147, 179, 229, 278, 322],
}

# Tabela 40: fator de temperatura ambiente (linhas não subterrâneas).
_FCT = {
    "PVC": {10: 1.22, 15: 1.17, 20: 1.12, 25: 1.06, 30: 1.00, 35: 0.94, 40: 0.87, 45: 0.79, 50: 0.71, 55: 0.61,
            60: 0.50},
    "EPR": {10: 1.15, 15: 1.12, 20: 1.08, 25: 1.04, 30: 1.00, 35: 0.96, 40: 0.91, 45: 0.87, 50: 0.82, 55: 0.76,
            60: 0.71, 65: 0.65, 70: 0.58, 75: 0.50, 80: 0.41},
}

# Tabela 42, referência 1: em feixe ao ar livre ou em conduto fechado. (até n circuitos, fator)
_FCA_FEIXE = [(1, 1.00), (2, 0.80), (3, 0.70), (4, 0.65), (5, 0.60), (6, 0.57), (7, 0.54), (8, 0.52), (11, 0.50),
              (15, 0.45), (19, 0.41)]
_FCA_FEIXE_MAIS = 0.38

FECHADOS = ("eletroduto", "eletrocalha_lisa")
ABERTOS = ("eletrocalha_perfurada", "leito")


def _isolacao(isolacao):
    """XLPE tem as mesmas tabelas do EPR."""
    return "EPR" if str(isolacao).upper() in ("EPR", "XLPE") else "PVC"


def capacidade(secao, metodo="B1", carregados=2, isolacao="PVC"):
    """Capacidade de condução [A] do condutor de cobre, a 30 °C, sem agrupamento.

    Raises:
        ValueError: seção, método ou combinação fora das tabelas.
    """
    metodo = "E" if metodo == "F" else metodo  # conservador, ver o docstring do módulo
    chave = (_isolacao(isolacao), metodo, 3 if int(carregados) >= 3 else 2)
    if chave not in _CAPACIDADE:
        raise ValueError(f"Sem tabela para {chave[0]}, método {metodo}, {chave[2]} condutores carregados.")
    secao = float(secao)
    if secao not in SECOES:
        raise ValueError(f"Seção {secao:g} mm² fora da tabela.")
    return _CAPACIDADE[chave][SECOES.index(secao)]


def fct(temperatura, isolacao="PVC"):
    """Fator de correção de temperatura ambiente (tabela 40).

    Temperatura entre duas linhas usa a de cima (mais quente), a favor da segurança.
    """
    tabela = _FCT[_isolacao(isolacao)]
    for limite in sorted(tabela):
        if float(temperatura) <= limite:
            return tabela[limite]
    raise ValueError(f"Temperatura de {temperatura} °C acima da tabela para {isolacao}.")


def fca(circuitos):
    """Fator de agrupamento para circuitos em feixe ou em conduto fechado (tabela 42)."""
    n = max(1, int(circuitos))
    return next((fator for ate, fator in _FCA_FEIXE if n <= ate), _FCA_FEIXE_MAIS)


def metodo_do_trajeto(tipos, multipolar=False):
    """Método de instalação do pior trecho do trajeto.

    Args:
        tipos: tipo de cada trecho ('eletroduto', 'eletrocalha_lisa',
            'eletrocalha_perfurada', 'leito').
        multipolar: o circuito usa cabo multipolar.
    Returns:
        'B1' se algum trecho é conduto fechado (ou não há trajeto); senão 'E'
        (multipolar) ou 'F' (unipolares) para bandeja aberta e leito.
    """
    tipos = list(tipos)
    if not tipos or any(t not in ABERTOS for t in tipos):
        return "B1"
    return "E" if multipolar else "F"


def exige_cabo(tipos):
    """O trajeto passa por bandeja aberta ou leito: condutor isolado não serve, só cabo 0,6/1 kV."""
    return any(t in ABERTOS for t in tipos)


def queda_tensao(corrente, comprimento, secao, tensao, n_fases=1, resistividade=RESISTIVIDADE_COBRE):
    """Queda de tensão [%] no fim do circuito, só pela resistência.

    Monofásico ou fase-fase: 2·ρ·L·I/S; trifásico: √3·ρ·L·I/S.
    """
    fator = math.sqrt(3) if int(n_fases) == 3 else 2.0
    volts = fator * resistividade * float(comprimento) * float(corrente) / float(secao)
    return volts / float(tensao) * 100.0


def queda_total_ok(queda_alimentador, queda_circuito, limite=7.0):
    """A queda desde a entrada (alimentador + circuito terminal) está dentro do limite."""
    return float(queda_alimentador) + float(queda_circuito) <= float(limite) + 1e-9


def secao_curto(corrente, tempo, isolacao="PVC", material="cobre"):
    """Seção mínima [mm²] para suportar o curto: S ≥ I·√t / k."""
    k = K_CURTO[(material, "EPR" if _isolacao(isolacao) == "EPR" else "PVC")]
    return float(corrente) * math.sqrt(float(tempo)) / k


def secao_comercial(valor):
    """Menor seção comercial maior ou igual ao valor."""
    secao = next((s for s in SECOES if s >= float(valor) - 1e-9), None)
    if secao is None:
        raise ValueError(f"Seção de {valor:.1f} mm² acima da tabela.")
    return secao


def comprimento_maximo_tn(tensao_fn, secao_fase, secao_pe, disjuntor, curva="C"):
    """Comprimento máximo [m] para o disjuntor seccionar no esquema TN.

    L = 0,8·U0·Sf / (ρ·(1 + m)·Ia), com m = Sf / Spe e Ia = múltiplo da curva × In.
    """
    corrente_disparo = MULTIPLO_DISPARO.get(str(curva).upper(), MULTIPLO_DISPARO["C"]) * float(disjuntor)
    m = float(secao_fase) / float(secao_pe)
    return (FATOR_TENSAO_SECCIONAMENTO * float(tensao_fn) * float(secao_fase)
            / (RESISTIVIDADE_COBRE_CURTO * (1 + m) * corrente_disparo))


def seccionamento_ok(comprimento, tensao_fn, secao_fase, secao_pe, disjuntor, curva="C", com_dr=False):
    """Proteção contra contatos indiretos no TN: pelo DR ou pelo comprimento máximo do disjuntor."""
    return bool(com_dr) or float(comprimento) <= comprimento_maximo_tn(tensao_fn, secao_fase, secao_pe, disjuntor,
                                                                       curva)


_PRIORIDADE = ["curto_circuito", "queda_tensao", "capacidade", "secao_minima"]


def dimensionar_circuito(corrente, tipo, comprimento, tensao, n_fases=1, metodo="B1", agrupados=1, temperatura=30.0,
                         isolacao="PVC", queda_max=4.0, icc_ka=None, tempo_curto=0.1, material="cobre"):
    """Disjuntor e seção do circuito pelos critérios da NBR 5410.

    Args:
        corrente: corrente de projeto Ib [A].
        tipo: 'ILUM', 'TUG' ou 'TUE'.
        comprimento: do quadro ao ponto mais distante [m].
        tensao: tensão entre os condutores do circuito [V].
        metodo: método de instalação (``metodo_do_trajeto``).
        agrupados: circuitos no trecho mais cheio do trajeto.
        icc_ka: corrente de curto no quadro [kA]; None não verifica o curto.
    Returns:
        dict com ``corrente``, ``disjuntor``, ``secao``, ``criterio`` (o que
        determinou a seção: 'secao_minima', 'capacidade', 'queda_tensao' ou
        'curto_circuito'), ``fator`` (FCT·FCA), ``iz`` [A], ``queda`` [%] e ``metodo``.
    Raises:
        ValueError: corrente acima do maior disjuntor ou nenhuma seção atende.
    """
    disjuntor = next((d for d in DISJUNTORES if d >= float(corrente)), None)
    if disjuntor is None:
        raise ValueError(f"Corrente de {corrente:.1f} A acima do maior disjuntor ({DISJUNTORES[-1]} A).")
    carregados = 3 if int(n_fases) == 3 else 2
    fator = round(fct(temperatura, isolacao) * fca(agrupados), 4)

    def primeira(condicao):
        return next((s for s in SECOES if condicao(s)), None)

    exigidas = {
        "secao_minima": SECAO_MINIMA.get(str(tipo).upper(), SECAO_MINIMA_PADRAO),
        "capacidade": primeira(lambda s: capacidade(s, metodo, carregados, isolacao) * fator >= disjuntor),
        "queda_tensao": primeira(lambda s: queda_tensao(corrente, comprimento, s, tensao, n_fases) <= queda_max),
    }
    if icc_ka:
        exigidas["curto_circuito"] = secao_comercial(secao_curto(float(icc_ka) * 1000, tempo_curto, isolacao, material))
    faltando = [nome for nome, secao in exigidas.items() if secao is None]
    if faltando:
        raise ValueError(f"Nenhuma seção da tabela atende: {', '.join(faltando)}.")

    secao = max(exigidas.values())
    criterio = next(nome for nome in _PRIORIDADE if exigidas.get(nome) == secao)
    return {
        "corrente": float(corrente),
        "disjuntor": disjuntor,
        "secao": secao,
        "criterio": criterio,
        "fator": fator,
        "iz": round(capacidade(secao, metodo, carregados, isolacao) * fator, 2),
        "queda": round(queda_tensao(corrente, comprimento, secao, tensao, n_fases), 2),
        "metodo": metodo,
    }
