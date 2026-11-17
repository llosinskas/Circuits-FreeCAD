"""Pavimentos do projeto e as pastas dos símbolos dentro de cada um.

Um pavimento é um nível da bancada BIM (BuildingPart do tipo "Building Storey")
ou, quando o projeto não tem níveis, uma pasta criada pela bancada. Os níveis do
BIM têm a cota e a altura lidas do próprio BIM e nunca são alterados aqui.
"""
import FreeCAD as App

from freecad.Circuits.core import pavimentos as regras
from freecad.Circuits.core.simbolos import CATALOGO

GRUPO_MAE = "Pontos_eletricos"  # criado por Novo projeto; os pavimentos ficam dentro dele, se existir


def _mm(valor):
    return valor.Value if hasattr(valor, "Value") else float(valor)


def _pai(obj):
    """Pasta (grupo) que contém o objeto, ou None."""
    pegar = getattr(obj, "getParentGroup", None)
    try:
        return pegar() if pegar else None
    except Exception:
        return None


def _rotular(obj, desejado, alternativo):
    """Dá o nome à pasta; se o FreeCAD recusar por já existir outra igual, usa o alternativo."""
    obj.Label = desejado
    if obj.Label != desejado:
        obj.Label = alternativo


# --- pavimentos ------------------------------------------------------------

def eh_nivel_bim(obj):
    """Nível da bancada BIM: um BuildingPart do tipo Building Storey."""
    return getattr(obj, "IfcType", "") == "Building Storey" and hasattr(obj, "Group")


def eh_pavimento(obj):
    return hasattr(obj, "AlturaPavimento") or eh_nivel_bim(obj)


def elevacao(pav):
    """Cota do piso do pavimento [mm]. Num nível do BIM é a posição Z dele."""
    return float(pav.Placement.Base.z) if eh_nivel_bim(pav) else _mm(pav.Elevacao)


def altura(pav):
    """Altura de piso a piso [mm]. Num nível do BIM vem da propriedade Height, ou vale o padrão se for zero."""
    if eh_nivel_bim(pav):
        altura_bim = _mm(pav.Height) if hasattr(pav, "Height") else 0.0
        return altura_bim if altura_bim > 0 else regras.ALTURA_PADRAO_MM
    return _mm(pav.AlturaPavimento)


def listar(doc):
    """Pavimentos do documento (níveis do BIM e pastas da bancada), do mais baixo para o mais alto."""
    return sorted((obj for obj in doc.Objects if eh_pavimento(obj)), key=elevacao)


def por_nome(doc, nome):
    nome = regras.nome_do_pavimento(nome)
    return next((pav for pav in listar(doc) if pav.Label == nome), None)


def ativo(doc):
    return next((pav for pav in listar(doc) if getattr(pav, "Ativo", False)), None)


def ativar(doc, pavimento):
    """Torna este o pavimento onde os próximos símbolos são inseridos."""
    for pav in listar(doc):
        if pav.Name == pavimento.Name:
            if not hasattr(pav, "Ativo"):  # nível do BIM: a marca é acrescentada só quando ele é ativado
                pav.addProperty("App::PropertyBool", "Ativo", "Pavimento", "Pavimento onde os próximos símbolos entram")
            pav.Ativo = True
        elif hasattr(pav, "Ativo"):
            pav.Ativo = False


def definir(doc, nome, elevacao_mm=0.0, altura_mm=regras.ALTURA_PADRAO_MM):
    """Cria o pavimento (ou atualiza o de mesmo nome) e o torna o ativo.

    Um nível do BIM só é ativado: a cota e a altura dele são do BIM e não mudam aqui.
    """
    nome = regras.nome_do_pavimento(nome)
    pav = por_nome(doc, nome)
    doc.openTransaction("Definir pavimento")
    try:
        if pav is not None and eh_nivel_bim(pav):
            ativar(doc, pav)
            doc.commitTransaction()
            return pav
        if pav is None:
            pav = doc.addObject("App::DocumentObjectGroup", "Pavimento")
            pav.Label = nome
            pav.addProperty("App::PropertyDistance", "Elevacao", "Pavimento", "Cota do piso do pavimento")
            pav.addProperty("App::PropertyDistance", "AlturaPavimento", "Pavimento", "Altura de piso a piso")
            pav.addProperty("App::PropertyBool", "Ativo", "Pavimento", "Pavimento onde os próximos símbolos entram")
            mae = doc.getObject(GRUPO_MAE)
            if mae is not None:
                mae.addObject(pav)
        pav.Elevacao = float(elevacao_mm)
        pav.AlturaPavimento = float(altura_mm)
        ativar(doc, pav)
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    return pav


def garantir_ativo(doc):
    """Pavimento ativo; sem nenhum ativo, ativa o mais baixo, e sem pavimentos cria o Térreo.

    Num projeto com níveis do BIM, o ativo é um deles, e o Térreo não é criado.
    """
    pav = ativo(doc)
    if pav is not None:
        return pav
    existentes = listar(doc)
    if existentes:
        ativar(doc, existentes[0])
        return existentes[0]
    return definir(doc, regras.PAVIMENTO_PADRAO)


def resumo(doc):
    """Dados dos pavimentos para os diálogos: nome, cota e altura em mm e se é o ativo."""
    return [
        {
            "nome": pav.Label,
            "elevacao_mm": elevacao(pav),
            "altura_mm": altura(pav),
            "ativo": bool(getattr(pav, "Ativo", False)),
            "bim": eh_nivel_bim(pav),
        }
        for pav in listar(doc)
    ]


def sugestao_novo(doc):
    """Nome, cota e altura sugeridos para o próximo pavimento."""
    return regras.sugerir_novo([(d["nome"], d["elevacao_mm"], d["altura_mm"]) for d in resumo(doc)])


# --- pastas dos símbolos -----------------------------------------------------

def chave_do_objeto(obj):
    """Chave da pasta do símbolo, ou None se o objeto não é um símbolo da planta."""
    tipo = getattr(getattr(obj, "Proxy", None), "Type", "")
    if tipo == "Ponto":
        return regras.pasta_do_objeto(tipo, obj.Simbolo)
    if getattr(obj, "tipo", "") == "tomada":
        return regras.pasta_do_objeto("tomada")
    return regras.pasta_do_objeto(tipo)


def pasta(doc, pavimento, chave):
    """Subpasta do pavimento para a chave, criada se ainda não existir."""
    for filho in pavimento.Group:
        if getattr(filho, "pasta", None) == chave:
            return filho
    grupo = doc.addObject("App::DocumentObjectGroup", f"Pasta_{chave}")
    grupo.addProperty("App::PropertyString", "pasta", "Pavimento", "Tipo de símbolo desta pasta")
    grupo.pasta = chave
    rotulo = regras.PASTAS[chave]
    _rotular(grupo, rotulo, f"{pavimento.Label} - {rotulo}")
    pavimento.addObject(grupo)
    return grupo


def _marcar(obj, nome):
    """Guarda o nome do pavimento no próprio símbolo, para ele saber onde está."""
    if not hasattr(obj, "Pavimento"):
        obj.addProperty("App::PropertyString", "Pavimento", "Elétrica", "Pavimento onde o símbolo está")
    obj.Pavimento = nome


def arquivar(doc, obj, pavimento=None):
    """Coloca o símbolo na pasta do tipo dele, dentro do pavimento (o ativo, se não for dado).

    Se o símbolo já estava em outra pasta, sai dela.

    Returns:
        A pasta onde o símbolo ficou, ou None se o objeto não é um símbolo da planta.
    """
    chave = chave_do_objeto(obj)
    if chave is None:
        return None
    pavimento = pavimento or garantir_ativo(doc)
    destino = pasta(doc, pavimento, chave)
    atual = _pai(obj)
    if atual is None or atual.Name != destino.Name:
        if atual is not None:
            atual.removeObject(obj)
        destino.addObject(obj)
    _marcar(obj, pavimento.Label)
    return destino


def mover(doc, objetos, pavimento):
    """Move os símbolos para as pastas do pavimento, em uma única operação de desfazer.

    Returns:
        Quantidade de símbolos movidos; objetos que não são símbolos são ignorados.
    """
    movidos = 0
    doc.openTransaction("Mover para pavimento")
    try:
        for obj in objetos:
            if arquivar(doc, obj, pavimento) is not None:
                movidos += 1
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    return movidos


def pavimento_do_objeto(doc, obj):
    """Pavimento onde o símbolo está: o da pasta em que ele fica, ou o do nome guardado nele."""
    pasta_do_simbolo = _pai(obj)
    pav = _pai(pasta_do_simbolo) if pasta_do_simbolo is not None else None
    if pav is not None and eh_pavimento(pav):
        return pav
    nome = getattr(obj, "Pavimento", "")
    return por_nome(doc, nome) if nome else None


def elevacao_do_objeto(doc, obj):
    """Cota do piso do pavimento do símbolo [mm]; fora de qualquer pavimento vale 0."""
    pav = pavimento_do_objeto(doc, obj)
    return elevacao(pav) if pav is not None else 0.0
