"""Montagem e dimensionamento dos circuitos terminais a partir dos pontos da planta.

Sem FreeCAD. Dimensionamento simplificado segundo a NBR 5410:

- condutores de cobre com isolação de PVC, método de referência B1 (condutores
  isolados em eletroduto embutido em alvenaria), a 30 °C, sem agrupamento;
- seção mínima de 1,5 mm² para iluminação e 2,5 mm² para tomadas (Tabela 47);
- coordenação com a proteção: Ib <= In <= Iz (5.3.4.1).

Queda de tensão, fatores de agrupamento e de temperatura e curto-circuito NÃO
entram neste cálculo: confira-os antes de usar o resultado em um projeto.

Unidades: potência em VA ou W, tensão em V, corrente em A, seção em mm².
"""
import math
import re

from freecad.Circuits.core import nbr5410
from freecad.Circuits.core.simbolos import ILUM, LIGACOES, TUE, TUG

# NBR 5410, Tabela 36, método B1, cobre/PVC: capacidade de condução [A] por seção [mm²].
CAPACIDADE_B1_PVC = {
    2: {1.5: 17.5, 2.5: 24, 4: 32, 6: 41, 10: 57, 16: 76, 25: 101, 35: 125, 50: 151, 70: 192, 95: 232, 120: 269},
    3: {1.5: 15.5, 2.5: 21, 4: 28, 6: 36, 10: 50, 16: 68, 25: 89, 35: 110, 50: 134, 70: 171, 95: 207, 120: 239},
}
SECAO_MINIMA = {ILUM: 1.5, TUG: 2.5, TUE: 2.5}
DISJUNTORES = [6, 10, 16, 20, 25, 32, 40, 50, 63, 70, 80, 100, 125]  # A
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
    disjuntor = next((valor for valor in DISJUNTORES if valor >= corrente), None)
    if disjuntor is None:
        raise ValueError(f"Corrente de {corrente:.1f} A acima do maior disjuntor ({DISJUNTORES[-1]} A).")

    tabela = CAPACIDADE_B1_PVC[3 if n_fases == 3 else 2]
    minima = SECAO_MINIMA.get(tipo, 2.5)
    cabo = next((secao for secao, capacidade in tabela.items() if secao >= minima and capacidade >= disjuntor), None)
    if cabo is None:
        raise ValueError(f"Nenhum cabo da tabela suporta o disjuntor de {disjuntor} A.")
    return {"corrente": corrente, "disjuntor": disjuntor, "cabo": cabo}


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
    """Atribui as fases de cada circuito, equilibrando a carga do quadro.

    Os circuitos de maior potência são colocados primeiro, sempre nas fases
    menos carregadas. Grava ``fases`` (ex.: ['R'] ou ['R', 'S']) em cada circuito.

    Returns:
        Carga [VA] por fase, ex.: {'R': 1200.0, 'S': 1100.0, 'T': 900.0}.
    """
    disponiveis = FASES[:max(1, min(3, int(fases_quadro)))]
    carga = {fase: 0.0 for fase in disponiveis}
    for circuito in sorted(circuitos, key=lambda c: -c["potencia_va"]):
        quantidade = min(circuito["n_fases"], len(disponiveis))
        escolhidas = sorted(disponiveis, key=lambda fase: (carga[fase], fase))[:quantidade]
        for fase in escolhidas:
            carga[fase] += circuito["potencia_va"] / quantidade
        circuito["fases"] = sorted(escolhidas)
    return carga


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
    )
    fases = circuito.get("fases") or list(FASES[:circuito["n_fases"]])
    com_dr = tipo in (TUG, TUE) or p.get("esquema") == "TT"
    sensibilidade = f"{p['sensibilidade_dr']:g}mA" if parametros else CORRENTE_DR

    avisos = []
    esquema = p.get("esquema", "")
    if esquema.startswith("TN") and comprimento > 0 and not nbr5410.seccionamento_ok(
            comprimento, p["tensao_fn"], calculo["secao"], calculo["secao"], calculo["disjuntor"], curva, com_dr):
        maximo = nbr5410.comprimento_maximo_tn(p["tensao_fn"], calculo["secao"], calculo["secao"],
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