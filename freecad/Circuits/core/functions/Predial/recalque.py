"""Bomba de recalque de água fria predial: vazão, tubulação, altura manométrica e motor.

Método usual de instalações prediais (NBR 5626 e manuais de hidráulica):

- consumo diário = população x consumo por pessoa;
- vazão de recalque = consumo diário / horas de funcionamento da bomba por dia;
- diâmetro de recalque pela fórmula de Forchheimer: D = 1,3 · X^(1/4) · raiz(Q),
  com X = horas de funcionamento / 24;
- perda de carga por Hazen-Williams, com as singularidades estimadas como um
  acréscimo percentual sobre o comprimento da tubulação;
- potência no eixo = peso específico x vazão x altura manométrica / rendimento,
  com a folga usual para escolher o motor.

ATENÇÃO: é um pré-dimensionamento para estimar a carga elétrica da bomba. O
projeto hidráulico (curva da bomba, NPSH, comprimentos equivalentes reais) é do
projetista de hidráulica.

Unidades: volume em litros, vazão em m³/s (também devolvida em m³/h),
comprimentos e alturas em m, diâmetros em mm, potência em kW.
"""
import math

from freecad.Circuits.core.functions.Predial import motores

CONSUMO_POR_PESSOA = 200.0  # L/dia, apartamento residencial
HORAS_FUNCIONAMENTO = 5.0  # h/dia
COEFICIENTE_HAZEN_WILLIAMS = {"PVC": 140.0, "Aço galvanizado": 125.0, "Cobre": 130.0}
MATERIAL_PADRAO = "PVC"
ACRESCIMO_SINGULARIDADES = 0.30  # conexões, registros e válvulas, sobre o comprimento real
RENDIMENTO_BOMBA = 0.50
PESO_ESPECIFICO_AGUA = 9810.0  # N/m³

# Tubo de PVC soldável: diâmetro nominal [mm] -> diâmetro interno [mm].
DIAMETROS_INTERNOS = {20: 17.0, 25: 21.6, 32: 27.8, 40: 35.2, 50: 44.0, 60: 53.4, 75: 66.6, 85: 75.6, 110: 97.8}

# Folga do motor sobre a potência no eixo da bomba: (potência até [cv], acréscimo).
FOLGAS_MOTOR = [(2, 0.50), (5, 0.30), (10, 0.20), (20, 0.15)]
FOLGA_MOTOR_ACIMA = 0.10


def consumo_diario(populacao, consumo_por_pessoa=CONSUMO_POR_PESSOA):
    """Consumo diário do edifício [L/dia]."""
    return populacao * consumo_por_pessoa


def vazao_recalque(consumo_diario_l, horas=HORAS_FUNCIONAMENTO):
    """Vazão da bomba [m³/s] para repor o consumo diário no tempo de funcionamento."""
    if horas <= 0 or horas > 24:
        raise ValueError("As horas de funcionamento precisam estar entre 0 e 24.")
    return consumo_diario_l / 1000.0 / (horas * 3600.0)


def diametro_forchheimer(vazao, horas=HORAS_FUNCIONAMENTO):
    """Diâmetro econômico de recalque [mm] pela fórmula de Forchheimer."""
    return 1.3 * (horas / 24.0) ** 0.25 * math.sqrt(vazao) * 1000.0


def diametro_comercial(diametro_mm):
    """Menor tubo cujo diâmetro interno atende o diâmetro calculado.

    Returns:
        (diâmetro nominal [mm], diâmetro interno [mm]).
    """
    for nominal, interno in DIAMETROS_INTERNOS.items():
        if interno >= diametro_mm:
            return nominal, interno
    raise ValueError(f"Diâmetro de {diametro_mm:.0f} mm acima do maior tubo da tabela.")


def perda_carga_unitaria(vazao, diametro_interno_mm, coeficiente=140.0):
    """Perda de carga por metro de tubo [m/m], pela fórmula de Hazen-Williams."""
    diametro = diametro_interno_mm / 1000.0
    return 10.643 * vazao ** 1.852 / (coeficiente ** 1.852 * diametro ** 4.87)


def folga_motor(potencia_eixo_cv):
    for limite, acrescimo in FOLGAS_MOTOR:
        if potencia_eixo_cv <= limite:
            return acrescimo
    return FOLGA_MOTOR_ACIMA


def dimensionar(
    populacao,
    altura_geometrica,
    comprimento_tubulacao,
    consumo_por_pessoa=CONSUMO_POR_PESSOA,
    horas=HORAS_FUNCIONAMENTO,
    material=MATERIAL_PADRAO,
    rendimento=RENDIMENTO_BOMBA,
    tensao=380,
    fases=3,
):
    """Pré-dimensiona a bomba de recalque de um edifício.

    Args:
        populacao: pessoas atendidas pelo reservatório superior.
        altura_geometrica: desnível entre o nível da água no reservatório
            inferior e a entrada do reservatório superior [m].
        comprimento_tubulacao: comprimento real de sucção + recalque [m].
        consumo_por_pessoa: [L/dia].
        horas: funcionamento da bomba por dia [h].
        material: chave de ``COEFICIENTE_HAZEN_WILLIAMS``.
        rendimento: rendimento da bomba (0 a 1).
        tensao: tensão entre os condutores do motor [V].
        fases: 1 (ou 2) para motor monofásico, 3 para trifásico.
    Returns:
        dict com consumo, vazão, tubo, perdas, altura manométrica, potência no
        eixo e os dados do motor (``core.functions.Predial.motores.dados_motor``).
    """
    if populacao <= 0 or altura_geometrica < 0 or comprimento_tubulacao < 0:
        raise ValueError("População precisa ser positiva; altura e comprimento não podem ser negativos.")
    if not 0 < rendimento <= 1:
        raise ValueError("O rendimento precisa estar entre 0 e 1.")

    consumo = consumo_diario(populacao, consumo_por_pessoa)
    vazao = vazao_recalque(consumo, horas)
    calculado = diametro_forchheimer(vazao, horas)
    nominal, interno = diametro_comercial(calculado)
    velocidade = vazao / (math.pi * (interno / 1000.0) ** 2 / 4.0)

    unitaria = perda_carga_unitaria(vazao, interno, COEFICIENTE_HAZEN_WILLIAMS[material])
    perdas = unitaria * comprimento_tubulacao * (1 + ACRESCIMO_SINGULARIDADES)
    manometrica = altura_geometrica + perdas

    eixo_kw = PESO_ESPECIFICO_AGUA * vazao * manometrica / rendimento / 1000.0
    com_folga = eixo_kw * (1 + folga_motor(eixo_kw / motores.KW_POR_CV))
    return {
        "consumo_diario_l": consumo,
        "vazao": vazao,
        "vazao_m3h": vazao * 3600.0,
        "diametro_calculado_mm": calculado,
        "diametro_nominal_mm": nominal,
        "diametro_interno_mm": interno,
        "velocidade": velocidade,
        "perda_carga": perdas,
        "altura_manometrica": manometrica,
        "potencia_eixo_kw": eixo_kw,
        "motor": motores.dados_motor(com_folga, tensao, fases),
    }


def relatorio(resultado):
    """Texto do cálculo, para mostrar ao usuário."""
    r, m = resultado, resultado["motor"]
    ligacao = "trifásico" if m["fases"] == 3 else "monofásico"
    return "\n".join([
        f"Consumo diário: {r['consumo_diario_l']:.0f} L",
        f"Vazão de recalque: {r['vazao_m3h']:.2f} m³/h ({r['vazao'] * 1000:.2f} L/s)",
        f"Tubo de recalque: DN {r['diametro_nominal_mm']} mm (calculado {r['diametro_calculado_mm']:.1f} mm),"
        f" velocidade {r['velocidade']:.2f} m/s",
        f"Perda de carga: {r['perda_carga']:.2f} m   Altura manométrica: {r['altura_manometrica']:.2f} m",
        f"Potência no eixo da bomba: {r['potencia_eixo_kw']:.2f} kW",
        "",
        f"Motor: {m['motor_cv']:g} cv ({m['motor_kw']:.2f} kW), {ligacao} {m['tensao']} V",
        f"Corrente nominal: {m['corrente']:.1f} A   Potência aparente: {m['potencia_aparente_kva']:.2f} kVA",
        "",
        "Pré-dimensionamento para estimar a carga elétrica. Preveja duas bombas (uma de reserva),",
        "que não funcionam ao mesmo tempo. Confira com o projeto hidráulico.",
    ])
