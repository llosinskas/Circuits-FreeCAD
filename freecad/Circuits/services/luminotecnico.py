"""Distribuição de luminárias dentro de um retângulo desenhado na planta."""
import FreeCAD as App

from freecad.Circuits.objects.ponto import create_ponto
from freecad.Circuits.services import pavimentos
from freecad.Circuits.services.identificacao import atualizar_anotacao

MM_POR_M = 1000.0
LADO_MINIMO_MM = 100.0


def ambiente_selecionado(objetos):
    """Primeiro objeto da seleção que serve de ambiente: tem forma e não é um símbolo.

    Vale o retângulo envolvente no plano XY, então um retângulo girado é
    tratado pelo retângulo reto que o contém.

    Returns:
        (objeto, x mínimo [mm], y mínimo [mm], comprimento [m], largura [m]), ou None.
    """
    for obj in objetos:
        if getattr(getattr(obj, "Proxy", None), "Type", "") in ("Ponto", "Switch", "Lighting", "Outlet"):
            continue
        forma = getattr(obj, "Shape", None)
        if forma is None or forma.isNull():
            continue
        caixa = forma.BoundBox
        if caixa.XLength < LADO_MINIMO_MM or caixa.YLength < LADO_MINIMO_MM:
            continue
        return obj, caixa.XMin, caixa.YMin, caixa.XLength / MM_POR_M, caixa.YLength / MM_POR_M
    return None


def luminarias_do_ambiente(doc, ambiente):
    """Pontos criados antes pelo luminotécnico para este ambiente."""
    return [obj for obj in doc.Objects if getattr(obj, "Ambiente", "") == ambiente.Name]


def distribuir(doc, ambiente, x_min, y_min, posicoes, simbolo, potencia_va, circuito):
    """Cria uma luminária em cada posição, substituindo as que o ambiente já tinha.

    Args:
        ambiente: objeto que delimita o ambiente (o retângulo desenhado).
        x_min, y_min: canto do ambiente [mm].
        posicoes: centros das luminárias a partir do canto [m], de
            ``core.functions.Predial.luminotecnico.dimensionar``.
        simbolo: chave de ``core.simbolos.CATALOGO``.
        potencia_va: potência de cada luminária [VA].
        circuito: número do circuito das luminárias.
    Returns:
        Lista dos pontos criados.
    """
    doc.openTransaction("Distribuir luminárias")
    try:
        for antigo in luminarias_do_ambiente(doc, ambiente):
            doc.removeObject(antigo.Name)
        criados = []
        for x, y in posicoes:
            ponto = create_ponto(simbolo)
            posicao = ponto.Placement
            posicao.Base = App.Vector(x_min + x * MM_POR_M, y_min + y * MM_POR_M, 0)
            ponto.Placement = posicao
            ponto.Potencia = float(potencia_va)
            ponto.Circuito = str(circuito)
            ponto.Ambiente = ambiente.Name
            pavimentos.arquivar(doc, ponto)
            criados.append(ponto)
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    atualizar_anotacao(doc)
    return criados
