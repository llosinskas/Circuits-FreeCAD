"""Demanda de uma unidade residencial pelos fatores de demanda usuais.

Método dos guias de instalações elétricas residenciais:

- iluminação e tomadas de uso geral (TUG): um fator único, escolhido pela faixa
  da potência instalada somada, aplicado ao total;
- tomadas de uso específico (TUE): um fator escolhido pelo número de circuitos,
  aplicado à soma das potências.

ATENÇÃO: cada concessionária publica a própria tabela de demanda na norma de
fornecimento. Use estes valores como estimativa e confira com a norma da
concessionária do projeto. Este módulo não calcula a demanda de um edifício
inteiro (diversidade entre apartamentos), só a de um quadro.

Unidades: potências em W.
"""
from freecad.Circuits.core.simbolos import ILUM, TUE, TUG

# (limite superior da faixa [W], fator). Acima do último limite vale FATOR_ILUM_TUG_ACIMA.
FATORES_ILUM_TUG = [
    (1000, 0.86), (2000, 0.75), (3000, 0.66), (4000, 0.59), (5000, 0.52),
    (6000, 0.45), (7000, 0.40), (8000, 0.35), (9000, 0.31), (10000, 0.27),
]
FATOR_ILUM_TUG_ACIMA = 0.24

# Fator por número de circuitos de uso específico. Acima de 25 vale o último.
FATORES_TUE = {
    1: 1.00, 2: 1.00, 3: 0.84, 4: 0.76, 5: 0.70, 6: 0.65, 7: 0.60, 8: 0.57, 9: 0.54, 10: 0.52,
    11: 0.49, 12: 0.48, 13: 0.46, 14: 0.45, 15: 0.44, 16: 0.43, 17: 0.40, 18: 0.40, 19: 0.40, 20: 0.40,
    21: 0.39, 22: 0.39, 23: 0.39, 24: 0.38, 25: 0.38,
}


def fator_ilum_tug(potencia_w):
    """Fator de demanda de iluminação + TUG para a potência instalada somada [W]."""
    for limite, fator in FATORES_ILUM_TUG:
        if potencia_w <= limite:
            return fator
    return FATOR_ILUM_TUG_ACIMA


def fator_tue(numero_circuitos):
    """Fator de demanda das tomadas de uso específico pelo número de circuitos."""
    if numero_circuitos <= 0:
        return 1.0
    return FATORES_TUE[min(int(numero_circuitos), max(FATORES_TUE))]


def demanda_residencial(potencia_ilum_tug_w, potencias_tue_w):
    """Demanda de um quadro residencial.

    Args:
        potencia_ilum_tug_w: soma da potência instalada de iluminação e TUG [W].
        potencias_tue_w: potência de cada circuito de uso específico [W].
    Returns:
        dict com as potências instaladas, os fatores e as demandas, tudo em W.
    """
    potencias_tue_w = list(potencias_tue_w)
    instalada_tue = sum(potencias_tue_w)
    g_ilum_tug = fator_ilum_tug(potencia_ilum_tug_w) if potencia_ilum_tug_w > 0 else 0.0
    g_tue = fator_tue(len(potencias_tue_w))
    demanda_ilum_tug = potencia_ilum_tug_w * g_ilum_tug
    demanda_tue = instalada_tue * g_tue
    instalada = potencia_ilum_tug_w + instalada_tue
    demanda = demanda_ilum_tug + demanda_tue
    return {
        "instalada_ilum_tug_w": potencia_ilum_tug_w,
        "fator_ilum_tug": g_ilum_tug,
        "demanda_ilum_tug_w": demanda_ilum_tug,
        "circuitos_tue": len(potencias_tue_w),
        "instalada_tue_w": instalada_tue,
        "fator_tue": g_tue,
        "demanda_tue_w": demanda_tue,
        "instalada_w": instalada,
        "demanda_w": demanda,
        "fator_global": demanda / instalada if instalada else 0.0,
    }


def demanda_de_circuitos(circuitos):
    """Demanda a partir dos circuitos de ``core.circuitos.agrupar`` (usa ``tipo`` e ``potencia_w``)."""
    ilum_tug = sum(c["potencia_w"] for c in circuitos if c["tipo"] in (ILUM, TUG))
    tue = [c["potencia_w"] for c in circuitos if c["tipo"] == TUE]
    return demanda_residencial(ilum_tug, tue)


def relatorio(resultado):
    """Texto do cálculo, para mostrar ao usuário."""
    r = resultado
    return "\n".join([
        f"Iluminação e tomadas (TUG): {r['instalada_ilum_tug_w']:.0f} W x {r['fator_ilum_tug']:.2f}"
        f" = {r['demanda_ilum_tug_w']:.0f} W",
        f"Uso específico (TUE), {r['circuitos_tue']} circuito(s): {r['instalada_tue_w']:.0f} W x {r['fator_tue']:.2f}"
        f" = {r['demanda_tue_w']:.0f} W",
        "",
        f"Potência instalada: {r['instalada_w'] / 1000:.2f} kW",
        f"Demanda: {r['demanda_w'] / 1000:.2f} kW (fator global {r['fator_global']:.2f})",
        "",
        "Fatores de guias de instalações residenciais. Confira com a norma da concessionária.",
    ])
