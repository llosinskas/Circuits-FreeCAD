"""Notas do projeto: numeração e quebra de linha, sem FreeCAD."""
import textwrap

LARGURA_PADRAO = 60  # caracteres por linha na planta


def limpar(notas):
    """Notas sem espaços nas pontas e sem linhas vazias, na ordem em que foram escritas."""
    return [str(nota).strip() for nota in notas if str(nota).strip()]


def formatar(notas, largura=LARGURA_PADRAO):
    """Numera as notas e quebra as longas em várias linhas.

    Returns:
        Uma lista por nota, com as linhas dela. A primeira linha começa com o
        número ('1 - ...') e as seguintes são recuadas para alinhar com o texto.
    """
    blocos = []
    for numero, nota in enumerate(limpar(notas), start=1):
        prefixo = f"{numero} - "
        linhas = textwrap.wrap(nota, width=max(10, largura - len(prefixo))) or [""]
        recuo = " " * len(prefixo)
        blocos.append([prefixo + linhas[0]] + [recuo + linha for linha in linhas[1:]])
    return blocos
