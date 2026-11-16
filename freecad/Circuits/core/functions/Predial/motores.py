"""Motores elétricos de indução: potência comercial e corrente nominal.

Unidades: potência em kW ou cv, tensão em V, corrente em A.
"""
import math

KW_POR_CV = 0.7355

# Potências comerciais de motores, em cv.
POTENCIAS_CV = [0.25, 0.33, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 6, 7.5, 10, 12.5, 15, 20, 25, 30, 40, 50, 60, 75, 100]

# Valores típicos, usados quando não há o catálogo do motor.
RENDIMENTO_TIPICO = 0.85
FATOR_POTENCIA_TIPICO = 0.85


def motor_comercial(potencia_eixo_kw):
    """Menor motor comercial que atende a potência no eixo.

    Returns:
        Potência do motor em cv.
    Raises:
        ValueError: se a potência passar do maior motor da lista.
    """
    for potencia in POTENCIAS_CV:
        if potencia * KW_POR_CV >= potencia_eixo_kw - 1e-9:
            return potencia
    raise ValueError(f"Potência de {potencia_eixo_kw:.1f} kW acima do maior motor da lista ({POTENCIAS_CV[-1]} cv).")


def potencia_eletrica(potencia_cv, rendimento=RENDIMENTO_TIPICO, fator_potencia=FATOR_POTENCIA_TIPICO):
    """Potência absorvida da rede por um motor.

    Returns:
        (potência ativa [kW], potência aparente [kVA]).
    """
    ativa = potencia_cv * KW_POR_CV / rendimento
    return ativa, ativa / fator_potencia


def corrente_nominal(potencia_cv, tensao, fases=3, rendimento=RENDIMENTO_TIPICO, fator_potencia=FATOR_POTENCIA_TIPICO):
    """Corrente nominal [A] do motor. ``tensao`` é a tensão entre os condutores [V]."""
    _, aparente = potencia_eletrica(potencia_cv, rendimento, fator_potencia)
    divisor = math.sqrt(3) * tensao if fases == 3 else tensao
    return aparente * 1000.0 / divisor


def dados_motor(potencia_eixo_kw, tensao=380, fases=3):
    """Motor comercial e os dados elétricos usados para dimensionar o circuito."""
    cv = motor_comercial(potencia_eixo_kw)
    ativa, aparente = potencia_eletrica(cv)
    return {
        "motor_cv": cv,
        "motor_kw": cv * KW_POR_CV,
        "potencia_ativa_kw": ativa,
        "potencia_aparente_kva": aparente,
        "fator_potencia": FATOR_POTENCIA_TIPICO,
        "tensao": tensao,
        "fases": fases,
        "corrente": corrente_nominal(cv, tensao, fases),
    }
