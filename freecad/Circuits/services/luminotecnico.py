"""Distribuição de luminárias dentro de um retângulo desenhado na planta."""
import json

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


MARCA_CALCULO = "Luminotecnico"


def gravar_calculo(ambiente, calculo):
    """Guarda no objeto do ambiente (JSON em ``Luminotecnico``) as entradas do cálculo, para o memorial."""
    if not hasattr(ambiente, MARCA_CALCULO):
        ambiente.addProperty("App::PropertyString", MARCA_CALCULO, "Luminotécnico",
                             "Entradas do cálculo luminotécnico (refeito no memorial do relatório)")
    setattr(ambiente, MARCA_CALCULO, json.dumps(calculo, ensure_ascii=False))


def ler_calculo(ambiente):
    """Entradas gravadas por ``gravar_calculo``, ou None."""
    try:
        dados = json.loads(getattr(ambiente, MARCA_CALCULO, "") or "null")
    except ValueError:
        return None
    return dados if isinstance(dados, dict) else None


def calculos(doc):
    """Ambientes do luminotécnico para o memorial: um por objeto com cálculo gravado ou com luminárias.

    Returns:
        [{'nome', 'calculo' (entradas, ou None nos projetos antigos), 'luminarias', 'potencia_va'}].
    """
    pontos = {}
    for obj in doc.Objects:
        nome = getattr(obj, "Ambiente", "")
        if nome and getattr(getattr(obj, "Proxy", None), "Type", "") == "Ponto":
            pontos.setdefault(nome, []).append(obj)
    nomes = [obj.Name for obj in doc.Objects if ler_calculo(obj)]
    nomes += [n for n in pontos if n not in nomes]
    lista = []
    for nome in nomes:
        obj = doc.getObject(nome)
        lum = pontos.get(nome, [])
        lista.append({
            "nome": obj.Label if obj is not None else nome,
            "calculo": ler_calculo(obj) if obj is not None else None,
            "luminarias": len(lum),
            "potencia_va": sum(float(getattr(p, "Potencia", 0) or 0) for p in lum),
        })
    return lista


def distribuir(doc, ambiente, x_min, y_min, posicoes, simbolo, potencia_va, circuito, calculo=None):
    """Cria uma luminária em cada posição, substituindo as que o ambiente já tinha.

    As luminárias entram no pavimento ativo e ficam na cota dele.

    Args:
        ambiente: objeto que delimita o ambiente (o retângulo desenhado).
        x_min, y_min: canto do ambiente [mm].
        posicoes: centros das luminárias a partir do canto [m], de
            ``core.functions.Predial.luminotecnico.dimensionar``.
        simbolo: chave de ``core.simbolos.CATALOGO``.
        potencia_va: potência de cada luminária [VA].
        circuito: número do circuito das luminárias.
        calculo: entradas do cálculo, guardadas no ambiente para o memorial (``gravar_calculo``).
    Returns:
        Lista dos pontos criados.
    """
    pavimento = pavimentos.garantir_ativo(doc)
    cota = pavimentos.elevacao(pavimento)
    doc.openTransaction("Distribuir luminárias")
    try:
        for antigo in luminarias_do_ambiente(doc, ambiente):
            doc.removeObject(antigo.Name)
        criados = []
        for x, y in posicoes:
            ponto = create_ponto(simbolo)
            posicao = ponto.Placement
            posicao.Base = App.Vector(x_min + x * MM_POR_M, y_min + y * MM_POR_M, cota)
            ponto.Placement = posicao
            ponto.Potencia = float(potencia_va)
            ponto.Circuito = str(circuito)
            ponto.Ambiente = ambiente.Name
            pavimentos.arquivar(doc, ponto, pavimento)
            criados.append(ponto)
        if calculo:
            gravar_calculo(ambiente, calculo)
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    atualizar_anotacao(doc)
    return criados
