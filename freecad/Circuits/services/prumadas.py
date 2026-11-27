"""Prumadas verticais no documento: andares do projeto, objeto paramétrico, símbolos em cada pavimento,
esquema vertical e materiais (``core.prumadas``, ``objects.prumada``)."""
import time

import Draft
import FreeCAD as App
import Part

from freecad.Circuits.core import prumadas as regras
from freecad.Circuits.objects.prumada import andares_do_texto, andares_em_texto, create_prumada
from freecad.Circuits.services import pavimentos

MARCA_SIMBOLO = "prumada_planta_de"   # símbolo das prumadas num pavimento: nome do objeto Prumada
MARCA_ESQUEMA = "esquema_prumadas_de"  # esquema vertical: nome do objeto Prumada
AFASTAMENTO_ESQUEMA_MM = 3000.0
GRUPO_MATERIAIS = "Prumadas verticais"
ULTIMO_DESENHO = 0.0  # time.monotonic() do último desenhar_2d, para o observador não repetir


def angulo_do_objeto(obj):
    """Rotação do objeto em torno de z, em graus."""
    try:
        return float(obj.Placement.Rotation.toEuler()[0])
    except Exception:
        return 0.0


def _tipo(obj):
    return getattr(getattr(obj, "Proxy", None), "Type", "")


def eh_prumada(obj):
    return _tipo(obj) == "Prumada"


def listar(doc):
    return [o for o in doc.Objects if eh_prumada(o)]


def andares_do_projeto(doc, unidades_padrao=4):
    """Andares a partir dos pavimentos do projeto, com as unidades da planilha do centro de medição
    (pelo nome do pavimento), senão as do Novo projeto (propriedade ``Unidades`` do pavimento), senão
    ``unidades_padrao`` (o mais baixo, a origem, sem unidades)."""
    unidades = {}
    try:
        from freecad.Circuits.services import centro_medicao
        folha = centro_medicao.planilha(doc)
        if folha is not None:
            unidades = {a["nome"]: a["unidades"] for a in centro_medicao.ler_andares(folha)}
    except Exception:
        unidades = {}
    lista = sorted(pavimentos.listar(doc), key=pavimentos.elevacao)
    andares = []
    for i, pav in enumerate(lista):
        padrao = 0 if i == 0 else int(unidades_padrao)
        informadas = getattr(pav, "Unidades", None)
        if informadas is not None:
            padrao = int(informadas)
        andares.append(regras.andar(pav.Label, pavimentos.elevacao(pav), unidades.get(pav.Label, padrao)))
    return andares


def criar(doc, pavimento, **valores):
    """Objeto de prumadas na pasta *Prumadas* do pavimento (o da origem), no piso dele."""
    if isinstance(valores.get("Andares"), list) and valores["Andares"] and isinstance(valores["Andares"][0], dict):
        valores["Andares"] = andares_em_texto(valores["Andares"])
    obj = create_prumada(doc, **valores)
    if pavimento is not None:
        pavimentos.pasta(doc, pavimento, "prumadas").addObject(obj)
        posicao = obj.Placement
        posicao.Base = App.Vector(posicao.Base.x, posicao.Base.y, pavimentos.elevacao(pavimento))
        obj.Placement = posicao
    doc.recompute()
    return obj


def atualizar(doc, obj, **valores):
    """Muda as entradas, mantendo a posição, e refaz os desenhos 2D."""
    if isinstance(valores.get("Andares"), list) and valores["Andares"] and isinstance(valores["Andares"][0], dict):
        valores["Andares"] = andares_em_texto(valores["Andares"])
    posicao = App.Placement(obj.Placement)
    for chave, valor in valores.items():
        if hasattr(obj, chave):
            setattr(obj, chave, valor)
    obj.Placement = posicao
    doc.recompute()
    desenhar_2d(doc, obj)
    return obj


def _figura(doc, nome, rotulo, desenho, origem, marca, valor_marca):
    """Part::Feature com as linhas e os círculos de ``desenho`` em ``origem`` e um texto Draft por rótulo."""
    arestas = [Part.makeLine(App.Vector(x1, y1, 0), App.Vector(x2, y2, 0))
               for x1, y1, x2, y2 in desenho["linhas"] if (x1, y1) != (x2, y2)]
    arestas += [Part.makeCircle(r, App.Vector(cx, cy, 0)) for cx, cy, r in desenho["circulos"]]
    figura = doc.addObject("Part::Feature", nome)
    figura.Label = rotulo
    figura.Shape = Part.makeCompound(arestas) if arestas else Part.Shape()
    figura.Placement = App.Placement(origem, App.Rotation())
    objetos = [figura]
    for x, y, conteudo, altura, angulo in desenho["textos"]:
        objetos.append(Draft.make_text([conteudo], placement=App.Placement(origem + App.Vector(x, y, 0),
                                                                           App.Rotation(App.Vector(0, 0, 1), angulo)),
                                       height=altura))
    for o in objetos:
        o.addProperty("App::PropertyString", marca, "Prumadas", "Desenho das prumadas verticais")
        setattr(o, marca, valor_marca)
    return objetos


def _remover(doc, marca, valor):
    for o in [o for o in doc.Objects if getattr(o, marca, None) == valor]:
        if doc.getObject(o.Name) is not None:
            doc.removeObject(o.Name)


def _posicao_antiga(doc, marca, valor):
    figura = next((o for o in doc.Objects if getattr(o, marca, None) == valor and o.TypeId == "Part::Feature"), None)
    return App.Vector(figura.Placement.Base) if figura is not None else None


def desenhar_2d(doc, obj):
    """Recria o símbolo das prumadas em cada pavimento (no ponto do shaft, no piso dele, na pasta
    *Prumadas*) e o esquema vertical (ao lado, ou onde o usuário o deixou).

    Returns:
        (quantidade de símbolos, grupo do esquema ou None).
    """
    global ULTIMO_DESENHO
    resultado = obj.Proxy.resultado(obj)
    _remover(doc, MARCA_SIMBOLO, obj.Name)
    xy = obj.Placement.Base
    angulo = angulo_do_objeto(obj)
    simbolos = 0
    for i, a in enumerate(resultado["andares"]):
        desenho = regras.simbolo_girado(resultado, i, angulo)
        if not desenho["circulos"]:
            continue
        pav = pavimentos.por_nome(doc, a["nome"])
        cota = pavimentos.elevacao(pav) if pav is not None else a["cota"]
        objetos = _figura(doc, "Prumadas_planta", f"Prumadas - {a['nome']}", desenho,
                          App.Vector(xy.x, xy.y, cota), MARCA_SIMBOLO, obj.Name)
        if pav is not None:
            pasta = pavimentos.pasta(doc, pav, "prumadas")
            for o in objetos:
                pasta.addObject(o)
        simbolos += 1
    origem = _posicao_antiga(doc, MARCA_ESQUEMA, obj.Name)
    _remover(doc, MARCA_ESQUEMA, obj.Name)
    grupo_antigo = next((o for o in doc.Objects if getattr(o, "esquema_grupo_de", None) == obj.Name), None)
    if grupo_antigo is not None:
        doc.removeObject(grupo_antigo.Name)
    desenho = regras.esquema(resultado)
    if not desenho["linhas"]:
        doc.recompute()
        ULTIMO_DESENHO = time.monotonic()
        return simbolos, None
    if origem is None:
        caixa = obj.Shape.BoundBox if not obj.Shape.isNull() else None
        x = (caixa.XMax if caixa is not None else xy.x) + AFASTAMENTO_ESQUEMA_MM - desenho["limites"][0]
        origem = App.Vector(x, xy.y, obj.Placement.Base.z)
    grupo = doc.addObject("App::DocumentObjectGroup", "Esquema_prumadas")
    grupo.Label = "Esquema vertical das prumadas"
    grupo.addProperty("App::PropertyString", "esquema_grupo_de", "Prumadas", "Prumadas deste esquema")
    grupo.esquema_grupo_de = obj.Name
    for o in _figura(doc, "Esquema_prumadas_desenho", "Esquema vertical", desenho, origem, MARCA_ESQUEMA, obj.Name):
        grupo.addObject(o)
    pasta = pavimentos.pasta_do_pavimento(doc, obj, "prumadas")
    if pasta is not None:
        pasta.addObject(grupo)
    doc.recompute()
    ULTIMO_DESENHO = time.monotonic()
    return simbolos, grupo


def materiais_por_pavimento(doc):
    """(pavimento da origem, itens) das prumadas para ``services.quantitativos``, grupo *Prumadas verticais*."""
    resultado = []
    for obj in listar(doc):
        pav = pavimentos.pavimento_do_objeto(doc, obj)
        itens = [{"item": item, "especificacao": f"{sistema} - {especificacao}", "quantidade": quantidade,
                  "unidade": unidade, "grupo": GRUPO_MATERIAIS}
                 for sistema, item, especificacao, quantidade, unidade in regras.materiais(obj.Proxy.resultado(obj))]
        resultado.append((pav.Label if pav is not None else "", itens))
    return resultado


def dados_do_memorial(doc):
    """[{'nome', 'resultado', 'materiais', 'esquema'}] de cada objeto de prumadas, para o relatório."""
    lista = []
    for obj in listar(doc):
        resultado = obj.Proxy.resultado(obj)
        lista.append({"nome": obj.Label, "resultado": resultado, "materiais": regras.materiais(resultado),
                      "esquema": regras.esquema(resultado)})
    return lista


__all__ = ["andares_do_projeto", "andares_do_texto", "criar", "atualizar", "desenhar_2d", "listar",
           "materiais_por_pavimento", "dados_do_memorial", "angulo_do_objeto"]
