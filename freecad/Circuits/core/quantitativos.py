"""Quantitativo de materiais do projeto elétrico, sem FreeCAD.

Recebe o que foi lido do documento (pontos, interruptores, eletrodutos e os
componentes de cada quadro) e devolve as linhas do quantitativo, somadas e em
ordem: Pontos, Interruptores, Caixas, Eletrodutos e Quadros.

Regras (estimativa; confira antes de comprar):

- uma caixa por ponto: 4x2" na parede, octogonal 4x4" no teto, de piso no piso;
  quadros não levam caixa;
- eletrodutos pelo comprimento desenhado e pelas verticais até as caixas, com
  ``PERDA_ELETRODUTO`` a mais;
- fios e cabos pelo roteamento dos circuitos na rede de eletrodutos
  (``core.rede``), já com as folgas nas caixas.

Unidades: comprimentos de entrada em mm, de saída em m.
"""
from freecad.Circuits.core import simbolos

GRUPOS = ["Pontos", "Interruptores", "Caixas", "Eletrodutos", "Fios e cabos", "Quadros", "Aterramento"]
COLUNAS = ["Grupo", "Item", "Especificação", "Unidade", "Quantidade"]
PERDA_ELETRODUTO = 0.10

CAIXAS = {
    "4x2": "Caixa 4x2\" de embutir",
    "octogonal": "Caixa octogonal 4x4\" de laje",
    "piso": "Caixa de piso 4x4\"",
    "passagem": "Caixa de passagem 4x4\"",
}
CABO_ATERRAMENTO = "Cabo de cobre nu"
PERDA_CABO_ATERRAMENTO = 0.10
CABO = "Cabo flexível 750 V"
FUNCOES_FIO = {
    "fase": "fase",
    "neutro": "neutro (azul claro)",
    "terra": "terra (verde e amarelo)",
    "retorno": "retorno",
}
_CAIXA_DO_SIMBOLO = {
    "luz_teto": "octogonal",
    "ventilador": "octogonal",
    "fluorescente": "octogonal",
    "embutida": "octogonal",
    "tomada_piso": "piso",
    "caixa_passagem": "passagem",
    "fotocelula": None,  # fica na própria base, na fachada ou no poste
}


def caixa_do_simbolo(simbolo):
    """Chave de ``CAIXAS`` para o símbolo do catálogo, ou None (quadros, aterramento e fotocélula não levam)."""
    dados = simbolos.CATALOGO.get(simbolo)
    if dados is None or dados["categoria"] in (simbolos.QUADRO, simbolos.ATERRAMENTO):
        return None
    return _CAIXA_DO_SIMBOLO.get(simbolo, "4x2")


def _linha(grupo, item, especificacao, unidade, quantidade):
    return {"grupo": grupo, "item": item, "especificacao": especificacao, "unidade": unidade, "quantidade": quantidade}


def _secao(valor):
    """Seção como texto: 2.5 -> '2,5'; 10.0 -> '10'."""
    return f"{float(valor):g}".replace(".", ",")


def montar(pontos=(), eletrodutos=(), componentes_quadros=(), fios=None, verticais=(), aterramento=()):
    """Linhas do quantitativo.

    Args:
        pontos: dicionários com ``grupo`` ('Pontos', 'Interruptores' ou 'Quadros'),
            ``item``, ``especificacao`` e ``caixa`` (chave de ``CAIXAS`` ou None).
        eletrodutos: pares (diâmetro nominal, comprimento [mm]).
        componentes_quadros: itens de ``core.quadro.componentes`` de todos os quadros.
        fios: {(seção [mm²], função): metros}, de ``core.rede.analisar``.
        verticais: verticais de ``core.rede.analisar`` (usa ``diametro`` e ``comprimento`` em m).
        aterramento: pares (seção [mm²], comprimento [mm]) dos condutores de aterramento.
    Returns:
        Lista de dicionários com ``grupo``, ``item``, ``especificacao``, ``unidade``
        e ``quantidade`` (inteiro para 'un', metros com duas casas para 'm').
    """
    somas = {}

    def somar(grupo, item, especificacao, unidade, quantidade):
        chave = (grupo, item, especificacao, unidade)
        somas[chave] = somas.get(chave, 0) + quantidade

    for ponto in pontos:
        if ponto.get("item"):  # a caixa de passagem só conta como caixa
            somar(ponto["grupo"], ponto["item"], ponto.get("especificacao", ""), "un", 1)
        if ponto.get("caixa"):
            somar("Caixas", CAIXAS[ponto["caixa"]], "", "un", 1)
    for diametro, comprimento_mm in eletrodutos:
        if comprimento_mm > 0:
            somar("Eletrodutos", "Eletroduto", f"{diametro}\" (inclui {PERDA_ELETRODUTO:.0%} de perdas)", "m",
                  comprimento_mm / 1000.0 * (1 + PERDA_ELETRODUTO))
    for vertical in verticais:
        somar("Eletrodutos", "Eletroduto", f"{vertical['diametro']}\" verticais (inclui {PERDA_ELETRODUTO:.0%} de perdas)",
              "m", vertical["comprimento"] * (1 + PERDA_ELETRODUTO))
    for (secao, funcao), metros in (fios or {}).items():
        somar("Fios e cabos", CABO, f"{_secao(secao)} mm² - {FUNCOES_FIO.get(funcao, funcao)}", "m", metros)
    for secao, comprimento_mm in aterramento:
        if comprimento_mm > 0:
            somar("Aterramento", CABO_ATERRAMENTO, f"{_secao(secao)} mm² (inclui {PERDA_CABO_ATERRAMENTO:.0%} de perdas)",
                  "m", comprimento_mm / 1000.0 * (1 + PERDA_CABO_ATERRAMENTO))
    for componente in componentes_quadros:
        somar(componente.get("grupo", "Quadros"), componente["item"], componente["especificacao"], componente["unidade"],
              componente["quantidade"])

    def ordem(chave):
        grupo, item, especificacao, _ = chave
        posicao = GRUPOS.index(grupo) if grupo in GRUPOS else len(GRUPOS)
        if grupo == "Fios e cabos":  # por seção numérica e depois pela ordem das funções
            secao, _, funcao = especificacao.partition(" mm² - ")
            rotulos = list(FUNCOES_FIO.values())
            return posicao, item, (float(secao.replace(",", ".")), rotulos.index(funcao) if funcao in rotulos else 9)
        return posicao, item, (0.0, especificacao)

    linhas = []
    for chave in sorted(somas, key=ordem):
        grupo, item, especificacao, unidade = chave
        quantidade = round(somas[chave], 2) if unidade == "m" else int(round(somas[chave]))
        linhas.append(_linha(grupo, item, especificacao, unidade, quantidade))
    return linhas


COLUNAS_VERTICAIS = ["Pavimento", "Caixa", "Circuito", "Altura do eletroduto [m]", "Altura da caixa [m]",
                     "Vertical [m]", "Sentido", "Diâmetro"]
COLUNAS_CIRCUITOS = ["Pavimento", "Quadro", "Circuito", "Seção [mm²]", "Condutores", "Pontos", "Trajeto [m]", "Fio total [m]"]


def tabela_verticais(verticais):
    """Lista de verticais (de ``core.rede.analisar``) como tabela, com cabeçalho."""
    ordenadas = sorted(verticais, key=lambda v: (v["pavimento"], v["circuito"], v["caixa"]))
    return [list(COLUNAS_VERTICAIS)] + [
        [v["pavimento"], v["caixa"], v["circuito"], round(v["altura_eletroduto"] / 1000.0, 2),
         round(v["altura_caixa"] / 1000.0, 2), round(v["comprimento"], 2), v["sentido"], f"{v['diametro']}\""]
        for v in ordenadas
    ]


def tabela_circuitos(circuitos):
    """Fiação por circuito (de ``core.rede.analisar``) como tabela, com cabeçalho."""
    return [list(COLUNAS_CIRCUITOS)] + [
        [c.get("pavimento", ""), c["quadro"], c["circuito"], _secao(c["secao"]), c["condutores"], c["pontos"], float(c["trajeto"]),
         float(c["fio"])]
        for c in circuitos
    ]


SEM_PAVIMENTO = "Sem pavimento"
COLUNAS_POR_PAVIMENTO = ["Pavimento"] + COLUNAS


def tabela_por_pavimento(por_pavimento):
    """Quantitativo separado por pavimento como tabela, com cabeçalho.

    Args:
        por_pavimento: pares (nome do pavimento, linhas de ``montar``) na ordem
            em que devem aparecer; nome vazio vira ``SEM_PAVIMENTO``.
    """
    tabela = [list(COLUNAS_POR_PAVIMENTO)]
    for pavimento, linhas in por_pavimento:
        for linha in linhas:
            tabela.append([pavimento or SEM_PAVIMENTO, linha["grupo"], linha["item"], linha["especificacao"],
                           linha["unidade"], linha["quantidade"]])
    return tabela


def como_tabela(linhas):
    """Linhas do quantitativo como lista de listas, com o cabeçalho ``COLUNAS`` na primeira."""
    return [list(COLUNAS)] + [
        [linha["grupo"], linha["item"], linha["especificacao"], linha["unidade"], linha["quantidade"]] for linha in linhas
    ]
