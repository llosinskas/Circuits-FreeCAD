"""Planilha de notas do projeto e o quadro de notas desenhado na planta."""
import Draft
import FreeCAD as App
import Spreadsheet  # noqa: F401  (registra o tipo Spreadsheet::Sheet)

from freecad.Circuits.core import notas as regras
from freecad.Circuits.objects.ponto import TAMANHO_PADRAO, escala_padrao
from freecad.Circuits.services import planilhas
from freecad.Circuits.services.legenda import NOME_GRUPO as GRUPO_LEGENDA
from freecad.Circuits.services.legenda import _canto_livre

NOME_PLANILHA = "Notas"
NOME_GRUPO = "Notas_projeto"
PRIMEIRA_LINHA = 3
EXEMPLOS = [
    "Instalação executada conforme a NBR 5410.",
    "Todos os circuitos têm condutor de proteção (terra).",
    "Apague estes exemplos e escreva uma nota por linha.",
]


def planilha_de_notas(doc, criar=True):
    """Planilha de notas do documento. Com ``criar``, é criada com exemplos se não existir."""
    for obj in doc.Objects:
        if hasattr(obj, "notas_do_projeto"):
            return obj
    if not criar:
        return None
    planilha = doc.addObject("Spreadsheet::Sheet", NOME_PLANILHA)
    planilha.addProperty("App::PropertyString", "notas_do_projeto", "Notas", "Marca a planilha de notas do projeto")
    planilha.notas_do_projeto = "Notas"
    planilha.set("A1", "Notas do projeto")
    planilha.set("A2", "Escreva uma nota por linha, a partir da linha 3. Depois use o botão Notas.")
    planilha.setColumnWidth("A", 600)
    for indice, exemplo in enumerate(EXEMPLOS):
        planilha.set(f"A{PRIMEIRA_LINHA + indice}", f"'{exemplo}")
    doc.recompute()
    return planilha


def ler_notas(planilha):
    """Textos da coluna A, da linha 3 em diante, sem as linhas vazias."""
    ultima = planilhas.ultima_linha(planilha)
    return regras.limpar(planilhas._texto(planilha, f"A{linha}") for linha in range(PRIMEIRA_LINHA, ultima + 1))


def _posicao_inicial(doc):
    """Embaixo da legenda, se existir; senão, à direita dos pontos da planta."""
    legenda = doc.getObject(GRUPO_LEGENDA)
    if legenda is not None and legenda.Group:
        base = legenda.Group[0].Placement.Base
        linhas = (len(legenda.Group) + 1) // 2 + 2  # título + um símbolo e um texto por linha
        return App.Vector(base.x, base.y - linhas * TAMANHO_PADRAO * 2.0, 0)  # 2 x tamanho por linha da legenda
    return _canto_livre(doc)


def gerar_notas(doc):
    """Recria na planta o quadro de notas, a partir da planilha de notas.

    O quadro fica onde estava (se o usuário o moveu) ou embaixo da legenda.

    Returns:
        Quantidade de notas desenhadas (0 se a planilha não existe ou está vazia).
    """
    planilha = planilha_de_notas(doc, criar=False)
    blocos = regras.formatar(ler_notas(planilha)) if planilha is not None else []
    altura_texto = TAMANHO_PADRAO * 0.6 * escala_padrao()

    anterior = doc.getObject(NOME_GRUPO)
    posicao = None
    if anterior is not None:
        if anterior.Group:
            posicao = anterior.Group[0].Placement.Base  # mantém onde o usuário deixou
        anterior.removeObjectsFromDocument()
        doc.removeObject(NOME_GRUPO)
    if not blocos:
        doc.recompute()
        return 0
    if posicao is None:
        posicao = _posicao_inicial(doc)

    grupo = doc.addObject("App::DocumentObjectGroup", NOME_GRUPO)
    grupo.Label = "Notas"
    passo = altura_texto * 1.7
    titulo = Draft.make_text("NOTAS", placement=App.Placement(posicao, App.Rotation()), height=altura_texto * 1.2)
    grupo.addObject(titulo)

    linha = 1.5  # linhas de texto já ocupadas abaixo do título
    for bloco in blocos:
        base = posicao + App.Vector(0, -linha * passo, 0)
        texto = Draft.make_text(bloco, placement=App.Placement(base, App.Rotation()), height=altura_texto)
        grupo.addObject(texto)
        linha += len(bloco) + 0.4
    doc.recompute()
    return len(blocos)
