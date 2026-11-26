"""Estudo de curto-circuito em baixa tensão pela IEC 60909 (método das impedâncias).

Impedâncias em mΩ, referidas à baixa tensão; correntes em kA; tensões de linha em V
(com mΩ e V, ``U / Z`` já sai em kA).

- **Rede:** Zq = c·U²/S″kQ, com c = 1,1; Xq = 0,995·Zq e Rq = 0,1·Xq.
- **Transformador:** ZT = uk·U²/SrT, RT = Pcu·U²/SrT², XT = √(ZT² − RT²), corrigidas
  por KT = 0,95·cmáx / (1 + 0,6·xT) (cmáx = 1,05; xT = XT em p.u. da base do transformador).
- **Cabo:** R = ρ·L/S a 20 °C (cobre, ``RESISTIVIDADE_COBRE``), corrigida por
  1 + 0,004·(θ − 20) para o curto mínimo; X por metro (``REATANCIA_CABO``); ramos em
  paralelo dividem as duas.
- **Correntes:** I″k3 = cmáx·U / (√3·|Z|), cmáx = 1,05; ip = κ·√2·I″k3 com
  κ = 1,02 + 0,98·e^(−3R/X); fase-terra mínima I″k1 = cmín·U0 / |Zfase + ZPE|, cmín = 0,95.

Valores de reatância de cabo e a lista de capacidades de interrupção são usuais, não de
um fabricante. Não trata contribuição de motores nem curto bifásico.
"""
import math

C_MAX = 1.05
C_REDE = 1.1
C_MIN = 0.95
RESISTIVIDADE_COBRE = 1000.0 / 54.0  # mΩ·mm²/m a 20 °C
RESISTIVIDADE_ALUMINIO = 1000.0 / 34.0
REATANCIA_CABO = 0.08  # mΩ/m, cabo unipolar em trifólio
ALFA = 0.004  # 1/°C
CAPACIDADES_KA = [3, 4.5, 6, 10, 15, 20, 25, 36, 50, 65, 70, 85, 100, 150]


def impedancia_rede(potencia_curto_mva, tensao):
    """(R, X) [mΩ] da rede pela potência de curto no ponto de entrega [MVA]."""
    z = C_REDE * tensao ** 2 / (float(potencia_curto_mva) * 1e6) * 1e3
    x = 0.995 * z
    return 0.1 * x, x


def impedancia_transformador(potencia_kva, tensao, uk, perdas_cobre_w=0.0):
    """(R, X) [mΩ] do transformador, já com o fator de correção KT.

    Args:
        potencia_kva: potência nominal.
        uk: tensão de curto-circuito [%].
        perdas_cobre_w: perdas no cobre a plena carga [W]; 0 despreza a resistência.
    """
    s = float(potencia_kva) * 1e3
    base = tensao ** 2 / s * 1e3  # mΩ
    z = float(uk) / 100.0 * base
    r = float(perdas_cobre_w) * tensao ** 2 / s ** 2 * 1e3
    x = math.sqrt(max(z * z - r * r, 0.0))
    kt = 0.95 * C_MAX / (1 + 0.6 * x / base)
    return r * kt, x * kt


def impedancia_cabo(secao, comprimento, paralelos=1, temperatura=20.0, material="cobre",
                    reatancia=REATANCIA_CABO):
    """(R, X) [mΩ] de um cabo de ``secao`` [mm²] e ``comprimento`` [m], na temperatura [°C]."""
    rho = RESISTIVIDADE_COBRE if material == "cobre" else RESISTIVIDADE_ALUMINIO
    paralelos = max(int(paralelos), 1)
    r = rho * float(comprimento) / float(secao) * (1 + ALFA * (float(temperatura) - 20.0))
    return r / paralelos, float(reatancia) * float(comprimento) / paralelos


def curto_trifasico(r, x, tensao, c=C_MAX):
    """I″k3 [kA] com a impedância (R, X) [mΩ] até o ponto."""
    return c * tensao / (math.sqrt(3) * math.hypot(r, x))


def fator_pico(r, x):
    """κ = 1,02 + 0,98·e^(−3R/X), entre 1,02 e 2."""
    if x <= 0:
        return 1.02
    return 1.02 + 0.98 * math.exp(-3.0 * r / x)


def corrente_pico(ik, r, x):
    """ip [kA] = κ·√2·I″k."""
    return fator_pico(r, x) * math.sqrt(2) * ik


def curto_minimo_fase_terra(r_fase, x_fase, r_pe, x_pe, tensao_fase, c=C_MIN):
    """I″k1 mínima [kA] pelo laço fase-proteção: cmín·U0 / |Zfase + ZPE| (mΩ, V)."""
    return c * tensao_fase / abs(complex(r_fase + r_pe, x_fase + x_pe))


def capacidade_interrupcao(ik):
    """Menor capacidade de interrupção comercial [kA] ≥ I″k3."""
    for valor in CAPACIDADES_KA:
        if valor >= ik - 1e-9:
            return valor
    raise ValueError(f"curto de {ik:.1f} kA acima das capacidades de interrupção da lista")


def _impedancia_da_barra(barra, tensao, temperatura=20.0):
    r = x = 0.0
    if barra.get("rede_mva"):
        dr, dx = impedancia_rede(barra["rede_mva"], tensao)
        r, x = r + dr, x + dx
    if barra.get("transformador"):
        t = barra["transformador"]
        dr, dx = impedancia_transformador(t["potencia_kva"], tensao, t["uk"], t.get("perdas_cobre_w", 0.0))
        r, x = r + dr, x + dx
    if barra.get("cabo"):
        c = barra["cabo"]
        dr, dx = impedancia_cabo(c["secao"], c["comprimento"], c.get("paralelos", 1), temperatura,
                                 c.get("material", "cobre"))
        r, x = r + dr, x + dx
    return r, x


def estudo(barras, tensao):
    """Curto em cada barra, somando as impedâncias de cima (origem) até ela.

    Args:
        barras: [{'nome', 'origem' ('' na entrada), e 'rede_mva', 'transformador'
            {'potencia_kva', 'uk', 'perdas_cobre_w'} e/ou 'cabo' {'secao', 'comprimento',
            'paralelos', 'material'}}].
        tensao: tensão de linha [V].
    Returns:
        {nome: {'r', 'x' [mΩ], 'ik3', 'ip', 'ik1_min' [kA], 'icu_minimo' [kA], 'origem'}}.
        ``ik1_min`` usa os cabos a 80 °C e um condutor de proteção igual à fase (estimativa).
    """
    por_nome = {b["nome"]: b for b in barras}
    resultado, visitando = {}, set()

    def calcular(nome):
        if nome in resultado:
            return resultado[nome]
        if nome not in por_nome:
            raise ValueError(f"barra de origem que não existe: {nome}")
        if nome in visitando:
            raise ValueError(f"origem em ciclo na barra {nome}")
        visitando.add(nome)
        barra = por_nome[nome]
        r, x = _impedancia_da_barra(barra, tensao)
        rq, xq = _impedancia_da_barra(barra, tensao, temperatura=80.0)
        r_pe = 0.0
        if barra.get("origem"):
            cima = calcular(barra["origem"])
            r, x = r + cima["r"], x + cima["x"]
            rq, xq = rq + cima["_r_quente"], xq + cima["_x_quente"]
            r_pe = cima["_r_pe"]
        if barra.get("cabo"):
            c = barra["cabo"]
            r_pe += impedancia_cabo(c["secao"], c["comprimento"], c.get("paralelos", 1), 80.0,
                                    c.get("material", "cobre"))[0]
        ik3 = curto_trifasico(r, x, tensao)
        dados = {"origem": barra.get("origem", ""), "r": r, "x": x, "ik3": ik3,
                 "ip": corrente_pico(ik3, r, x),
                 "ik1_min": curto_minimo_fase_terra(rq, xq, r_pe, 0.0, tensao / math.sqrt(3)),
                 "icu_minimo": capacidade_interrupcao(ik3),
                 "_r_quente": rq, "_x_quente": xq, "_r_pe": r_pe}
        resultado[nome] = dados
        visitando.discard(nome)
        return dados

    for barra in barras:
        calcular(barra["nome"])
    return {nome: {k: v for k, v in dados.items() if not k.startswith("_")} for nome, dados in resultado.items()}


def _br(valor, casas=2):
    return f"{valor:.{casas}f}".replace(".", ",")


def relatorio(resultado):
    """Texto do estudo, uma linha por barra."""
    linhas = ["Barra: I″k3 · ip · I″k1 mín (fase-terra) · capacidade de interrupção mínima"]
    for nome, d in resultado.items():
        linhas.append(f"{nome}: {_br(d['ik3'])} kA · {_br(d['ip'])} kA · {_br(d['ik1_min'])} kA · "
                      f"Icu ≥ {_br(d['icu_minimo'], 1).rstrip('0').rstrip(',')} kA")
    linhas.append("IEC 60909 (cmáx 1,05, cmín 0,95); PE igual à fase; sem contribuição de motores.")
    return "\n".join(linhas)



# --- planilha "Estudo de curto" -----------------------------------------------------------------

AJUDA = ("Uma barra por linha. A entrada (sem origem) leva a rede e, se houver, o transformador; as outras, "
         "o cabo que vem da barra de origem. Depois clique de novo em Curto-circuito.")
COLUNAS_ESTUDO = [
    ("A", "nome", "Barra"),
    ("B", "origem", "Origem (barra de cima)"),
    ("C", "rede_mva", "Rede: Scc [MVA]"),
    ("D", "trafo_kva", "Transformador [kVA]"),
    ("E", "uk", "uk [%]"),
    ("F", "perdas_cobre_w", "Perdas no cobre [W]"),
    ("G", "secao", "Cabo [mm²]"),
    ("H", "comprimento", "Comprimento [m]"),
    ("I", "paralelos", "Cabos em paralelo"),
    ("J", "material", "Material (cobre/alumínio)"),
]
COLUNAS_RESULTADO = [("L", "ik3", "I″k3 [kA]"), ("M", "ip", "ip [kA]"), ("N", "ik1_min", "I″k1 mín [kA]"),
                     ("O", "icu_minimo", "Icu mínima [kA]")]
CELULA_ROTULO_TENSAO, CELULA_TENSAO = "Q1", "R1"
LINHA_TITULOS, PRIMEIRA_LINHA = 2, 3
TENSAO_PADRAO = 380.0
ENTRADA = "Entrada"
EXEMPLO_ENTRADA = {"nome": ENTRADA, "rede_mva": "500", "trafo_kva": "1000", "uk": "5", "perdas_cobre_w": "10500"}
COMPRIMENTO_PADRAO_M = "10"


def linhas_dos_quadros(quadros):
    """Linhas iniciais: a entrada (exemplo de rede e transformador) e uma barra por quadro.

    Args:
        quadros: [(nome, origem, seção do cabo de entrada)] (textos; origem que não é
            outro quadro vira a entrada).
    """
    nomes = {nome for nome, _, _ in quadros}
    linhas = [dict(EXEMPLO_ENTRADA)]
    for nome, origem, secao in quadros:
        linhas.append({"nome": nome, "origem": origem if origem in nomes and origem != nome else ENTRADA,
                       "secao": secao or "10", "comprimento": COMPRIMENTO_PADRAO_M, "paralelos": "1",
                       "material": "cobre"})
    return linhas


def _numero(texto, linha, rotulo, obrigatorio=False):
    texto = str(texto or "").strip().replace(",", ".")
    if not texto:
        if obrigatorio:
            raise ValueError(f"Linha {linha}: falta {rotulo}.")
        return None
    try:
        return float(texto)
    except ValueError:
        raise ValueError(f"Linha {linha}: {rotulo} não é um número ({texto}).") from None


def barras_das_linhas(linhas):
    """Barras de ``estudo`` a partir das linhas da planilha.

    Args:
        linhas: [(número da linha, {chave de COLUNAS_ESTUDO: texto})].
    Raises:
        ValueError com o número da linha, se faltar dado ou um número não for número.
    """
    barras = []
    for numero_linha, c in linhas:
        nome = str(c.get("nome", "")).strip()
        if not nome:
            continue
        barra = {"nome": nome, "origem": str(c.get("origem", "")).strip()}
        rede = _numero(c.get("rede_mva"), numero_linha, "a potência de curto da rede")
        if rede:
            barra["rede_mva"] = rede
        trafo = _numero(c.get("trafo_kva"), numero_linha, "a potência do transformador")
        if trafo:
            barra["transformador"] = {
                "potencia_kva": trafo, "uk": _numero(c.get("uk"), numero_linha, "o uk do transformador", True),
                "perdas_cobre_w": _numero(c.get("perdas_cobre_w"), numero_linha, "as perdas no cobre") or 0.0}
        secao = _numero(c.get("secao"), numero_linha, "a seção do cabo")
        if secao:
            barra["cabo"] = {"secao": secao,
                             "comprimento": _numero(c.get("comprimento"), numero_linha, "o comprimento do cabo", True),
                             "paralelos": int(_numero(c.get("paralelos"), numero_linha, "os cabos em paralelo") or 1),
                             "material": "aluminio" if str(c.get("material", "")).strip().lower().startswith("al")
                             else "cobre"}
        if not barra["origem"] and "rede_mva" not in barra:
            raise ValueError(f"Linha {numero_linha}: a barra {nome} não tem origem nem a potência de curto da rede.")
        barras.append(barra)
    if not barras:
        raise ValueError("A planilha não tem nenhuma barra.")
    return barras
