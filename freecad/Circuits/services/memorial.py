"""Coleta, no documento, os dados do memorial descritivo e de cálculo (``core.memorial``).

Cada parte é lida à parte: se uma falhar (planilha com erro, rede incompleta), o memorial sai
sem ela e o motivo vai para os avisos.
"""
import datetime
import os

import FreeCAD as App

from freecad.Circuits.core import ambientes as regras_ambientes
from freecad.Circuits.core import centro_medicao as regras_centro
from freecad.Circuits.core import curto as regras_curto
from freecad.Circuits.core import ocupacao as regras_ocupacao
from freecad.Circuits.core import parametros as regras_parametros
from freecad.Circuits.core.simbolos import CATALOGO, PASSAGEM
from freecad.Circuits.services import parametros as servico_parametros
from freecad.Circuits.services import planilhas


def _tipo(obj):
    return getattr(getattr(obj, "Proxy", None), "Type", "")


def _projeto(doc):
    textos = servico_parametros.textos(doc)
    dados = {chave: textos.get(chave, "") for chave in ("projeto", "obra", "cliente", "responsavel", "registro",
                                                        "desenhista")}
    dados["projeto"] = dados["projeto"] or doc.Label
    dados["data"] = datetime.date.today().strftime("%d/%m/%Y")
    dados["documento"] = os.path.basename(doc.FileName) if getattr(doc, "FileName", "") else doc.Label
    return dados


def _contagem(doc):
    contagem = {}

    def somar(nome):
        contagem[nome] = contagem.get(nome, 0) + 1

    for obj in doc.Objects:
        tipo = _tipo(obj)
        if tipo == "Ponto":
            dados = CATALOGO.get(getattr(obj, "Simbolo", ""), {})
            somar("Caixas de passagem" if dados.get("categoria") == PASSAGEM else str(dados.get("legenda", "Ponto")))
        elif tipo in ("Switch",):
            somar("Interruptores")
        elif tipo in ("Outlet", "Lighting"):
            somar("Tomadas (antigas)" if tipo == "Outlet" else "Iluminação (antiga)")
        elif hasattr(obj, "Diametro") and hasattr(obj, "Altura3D"):
            somar("Eletrodutos")
        elif hasattr(obj, "TipoBandeja"):
            somar("Eletrocalhas e leitos")
        elif hasattr(obj, "quadro"):
            somar("Quadros (planilhas)")
    return dict(sorted(contagem.items()))


def _ambientes(doc, avisos):
    from freecad.Circuits.services import ambientes as servico_ambientes
    resultado = []
    for obj in servico_ambientes.listar_ambientes(doc):
        try:
            tipo = str(obj.TipoAmbiente)
            area, perimetro = float(obj.AreaAmbiente), float(obj.PerimetroAmbiente)
            item = {"nome": str(getattr(obj, "NomeAmbiente", "") or obj.Label), "tipo": tipo, "area": area,
                    "perimetro": perimetro, "previsao": regras_ambientes.previsao(tipo, area, perimetro)}
            try:
                padrao = regras_ambientes.LUMINOTECNICO_PADRAO
                item["luminotecnico"] = regras_ambientes.luminarias(
                    servico_ambientes.pontos_do_ambiente(obj), tipo, padrao["fluxo"], padrao["potencia"],
                    padrao["pe_direito"], simbolo=padrao["simbolo"])
            except Exception:
                item["luminotecnico"] = None
            resultado.append(item)
        except Exception as erro:
            avisos.append(f"Ambiente {obj.Label} fora do memorial: {erro}")
    return resultado


def _quadros(doc, avisos):
    from freecad.Circuits.services import rede
    quadros = planilhas.listar_quadros(doc)
    resultado = []
    for quadro in quadros:
        try:
            item = {"nome": quadro.Label, "dados": planilhas.ler_quadro(quadro),
                    "circuitos": planilhas.ler_circuitos_completos(quadro), "rede": {}, "demanda": None}
        except Exception as erro:
            avisos.append(f"Quadro {quadro.Label} fora do memorial: {erro}")
            continue
        try:
            item["rede"] = {str(chave).strip(): valor for chave, valor in rede.dados_dos_circuitos(doc, quadro).items()}
        except Exception as erro:
            avisos.append(f"Quadro {quadro.Label}: comprimentos da rede não lidos ({erro}); usada a coluna Comprimento.")
        resultado.append(item)
    return resultado


def _curto(doc, avisos):
    from freecad.Circuits.services import curto
    folha = curto.planilha(doc)
    if folha is None:
        return None
    try:
        barras, tensao = curto.ler(folha)
        return {"tensao": tensao, "resultado": regras_curto.estudo(barras, tensao)}
    except Exception as erro:
        avisos.append(f"Estudo de curto fora do memorial: {erro}")
        return None


def _gerador(doc, avisos):
    from freecad.Circuits.services import gerador
    folha = gerador.planilha(doc)
    if folha is None:
        return None
    try:
        return {"cargas": gerador.ler_cargas(folha), "resumo": gerador.ler_resumo(folha)}
    except Exception as erro:
        avisos.append(f"Gerador fora do memorial: {erro}")
        return None


def _centro(doc, avisos):
    from freecad.Circuits.services import centro_medicao
    folha = centro_medicao.planilha(doc)
    if folha is None:
        return None
    try:
        resumo = {}
        for linha in range(regras_centro.PRIMEIRA_LINHA, planilhas.ultima_linha(folha) + 1):
            rotulo = centro_medicao._texto(folha, f"{regras_centro.COLUNA_RESULTADO_ROTULO}{linha}")
            if rotulo:
                resumo[rotulo] = centro_medicao._texto(folha, f"{regras_centro.COLUNA_RESULTADO_VALOR}{linha}")
        return {"andares": centro_medicao.ler_andares(folha), "resumo": resumo}
    except Exception as erro:
        avisos.append(f"Centro de medição fora do memorial: {erro}")
        return None


def _ocupacao(doc, avisos):
    from freecad.Circuits.services import rede, roteamento
    if not rede.listar_eletrodutos(doc):
        return None
    try:
        dados = roteamento.ocupacao(doc)
    except Exception as erro:
        avisos.append(f"Ocupação dos eletrodutos fora do memorial: {erro}")
        return None
    if not dados["eletrodutos"] and not dados["bandejas"]:
        return None
    return {"tabela": regras_ocupacao.tabela(dados["eletrodutos"], dados["bandejas"]), "avisos": dados["avisos"]}


def _luminotecnico(doc, avisos):
    from freecad.Circuits.services import luminotecnico
    return luminotecnico.calculos(doc) or None


def _aterramento(doc, avisos):
    from freecad.Circuits.services import aterramento
    return {"levantamento": aterramento.levantamento(doc), "calculo": aterramento.ler_calculo(doc)}


def coletar(doc):
    """Dados do documento para ``core.memorial.montar``."""
    avisos = []
    dados = {
        "projeto": _projeto(doc),
        "contagem": _contagem(doc),
        "parametros": servico_parametros.ler(doc),
        "rotulos_parametros": {chave: valor[1] for chave, valor in regras_parametros.CAMPOS.items()},
    }
    for chave, funcao in (("ambientes", _ambientes), ("luminotecnico", _luminotecnico), ("quadros", _quadros),
                          ("curto", _curto), ("aterramento", _aterramento), ("gerador", _gerador), ("centro_medicao", _centro), ("ocupacao", _ocupacao)):
        try:
            dados[chave] = funcao(doc, avisos)
        except Exception as erro:
            avisos.append(f"{chave}: não lido ({erro})")
            App.Console.PrintWarning(f"Memorial: {chave} não lido: {erro}\n")
    dados["avisos"] = avisos
    return dados
