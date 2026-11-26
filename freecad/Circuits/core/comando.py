"""Quadro de comando de motores: partida, contatores, relé térmico e disjuntor-motor.

- **Direta:** um contator (K1) e o relé térmico na corrente nominal.
- **Estrela-triângulo:** contatores de rede (K1) e de triângulo (K2) com 0,58·In, de estrela
  (K3) com 0,33·In; o relé fica nas fases do enrolamento, ajustado em 0,58·In.
- **Soft-starter e inversor:** o dispositivo pela corrente nominal, com a proteção do
  motor nele (sem relé térmico) e um contator de isolação K1.

As listas de contatores em AC-3, faixas de relé e de disjuntor-motor e correntes de
soft-starter e inversor são valores genéricos de catálogo, não de um fabricante.
Correntes em A; potência em cv; tensão de linha em V.
"""
from freecad.Circuits.core.functions.Predial import motores

PARTIDAS = {
    "direta": "Partida direta",
    "estrela_triangulo": "Estrela-triângulo",
    "soft_starter": "Soft-starter",
    "inversor": "Inversor de frequência",
}
FATOR_TRIANGULO = 0.58  # 1/√3
FATOR_ESTRELA = 0.33

CONTATORES_AC3 = [9, 12, 18, 25, 32, 38, 40, 50, 65, 80, 95, 115, 150, 185, 225, 265, 330, 400, 500, 630, 780]
RELES = [(0.1, 0.16), (0.16, 0.25), (0.25, 0.4), (0.4, 0.63), (0.63, 1.0), (1.0, 1.6), (1.6, 2.5), (2.5, 4.0),
         (4.0, 6.0), (5.5, 8.0), (7.0, 10.0), (9.0, 13.0), (12.0, 18.0), (17.0, 25.0), (23.0, 32.0), (30.0, 40.0),
         (37.0, 50.0), (48.0, 65.0), (55.0, 70.0), (63.0, 80.0), (80.0, 104.0), (95.0, 120.0), (110.0, 140.0),
         (137.0, 175.0), (160.0, 200.0), (200.0, 250.0), (250.0, 320.0), (320.0, 400.0), (400.0, 500.0),
         (500.0, 630.0)]
DISJUNTORES_MOTOR = [(0.1, 0.16), (0.16, 0.25), (0.25, 0.4), (0.4, 0.63), (0.63, 1.0), (1.0, 1.6), (1.6, 2.5),
                     (2.5, 4.0), (4.0, 6.3), (6.0, 10.0), (9.0, 14.0), (13.0, 18.0), (17.0, 23.0), (20.0, 25.0),
                     (24.0, 32.0), (30.0, 40.0), (37.0, 50.0), (48.0, 65.0), (55.0, 80.0), (70.0, 100.0),
                     (90.0, 125.0), (110.0, 160.0), (140.0, 200.0), (180.0, 250.0), (225.0, 320.0), (280.0, 400.0),
                     (350.0, 500.0), (440.0, 630.0)]
SOFT_STARTERS = [9, 12, 17, 22, 30, 37, 45, 60, 85, 115, 140, 170, 205, 255, 290, 340, 410, 485, 590]
INVERSORES = [2.6, 4.3, 7.3, 10, 16, 24, 31, 38, 45, 60, 73, 88, 105, 142, 180, 211, 250, 300, 370, 450, 550]


def _menor_que_atende(lista, corrente, nome):
    for valor in lista:
        if valor >= corrente - 1e-9:
            return valor
    raise ValueError(f"{nome}: nenhum de catálogo atende {corrente:.1f} A")


def _faixa(faixas, corrente, nome):
    """A faixa que contém a corrente, com ela o mais longe possível das pontas."""
    candidatas = [(lo, hi) for lo, hi in faixas if lo - 1e-9 <= corrente <= hi + 1e-9]
    if not candidatas:
        raise ValueError(f"{nome}: nenhuma faixa de catálogo contém {corrente:.2f} A")
    return max(candidatas, key=lambda f: min(corrente - f[0], f[1] - corrente) / (f[1] - f[0]))


def faixa_rele(corrente):
    """Faixa de ajuste (mín, máx) do relé térmico que contém a corrente [A]."""
    return _faixa(RELES, corrente, "Relé térmico")


def faixa_disjuntor_motor(corrente):
    """Faixa de ajuste (mín, máx) do disjuntor-motor que contém a corrente [A]."""
    return _faixa(DISJUNTORES_MOTOR, corrente, "Disjuntor-motor")


def dimensionar_partida(corrente_nominal, partida="direta"):
    """Componentes da partida do motor.

    Args:
        corrente_nominal: In do motor [A].
        partida: chave de ``PARTIDAS``.
    Returns:
        dict com ``partida``, ``corrente_nominal``, ``contatores`` {nome: A em AC-3},
        ``rele`` (faixa ou None), ``ajuste_rele`` [A], ``dispositivo`` (soft-starter ou
        inversor [A], ou None) e ``disjuntor_motor`` (faixa).
    """
    if partida not in PARTIDAS:
        raise ValueError(f"partida desconhecida: {partida}")
    corrente = float(corrente_nominal)
    if corrente <= 0:
        raise ValueError("a corrente nominal precisa ser positiva")
    resultado = {"partida": partida, "corrente_nominal": corrente, "dispositivo": None,
                 "disjuntor_motor": faixa_disjuntor_motor(corrente)}
    if partida == "direta":
        resultado["contatores"] = {"K1": _menor_que_atende(CONTATORES_AC3, corrente, "Contator")}
        resultado["ajuste_rele"] = round(corrente, 4)
        resultado["rele"] = faixa_rele(corrente)
    elif partida == "estrela_triangulo":
        enrolamento = round(FATOR_TRIANGULO * corrente, 4)
        resultado["contatores"] = {
            "K1_rede": _menor_que_atende(CONTATORES_AC3, enrolamento, "Contator de rede"),
            "K2_triangulo": _menor_que_atende(CONTATORES_AC3, enrolamento, "Contator de triângulo"),
            "K3_estrela": _menor_que_atende(CONTATORES_AC3, FATOR_ESTRELA * corrente, "Contator de estrela"),
        }
        resultado["ajuste_rele"] = enrolamento
        resultado["rele"] = faixa_rele(enrolamento)
    else:
        lista = SOFT_STARTERS if partida == "soft_starter" else INVERSORES
        resultado["dispositivo"] = _menor_que_atende(lista, corrente, PARTIDAS[partida])
        resultado["contatores"] = {"K1": _menor_que_atende(CONTATORES_AC3, corrente, "Contator de isolação")}
        resultado["ajuste_rele"] = round(corrente, 4)  # proteção eletrônica do próprio dispositivo
        resultado["rele"] = None
    return resultado


def dados_do_motor(potencia_cv, tensao=380.0, fases=3):
    """Dados do motor como os de ``motores.dados_motor``, para inserir o ponto de força na planta."""
    ativa, aparente = motores.potencia_eletrica(potencia_cv)
    return {"motor_cv": float(potencia_cv), "motor_kw": float(potencia_cv) * motores.KW_POR_CV,
            "potencia_ativa_kw": ativa, "potencia_aparente_kva": aparente,
            "fator_potencia": motores.FATOR_POTENCIA_TIPICO, "tensao": tensao, "fases": fases,
            "corrente": motores.corrente_nominal(potencia_cv, tensao, fases)}


def dimensionar_motor(potencia_cv, tensao=380.0, partida="direta"):
    """Partida pelo motor trifásico: a corrente nominal de ``core.functions.Predial.motores.corrente_nominal``."""
    corrente = motores.corrente_nominal(potencia_cv, tensao)
    resultado = dimensionar_partida(corrente, partida)
    resultado.update(potencia_cv=float(potencia_cv), tensao=float(tensao),
                     motor=dados_do_motor(potencia_cv, tensao))
    return resultado


def partida_pelo_rotulo(rotulo):
    """Chave de ``PARTIDAS`` pelo texto mostrado no formulário."""
    return next(chave for chave, texto in PARTIDAS.items() if texto == rotulo)


NOMES_CONTATORES = {"K1": "K1", "K1_rede": "K1 (rede)", "K2_triangulo": "K2 (triângulo)", "K3_estrela": "K3 (estrela)"}


def _br(valor, casas=1):
    return f"{valor:.{casas}f}".replace(".", ",")


def relatorio(resultado):
    """Texto do resultado para o formulário."""
    linhas = []
    if "potencia_cv" in resultado:
        linhas.append(f"Motor de {_br(resultado['potencia_cv'], 2)} cv em {resultado['tensao']:.0f} V")
    linhas.append(f"Corrente nominal: {_br(resultado['corrente_nominal'])} A — {PARTIDAS[resultado['partida']]}")
    lo, hi = resultado["disjuntor_motor"]
    linhas.append(f"Disjuntor-motor: faixa {_br(lo, 2)} a {_br(hi, 2)} A, ajuste {_br(resultado['corrente_nominal'])} A")
    for nome, corrente in resultado["contatores"].items():
        linhas.append(f"Contator {NOMES_CONTATORES.get(nome, nome)}: {corrente} A em AC-3")
    if resultado["rele"]:
        lo, hi = resultado["rele"]
        linhas.append(f"Relé térmico: faixa {_br(lo, 2)} a {_br(hi, 2)} A, ajuste {_br(resultado['ajuste_rele'], 2)} A")
    if resultado["dispositivo"]:
        linhas.append(f"{PARTIDAS[resultado['partida']]}: {resultado['dispositivo']} A (proteção do motor no próprio "
                      "dispositivo)")
    linhas.append("Valores de catálogo genéricos: confira com o fabricante.")
    return "\n".join(linhas)
