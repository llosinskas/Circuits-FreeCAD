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
    "IDR",
    "sensibilidade_IDR",
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
    "W": "Comprimento",
    "X": "Queda",
    "Y": "Criterio",
    "Z": "Grupo_DR",
}

LINHA_CABECALHO_CIRCUITOS = 5
PRIMEIRA_LINHA_CIRCUITOS = 6


def coluna(indice):
    """Letra da coluna para um índice a partir de zero (só de A a Z)."""
    return chr(ord("A") + indice)


def ultima_linha(celulas):
    """Maior linha usada, dado nomes de células como 'A1' ou 'AB12'."""
    linhas = [int(re.search(r"\d+$", celula).group()) for celula in celulas]
    return max(linhas) if linhas else 0


# --- Planilha de circuitos do quadro -----------------------------------------
# Cada quadro tem uma planilha própria de circuitos, ligada a ele. O usuário
# pode preenchê-la à mão: bastam o número, a descrição, a potência e a tensão;
# o que ficar em branco (corrente, cabo, disjuntor) é calculado na leitura.

# (coluna, chave, título). As chaves são as mesmas de COLUNAS_CIRCUITO, menos
# as três de fase, que aqui são um texto só ("R", "RS", "RST").
PLANILHA_CIRCUITOS = [
    ("A", "N_circuito", "Circuito"),
    ("B", "Destino", "Descrição"),
    ("C", "Potencia", "Potência [W]"),
    ("D", "Tensao", "Tensão [V]"),
    ("E", "Fases", "Fases (R, S, T)"),
    ("F", "Corrente", "Corrente [A]"),
    ("G", "Cabo", "Cabo [mm²]"),
    ("H", "Disjuntor", "Disjuntor [A]"),
    ("I", "Curva", "Curva"),
    ("J", "DR", "DR (S/N)"),
    ("K", "Corrente_DR", "Sensibilidade do DR"),
    ("L", "Neutro", "Neutro (S/N)"),
    ("M", "Terra", "Terra (S/N)"),
    ("N", "Comprimento", "Comprimento [m]"),
    ("O", "Queda", "Queda de tensão [%]"),
    ("P", "Criterio", "Critério determinante"),
    ("Q", "Grupo_DR", "Grupo do DR (mesmo nome = um DR)"),
]
LINHA_TITULO_CIRCUITOS = 1
LINHA_TITULOS_COLUNAS = 2
PRIMEIRA_LINHA_PLANILHA_CIRCUITOS = 3
AJUDA_CIRCUITOS = (
    "Um circuito por linha. Preencha circuito, descrição, potência e tensão; "
    "corrente, cabo e disjuntor em branco são calculados."
)

_SIM = ("s", "sim", "true", "x", "1", "1.0", "y", "yes")
_CAMPOS_SIM_NAO = ("DR", "Neutro", "Terra")


def sim_ou_nao(texto):
    """Lê uma célula de sim/não: S, Sim, True, X e 1 valem sim; o resto, não."""
    return str(texto).strip().lower() in _SIM


def linha_para_circuito(celulas):
    """Converte uma linha da planilha de circuitos nos dados de circuito usados pela bancada.

    Args:
        celulas: textos da linha, pelas chaves de ``PLANILHA_CIRCUITOS``.
    Returns:
        dict com as chaves de ``COLUNAS_CIRCUITO`` (fases separadas e sim/não como 'True'/'False').
    """
    fases = str(celulas.get("Fases", "")).upper()
    circuito = {chave: str(celulas.get(chave, "")).strip() for _, chave, _ in PLANILHA_CIRCUITOS if chave != "Fases"}
    for fase in "RST":
        circuito[f"Fase_{fase}"] = str(fase in fases)
    for chave in _CAMPOS_SIM_NAO:
        circuito[chave] = str(sim_ou_nao(circuito[chave]))
    return circuito


def circuito_para_linha(circuito):
    """Converte os dados de um circuito nos textos de uma linha da planilha de circuitos.

    Returns:
        dict {coluna: texto}.
    """
    fases = "".join(fase for fase in "RST" if sim_ou_nao(circuito.get(f"Fase_{fase}", "")))
    linha = {}
    for coluna, chave, _ in PLANILHA_CIRCUITOS:
        if chave == "Fases":
            linha[coluna] = fases
        elif chave in _CAMPOS_SIM_NAO:
            linha[coluna] = "S" if sim_ou_nao(circuito.get(chave, "")) else "N"
        else:
            linha[coluna] = str(circuito.get(chave, "")).strip()
    return linha
