"""Legenda dos símbolos usados na planta."""
import Draft
import FreeCAD as App

from freecad.Circuits.core import simbolos
from freecad.Circuits.objects.ponto import TAMANHO_PADRAO, forma_do_simbolo

NOME_GRUPO = "Legenda_simbolos"
MARGEM = 1000.0  # mm entre a planta e a legenda


def simbolos_usados(doc):
    """Chaves do catálogo presentes no documento, na ordem do catálogo."""
    usados = {
        obj.Simbolo for obj in doc.Objects
        if getattr(getattr(obj, "Proxy", None), "Type", "") == "Ponto"
    }
    return [chave for chave in simbolos.CATALOGO if chave in usados]


def _canto_livre(doc):
    """Ponto à direita de todos os pontos elétricos, alinhado ao topo deles."""
    x_max, y_max = None, None
    for obj in doc.Objects:
        if getattr(getattr(obj, "Proxy", None), "Type", "") != "Ponto":
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
    usados = simbolos_usados(doc)
    anterior = doc.getObject(NOME_GRUPO)
    posicao = _canto_livre(doc)
    if anterior:
        if anterior.Group:
            posicao = anterior.Group[0].Placement.Base  # mantém onde o usuário deixou
        anterior.removeObjectsFromDocument()
        doc.removeObject(NOME_GRUPO)
    if not usados:
        doc.recompute()
        return 0

    grupo = doc.addObject("App::DocumentObjectGroup", NOME_GRUPO)
    grupo.Label = "Legenda"
    passo = tamanho * 2.0
    altura_texto = tamanho * 0.6

    titulo = Draft.make_text("LEGENDA", placement=App.Placement(posicao, App.Rotation()), height=altura_texto * 1.2)
    grupo.addObject(titulo)

    for indice, chave in enumerate(usados, start=1):
        dados = simbolos.CATALOGO[chave]
        xmin, ymin, xmax, ymax = simbolos.limites(chave, tamanho)
        linha = posicao + App.Vector(0, -indice * passo, 0)

        desenho = doc.addObject("Part::Feature", f"Legenda_{chave}")
        desenho.Shape = forma_do_simbolo(chave, tamanho)
        # Alinha a borda esquerda e o meio do símbolo com a linha do texto.
        encaixe = linha + App.Vector(-xmin, altura_texto / 2 - (ymin + ymax) / 2, 0)
        desenho.Placement = App.Placement(encaixe, App.Rotation())
        grupo.addObject(desenho)

        texto = Draft.make_text(
            f"{dados['legenda']} - {dados['dica']}",
            placement=App.Placement(linha + App.Vector(tamanho * 2.0, 0, 0), App.Rotation()),
            height=altura_texto,
        )
        grupo.addObject(texto)

    doc.recompute()
    return len(usados)
