"""Pressurização de escada de segurança: vazão de ar, ventilador e motor.

Segue o método da NBR 14880 (controle de fumaça por pressurização de escadas):

- com todas as portas fechadas, o ar insuflado escapa pelas frestas das portas
  e mantém a escada na pressão de projeto (50 Pa): Q = 0,827 x A x P^(1/N);
- com portas abertas, o ar precisa atravessar cada porta aberta com velocidade
  mínima de 1 m/s, além de escapar pelas frestas das portas que ficaram fechadas;
- o ventilador é escolhido para a maior das duas vazões, com acréscimos para
  vazamentos não identificados e para vazamento nos dutos.

ATENÇÃO: é um pré-dimensionamento para estimar a carga elétrica do ventilador.
O número de portas abertas, as áreas de fresta e os acréscimos dependem da
edição da NBR 14880 e da instrução técnica do Corpo de Bombeiros do estado:
confira os valores padrão deste módulo antes de usar. O projeto de
pressurização em si é do projetista de ventilação e de incêndio.

Unidades: vazão em m³/s, pressão em Pa, áreas em m², potência em kW.
"""
from freecad.Circuits.core.functions.Predial import motores

PRESSAO_PROJETO = 50.0  # Pa, diferença de pressão entre a escada e o pavimento
VELOCIDADE_PORTA_ABERTA = 1.0  # m/s
COEFICIENTE = 0.827
EXPOENTE_PORTAS = 2.0  # N = 2 para frestas grandes, como as de portas

# Área de fresta por porta fechada [m²].
AREA_FRESTA = {
    "Simples, abre para a escada": 0.01,
    "Simples, abre para fora da escada": 0.02,
    "Dupla": 0.03,
    "De elevador": 0.06,
}
PORTA_PADRAO = "Simples, abre para a escada"

ACRESCIMO_NAO_IDENTIFICADO = 0.25  # vazamentos não identificados
ACRESCIMO_DUTO = {"Metálico": 0.15, "Alvenaria": 0.25}
DUTO_PADRAO = "Metálico"

RENDIMENTO_VENTILADOR = 0.65
RENDIMENTO_TRANSMISSAO = 0.95
FOLGA_MOTOR = 0.15  # reserva sobre a potência no eixo


def vazao_frestas(area_m2, pressao=PRESSAO_PROJETO, expoente=EXPOENTE_PORTAS):
    """Vazão que escapa por uma área de fresta sob a diferença de pressão: Q = 0,827·A·P^(1/N)."""
    if area_m2 < 0 or pressao < 0:
        raise ValueError("Área e pressão não podem ser negativas.")
    return COEFICIENTE * area_m2 * pressao ** (1.0 / expoente)


def vazao_portas_abertas(numero_portas, largura=0.9, altura=2.1, velocidade=VELOCIDADE_PORTA_ABERTA):
    """Vazão para manter a velocidade mínima através das portas abertas."""
    return numero_portas * largura * altura * velocidade


def potencia_ventilador(vazao, pressao_total, rendimento=RENDIMENTO_VENTILADOR, transmissao=RENDIMENTO_TRANSMISSAO):
    """Potência no eixo do motor do ventilador [kW], para a pressão total [Pa] do sistema."""
    return vazao * pressao_total / (rendimento * transmissao) / 1000.0


def dimensionar(
    numero_portas,
    portas_abertas=2,
    tipo_porta=PORTA_PADRAO,
    largura_porta=0.9,
    altura_porta=2.1,
    duto=DUTO_PADRAO,
    pressao_total_ventilador=500.0,
    tensao=380,
    pressao=PRESSAO_PROJETO,
):
    """Pré-dimensiona o ventilador de pressurização de uma escada.

    Args:
        numero_portas: portas da escada (em geral uma por pavimento, mais a da descarga).
        portas_abertas: portas consideradas abertas ao mesmo tempo.
        tipo_porta: chave de ``AREA_FRESTA``.
        largura_porta, altura_porta: vão livre da porta [m].
        duto: chave de ``ACRESCIMO_DUTO``.
        pressao_total_ventilador: pressão total que o ventilador precisa vencer [Pa]:
            os 50 Pa da escada mais as perdas em dutos, grelhas, veneziana e filtro.
        tensao: tensão de linha do motor trifásico [V].
        pressao: diferença de pressão de projeto [Pa].
    Returns:
        dict com as vazões [m³/s], a vazão do ventilador também em m³/h, a potência
        no eixo [kW] e os dados do motor (``core.functions.Predial.motores.dados_motor``).
    """
    if numero_portas < 1:
        raise ValueError("A escada precisa ter pelo menos uma porta.")
    if not 0 <= portas_abertas <= numero_portas:
        raise ValueError("O número de portas abertas precisa estar entre zero e o número de portas.")

    fresta = AREA_FRESTA[tipo_porta]
    fechadas = vazao_frestas(numero_portas * fresta, pressao)
    abertas = vazao_portas_abertas(portas_abertas, largura_porta, altura_porta)
    abertas += vazao_frestas((numero_portas - portas_abertas) * fresta, pressao)

    base = max(fechadas, abertas)
    ventilador = base * (1 + ACRESCIMO_NAO_IDENTIFICADO) * (1 + ACRESCIMO_DUTO[duto])
    eixo = potencia_ventilador(ventilador, pressao_total_ventilador)
    return {
        "vazao_portas_fechadas": fechadas,
        "vazao_portas_abertas": abertas,
        "condicao": "portas abertas" if abertas > fechadas else "portas fechadas",
        "vazao_ventilador": ventilador,
        "vazao_ventilador_m3h": ventilador * 3600.0,
        "pressao_total": pressao_total_ventilador,
        "potencia_eixo_kw": eixo,
        "motor": motores.dados_motor(eixo * (1 + FOLGA_MOTOR), tensao),
    }


def relatorio(resultado):
    """Texto do cálculo, para mostrar ao usuário."""
    r, m = resultado, resultado["motor"]
    return "\n".join([
        f"Vazão com as portas fechadas (frestas): {r['vazao_portas_fechadas']:.2f} m³/s",
        f"Vazão com portas abertas: {r['vazao_portas_abertas']:.2f} m³/s",
        f"Condição que define o ventilador: {r['condicao']}",
        "",
        f"Vazão do ventilador, com acréscimos: {r['vazao_ventilador']:.2f} m³/s"
        f" ({r['vazao_ventilador_m3h']:.0f} m³/h)",
        f"Pressão total: {r['pressao_total']:.0f} Pa",
        f"Potência no eixo: {r['potencia_eixo_kw']:.2f} kW",
        "",
        f"Motor: {m['motor_cv']:g} cv ({m['motor_kw']:.2f} kW), trifásico {m['tensao']} V",
        f"Corrente nominal: {m['corrente']:.1f} A   Potência aparente: {m['potencia_aparente_kva']:.2f} kVA",
        "",
        "Pré-dimensionamento para estimar a carga elétrica. O ventilador de pressurização é",
        "carga de segurança: precisa de alimentação que continue ligada em caso de incêndio.",
        "Confira os parâmetros com a NBR 14880 e com o Corpo de Bombeiros.",
    ])
