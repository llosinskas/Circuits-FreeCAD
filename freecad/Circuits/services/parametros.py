"""Planilha "Parâmetros do projeto": criação e leitura (``core.parametros``).

Uma linha por parâmetro, da linha 3 em diante: A rótulo, B valor (o usuário
edita), C chave e D dica. A planilha é marcada pela propriedade
``parametros_do_projeto``. Sem planilha, valem os padrões.
"""
import Spreadsheet  # noqa: F401  (registra o tipo Spreadsheet::Sheet)

from freecad.Circuits.core import parametros as regras

PRIMEIRA_LINHA = 3


def planilha(doc, criar=False):
    """A planilha de parâmetros do documento; com ``criar``, criada com os padrões se faltar."""
    for obj in doc.Objects:
        if hasattr(obj, "parametros_do_projeto"):
            return obj
    if not criar:
        return None
    folha = doc.addObject("Spreadsheet::Sheet", "Parametros_projeto")
    folha.Label = "Parâmetros do projeto"
    folha.addProperty("App::PropertyString", "parametros_do_projeto", "Projeto", "Parâmetros lidos pelos cálculos")
    folha.parametros_do_projeto = "1"
    folha.set("A1", "'Parâmetros do projeto: edite a coluna B; em branco vale o padrão")
    for coluna, titulo in zip("ABCD", ("Parâmetro", "Valor", "Chave", "Dica")):
        folha.set(f"{coluna}2", f"'{titulo}")
    for linha, (chave, (padrao, rotulo, dica)) in enumerate(regras.CAMPOS.items(), start=PRIMEIRA_LINHA):
        folha.set(f"A{linha}", f"'{rotulo}")
        folha.set(f"B{linha}", f"'{padrao:g}" if isinstance(padrao, float) else f"'{padrao}")
        folha.set(f"C{linha}", f"'{chave}")
        folha.set(f"D{linha}", f"'{dica}")
    doc.recompute()
    return folha


def _texto(folha, celula):
    try:
        conteudo = folha.getContents(celula)
    except Exception:
        return ""
    return str(conteudo or "").lstrip("'=").strip()


def ler(doc):
    """Parâmetros do projeto (``core.parametros.ler``): os da planilha, ou os padrões."""
    folha = planilha(doc)
    if folha is None:
        return regras.ler({})
    valores = {}
    for linha in range(PRIMEIRA_LINHA, PRIMEIRA_LINHA + len(regras.CAMPOS) + 20):
        chave = _texto(folha, f"C{linha}")
        if chave:
            valores[chave] = _texto(folha, f"B{linha}")
    return regras.ler(valores)


def _linhas_das_chaves(folha):
    """{chave: linha} das chaves da coluna C."""
    linhas = {}
    for linha in range(PRIMEIRA_LINHA, PRIMEIRA_LINHA + len(regras.CAMPOS) + 40):
        chave = _texto(folha, f"C{linha}")
        if chave:
            linhas[chave] = linha
    return linhas


def completar(doc):
    """Acrescenta no fim da planilha as linhas dos parâmetros novos (ex.: os do carimbo) que faltam
    em projetos antigos. Devolve a planilha (criada, se faltar)."""
    folha = planilha(doc, criar=True)
    linhas = _linhas_das_chaves(folha)
    proxima = max(linhas.values(), default=PRIMEIRA_LINHA - 1) + 1
    for chave, (padrao, rotulo, dica) in regras.CAMPOS.items():
        if chave in linhas:
            continue
        folha.set(f"A{proxima}", f"'{rotulo}")
        folha.set(f"B{proxima}", f"'{padrao:g}" if isinstance(padrao, float) else f"'{padrao}")
        folha.set(f"C{proxima}", f"'{chave}")
        folha.set(f"D{proxima}", f"'{dica}")
        proxima += 1
    return folha


def textos(doc):
    """{chave: texto da coluna B}, sem conversão (os campos de texto, como os do carimbo)."""
    folha = planilha(doc)
    if folha is None:
        return {}
    return {chave: _texto(folha, f"B{linha}") for chave, linha in _linhas_das_chaves(folha).items()}


def gravar(doc, valores):
    """Grava {chave: texto} na coluna B; acrescenta a linha da chave se faltar.

    Returns:
        Chaves que mudaram.
    """
    folha = completar(doc)
    linhas = _linhas_das_chaves(folha)
    mudaram = []
    for chave, valor in valores.items():
        if chave not in linhas:
            continue
        celula = f"B{linhas[chave]}"
        if _texto(folha, celula) == str(valor).strip():
            continue
        folha.set(celula, f"'{valor}")
        mudaram.append(chave)
    return mudaram
