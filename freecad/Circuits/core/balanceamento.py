"""Balanceamento das cargas entre as fases de um quadro, sem FreeCAD.

Cada circuito ocupa 1, 2 ou 3 fases (``R``, ``RS``, ``RST``) e soma a sua
potência dividida igualmente entre elas. O balanceamento procura a
distribuição com a menor diferença entre a fase mais carregada e a menos
carregada:

1. parte da distribuição atual e de uma distribuição nova (maiores circuitos
   primeiro, cada um nas fases menos carregadas);
2. melhora as duas trocando um circuito de fase e trocando dois circuitos
   entre si, enquanto a diferença diminuir;
3. fica com a melhor; no empate, a que muda menos circuitos.

Circuitos trifásicos (todas as fases do quadro) e os ``fixos`` não mudam.

Desequilíbrio = (maior carga − menor carga) / maior carga × 100. Em projetos é
comum buscar até 10 %; a NBR 5410 não fixa um limite.

Unidades: potência em W (ou VA, desde que todos iguais), corrente em A, tensão em V.
"""
from itertools import combinations

FASES = "RST"
LIMITE_USUAL = 10.0  # % de desequilíbrio aceito na prática
MAXIMO_PASSOS = 500


def disponiveis(n_fases):
    """Fases do quadro: 'R', 'RS' ou 'RST'."""
    return FASES[:max(1, min(3, int(n_fases or 3)))]


def normalizar(texto):
    """'s r' -> 'RS'; só as letras de fase, em ordem e sem repetir."""
    return "".join(f for f in FASES if f in str(texto).upper())


def cargas_por_fase(circuitos, fases, distribuicao=None):
    """Carga [W] de cada fase.

    Args:
        circuitos: dicionários com ``numero``, ``potencia`` e ``fases`` (texto).
        fases: fases do quadro ('RST').
        distribuicao: {numero: fases}; None usa as ``fases`` de cada circuito.
    """
    cargas = {f: 0.0 for f in fases}
    for c in circuitos:
        ligadas = [f for f in (distribuicao or {}).get(c["numero"], c["fases"]) if f in cargas]
        for f in ligadas:
            cargas[f] += float(c["potencia"]) / len(ligadas)
    return cargas


def desequilibrio(cargas):
    """(maior − menor) / maior × 100; 0 sem carga."""
    maior = max(cargas.values(), default=0.0)
    return (maior - min(cargas.values())) / maior * 100.0 if maior > 0 else 0.0


def _objetivo(cargas):
    valores = list(cargas.values())
    return (round(max(valores) - min(valores), 6), round(sum(v * v for v in valores), 3))


def _opcoes(n, fases):
    return ["".join(c) for c in combinations(fases, n)]


def _melhorar(circuitos, fases, distribuicao, moveis):
    """Busca local: troca um circuito de fase, ou dois circuitos entre si, enquanto a diferença cair."""
    distribuicao = dict(distribuicao)
    atual = _objetivo(cargas_por_fase(circuitos, fases, distribuicao))
    for _ in range(MAXIMO_PASSOS):
        melhor = None
        for c in moveis:
            for opcao in _opcoes(len(distribuicao[c["numero"]]), fases):
                if opcao == distribuicao[c["numero"]]:
                    continue
                teste = dict(distribuicao, **{c["numero"]: opcao})
                valor = _objetivo(cargas_por_fase(circuitos, fases, teste))
                if valor < (melhor or (atual,))[0]:
                    melhor = (valor, teste)
        for a, b in combinations(moveis, 2):
            fa, fb = distribuicao[a["numero"]], distribuicao[b["numero"]]
            if len(fa) != len(fb) or fa == fb:
                continue
            teste = dict(distribuicao, **{a["numero"]: fb, b["numero"]: fa})
            valor = _objetivo(cargas_por_fase(circuitos, fases, teste))
            if valor < (melhor or (atual,))[0]:
                melhor = (valor, teste)
        if melhor is None:
            break
        atual, distribuicao = melhor
    return distribuicao


def _gulosa(circuitos, fases, distribuicao, moveis):
    """Maiores primeiro, cada um nas fases menos carregadas (os fixos já contam)."""
    fixos = [c for c in circuitos if c not in moveis]
    nova = {c["numero"]: distribuicao[c["numero"]] for c in fixos}
    cargas = cargas_por_fase(fixos, fases, nova)
    for c in sorted(moveis, key=lambda c: -float(c["potencia"])):
        n = len(distribuicao[c["numero"]])
        escolha = min(_opcoes(n, fases), key=lambda o: (max(cargas[f] + float(c["potencia"]) / n for f in o), o))
        nova[c["numero"]] = escolha
        for f in escolha:
            cargas[f] += float(c["potencia"]) / n
    return nova


def balancear(circuitos, fases=FASES, fixos=(), do_zero=False):
    """Nova distribuição dos circuitos entre as fases.

    Args:
        circuitos: dicionários com ``numero``, ``potencia`` [W] e ``fases`` (texto;
            vazio vale uma fase, que o balanceamento escolhe).
        fases: fases do quadro ('R', 'RS' ou 'RST').
        fixos: números dos circuitos que não podem mudar de fase.
        do_zero: ignora a distribuição atual (só o número de fases de cada
            circuito conta); para circuitos que ainda não têm fase.
    Returns:
        dict com ``fases`` {numero: 'R'}, ``antes`` e ``depois`` (carga por fase),
        ``desequilibrio_antes`` e ``desequilibrio_depois`` [%] e ``mudados`` (números).
    """
    fases = normalizar(fases) or FASES
    atual = {}
    for c in circuitos:
        ligadas = normalizar(c["fases"])
        n = min(len(ligadas) or 1, len(fases))
        atual[c["numero"]] = ligadas if len(ligadas) == n and all(f in fases for f in ligadas) else fases[:n]
    moveis = [c for c in circuitos if c["numero"] not in set(fixos) and len(atual[c["numero"]]) < len(fases)]
    candidatas = [_melhorar(circuitos, fases, _gulosa(circuitos, fases, atual, moveis), moveis)]
    if not do_zero:
        candidatas.insert(0, _melhorar(circuitos, fases, atual, moveis))

    def chave(distribuicao):
        mudados = sum(1 for c in circuitos if distribuicao[c["numero"]] != normalizar(c["fases"]))
        return _objetivo(cargas_por_fase(circuitos, fases, distribuicao))[0], mudados

    escolhida = min(candidatas, key=chave)
    antes = cargas_por_fase(circuitos, fases, {c["numero"]: normalizar(c["fases"]) for c in circuitos})
    depois = cargas_por_fase(circuitos, fases, escolhida)
    return {
        "fases": escolhida,
        "antes": antes,
        "depois": depois,
        "desequilibrio_antes": desequilibrio(antes),
        "desequilibrio_depois": desequilibrio(depois),
        "mudados": [c["numero"] for c in circuitos if escolhida[c["numero"]] != normalizar(c["fases"])],
    }


def _br(valor, casas=0):
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def relatorio(resultado, tensao_fn=127.0):
    """Texto com a carga e a corrente de cada fase, antes e depois, e os circuitos mudados."""
    linhas = ["Fase    Antes                Depois"]
    for f in resultado["depois"]:
        antes, depois = resultado["antes"][f], resultado["depois"][f]
        linhas.append(f"  {f}     {_br(antes):>7} W {_br(antes / tensao_fn, 1):>6} A   "
                      f"{_br(depois):>7} W {_br(depois / tensao_fn, 1):>6} A")
    linhas += [
        "",
        f"Desequilíbrio: {_br(resultado['desequilibrio_antes'], 1)} % → {_br(resultado['desequilibrio_depois'], 1)} %"
        f" (usual: até {LIMITE_USUAL:g} %)",
    ]
    if resultado["mudados"]:
        mudancas = ", ".join(f"C{n} → {resultado['fases'][n]}" for n in resultado["mudados"])
        linhas.append(f"Circuitos que mudam de fase: {mudancas}")
    else:
        linhas.append("Nenhum circuito precisa mudar de fase.")
    return "\n".join(linhas)
