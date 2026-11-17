"""Carrega o módulo de uma etapa ou falha com uma mensagem clara, sem erro de importação."""
import importlib

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)


def carregar(caso, nome, etapa):
    """Módulo ``freecad.Circuits.core.<nome>``; se ainda não existe, o teste falha (não dá erro)."""
    completo = f"freecad.Circuits.core.{nome}"
    try:
        return importlib.import_module(completo)
    except ModuleNotFoundError as erro:
        if erro.name != completo:
            raise
        caso.fail(f"Etapa {etapa}: o módulo core/{nome.replace('.', '/')}.py ainda não existe")


def circuito(numero, potencia, fases="R", destino="", dr=False, grupo_dr="", **outros):
    """Linha da planilha de circuitos, no formato de ``planilhas.ler_circuitos_completos``."""
    linha = {
        "N_circuito": str(numero), "Destino": destino, "Potencia": str(potencia),
        "Fase_R": str("R" in fases), "Fase_S": str("S" in fases), "Fase_T": str("T" in fases),
        "DR": str(dr), "Grupo_DR": grupo_dr, "Corrente": "", "Disjuntor": "", "Cabo": "",
    }
    linha.update(outros)
    return linha
