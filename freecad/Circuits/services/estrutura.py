"""Estrutura de pastas do projeto no documento (``core.estrutura``): criar, organizar e limpar."""
import FreeCAD as App

from freecad.Circuits.core import estrutura as regras


def _grupo(obj):
    return obj is not None and obj.TypeId == "App::DocumentObjectGroup"


def ativa(doc):
    """O documento usa a estrutura nova (tem alguma pasta marcada)."""
    return any(hasattr(o, regras.MARCA) for o in doc.Objects)


def pasta(doc, chave, criar=True):
    """Pasta da chave; adota o grupo antigo de mesmo nome, se houver, e cria se ``criar``."""
    for obj in doc.Objects:
        if getattr(obj, regras.MARCA, None) == chave:
            return obj
    nome, rotulo, descricao = regras.PASTAS[chave]
    existente = doc.getObject(nome)
    if not _grupo(existente):
        if not criar:
            return None
        existente = doc.addObject("App::DocumentObjectGroup", nome)
    existente.addProperty("App::PropertyString", regras.MARCA, "Projeto", descricao)
    setattr(existente, regras.MARCA, chave)
    existente.setEditorMode(regras.MARCA, 1)
    existente.Label = rotulo
    return existente


def _na_raiz(obj):
    try:
        if obj.getParentGroup() is not None:
            return False
        geo = getattr(obj, "getParentGeoFeatureGroup", None)
        return geo is None or geo() is None
    except Exception:
        return False


def organizar(doc):
    """Leva para a pasta certa os objetos da bancada que estão na raiz. Devolve quantos foram movidos."""
    movidos = 0
    for obj in list(doc.Objects):
        if not _na_raiz(obj):
            continue
        try:
            chave = regras.pasta_de(obj.PropertiesList, obj.TypeId, obj.Name)
        except Exception:
            continue
        if chave is None:
            continue
        destino = pasta(doc, chave)
        if destino is not None and destino is not obj:
            destino.addObject(obj)
            movidos += 1
    return movidos


def remover_antigas(doc):
    """Apaga as pastas que versões anteriores criavam no Novo projeto, se estiverem vazias.

    Returns:
        Nomes das pastas apagadas.
    """
    apagadas = []
    for nome in regras.PASTAS_ANTIGAS:
        obj = doc.getObject(nome)
        if _grupo(obj) and not hasattr(obj, regras.MARCA) and not obj.Group:
            doc.removeObject(nome)
            apagadas.append(nome)
    return apagadas


def edificio_bim(doc, nome):
    """Edifício da bancada BIM (IfcType Building) para os níveis; cria um com ``nome`` se não houver."""
    existente = next((o for o in doc.Objects if getattr(o, "IfcType", "") == "Building"), None)
    if existente is not None:
        return existente
    try:
        import Arch
    except ImportError:
        return None
    edificio = Arch.makeBuildingPart()
    edificio.IfcType = "Building"
    edificio.Label = nome or "Edifício"
    return edificio


def criar(doc, niveis_bim=False, nome_do_projeto=""):
    """Estrutura de um projeto novo (ou a atualização de um antigo): apaga as pastas antigas vazias,
    cria Pavimentos (sem níveis do BIM) e Planilhas, o edifício do BIM (com níveis) e organiza a raiz.

    Returns:
        {'pastas': [rótulos], 'apagadas': [nomes], 'movidos': n}.
    """
    apagadas = remover_antigas(doc)
    pastas = [pasta(doc, chave) for chave in regras.pastas_iniciais(niveis_bim)]
    pavimentos_antiga = doc.getObject(regras.PASTAS["pavimentos"][0])
    if niveis_bim and _grupo(pavimentos_antiga):
        pasta(doc, "pavimentos")  # o projeto já tinha pastas de pavimento: a pasta continua, com o rótulo novo
    if niveis_bim:
        edificio_bim(doc, nome_do_projeto)
    movidos = organizar(doc)
    return {"pastas": [p.Label for p in pastas if p is not None], "apagadas": apagadas, "movidos": movidos}


__all__ = ["ativa", "criar", "edificio_bim", "organizar", "pasta", "remover_antigas"]
