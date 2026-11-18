"""Montagem e dimensionamento dos circuitos terminais a partir dos pontos da planta.

Sem FreeCAD. O dimensionamento é o de ``core.nbr5410.dimensionar_circuito``:
seção mínima (tabela 47), capacidade de condução com temperatura e
agrupamento (Ib ≤ In ≤ Iz), queda de tensão com o fator de potência do
circuito, curto-circuito (com ``tempo_curto``) e, no TN, o seccionamento
automático com o condutor de proteção da tabela 58.

``dimensionar`` (sem parâmetros do projeto) usa PVC, método B1, 30 °C, sem
agrupamento nem queda: serve para uma estimativa rápida.

Unidades: potência em VA ou W, tensão em V, corrente em A, seção em mm².
"""
import math
import re

from freecad.Circuits.core import balanceamento, nbr5410
from freecad.Circuits.core.simbolos import ILUM, LIGACOES, TUE, TUG

# NBR 5410, Tabela 36, método B1, cobre/PVC: capacidade de condução [A] por seção [mm²] (de ``core.nbr5410``).
CAPACIDADE_B1_PVC = {n: {s: nbr5410.capacidade(s, "B1", n, "PVC") for s in nbr5410.SECOES} for n in (2, 3)}
SECAO_MINIMA = {ILUM: nbr5410.SECAO_MINIMA["ILUM"], TUG: nbr5410.SECAO_MINIMA_PADRAO, TUE: nbr5410.SECAO_MINIMA_PADRAO}
DISJUNTORES = nbr5410.DISJUNTORES  # A
DESTINO_PADRAO = {ILUM: "Iluminação", TUG: "Tomadas", TUE: "Uso específico"}
CORRENTE_DR = "30mA"
FASES = ("R", "S", "T")
CRITERIOS = {
    "secao_minima": "Seção mínima",
    "capacidade": "Capacidade de condução",
    "queda_tensao": "Queda de tensão",
    "curto_circuito": "Curto-circuito",
}

_MULTIPLOS = {"": 1.0, "k": 1000.0}


def potencia_va(valor, padrao=0.0):
    """Converte '600VA', '100 W', '1,5kW' ou um número em potência [VA ou W].

    Texto sem número devolve ``padrao``.
    """
    if isinstance(valor, (int, float)):
        return float(valor)
    achado = re.search(r"(\d+(?:[.,]\d+)?)\s*(k?)", str(valor), re.IGNORECASE)
    if not achado:
        return padrao
    return float(achado.group(1).replace(",", ".")) * _MULTIPLOS[achado.group(2).lower()]


def corrente_projeto(potencia_aparente, tensao, n_fases):
    """Corrente de projeto Ib [A]. ``tensao`` é a tensão entre os condutores do circuito."""
    if tensao <= 0:
        raise ValueError("A tensão precisa ser maior que zero.")
    divisor = math.sqrt(3) * tensao if n_fases == 3 else tensao
    return potencia_aparente / divisor


def dimensionar(potencia_aparente, tensao, n_fases, tipo):
    """Escolhe disjuntor e cabo de um circuito.

    Returns:
        dict com ``corrente`` (Ib), ``disjuntor`` (In) e ``cabo`` (seção, com Iz >= In).
    Raises:
        ValueError: se a corrente passar do maior disjuntor ou cabo das tabelas.
    """
    corrente = corrente_projeto(potencia_aparente, tensao, n_fases)
    calculo = nbr5410.dimensionar_circuito(corrente, tipo, 0.0, tensao, n_fases)
    return {"corrente": corrente, "disjuntor": calculo["disjuntor"], "cabo": calculo["secao"]}


def _chave_ordenacao(numero):
    """Ordena '2' antes de '10', e textos depois dos números."""
    achado = re.match(r"\d+", str(numero))
    return (0, int(achado.group()), str(numero)) if achado else (1, 0, str(numero))


def agrupar(pontos):
    """Junta os pontos da planta por número de circuito.

    Args:
        pontos: dicionários com ``circuito``, ``potencia_va``, ``fator_potencia``,
            ``tensao`` [V], ``ligacao`` ('F+N', 'F+F' ou '3F'), ``tipo_circuito``
            e ``descricao``.
    Returns:
        Lista de circuitos, ordenada pelo número, cada um com ``numero``,
        ``destino``, ``tipo``, ``potencia_va``, ``potencia_w``, ``tensao``,
        ``n_fases``, ``pontos`` (quantidade) e ``avisos``.
    """
    grupos = {}
    for ponto in pontos:
        numero = str(ponto.get("circuito", "")).strip()
        if not numero:
            continue
        grupos.setdefault(numero, []).append(ponto)

    circuitos = []
    for numero in sorted(grupos, key=_chave_ordenacao):
        membros = grupos[numero]
        tipos = {p["tipo_circuito"] for p in membros}
        tensoes = {p["tensao"] for p in membros}
        avisos = []
        if len(tensoes) > 1:
            avisos.append("pontos com tensões diferentes no mesmo circuito")
        if TUE in tipos and len(membros) > 1:
            avisos.append("ponto de uso específico dividindo o circuito com outros pontos")
        if ILUM in tipos and TUG in tipos:
            avisos.append("iluminação e tomadas no mesmo circuito")

        # O tipo mais exigente define a seção mínima e o destino.
        tipo = TUE if TUE in tipos else TUG if TUG in tipos else ILUM
        if tipo == TUE and len(membros) == 1:
            destino = membros[0].get("descricao") or DESTINO_PADRAO[TUE]
        else:
            destino = DESTINO_PADRAO[tipo]

        circuitos.append({
            "numero": numero,
            "destino": destino,
            "tipo": tipo,
            "potencia_va": sum(p["potencia_va"] for p in membros),
            "potencia_w": sum(p["potencia_va"] * p["fator_potencia"] for p in membros),
            "tensao": max(tensoes),
            "n_fases": max(LIGACOES.get(p["ligacao"], 1) for p in membros),
            "pontos": len(membros),
            "avisos": avisos,
        })
    return circuitos


def distribuir_fases(circuitos, fases_quadro=3):
    """Atribui as fases de cada circuito, equilibrando a carga do quadro (``core.balanceamento``).

    Grava ``fases`` (ex.: ['R'] ou ['R', 'S']) em cada circuito.

    Returns:
        Carga [VA] por fase, ex.: {'R': 1200.0, 'S': 1100.0, 'T': 900.0}.
    """
    disponiveis = balanceamento.disponiveis(fases_quadro)
    itens = [{"numero": str(indice), "potencia": c["potencia_va"],
              "fases": disponiveis[:min(c["n_fases"], len(disponiveis))]} for indice, c in enumerate(circuitos)]
    resultado = balanceamento.balancear(itens, disponiveis, do_zero=True)
    for indice, circuito in enumerate(circuitos):
        circuito["fases"] = list(resultado["fases"][str(indice)])
    return resultado["depois"]


def _numero(valor):
    """Texto de um número sem zeros à direita: 16.0 -> '16', 2.5 -> '2.5'."""
    return f"{valor:.2f}".rstrip("0").rstrip(".")


def linha_planilha(circuito, curva="C", parametros=None, comprimento=0.0, agrupados=1, metodo="B1"):
    """Dados do circuito com as chaves de ``core.planilha.COLUNAS_CIRCUITO``, dimensionado pela NBR 5410.

    Além das colunas antigas, traz ``Comprimento`` [m], ``Queda`` [%] e
    ``Criterio`` (o critério que determinou o cabo), e ``_avisos`` (textos,
    não gravados na planilha).

    Args:
        parametros: de ``core.parametros.ler``; None usa a curva dada, PVC, 30 °C,
            4 % de queda e não verifica curto nem seccionamento.
        comprimento: do quadro ao ponto mais distante [m]; 0 não verifica a queda.
        agrupados: circuitos no trecho mais cheio do trajeto.
        metodo: método de instalação da NBR 5410.

    DR de 30 mA em tomadas e pontos de uso específico: é uma simplificação a
    favor da segurança do item 5.1.3.2.2 da NBR 5410, que o exige em áreas
    molhadas e externas. No esquema TT, DR em todos os circuitos.
    """
    p = parametros or {}
    tipo = circuito["tipo"]
    if parametros:
        curva = p["curva_iluminacao"] if tipo == ILUM else p["curva_tomadas"]
    corrente = corrente_projeto(circuito["potencia_va"], circuito["tensao"], circuito["n_fases"])
    calculo = nbr5410.dimensionar_circuito(
        corrente, tipo, comprimento, circuito["tensao"], circuito["n_fases"], metodo=metodo, agrupados=agrupados,
        temperatura=p.get("temperatura_ambiente", 30.0), isolacao=p.get("isolacao", "PVC"),
        queda_max=p.get("queda_terminal", 4.0),
        icc_ka=p.get("icc_entrada_ka") if p.get("tempo_curto", 0.0) > 0 else None,
        tempo_curto=p.get("tempo_curto", 0.0) or 0.1, material=p.get("material", "cobre"),
        fator_potencia=circuito["potencia_w"] / circuito["potencia_va"] if circuito["potencia_va"] else 1.0,
    )
    fases = circuito.get("fases") or list(FASES[:circuito["n_fases"]])
    com_dr = tipo in (TUG, TUE) or p.get("esquema") == "TT"
    sensibilidade = f"{p['sensibilidade_dr']:g}mA" if parametros else CORRENTE_DR

    avisos = []
    esquema = p.get("esquema", "")
    if esquema.startswith("TN") and comprimento > 0 and not nbr5410.seccionamento_ok(
            comprimento, p["tensao_fn"], calculo["secao"], calculo["protecao"], calculo["disjuntor"], curva, com_dr):
        maximo = nbr5410.comprimento_maximo_tn(p["tensao_fn"], calculo["secao"], calculo["protecao"],
                                               calculo["disjuntor"], curva)
        avisos.append(f"proteção contra contatos indiretos: {comprimento:.0f} m passa do máximo de {maximo:.0f} m "
                      f"para o disjuntor {curva}{calculo['disjuntor']}; use DR ou aumente o cabo de proteção")
    return {
        "N_circuito": circuito["numero"],
        "Destino": circuito["destino"],
        "Potencia": _numero(circuito["potencia_w"]),
        "Tensao": _numero(circuito["tensao"]),
        "Corrente": _numero(calculo["corrente"]),
        "Cabo": _numero(calculo["secao"]),
        "Disjuntor": _numero(calculo["disjuntor"]),
        "Curva": curva,
        "Fase_R": str("R" in fases),
        "Fase_S": str("S" in fases),
        "Fase_T": str("T" in fases),
        "Neutro": str(circuito["n_fases"] == 1),
        "Terra": "True",
        "DR": str(com_dr),
        "Corrente_DR": sensibilidade if com_dr else "",
        "Comprimento": _numero(comprimento) if comprimento else "",
        "Queda": _numero(calculo["queda"]) if comprimento else "",
        "Criterio": CRITERIOS[calculo["criterio"]],
        "_avisos": avisos,
    }