"""Layout das planilhas de quadros e circuitos, independente do FreeCAD."""
import re

CABECALHO_CIRCUITOS = [
    "ID",
    "Origem",
    "Destino",
    "Potência (kW)",
    "Tensão (V)",
    "Fator de potência",
    "Potência aparente (kVA)",
    "Corrente (A)",
    "Comprimento do circuito (m)",
    "% de queda de tensão ",
    "Secção do cabo mm²",
    "Método de instalação",
    "Fator de agrupamento",
    "Fator de temperatura",
    "Disjutor (A)",
    "Curva do disjuntor",
    "Fase R",
    "Fase S",
    "Fase T",
]

# Também são os aliases das células da linha 3: o unifilar lê os dados por eles.
CABECALHO_QUADRO = [
    "indentificacao_painel",
    "bitola",
    "origem",
    "curto_circuito",
    "descricao",
    "tensao",
    "numero_fases",
    "terra",
    "neutro",
    "curva_disjuntor",
    "corrente_nominal_disjuntor",
    "corrente_curto_circuito",
    "potencia_instalada",
    "potencia_demanda",
    "material_quadro",
    "DPS",
    "classe_DPS",
    "tensao_DPS",
    "corrente_DPS",
]

CABECALHO_CIRCUITO_QUADRO = [
    "N_circuito",
    "Destino",
    "Potência [kW]",
    "Tensão [V]",
    "Fator de potência",
    "Comprimento",
    "Potência Aparente [kVA]",
    "Corrente [A]",
    "Queda de tensão [%]",
    "Cabo [mm²]",
    "Método de instalação",
    "fator de agrupamento",
    "Fator de temperatura",
    "Disjuntor",
    "Curva disjuntor",
    "Fase R",
    "Fase S",
    "Fase T",
    "Neutro",
    "Terra",
    "DR",
    "Corrente DR",
    "Descrição do Circuito",
]

# Coluna da planilha do quadro onde cada dado do diálogo de circuito é gravado.
COLUNAS_CIRCUITO = {
    "A": "N_circuito",
    "B": "Destino",
    "C": "Potencia",
    "D": "Tensao",
    "H": "Corrente",
    "J": "Cabo",
    "N": "Disjuntor",
    "O": "Curva",
    "P": "Fase_R",
    "Q": "Fase_S",
    "R": "Fase_T",
    "S": "Neutro",
    "T": "Terra",
    "U": "DR",
    "V": "Corrente_DR",
}

LINHA_CABECALHO_CIRCUITOS = 5
PRIMEIRA_LINHA_CIRCUITOS = 6


def coluna(indice):
    """Letra da coluna para um índice a partir de zero (só de A a Z)."""
    return chr(ord("A") + indice)


def ultima_linha(celulas):
    """Maior linha usada, dado nomes de células como 'A1'.

    Limitação conhecida: considera só o primeiro dígito, então 'A12' conta como
    linha 1. Ver "Problemas conhecidos" no AGENTS.md.
    """
    linhas = [int(re.search(r"\d", celula).group()) for celula in celulas]
    return max(linhas) if linhas else 0
