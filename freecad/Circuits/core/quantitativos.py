"""Quantitativo de materiais do projeto elétrico, sem FreeCAD.

Recebe o que foi lido do documento (pontos, interruptores, eletrodutos e os
componentes de cada quadro) e devolve as linhas do quantitativo, somadas e em
ordem: Pontos, Interruptores, Caixas, Eletrodutos e Quadros.

Regras (estimativa; confira antes de comprar):

- uma caixa por ponto: 4x2" na parede, octogonal 4x4" no teto, de piso no piso;
  quadros não levam caixa;
- eletrodutos pelo comprimento desenhado, com ``PERDA_ELETRODUTO`` a mais;
  as descidas até as caixas não entram;
- os condutores (fios e cabos) não entram: dependem do roteamento dos circuitos,
  que a bancada ainda não faz.

Unidades: comprimentos de entrada em mm, de saída em m.
"""
from freecad.Circuits.core import simbolos

GRUPOS = ["Pontos", "Interruptores", "Caixas", "Eletrodutos", "Quadros"]
COLUNAS = ["Grupo", "Item", "Especificação", "Unidade", "Quantidade"]
PERDA_ELETRODUTO = 0.10

CAIXAS = {
    "4x2": "Caixa 4x2\" de embutir",
    "octogonal": "Caixa octogonal 4x4\" de laje",
    "piso": "Caixa de piso 4x4\"",
}
_CAIXA_DO_SIMBOLO = {
    "luz_teto": "octogonal",
    "ventilador": "octogonal",
    "fluorescente": "octogonal",
    "embutida": "octogonal",
    "tomada_piso": "piso",
}


def caixa_do_simbolo(simbolo):
    """Chave de ``CAIXAS`` para o símbolo do catálogo, ou None (quadros não levam caixa)."""
    dados = simbolos.CATALOGO.get(simbolo)
    if dados is None or dados["categoria"] == simbolos.QUADRO:
        return None
    return _CAIXA_DO_SIMBOLO.get(simbolo, "4x2")


def _linha(grupo, item, especificacao, unidade, quantidade):
    return {"grupo": grupo, "item": item, "especificacao": especificacao, "unidade": unidade, "quantidade": quantidade}


def montar(pontos=(), eletrodutos=(), componentes_quadros=()):
    """Linhas do quantitativo.

    Args:
        pontos: dicionários com ``grupo`` ('Pontos', 'Interruptores' ou 'Quadros'),
            ``item``, ``especificacao`` e ``caixa`` (chave de ``CAIXAS`` ou None).
        eletrodutos: pares (diâmetro nominal, comprimento [mm]).
        componentes_quadros: itens de ``core.quadro.componentes`` de todos os quadros.
    Returns:
        Lista de dicionários com ``grupo``, ``item``, ``especificacao``, ``unidade``
        e ``quantidade`` (inteiro para 'un', metros com duas casas para 'm').
    """
    somas = {}

    def somar(grupo, item, especificacao, unidade, quantidade):
        chave = (grupo, item, especificacao, unidade)
        somas[chave] = somas.get(chave, 0) + quantidade

    for ponto in pontos:
        somar(ponto["grupo"], ponto["item"], ponto.get("especificacao", ""), "un", 1)
        if ponto.get("caixa"):
            somar("Caixas", CAIXAS[ponto["caixa"]], "", "un", 1)
    for diametro, comprimento_mm in eletrodutos:
        if comprimento_mm > 0:
            somar("Eletrodutos", "Eletroduto", f"{diametro}\" (inclui {PERDA_ELETRODUTO:.0%} de perdas)", "m",
                  comprimento_mm / 1000.0 * (1 + PERDA_ELETRODUTO))
    for componente in componentes_quadros:
        somar("Quadros", componente["item"], componente["especificacao"], componente["unidade"], componente["quantidade"])

    def ordem(chave):
        grupo, item, especificacao, _ = chave
        posicao = GRUPOS.index(grupo) if grupo in GRUPOS else len(GRUPOS)
        return posicao, item, especificacao

    linhas = []
    for chave in sorted(somas, key=ordem):
        grupo, item, especificacao, unidade = chave
        quantidade = round(somas[chave], 2) if unidade == "m" else int(round(somas[chave]))
        linhas.append(_linha(grupo, item, especificacao, unidade, quantidade))
    return linhas


def como_tabela(linhas):
    """Linhas do quantitativo como lista de listas, com o cabeçalho ``COLUNAS`` na primeira."""
    return [list(COLUNAS)] + [
        [linha["grupo"], linha["item"], linha["especificacao"], linha["unidade"], linha["quantidade"]] for linha in linhas
    ]
