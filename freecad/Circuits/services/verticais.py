"""Subidas e descidas na planta e detalhes das verticais (``core.verticais``).

- ``desenhar_simbolos``: um objeto por pavimento e tipo (eletroduto ou
  eletrocalha) com os símbolos, e um texto por vertical, todos com a
  propriedade ``simbolo_vertical``, nas pastas Eletrodutos e Bandejas e leitos
  do pavimento. Recriados a cada uso.
- ``desenhar_detalhes``: grupo ``Detalhes_verticais`` com um detalhe em
  elevação por tipo de vertical (V1, V2...), recriado na posição em que estava.
"""
import math

import Draft
import FreeCAD as App
import Part

from freecad.Circuits.core import verticais as regras
from freecad.Circuits.services import bandejas, legenda, parametros, pavimentos, rede

GRUPO_DETALHES = "Detalhes_verticais"
TAMANHO_SIMBOLO = 300.0
AFASTAMENTO_DA_LEGENDA = 8000.0  # os detalhes começam à direita da legenda
ESPACO_ENTRE_DETALHES = 500.0
_PASTA_DO_TIPO = {"eletroduto": "eletrodutos", "eletrocalha": "bandejas"}


def coletar(doc, com_caixas=None):
    """Itens verticais do documento (``core.verticais``).

    Args:
        com_caixas: inclui as descidas e subidas até as caixas; None segue o
            parâmetro do projeto ``simbolos_descida_caixas``.
    """
    if com_caixas is None:
        com_caixas = parametros.ler(doc)["simbolos_descida_caixas"] == "S"
    fiacao = rede.analisar(doc)
    itens = regras.itens_de_eletroduto(fiacao["verticais"] if com_caixas else [], fiacao.get("transicoes", []))
    for pav, resultado in bandejas.analisar(doc).items():
        itens += regras.itens_de_eletrocalha([dict(v, pavimento=pav) for v in resultado["verticais"]])
    return itens


def _pavimento(doc, nome):
    return pavimentos.por_nome(doc, nome) if nome else None


def _piso(doc, nome):
    pav = _pavimento(doc, nome)
    return pavimentos.elevacao(pav) if pav is not None else 0.0


def _remover_marcados(doc, propriedade):
    for obj in [o for o in doc.Objects if hasattr(o, propriedade)]:
        doc.removeObject(obj.Name)


def _marcar(obj, valor):
    obj.addProperty("App::PropertyString", "simbolo_vertical", "Verticais", "Símbolo de subida ou descida")
    obj.simbolo_vertical = valor


def desenhar_simbolos(doc, tamanho=TAMANHO_SIMBOLO):
    """Recria os símbolos de subida e descida na planta, no piso de cada pavimento.

    Returns:
        Quantidade de verticais com símbolo.
    """
    _remover_marcados(doc, "simbolo_vertical")
    itens = coletar(doc)
    arestas = {}
    for item in itens:
        z = _piso(doc, item["pavimento"])
        x0, y0 = item["x"], item["y"]
        desenho = regras.simbolo(item, tamanho)
        grupo = arestas.setdefault((item["pavimento"], item["tipo"]), [])
        grupo += [Part.makeLine(App.Vector(x0 + x1, y0 + y1, z), App.Vector(x0 + x2, y0 + y2, z))
                  for x1, y1, x2, y2 in desenho["linhas"]]
        grupo += [Part.makeCircle(r, App.Vector(x0 + cx, y0 + cy, z)) for cx, cy, r in desenho["circulos"]]
        tx, ty = desenho["texto"]
        rotulo = Draft.make_text([regras.texto(item)], placement=App.Placement(App.Vector(x0 + tx, y0 + ty, z),
                                                                              App.Rotation()),
                                 height=tamanho * 0.3)
        _marcar(rotulo, item["local"])
        _guardar(doc, item["pavimento"], item["tipo"], rotulo)
    for indice, ((pav, tipo), lista) in enumerate(sorted(arestas.items())):
        objeto = doc.addObject("Part::Feature", f"Simbolos_verticais_{indice}")
        objeto.Shape = Part.makeCompound(lista)
        objeto.Label = f"Subidas e descidas {pav or 'sem pavimento'} ({tipo})"
        _marcar(objeto, pav)
        _guardar(doc, pav, tipo, objeto)
    doc.recompute()
    return len(itens)


def _guardar(doc, pav_nome, tipo, objeto):
    pav = _pavimento(doc, pav_nome)
    if pav is not None:
        pavimentos.pasta(doc, pav, _PASTA_DO_TIPO[tipo]).addObject(objeto)


def desenhar_detalhes(doc):
    """Recria o grupo com um detalhe em elevação por tipo de vertical.

    Os detalhes ficam lado a lado, à direita da legenda, ou onde o grupo estava.

    Returns:
        Quantidade de detalhes.
    """
    itens = coletar(doc, com_caixas=True)
    anterior = doc.getObject(GRUPO_DETALHES)
    posicao = legenda._canto_livre(doc) + App.Vector(AFASTAMENTO_DA_LEGENDA, 0, 0)
    if anterior is not None:
        if anterior.Group:
            posicao = anterior.Group[0].Placement.Base  # mantém onde o usuário deixou
        anterior.removeObjectsFromDocument()
        doc.removeObject(GRUPO_DETALHES)
    if not itens:
        doc.recompute()
        return 0

    grupo = doc.addObject("App::DocumentObjectGroup", GRUPO_DETALHES)
    grupo.Label = "Detalhes das verticais"
    grupo.addObject(Draft.make_text(["DETALHES DAS VERTICAIS"], placement=App.Placement(posicao, App.Rotation()),
                                    height=150.0))
    detalhes = regras.detalhes(itens)
    for indice, detalhe in enumerate(detalhes):
        pe_direito = bandejas.pe_direito(doc, detalhe["pavimento"])
        g = regras.geometria_detalhe(detalhe, pe_direito)
        origem = posicao + App.Vector(regras.LARGURA_DETALHE / 2 + indice * (regras.LARGURA_DETALHE +
                                                                            ESPACO_ENTRE_DETALHES),
                                      -(pe_direito + 800.0), 0)
        desenho = doc.addObject("Part::Feature", f"Detalhe_{detalhe['id']}")
        arestas = [Part.makeLine(origem + App.Vector(x1, y1, 0), origem + App.Vector(x2, y2, 0))
                   for x1, y1, x2, y2 in g["linhas"]]
        for cx, cy, raio, inicio, varredura in g["arcos"]:
            circulo = Part.Circle(origem + App.Vector(cx, cy, 0), App.Vector(0, 0, 1), raio)
            arestas.append(Part.ArcOfCircle(circulo, math.radians(inicio), math.radians(inicio + varredura)).toShape())
        desenho.Shape = Part.makeCompound(arestas)
        desenho.Label = f"Detalhe {detalhe['id']}"
        grupo.addObject(desenho)
        for x, y, conteudo, altura in g["textos"]:
            grupo.addObject(Draft.make_text([conteudo], placement=App.Placement(origem + App.Vector(x, y, 0),
                                                                                App.Rotation()), height=altura))
    doc.recompute()
    return len(detalhes)
