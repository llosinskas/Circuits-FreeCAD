"""Resistência de aterramento com hastes verticais.

Sem FreeCAD. Fórmulas usuais (IEEE Std 142, "Green Book"):

- uma haste: R1 = ρ / (2π·L) · [ln(4L/a) − 1], com a = raio da haste (Dwight);
- n hastes em linha, espaçadas de s: Rn = R1 · (1 + λ·α) / n, com
  α = ρ / (2π·R1·s) e λ = 2·(1/2 + 1/3 + ... + 1/n), que reproduz a tabela
  da norma para hastes alinhadas (λ = 1,00; 1,67; 2,17; 2,57... para n = 2, 3, 4, 5).

ATENÇÃO: o resultado depende da resistividade real do solo, que deve ser
medida (método de Wenner). As resistividades da lista são valores típicos. A
resistência máxima depende do esquema de aterramento e do SPDA: confira com a
NBR 5410 e a NBR 5419.

Unidades: resistividade em Ω·m, comprimentos em m, diâmetro em mm, resistência em Ω.
"""
import math

ALVO_PADRAO = 10.0  # Ω, valor usual de referência para SPDA
HASTE_COMPRIMENTO = 2.4  # m
HASTE_DIAMETRO_MM = 15.9  # 5/8"
ESPACAMENTO_PADRAO = 3.0  # m, ao menos o comprimento da haste
MAXIMO_HASTES = 30

# Resistividade típica por tipo de solo [Ω·m].
SOLOS = {
    "Terra vegetal úmida (50 Ω·m)": 50.0,
    "Argila (100 Ω·m)": 100.0,
    "Argila com areia (300 Ω·m)": 300.0,
    "Areia úmida (500 Ω·m)": 500.0,
    "Areia seca ou cascalho (1000 Ω·m)": 1000.0,
    "Rocha (3000 Ω·m)": 3000.0,
}


def resistencia_haste(resistividade, comprimento=HASTE_COMPRIMENTO, diametro_mm=HASTE_DIAMETRO_MM):
    """Resistência de uma haste vertical [Ω] (fórmula de Dwight)."""
    if resistividade <= 0 or comprimento <= 0 or diametro_mm <= 0:
        raise ValueError("Resistividade, comprimento e diâmetro da haste precisam ser maiores que zero.")
    raio = diametro_mm / 2000.0
    return resistividade / (2 * math.pi * comprimento) * (math.log(4 * comprimento / raio) - 1)


def fator_lambda(hastes):
    """Fator λ das hastes em linha: 2·(1/2 + 1/3 + ... + 1/n); zero para uma haste."""
    return 2 * sum(1.0 / k for k in range(2, int(hastes) + 1))


def resistencia_hastes(resistividade, hastes, espacamento=ESPACAMENTO_PADRAO, comprimento=HASTE_COMPRIMENTO,
                       diametro_mm=HASTE_DIAMETRO_MM):
    """Resistência de n hastes em linha, igualmente espaçadas [Ω]."""
    if hastes < 1:
        raise ValueError("É preciso ao menos uma haste.")
    if hastes > 1 and espacamento <= 0:
        raise ValueError("O espaçamento entre as hastes precisa ser maior que zero.")
    r1 = resistencia_haste(resistividade, comprimento, diametro_mm)
    if hastes == 1:
        return r1
    alfa = resistividade / (2 * math.pi * r1 * espacamento)
    return r1 * (1 + fator_lambda(hastes) * alfa) / hastes


def dimensionar(resistividade, resistencia_alvo=ALVO_PADRAO, hastes=0, espacamento=ESPACAMENTO_PADRAO,
                comprimento_haste=HASTE_COMPRIMENTO, diametro_haste=HASTE_DIAMETRO_MM):
    """Resistência de aterramento e número de hastes.

    Args:
        resistividade: do solo [Ω·m].
        resistencia_alvo: resistência máxima desejada [Ω].
        hastes: número de hastes; 0 calcula o menor número que atinge o alvo.
        espacamento: distância entre hastes vizinhas [m].
        comprimento_haste [m], diametro_haste [mm].
    Returns:
        dict com a resistência de uma haste, o número de hastes, a resistência
        final, se atende ao alvo, o comprimento do cabo entre as hastes [m] e o
        número de hastes que atenderia (None se nem com ``MAXIMO_HASTES``).
    """
    if resistencia_alvo <= 0:
        raise ValueError("A resistência desejada precisa ser maior que zero.")
    r1 = resistencia_haste(resistividade, comprimento_haste, diametro_haste)
    necessarias = next(
        (n for n in range(1, MAXIMO_HASTES + 1)
         if resistencia_hastes(resistividade, n, espacamento, comprimento_haste, diametro_haste) <= resistencia_alvo),
        None,
    )
    usadas = int(hastes) if hastes else (necessarias or MAXIMO_HASTES)
    final = resistencia_hastes(resistividade, usadas, espacamento, comprimento_haste, diametro_haste)
    return {
        "resistividade": resistividade,
        "resistencia_alvo": resistencia_alvo,
        "resistencia_uma_haste": r1,
        "hastes": usadas,
        "espacamento": espacamento,
        "resistencia": final,
        "atende": final <= resistencia_alvo,
        "hastes_necessarias": necessarias,
        "cabo_entre_hastes": (usadas - 1) * espacamento,
    }


def relatorio(resultado):
    """Texto do cálculo, para mostrar ao usuário."""
    r = resultado
    linhas = [
        f"Resistividade do solo: {r['resistividade']:.0f} Ω·m",
        f"Uma haste: {r['resistencia_uma_haste']:.1f} Ω",
        f"{r['hastes']} haste(s) em linha, a cada {r['espacamento']:.1f} m: {r['resistencia']:.1f} Ω",
        f"Resistência desejada: {r['resistencia_alvo']:.1f} Ω - " + ("atende" if r["atende"] else "NÃO atende"),
    ]
    if not r["atende"]:
        if r["hastes_necessarias"]:
            linhas.append(f"Seriam necessárias {r['hastes_necessarias']} hastes em linha.")
        else:
            linhas.append(f"Nem {MAXIMO_HASTES} hastes em linha atingem o valor: trate o solo ou use malha.")
    linhas += [
        f"Cabo de cobre nu entre as hastes: {r['cabo_entre_hastes']:.1f} m",
        "",
        "Resistividade típica: meça o solo (método de Wenner) e confira o valor máximo com a NBR 5410 e a NBR 5419.",
    ]
    return "\n".join(linhas)
