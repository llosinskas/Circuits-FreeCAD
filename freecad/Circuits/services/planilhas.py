"""Planilhas de circuitos e de quadros de distribuição."""
import Spreadsheet  # noqa: F401  (registra o tipo Spreadsheet::Sheet)

from freecad.Circuits.core import planilha as layout


def criar_planilha_circuitos(doc):
    planilha = doc.addObject("Spreadsheet::Sheet", "Circuitos")
    for indice, titulo in enumerate(layout.CABECALHO_CIRCUITOS):
        planilha.set(f"{layout.coluna(indice)}1", titulo)
    doc.recompute()
    return planilha


def criar_planilha_quadro(doc, dados):
    """Cria a planilha de um quadro a partir dos dados do diálogo CriarQuadro."""
    nome_quadro = dados["indentificacao"]
    if not hasattr(doc, nome_quadro):
        planilha = doc.addObject("Spreadsheet::Sheet", nome_quadro)
        doc.recompute()
    else:
        planilha = doc.Spreadsheet(nome_quadro)

    planilha.addProperty("App::PropertyString", "quadro")
    planilha.quadro = "Quadro"
    planilha.set("A1", nome_quadro)
    planilha.mergeCells("A1:S1")
    for indice, titulo in enumerate(layout.CABECALHO_QUADRO):
        coluna = layout.coluna(indice)
        planilha.set(f"{coluna}2", titulo)
        planilha.setAlias(f"{coluna}3", titulo)
    planilha.set("A4", "Circuitos")
    planilha.mergeCells("A4:S4")
    for indice, valor in enumerate(dados.values()):
        planilha.set(f"{layout.coluna(indice)}3", str(valor))
    return planilha


def listar_quadros(doc):
    """Planilhas marcadas com a propriedade 'quadro'."""
    return [obj for obj in doc.Objects if hasattr(obj, "quadro")]


def ultima_linha(planilha):
    return layout.ultima_linha(planilha.getUsedCells())


def adicionar_circuito(planilha, dados):
    """Grava o cabeçalho de circuitos e acrescenta uma linha com os dados."""
    for indice, titulo in enumerate(layout.CABECALHO_CIRCUITO_QUADRO):
        planilha.set(f"{layout.coluna(indice)}{layout.LINHA_CABECALHO_CIRCUITOS}", titulo)

    ultima = ultima_linha(planilha)
    linha = layout.PRIMEIRA_LINHA_CIRCUITOS if ultima < layout.LINHA_CABECALHO_CIRCUITOS else ultima + 1
    for coluna, chave in layout.COLUNAS_CIRCUITO.items():
        planilha.set(f"{coluna}{linha}", f"'{dados[chave]}")
