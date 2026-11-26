"""Planilha "Estudo de curto": barras, leitura e resultado (``core.curto``, IEC 60909).

Uma barra por linha, da linha 3 em diante, nas colunas de ``regras.COLUNAS_ESTUDO``; a
tensão de linha em ``regras.CELULA_TENSAO``. A planilha é marcada pela propriedade
``estudo_de_curto``. Ao ser criada, recebe a entrada (exemplo de rede e transformador) e
uma barra por quadro do projeto, com o cabo de entrada dele. O resultado vai para as
colunas L a O e, em cada quadro com o mesmo nome, para o campo ``curto_circuito`` (kA).
"""
import Spreadsheet  # noqa: F401  (registra o tipo Spreadsheet::Sheet)

from freecad.Circuits.core import curto as regras
from freecad.Circuits.services import planilhas

MARCA = "estudo_de_curto"


def _br(valor):
    return f"{round(valor, 1):g}".replace(".", ",")


def planilha(doc):
    return next((obj for obj in doc.Objects if hasattr(obj, MARCA)), None)


def _texto(folha, celula):
    try:
        conteudo = folha.getContents(celula)
    except Exception:
        return ""
    return str(conteudo or "").lstrip("'=").strip()


def _nome_do_quadro(quadro):
    dados = planilhas.ler_quadro(quadro)
    return dados.get("indentificacao_painel") or quadro.Label


def quadros_do_projeto(doc):
    """[(nome, origem, seção do cabo de entrada)] de cada quadro."""
    resultado = []
    for quadro in planilhas.listar_quadros(doc):
        dados = planilhas.ler_quadro(quadro)
        resultado.append((_nome_do_quadro(quadro), dados.get("origem", ""), dados.get("bitola", "")))
    return resultado


def criar(doc):
    """Cria a planilha com a entrada e os quadros do projeto. Devolve (planilha, quantidade de quadros)."""
    folha = doc.addObject("Spreadsheet::Sheet", "Estudo_curto")
    folha.Label = "Estudo de curto"
    folha.addProperty("App::PropertyString", MARCA, "Curto", "Barras lidas pelo estudo de curto-circuito")
    setattr(folha, MARCA, "IEC 60909")
    folha.set("A1", f"'{regras.AJUDA}")
    folha.set(regras.CELULA_ROTULO_TENSAO, "'Tensão de linha [V]")
    folha.set(regras.CELULA_TENSAO, f"{regras.TENSAO_PADRAO:g}")
    for coluna, _, titulo in regras.COLUNAS_ESTUDO + regras.COLUNAS_RESULTADO:
        folha.set(f"{coluna}{regras.LINHA_TITULOS}", f"'{titulo}")
    try:
        folha.setColumnWidth("A", 160)
        folha.setColumnWidth("B", 170)
    except Exception:
        pass
    quadros = quadros_do_projeto(doc)
    for linha, dados in enumerate(regras.linhas_dos_quadros(quadros), start=regras.PRIMEIRA_LINHA):
        for coluna, chave, _ in regras.COLUNAS_ESTUDO:
            if dados.get(chave):
                folha.set(f"{coluna}{linha}", f"'{dados[chave]}")
    doc.recompute()
    return folha, len(quadros)


def ler(folha):
    """(barras de ``core.curto.estudo``, tensão [V]); ValueError com a linha que tem problema."""
    linhas = []
    for linha in range(regras.PRIMEIRA_LINHA, planilhas.ultima_linha(folha) + 1):
        linhas.append((linha, {chave: _texto(folha, f"{coluna}{linha}") for coluna, chave, _ in regras.COLUNAS_ESTUDO}))
    texto = _texto(folha, regras.CELULA_TENSAO).replace(",", ".")
    try:
        tensao = float(texto) if texto else regras.TENSAO_PADRAO
    except ValueError:
        raise ValueError(f"A tensão em {regras.CELULA_TENSAO} não é um número ({texto}).") from None
    return regras.barras_das_linhas(linhas), tensao


def gravar_resultado(doc, folha, resultado):
    """Escreve o resultado ao lado de cada barra e o I″k3 no ``curto_circuito`` dos quadros.

    Returns:
        Avisos: quadros cujo disjuntor geral tem capacidade de interrupção menor que a pedida.
    """
    for linha in range(regras.PRIMEIRA_LINHA, planilhas.ultima_linha(folha) + 1):
        nome = _texto(folha, f"A{linha}")
        dados = resultado.get(nome)
        for coluna, chave, _ in regras.COLUNAS_RESULTADO:
            folha.set(f"{coluna}{linha}", f"{dados[chave]:.2f}" if dados else "")
    avisos = []
    for quadro in planilhas.listar_quadros(doc):
        dados = resultado.get(_nome_do_quadro(quadro))
        if dados is None:
            continue
        quadro.set(planilhas.celula_do_campo(quadro, "curto_circuito"), f"{dados['ik3']:.2f}")
        icu = planilhas.ler_quadro(quadro).get("corrente_curto_circuito", "").replace(",", ".")
        try:
            if icu and float(icu) < dados["ik3"]:
                avisos.append(f"{_nome_do_quadro(quadro)}: disjuntor geral de {_br(float(icu))} kA para um curto de "
                              f"{_br(dados['ik3'])} kA; use pelo menos {_br(dados['icu_minimo'])} kA.")
        except ValueError:
            pass
    doc.recompute()
    return avisos
