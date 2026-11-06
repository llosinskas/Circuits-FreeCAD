"""Grava no documento os fios lidos de um arquivo do QElectroTech."""
from freecad.Circuits.core import qet
from freecad.Circuits.core.planilha import coluna


def criar_planilha_fios(doc, nome, root):
    """Cria a planilha de fios a partir da raiz XML de um arquivo .qet."""
    planilha = doc.addObject("Spreadsheet::Sheet", nome)
    planilha.Label = nome

    for indice, titulo in enumerate(qet.CABECALHO):
        planilha.set(f"{coluna(indice)}1", titulo)

    for numero, valores in enumerate(qet.extrair_linhas(root), start=2):
        for indice, valor in enumerate(valores):
            planilha.set(f"{coluna(indice)}{numero}", valor)
    return planilha
