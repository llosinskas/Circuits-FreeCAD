"""Leitura dos pontos elétricos da planta e gravação dos circuitos no quadro."""
import FreeCAD as App

from freecad.Circuits.core import circuitos as calculo
from freecad.Circuits.core import simbolos
from freecad.Circuits.core.functions.Predial import demanda as calculo_demanda
from freecad.Circuits.objects.ponto import TENSOES, create_ponto
from freecad.Circuits.services import planilhas
from freecad.Circuits.services.tomadas import listar_tomadas

# Objetos anteriores ao PontoEletrico: tipo de circuito e dados que eles não guardam.
_LEGADOS = {
    "Outlet": (simbolos.TUG, 0.8),
    "Lighting": (simbolos.ILUM, 1.0),
}
_TENSAO_LEGADA = {"127V": (127, "F+N"), "220V": (220, "F+N"), "Bifásica": (220, "F+F")}


def _valor(propriedade):
    return propriedade.Value if hasattr(propriedade, "Value") else float(propriedade)


def _de_ponto(obj):
    return {
        "circuito": obj.Circuito,
        "quadro": obj.Quadro,
        "potencia_va": float(obj.Potencia),
        "fator_potencia": float(obj.FatorPotencia),
        "tensao": int(str(obj.Tensao).rstrip("V")),
        "ligacao": obj.Ligacao,
        "tipo_circuito": simbolos.CATALOGO[obj.Simbolo]["tipo_circuito"],
        "descricao": obj.Descricao,
    }


def _de_legado(obj, tipo):
    tipo_circuito, fator = _LEGADOS[tipo]
    tensao, ligacao = _TENSAO_LEGADA.get(str(getattr(obj, "Tensao", "127V")), (127, "F+N"))
    potencia = calculo.potencia_va(obj.Potencia) * max(1, int(getattr(obj, "QtdPontos", 1)))
    return {
        "circuito": obj.Circuito,
        "quadro": "",
        "potencia_va": potencia,
        "fator_potencia": fator,
        "tensao": tensao,
        "ligacao": ligacao,
        "tipo_circuito": tipo_circuito,
        "descricao": obj.Label,
    }


def _de_tomada_sketch(obj):
    # Estas tomadas guardam potência e tensão como grandezas do FreeCAD, gravadas
    # sem unidade: o número digitado (100, 220) é o que vale como W e V.
    fases = int(getattr(obj, "Fase", 1))
    return {
        "circuito": str(obj.Circuito),
        "quadro": "",
        "potencia_va": _valor(obj.potencia) / (float(obj.Fator_potencia) or 1.0),
        "fator_potencia": float(obj.Fator_potencia) or 1.0,
        "tensao": int(round(_valor(obj.Tensao))),
        "ligacao": {1: "F+N", 2: "F+F", 3: "3F"}.get(fases, "F+N"),
        "tipo_circuito": simbolos.TUG,
        "descricao": obj.Label,
    }


def coletar_pontos(doc):
    """Dados elétricos de todos os pontos da planta, no formato de ``core.circuitos.agrupar``."""
    pontos = []
    for obj in doc.Objects:
        tipo = getattr(getattr(obj, "Proxy", None), "Type", "")
        try:
            if tipo == "Ponto":
                if simbolos.CATALOGO[obj.Simbolo]["categoria"] not in simbolos.SEM_CARGA:  # quadros, comandos etc.
                    pontos.append(_de_ponto(obj))
            elif tipo in _LEGADOS:
                pontos.append(_de_legado(obj, tipo))
        except Exception as erro:
            App.Console.PrintWarning(f"Ponto {obj.Label} ignorado: {erro}\n")
    for obj in listar_tomadas(doc):
        try:
            pontos.append(_de_tomada_sketch(obj))
        except Exception as erro:
            App.Console.PrintWarning(f"Tomada {obj.Label} ignorada: {erro}\n")
    return pontos


def _fases_do_quadro(quadro):
    try:
        return int(float(quadro.get("numero_fases")))
    except Exception:
        return 3


def _circuitos_do_quadro(doc, quadro):
    """Circuitos dos pontos sem quadro definido e dos que apontam para este quadro."""
    nomes = (quadro.Label, quadro.Name)
    pontos = [p for p in coletar_pontos(doc) if not p["quadro"].strip() or p["quadro"].strip() in nomes]
    return calculo.agrupar(pontos)


def calcular_demanda(doc, quadro):
    """Calcula a demanda do quadro pelos pontos da planta e a grava na planilha.

    Returns:
        Resultado de ``core.functions.Predial.demanda.demanda_de_circuitos``,
        ou None se não há pontos com circuito definido.
    """
    circuitos = _circuitos_do_quadro(doc, quadro)
    if not circuitos:
        return None
    resultado = calculo_demanda.demanda_de_circuitos(circuitos)
    planilhas.gravar_potencia_instalada(quadro, round(resultado["instalada_w"] / 1000.0, 2))
    planilhas.gravar_potencia_demanda(quadro, round(resultado["demanda_w"] / 1000.0, 2))
    doc.recompute()
    return resultado


def criar_ponto_motor(descricao, motor):
    """Cria na planta um ponto de força com os dados elétricos de um motor.

    Args:
        descricao: texto que identifica a carga no quadro (ex.: 'Bomba de recalque 2 cv').
        motor: resultado de ``core.functions.Predial.motores.dados_motor``.
    Returns:
        O PontoEletrico criado, ou None se não há documento ativo.
    """
    obj = create_ponto("ponto_forca")
    if obj is None:
        return None
    tensao = f"{int(motor['tensao'])}V"
    obj.Descricao = descricao
    obj.Label = descricao
    obj.Potencia = round(motor["potencia_aparente_kva"] * 1000.0, 1)
    obj.FatorPotencia = motor["fator_potencia"]
    if tensao in TENSOES:
        obj.Tensao = tensao
    obj.Ligacao = {1: "F+N", 2: "F+F"}.get(motor["fases"], "3F")
    return obj


def montar_circuitos(doc, quadro):
    """Monta os circuitos do quadro a partir dos pontos da planta e os grava na planilha.

    Entram os pontos sem quadro definido e os que apontam para este quadro.
    Circuitos que já estão na planilha com o mesmo número são atualizados.

    Returns:
        (circuitos gravados, avisos) — avisos é uma lista de textos para o usuário.
    """
    circuitos = _circuitos_do_quadro(doc, quadro)
    calculo.distribuir_fases(circuitos, _fases_do_quadro(quadro))

    avisos = []
    gravados = []
    for circuito in circuitos:
        avisos += [f"Circuito {circuito['numero']}: {aviso}." for aviso in circuito["avisos"]]
        try:
            dados = calculo.linha_planilha(circuito)
        except ValueError as erro:
            avisos.append(f"Circuito {circuito['numero']} não foi gravado: {erro}")
            continue
        planilhas.adicionar_circuito(quadro, dados)
        gravados.append(circuito)

    if gravados:
        total_kw = sum(c["potencia_w"] for c in gravados) / 1000.0
        planilhas.gravar_potencia_instalada(quadro, round(total_kw, 2))
    doc.recompute()
    return gravados, avisos
