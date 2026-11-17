"""Parâmetros do projeto elétrico, sem FreeCAD.

Os valores ficam na planilha "Parâmetros do projeto" e chegam aqui como
{nome: texto}. ``ler`` completa o que faltar com ``PADROES``, converte os
números (aceita vírgula decimal) e troca valores inválidos pelo padrão.

Unidades: tensões em V, temperaturas em °C, quedas em %, sensibilidade do DR
em mA, corrente de curto em kA, resistência de aterramento em Ω.
"""

ESQUEMAS = ("TN-S", "TN-C-S", "TT")
ISOLACOES = ("PVC", "EPR", "XLPE")
MATERIAIS = ("cobre", "aluminio")

# nome -> (padrão, rótulo na planilha, dica)
CAMPOS = {
    "concessionaria": ("", "Concessionária", "Distribuidora de energia; define as tabelas de demanda e o padrão de entrada"),
    "tensao_fn": (127.0, "Tensão fase-neutro [V]", "127 ou 220 V, conforme a rede da concessionária"),
    "tensao_ff": (220.0, "Tensão fase-fase [V]", "220 ou 380 V, conforme a rede da concessionária"),
    "icc_entrada_ka": (5.0, "Corrente de curto na entrada [kA]", "Informada pela concessionária no ponto de entrega"),
    "esquema": ("TN-S", "Esquema de aterramento", "TN-S, TN-C-S ou TT"),
    "resistencia_terra": (10.0, "Resistência de aterramento [Ω]", "Medida ou calculada; usada no esquema TT"),
    "material": ("cobre", "Material dos condutores", "cobre ou aluminio"),
    "isolacao": ("PVC", "Isolação dos condutores", "PVC (70 °C), EPR ou XLPE (90 °C)"),
    "temperatura_ambiente": (30.0, "Temperatura ambiente [°C]", "Temperatura do ar onde passam os cabos"),
    "temperatura_solo": (20.0, "Temperatura do solo [°C]", "Para linhas enterradas"),
    "queda_terminal": (4.0, "Queda máxima nos circuitos terminais [%]", "NBR 5410: 4 % a partir do quadro"),
    "queda_total": (7.0, "Queda máxima total [%]", "NBR 5410: 7 % desde a entrada, com o alimentador"),
    "tempo_curto": (0.0, "Tempo de atuação no curto [s]",
                    "0 não verifica: disjuntores limitadores têm I²t menor que I²·t; confira no catálogo. "
                    "Preencha (ex.: 0,1 s) para verificar S ≥ I·√t / k"),
    "sensibilidade_dr": (30.0, "Sensibilidade do DR [mA]", "30 mA para proteção de pessoas"),
    "curva_iluminacao": ("B", "Curva dos disjuntores de iluminação", "B ou C"),
    "curva_tomadas": ("C", "Curva dos disjuntores de tomadas e uso específico", "B, C ou D"),
    "simbolos_descida_caixas": ("S", "Símbolo de descida em cada caixa",
                                "S: símbolo de subida/descida em toda caixa fora da altura do eletroduto; "
                                "N: só nas mudanças de altura entre eletrodutos e nas eletrocalhas"),
}
PADROES = {nome: dados[0] for nome, dados in CAMPOS.items()}
_ESCOLHAS = {
    "esquema": ESQUEMAS,
    "isolacao": ISOLACOES,
    "material": MATERIAIS,
    "curva_iluminacao": ("B", "C", "D"),
    "curva_tomadas": ("B", "C", "D"),
    "simbolos_descida_caixas": ("S", "N"),
}


def _numero(texto):
    return float(str(texto).strip().replace(",", "."))


def _escolha(texto, opcoes):
    """A opção que corresponde ao texto, sem diferenciar maiúsculas, ou None."""
    procurado = str(texto).strip().lower()
    return next((opcao for opcao in opcoes if opcao.lower() == procurado), None)


def ler(valores):
    """Parâmetros completos a partir dos textos da planilha.

    Args:
        valores: {nome: texto}; nomes que não estão em ``CAMPOS`` são ignorados.
    Returns:
        Novo dicionário com todos os nomes de ``CAMPOS``.
    """
    resultado = dict(PADROES)
    for nome, texto in (valores or {}).items():
        if nome not in PADROES or str(texto).strip() == "":
            continue
        padrao = PADROES[nome]
        if nome in _ESCOLHAS:
            escolhido = _escolha(texto, _ESCOLHAS[nome])
            if escolhido is not None:
                resultado[nome] = escolhido
        elif isinstance(padrao, float):
            try:
                resultado[nome] = _numero(texto)
            except ValueError:
                pass
        else:
            resultado[nome] = str(texto).strip()
    return resultado


def tensao_do_circuito(parametros, n_fases):
    """Tensão entre os condutores do circuito [V]: fase-neutro no monofásico, fase-fase nos outros."""
    return parametros["tensao_fn"] if int(n_fases) <= 1 else parametros["tensao_ff"]
