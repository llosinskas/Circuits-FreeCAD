"""Legenda dos símbolos usados na planta."""
import Draft
import FreeCAD as App

from freecad.Circuits.core import simbolos
from freecad.Circuits.objects.ponto import TAMANHO_PADRAO, forma_das_primitivas

NOME_GRUPO = "Legenda_simbolos"
MARGEM = 1000.0  # mm entre a planta e a legenda


def simbolos_usados(doc):
    """Chaves do catálogo presentes no documento, na ordem do catálogo."""
    usados = {
        obj.Simbolo for obj in doc.Objects
        if getattr(getattr(obj, "Proxy", None), "Type", "") == "Ponto"
    }
    return [chave for chave in simbolos.CATALOGO if chave in usados]


def interruptores_usados(doc):
    """Tipos de interruptor (Simples, Paralelo, Intermediário) presentes no documento, nessa ordem."""
    usados = {
        str(obj.Tipo) for obj in doc.Objects
        if getattr(getattr(obj, "Proxy", None), "Type", "") == "Switch"
    }
    return [tipo for tipo in simbolos.INTERRUPTORES if tipo in usados]


def itens_da_legenda(doc, tamanho=TAMANHO_PADRAO):
    """Linhas da legenda: (nome do objeto, primitivas do desenho, texto), pontos e depois interruptores."""
    itens = []
    for chave in simbolos_usados(doc):
        dados = simbolos.CATALOGO[chave]
        itens.append((chave, simbolos.geometria(chave, tamanho), f"{dados['legenda']} - {dados['dica']}"))
    for tipo in interruptores_usados(doc):
        legenda, dica = simbolos.INTERRUPTORES[tipo]
        chave = "interruptor_" + {"Simples": "simples", "Paralelo": "paralelo"}.get(tipo, "intermediario")
        itens.append((chave, simbolos.geometria_interruptor(tipo, tamanho), f"{legenda} - {dica}"))
    return itens + _itens_de_fiacao(doc, tamanho) + _itens_de_verticais(doc, tamanho)


def _itens_de_fiacao(doc, tamanho):
    """Marcas dos condutores (fase, neutro, retorno, terra) da fiação desenhada na planta."""
    from freecad.Circuits.core.simbologia import itens_de_legenda_fiacao, lista_de_condutores
    usados = set()
    for obj in doc.Objects:
        if hasattr(obj, "fiacao_de"):
            usados.update(lista_de_condutores(getattr(obj, "Condutores", "") or "F+N+T"))
    return itens_de_legenda_fiacao(usados, tamanho) if usados else []


def _itens_de_verticais(doc, tamanho):
    """Tipos de subida, descida e prumada usados (``core.verticais.itens_de_legenda``)."""
    from freecad.Circuits.core import verticais as regras_verticais
    from freecad.Circuits.services import verticais  # aqui, porque verticais também usa a legenda
    try:
        itens = verticais.coletar(doc)
    except Exception as erro:  # sem rede legível, a legenda sai só com os símbolos
        App.Console.PrintWarning(f"Legenda sem as verticais: {erro}\n")
        return []
    return regras_verticais.itens_de_legenda(itens, tamanho * 1.5)


def _canto_livre(doc):
    """Ponto à direita de todos os pontos elétricos, alinhado ao topo deles."""
    x_max, y_max = None, None
    for obj in doc.Objects:
        if getattr(getattr(obj, "Proxy", None), "Type", "") not in ("Ponto", "Switch"):
            continue
        base = obj.Placement.Base
        x_max = base.x if x_max is None else max(x_max, base.x)
        y_max = base.y if y_max is None else max(y_max, base.y)
    if x_max is None:
        return App.Vector(0, 0, 0)
    return App.Vector(x_max + MARGEM, y_max, 0)


def gerar_legenda(doc, tamanho=TAMANHO_PADRAO):
    """Recria o grupo com um símbolo e uma descrição por tipo de ponto usado.

    Returns:
        Quantidade de linhas da legenda (0 se não há pontos na planta).
    """
    itens = itens_da_legenda(doc, tamanho)
    anterior = doc.getObject(NOME_GRUPO)
    posicao = _canto_livre(doc)
    if anterior:
        if anterior.Group:
            posicao = anterior.Group[0].Placement.Base  # mantém onde o usuário deixou
        anterior.removeObjectsFromDocument()
        doc.removeObject(NOME_GRUPO)
    if not itens:
        doc.recompute()
        return 0

    grupo = doc.addObject("App::DocumentObjectGroup", NOME_GRUPO)
    grupo.Label = "Legenda"
    passo = tamanho * 2.0
    altura_texto = tamanho * 0.6

    titulo = Draft.make_text("LEGENDA", placement=App.Placement(posicao, App.Rotation()), height=altura_texto * 1.2)
    grupo.addObject(titulo)

    for indice, (chave, primitivas, descricao) in enumerate(itens, start=1):
        xmin, ymin, xmax, ymax = simbolos.limites_de(primitivas)
        linha = posicao + App.Vector(0, -indice * passo, 0)

        desenho = doc.addObject("Part::Feature", f"Legenda_{chave}")
        desenho.Shape = forma_das_primitivas(primitivas)
        # Alinha a borda esquerda e o meio do símbolo com a linha do texto.
        encaixe = linha + App.Vector(-xmin, altura_texto / 2 - (ymin + ymax) / 2, 0)
        desenho.Placement = App.Placement(encaixe, App.Rotation())
        grupo.addObject(desenho)

        texto = Draft.make_text(
            descricao,
            placement=App.Placement(linha + App.Vector(tamanho * 2.0, 0, 0), App.Rotation()),
            height=altura_texto,
        )
        grupo.addObject(texto)

    doc.recompute()
    return len(itens)
