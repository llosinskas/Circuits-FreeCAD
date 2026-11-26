"""Planilha "Quadro de cargas" de cada quadro (``core.quadro_cargas``).

Uma por quadro, marcada pela propriedade ``quadro_cargas_de`` (nome da planilha do
quadro), na mesma pasta dele, recriada a cada uso: uma linha por circuito com a carga
de cada fase, a linha de total com o desequilíbrio, os DRs por grupo e os avisos.
"""
import Spreadsheet  # noqa: F401  (registra o tipo Spreadsheet::Sheet)

from freecad.Circuits.core import quadro_cargas as regras
from freecad.Circuits.services import pavimentos, planilhas

MARCA = "quadro_cargas_de"
COLUNAS = "ABCDEFGHI"


def reservas_que_faltam(quadro):
    """Linhas de reserva da NBR 5410 que ainda não estão na planilha de circuitos."""
    circuitos = planilhas.ler_circuitos(quadro)
    return regras.com_reservas(circuitos)[len(circuitos):]


def acrescentar_reservas(quadro):
    """Grava na planilha de circuitos as reservas que faltam. Devolve quantas."""
    novas = reservas_que_faltam(quadro)
    for reserva in novas:
        planilhas.adicionar_circuito(quadro, reserva)
    if novas:
        quadro.Document.recompute()
    return len(novas)


def gerar(doc, quadro):
    """Recria a planilha do quadro de cargas.

    Returns:
        (planilha, dados) com ``desequilibrio`` [%], ``sem_fase``, ``grupos_dr`` e
        ``sugestao`` (fases sugeridas, só quando o desequilíbrio passa do usual).
    """
    for antiga in [o for o in doc.Objects if getattr(o, MARCA, None) == quadro.Name]:
        doc.removeObject(antiga.Name)
    circuitos = planilhas.ler_circuitos_completos(quadro)
    folha = doc.addObject("Spreadsheet::Sheet", f"Quadro_cargas_{quadro.Name}")
    folha.Label = f"Quadro de cargas {quadro.Label}"
    folha.addProperty("App::PropertyString", MARCA, "Quadro", "Planilha do quadro deste quadro de cargas")
    setattr(folha, MARCA, quadro.Name)
    folha.set("A1", f"'Quadro de cargas — {quadro.Label}")
    linhas = regras.tabela(circuitos)
    for numero, valores in enumerate(linhas, start=2):
        for coluna, valor in zip(COLUNAS, valores):
            folha.set(f"{coluna}{numero}", f"{valor:.0f}" if isinstance(valor, float) else f"'{valor}")
    carga = regras.carga_por_fase(circuitos)
    dados = {"desequilibrio": regras.desequilibrio(carga), "sem_fase": regras.sem_fase(circuitos),
             "grupos_dr": regras.grupos_dr(circuitos), "carga": carga, "sugestao": {}}
    linha = len(linhas) + 3
    if dados["grupos_dr"]:
        folha.set(f"A{linha}", "'DRs")
        for nome, numeros in dados["grupos_dr"]:
            folha.set(f"B{linha}", f"'{nome}: circuitos {', '.join(numeros)}")
            linha += 1
    if dados["sem_fase"]:
        folha.set(f"A{linha}", "'Sem fase")
        folha.set(f"B{linha}", f"'circuitos {', '.join(dados['sem_fase'])} (fora da carga por fase)")
        linha += 1
    if dados["desequilibrio"] > regras.balanceamento.LIMITE_USUAL:
        fases = planilhas.ler_quadro(quadro).get("numero_fases", "3")
        try:
            n_fases = int(float(fases or 3))
        except ValueError:
            n_fases = 3
        dados["sugestao"] = {n: f for n, f in regras.sugerir_fases(circuitos, n_fases).items()
                             if f != regras.fases_do_circuito(next(c for c in circuitos if str(c["N_circuito"]) == n))}
    pavimentos.guardar_junto(quadro, folha)
    doc.recompute()
    return folha, dados
