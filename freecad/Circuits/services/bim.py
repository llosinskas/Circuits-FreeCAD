"""Propriedades BIM (IFC) dos objetos da bancada, para a exportação IFC da bancada BIM do FreeCAD.

``aplicar(doc, obj)`` reconhece o objeto (ponto, interruptor, eletroduto, eletrocalha, conexões,
suportes, colunas de medição, prumadas, busway, equipamento da biblioteca e o 3D de cada um),
monta a classe com ``core.bim`` e grava:

- ``IfcType`` (grupo *IFC*): a classe, como nos objetos da bancada BIM (``Outlet``, ``Light Fixture``...);
- ``PredefinedType``, ``ObjectType`` e ``Tag`` (grupo *IFC Attributes*), que o exportador copia para a
  entidade IFC;
- ``IfcProperties`` (mapa ``"nome;;pset" -> "tipo;;valor"``), que o exportador grava como
  ``IfcPropertySet`` (``Pset_OutletTypeCommon``, ``Pset_ElectricalDeviceCommon``... e
  ``Circuits_Eletrica``, com circuito, quadro, comando, pavimento e altura de montagem).

O 3D de um símbolo, eletroduto ou eletrocalha (``<nome>_3D``) recebe a classe da origem: é ele que o
exportador leva como sólido; o símbolo 2D vira anotação. ``atualizar_documento`` refaz tudo
(é o que o comando *Propriedades BIM* e o *Exportar IFC* chamam).
"""
import FreeCAD as App

from freecad.Circuits.core import bim as regras
from freecad.Circuits.core import simbolos
from freecad.Circuits.core.tables.eletrodutos import DIAMETROS_EXTERNOS
from freecad.Circuits.services import pavimentos

GRUPO_IFC = "IFC"
GRUPO_ATRIBUTOS = "IFC Attributes"
PREFERENCIAS_BIM = "User parameter:BaseApp/Preferences/Mod/Arch"
MARCA = "circuits_bim"  # tipo de core.bim que gerou as propriedades (escondida)
SIMBOLO_DAS_ANTIGAS = {"Outlet": "tomada_baixa", "Lighting": "luz_teto"}


def _tipo(obj):
    return getattr(getattr(obj, "Proxy", None), "Type", "")


def _mm(valor, padrao=None):
    if valor is None:
        return padrao
    try:
        return float(valor.Value) if hasattr(valor, "Value") else float(valor)
    except (TypeError, ValueError):
        return padrao


def _texto(valor):
    if valor is None:
        return ""
    if isinstance(valor, (list, tuple)):
        return "; ".join(str(v) for v in valor)
    return str(valor)


def fator(doc=None):
    """Unidade do arquivo IFC por mm, pela preferência ``ifcUnit`` da bancada BIM (metro ou pé)."""
    try:
        return regras.fator_da_unidade(App.ParamGet(PREFERENCIAS_BIM).GetInt("ifcUnit", 0))
    except Exception:
        return regras.FATOR_METRO


def _pavimento(doc, obj):
    try:
        pav = pavimentos.pavimento_do_objeto(doc, obj)
    except Exception:
        pav = None
    if pav is not None:
        return pav.Label
    return str(getattr(obj, "Pavimento", "") or "")


def _dados_do_ponto(doc, obj):
    simbolo = getattr(obj, "Simbolo", None) or SIMBOLO_DAS_ANTIGAS.get(_tipo(obj), "tomada_baixa")
    catalogo = simbolos.CATALOGO.get(str(simbolo), {})
    altura = _mm(getattr(obj, "Altura3D", None))
    if altura is None:
        altura = _mm(getattr(obj, "altura_piso", None), catalogo.get("altura_mm"))
    return {
        "simbolo": str(simbolo), "legenda": catalogo.get("legenda"), "categoria": catalogo.get("categoria"),
        "descricao": _texto(getattr(obj, "Descricao", "")) or catalogo.get("descricao"),
        "potencia_va": _mm(getattr(obj, "Potencia", None), catalogo.get("potencia_va")),
        "fator_potencia": _mm(getattr(obj, "FatorPotencia", None), catalogo.get("fator_potencia")),
        "tensao": _texto(getattr(obj, "Tensao", "")) or catalogo.get("tensao"),
        "ligacao": _texto(getattr(obj, "Ligacao", "")) or catalogo.get("ligacao"),
        "circuito": _texto(getattr(obj, "Circuito", "")), "quadro": _texto(getattr(obj, "Quadro", "")),
        "comando": _texto(getattr(obj, "Comando", "")), "ambiente": _texto(getattr(obj, "Ambiente", "")),
        "pavimento": _pavimento(doc, obj), "altura_mm": altura, "caixa_mm": catalogo.get("caixa_mm"),
        "medidores": getattr(obj, "Medidores", None),
    }


def _dados_do_interruptor(doc, obj):
    return {"tipo": _texto(getattr(obj, "Tipo", "Simples")), "circuito": _texto(getattr(obj, "Circuito", "")),
            "comando": _texto(getattr(obj, "Comando", "")), "pavimento": _pavimento(doc, obj),
            "altura_mm": _mm(getattr(obj, "Altura3D", None)), "quadro": _texto(getattr(obj, "Quadro", ""))}


def _dados_do_eletroduto(doc, obj):
    nominal = _texto(getattr(obj, "Diametro", ""))
    comprimento = None
    try:
        comprimento = float(obj.Shape.Length) if not obj.Shape.isNull() else None
    except Exception:
        pass
    externo = DIAMETROS_EXTERNOS.get(nominal.rstrip('"'))
    return {"diametro": f'{nominal}"' if nominal and not nominal.endswith('"') else nominal,
            "diametro_mm": externo, "tipo": _texto(getattr(obj, "Tipo", "Flexível")),
            "material": _texto(getattr(obj, "Material", "PVC")), "instalacao": _texto(getattr(obj, "Instalacao", "")),
            "altura_mm": _mm(getattr(obj, "Altura3D", None)), "comprimento_mm": comprimento,
            "pavimento": _pavimento(doc, obj)}


def _dados_da_bandeja(doc, obj):
    return {"tipo_bandeja": _texto(getattr(obj, "TipoBandeja", "")), "largura_mm": _mm(getattr(obj, "Largura", None)),
            "aba_mm": _mm(getattr(obj, "Aba", None)), "altura_mm": _mm(getattr(obj, "AlturaBandeja", None)),
            "tampa": bool(getattr(obj, "Tampa", False)), "pavimento": _pavimento(doc, obj)}


def _dados_da_coluna(doc, obj):
    return {"medidores": getattr(obj, "Medidores", 0), "por_coluna": getattr(obj, "MedidoresPorColuna", 0),
            "modelo": _texto(getattr(obj, "Modelo", "")), "solucao": _texto(getattr(obj, "Solucao", "")),
            "corrente_a": _mm(getattr(obj, "CorrenteTotal", None)), "tensao": _mm(getattr(obj, "Tensao", None)),
            "fases": getattr(obj, "Fases", None), "disjuntor_unidade":
                f"{getattr(obj, 'DisjuntorUnidade', 0)} A" if getattr(obj, "DisjuntorUnidade", 0) else "",
            "conjuntos": _texto(getattr(obj, "Conjuntos", [])), "pavimento": _pavimento(doc, obj),
            "descricao": "CM"}


def _dados_da_prumada(doc, obj):
    sistemas = [nome for chave, nome in (("Energia", "Energia"), ("Dados", "Dados"), ("Interfone", "Interfone"),
                                         ("IluminacaoEmergencia", "Iluminação de emergência"))
                if bool(getattr(obj, chave, False))]
    return {"sistemas": sistemas, "andares": len(getattr(obj, "Andares", []) or []),
            "eletrocalha": str(getattr(obj, "FormaEnergia", "")).lower().startswith("eletrocalha") and sistemas == ["Energia"],
            "pavimento": _pavimento(doc, obj), "descricao": "Prumadas verticais"}


def _origem_do_3d(doc, obj):
    nome = getattr(obj, "Name", "")
    if not nome.endswith("_3D"):
        return None
    origem = doc.getObject(nome[:-3])
    return origem if origem is not None and origem is not obj else None


def _quadro_da_peca(doc, obj):
    simbolo = doc.getObject(getattr(obj, "quadro_3d_de", "") or "")
    return _texto(getattr(simbolo, "Descricao", "")) if simbolo is not None else ""


def classificar(doc, obj, _profundidade=0):
    """(tipo de ``core.bim``, dados) do objeto, ou None se não for da bancada."""
    tipo = _tipo(obj)
    if tipo in ("Ponto", "Outlet", "Lighting") or getattr(obj, "tipo", None) == "tomada":
        return "ponto", _dados_do_ponto(doc, obj)
    if tipo == "Switch":
        return "interruptor", _dados_do_interruptor(doc, obj)
    if tipo == "ColunaMedicao":
        return "coluna_medicao", _dados_da_coluna(doc, obj)
    if tipo == "Prumada":
        return "prumada", _dados_da_prumada(doc, obj)
    if hasattr(obj, "TipoBandeja"):
        return "bandeja", _dados_da_bandeja(doc, obj)
    if hasattr(obj, "CorrenteBusway") or (hasattr(obj, "prumada_busway_de") and hasattr(obj, "Shape")
                                          and not hasattr(obj, "CaixasMEC")):
        corrente = _mm(getattr(obj, "CorrenteBusway", None))
        if corrente is None:
            linha = doc.getObject(getattr(obj, "prumada_busway_de", "") or "")
            corrente = _mm(getattr(linha, "CorrenteBusway", None)) if linha is not None else None
        return "busway", {"corrente_a": corrente, "pavimento": _pavimento(doc, obj)}
    if tipo == "ConduitPath" or all(hasattr(obj, n) for n in ("Points", "Diametro", "Altura3D")):
        return "eletroduto", _dados_do_eletroduto(doc, obj)
    if hasattr(obj, "conexoes_3d_de"):
        return "conexao", {"peca": "conexoes", "pavimento": obj.conexoes_3d_de}
    if hasattr(obj, "descida_3d"):
        return "conexao", {"peca": "descida", "pavimento": _pavimento(doc, obj)}
    if hasattr(obj, "saida_3d"):
        return "conexao", {"peca": "saida", "pavimento": _pavimento(doc, obj)}
    if hasattr(obj, "suportes_de"):
        return "suporte", {"quantidade": getattr(obj, "Quantidade", None), "pavimento": obj.suportes_de}
    if hasattr(obj, "prumada_3d"):
        return "prumada", {"descricao": f"Prumada entre pavimentos ({obj.prumada_3d})", "simples": True,
                           "pavimento": _pavimento(doc, obj)}
    if hasattr(obj, "AlturaMontagem") and hasattr(obj, "Descricao") and hasattr(obj, "Potencia"):
        return "equipamento", {"descricao": _texto(obj.Descricao), "potencia_va": _mm(obj.Potencia),
                               "altura_mm": _mm(obj.AlturaMontagem), "pavimento": _pavimento(doc, obj)}
    if hasattr(obj, "peca_quadro"):
        return "componente_quadro", {"peca": obj.peca_quadro, "especificacao": _texto(getattr(obj, "Especificacao", "")),
                                     "circuitos": list(getattr(obj, "Circuitos", []) or []),
                                     "quadro": _quadro_da_peca(doc, obj), "pavimento": _pavimento(doc, obj)}
    origem = _origem_do_3d(doc, obj)
    if origem is not None and _profundidade == 0 and obj.TypeId.startswith("Part::"):
        return classificar(doc, origem, 1)
    return None


def _garantir(obj, tipo, nome, grupo, dica):
    if not hasattr(obj, nome):
        obj.addProperty(tipo, nome, grupo, dica)
        return True
    return False


def _tipos_ifc():
    try:
        import ArchIFC
        return list(ArchIFC.IfcTypes)
    except Exception:
        return None


def gravar(obj, resultado, tipo=None):
    """Grava ``IfcType``, os atributos IFC e ``IfcProperties`` de ``resultado`` (``core.bim.classe``).

    Só regrava o que mudou (não marca o objeto para recálculo à toa)."""
    tipos = _tipos_ifc()
    ifc_type = resultado["IfcType"]
    if not hasattr(obj, "IfcType"):
        if tipos and ifc_type in tipos:
            obj.addProperty("App::PropertyEnumeration", "IfcType", GRUPO_IFC, "Classe IFC do objeto")
            obj.IfcType = tipos
        else:
            obj.addProperty("App::PropertyString", "IfcType", GRUPO_IFC, "Classe IFC do objeto")
    if obj.IfcType != ifc_type:
        try:
            obj.IfcType = ifc_type
        except Exception:
            pass  # enumeração sem esta classe (outra versão do esquema)
    for nome, dica in (("PredefinedType", "Tipo predefinido da classe IFC"),
                       ("ObjectType", "Tipo do objeto (quando PredefinedType é USERDEFINED)"),
                       ("Tag", "Identificação: circuito ou sigla do quadro")):
        _garantir(obj, "App::PropertyString", nome, GRUPO_ATRIBUTOS, dica)
        valor = str(resultado.get(nome) or "")
        if getattr(obj, nome) != valor:
            setattr(obj, nome, valor)
    _garantir(obj, "App::PropertyMap", "IfcProperties", GRUPO_IFC,
              "Propriedades IFC: 'nome;;pset' -> 'tipo;;valor'")
    mapa = regras.mapa_ifc(resultado["propriedades"])
    if dict(obj.IfcProperties) != mapa:
        obj.IfcProperties = mapa
    if tipo is not None:
        if _garantir(obj, "App::PropertyString", MARCA, GRUPO_IFC, "Regra da bancada que gerou as propriedades IFC"):
            obj.setEditorMode(MARCA, 2)
        if getattr(obj, MARCA) != tipo:
            setattr(obj, MARCA, tipo)
    return obj


def aplicar(doc, obj, fator_comprimento=None):
    """Grava as propriedades BIM do objeto, se ele for da bancada. Devolve o resultado ou None."""
    try:
        achado = classificar(doc, obj)
    except Exception as erro:
        App.Console.PrintWarning(f"Circuits: propriedades BIM de {getattr(obj, 'Label', obj)}: {erro}\n")
        return None
    if achado is None:
        return None
    tipo, dados = achado
    resultado = regras.classe(tipo, dados, fator(doc) if fator_comprimento is None else fator_comprimento)
    try:
        gravar(obj, resultado, tipo)
    except Exception as erro:
        App.Console.PrintWarning(f"Circuits: propriedades BIM de {obj.Label} não gravadas: {erro}\n")
        return None
    return resultado


def aplicar_com_3d(doc, obj):
    """Grava no objeto e no 3D dele (``<nome>_3D``), se houver."""
    resultado = aplicar(doc, obj)
    tres_d = doc.getObject(f"{obj.Name}_3D")
    if tres_d is not None:
        aplicar(doc, tres_d)
    return resultado


def atualizar_documento(doc):
    """Grava as propriedades BIM em todos os objetos da bancada.

    Returns:
        {classe IFC: quantidade}.
    """
    contagem = {}
    escala = fator(doc)
    for obj in list(doc.Objects):
        resultado = aplicar(doc, obj, escala)
        if resultado is not None:
            contagem[resultado["IfcType"]] = contagem.get(resultado["IfcType"], 0) + 1
    return contagem


def objetos_para_exportar(doc):
    """Objetos com sólido para o arquivo IFC: os 3D da bancada e o que mais tiver sólido visível
    (paredes, lajes, níveis do BIM)."""
    lista = []
    for obj in doc.Objects:
        if obj.TypeId in ("App::DocumentObjectGroup",) or getattr(obj, "IfcType", None) in (
                "Building Storey", "Building", "Site", "Project"):
            continue
        forma = getattr(obj, "Shape", None)
        try:
            if forma is None or forma.isNull() or not forma.Solids:
                continue
        except Exception:
            continue
        lista.append(obj)
    return lista


def exportar(doc, caminho, objetos=None):
    """Atualiza as propriedades e grava o IFC pelo exportador da bancada BIM.

    Args:
        objetos: o que exportar; sem eles, os níveis/edifício do BIM, se houver (o exportador leva o
            que está dentro), senão ``objetos_para_exportar``.
    """
    contagem = atualizar_documento(doc)
    if objetos is None:
        raiz = [o for o in doc.Objects if getattr(o, "IfcType", None) in ("Site", "Building")
                and not any(getattr(p, "IfcType", None) in ("Site", "Building") for p in o.InList)]
        objetos = raiz or objetos_para_exportar(doc)
    from importers import exportIFC
    exportIFC.export(objetos, caminho)
    return contagem, len(objetos)


__all__ = ["aplicar", "aplicar_com_3d", "atualizar_documento", "classificar", "exportar", "fator", "gravar",
           "objetos_para_exportar"]
