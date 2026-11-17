"""Eletrodutos na planta com a dinâmica das eletrocalhas (``core.pecas_eletroduto``).

Fluxo do botão Eletroduto com linhas selecionadas: ``marcar`` (diâmetro, tipo,
material, instalação, altura, pasta do pavimento, tracejado no piso),
``encaixar`` (pontas soltas nos outros eletrodutos) e ``rede.conectar`` (nas
caixas), ``criar_caixas`` (caixa de passagem nas derivações embutidas sem
caixa) e ``anotar`` (diâmetro de cada eletroduto e siglas das peças, textos com
a propriedade ``rotulo_eletroduto`` na pasta Eletrodutos do pavimento).
"""
import Draft
import FreeCAD as App

from freecad.Circuits.core import pecas_eletroduto as regras
from freecad.Circuits.objects.ponto import create_ponto
from freecad.Circuits.services import eletrodutos, pavimentos, rede

ALTURA_TEXTO = 120.0


def _propriedade_enum(obj, nome, opcoes, valor, dica):
    if not hasattr(obj, nome):
        obj.addProperty("App::PropertyEnumeration", nome, "Conduit", dica)
        setattr(obj, nome, list(opcoes))
    setattr(obj, nome, valor)


def marcar(doc, objetos, diametro="3/4", tipo="Flexível", material="PVC", instalacao=regras.TETO, altura=None):
    """Marca as linhas como eletrodutos, guarda-as no pavimento de inserção e aplica o estilo da instalação.

    Returns:
        Linhas marcadas.
    """
    linhas = [obj for obj in objetos if hasattr(obj, "Points")]
    destino = pavimentos.pavimento_para_insercao(doc) if linhas else None
    for obj in linhas:
        eletrodutos._preparar_caminho(obj)
        obj.Diametro = str(diametro)
        obj.Tipo = tipo
        _propriedade_enum(obj, "Material", regras.MATERIAIS, material, "PVC ou aço galvanizado")
        _propriedade_enum(obj, "Instalacao", regras.INSTALACOES, instalacao, "Onde o eletroduto passa")
        obj.Altura3D = float(regras.ALTURA_PADRAO[instalacao] if altura is None else altura)
        eletrodutos._preparar_caminho(obj)  # refaz o raio das curvas com o tipo novo
        if pavimentos.pavimento_do_objeto(doc, obj) is None:
            pavimentos.arquivar(doc, obj, destino)
        try:
            obj.ViewObject.DrawStyle = "Dashed" if regras.tracejado(instalacao) else "Solid"
        except Exception:
            pass
    return linhas


def _texto(valor):
    return str(getattr(valor, "Value", valor))


def caminho(obj):
    """Dados do eletroduto para ``core.pecas_eletroduto``, com padrões para os marcados antes."""
    pontos = [(v.x, v.y) for v in (obj.Placement.multVec(p) for p in obj.Points)]
    altura = getattr(obj, "Altura3D", 2800.0)
    return {
        "pontos": pontos, "nome": obj.Name, "diametro": _texto(getattr(obj, "Diametro", "3/4")),
        "tipo": _texto(getattr(obj, "Tipo", "Flexível") or "Flexível"),
        "material": _texto(getattr(obj, "Material", "PVC") or "PVC"),
        "instalacao": _texto(getattr(obj, "Instalacao", regras.TETO) or regras.TETO),
        "altura": float(getattr(altura, "Value", altura)),
    }


def _nome_pavimento(doc, obj):
    pav = pavimentos.pavimento_do_objeto(doc, obj)
    return pav.Label if pav is not None else ""


def encaixar(doc, objetos=None):
    """Junta as pontas soltas dos eletrodutos aos vizinhos do mesmo pavimento.

    Returns:
        Quantidade de junções feitas.
    """
    por_pavimento = {}
    for obj in rede.listar_eletrodutos(doc):
        if hasattr(obj, "Points"):
            por_pavimento.setdefault(_nome_pavimento(doc, obj), []).append(obj)
    alvo = {obj.Name for obj in objetos} if objetos is not None else None
    juncoes = 0
    for objs in por_pavimento.values():
        if alvo is not None and not any(obj.Name in alvo for obj in objs):
            continue
        antes = [caminho(obj)["pontos"] for obj in objs]
        novos, feitas = regras.encaixar(antes)
        for obj, pontos, ajustados in zip(objs, antes, novos):
            if [(float(x), float(y)) for x, y in pontos] != ajustados:
                rede._gravar_pontos(obj, ajustados)
        juncoes += feitas
    return juncoes


def analisar(doc):
    """{nome do pavimento: resultado de ``core.pecas_eletroduto.analisar``}."""
    caixas = {}
    for caixa in rede.listar_caixas(doc):
        caixas.setdefault(caixa["pavimento"], []).append((caixa["x"], caixa["y"]))
    caminhos = {}
    for obj in rede.listar_eletrodutos(doc):
        if not hasattr(obj, "Points"):
            continue
        try:
            caminhos.setdefault(_nome_pavimento(doc, obj), []).append(caminho(obj))
        except Exception:
            continue
    return {pav: regras.analisar(lista, caixas.get(pav, []) + (caixas.get("", []) if pav else []))
            for pav, lista in caminhos.items()}


def criar_caixas(doc, resultados=None):
    """Cria uma caixa de passagem em cada derivação embutida sem caixa.

    Returns:
        Quantidade de caixas criadas.
    """
    resultados = resultados if resultados is not None else analisar(doc)
    criadas = 0
    for pav_nome, resultado in resultados.items():
        pav = pavimentos.por_nome(doc, pav_nome) if pav_nome else None
        for nova in resultado.get("caixas_novas", []):
            caixa = create_ponto("caixa_passagem")
            if caixa is None:
                continue
            posicao = caixa.Placement
            posicao.Base = App.Vector(nova["x"], nova["y"], 0.0)
            caixa.Placement = posicao
            caixa.Label = "Caixa de passagem"
            pavimentos.arquivar(doc, caixa, pav)  # leva à cota do piso do pavimento
            criadas += 1
    return criadas


def _remover_rotulos(doc):
    for obj in [o for o in doc.Objects if hasattr(o, "rotulo_eletroduto")]:
        doc.removeObject(obj.Name)


def _novo_texto(doc, pav_nome, x, y, z, conteudo, angulo=0.0):
    texto = Draft.make_text([conteudo], placement=App.Placement(App.Vector(x, y, z),
                                                                 App.Rotation(App.Vector(0, 0, 1), angulo)),
                            height=ALTURA_TEXTO)
    texto.addProperty("App::PropertyString", "rotulo_eletroduto", "Conduit", "Texto do eletroduto na planta")
    texto.rotulo_eletroduto = conteudo
    pav = pavimentos.por_nome(doc, pav_nome) if pav_nome else None
    if pav is not None:
        pavimentos.pasta(doc, pav, "eletrodutos").addObject(texto)
    return texto


def anotar(doc, resultados=None):
    """Recria o diâmetro de cada eletroduto e as siglas das peças (C90, C45, CT, CX) na planta.

    Returns:
        Quantidade de textos.
    """
    _remover_rotulos(doc)
    resultados = resultados if resultados is not None else analisar(doc)
    por_pavimento = {}
    for obj in rede.listar_eletrodutos(doc):
        if hasattr(obj, "Points"):
            por_pavimento.setdefault(_nome_pavimento(doc, obj), []).append(caminho(obj))
    total = 0
    for pav_nome, caminhos in por_pavimento.items():
        pav = pavimentos.por_nome(doc, pav_nome) if pav_nome else None
        z = pavimentos.elevacao(pav) if pav is not None else 0.0
        siglas = regras.siglas(resultados.get(pav_nome, {"pecas": []}))
        for x, y, angulo, conteudo in regras.rotulos(caminhos, evitar=[(sx, sy) for sx, sy, _ in siglas]):
            if 90.0 < abs(angulo) <= 180.0:  # texto sempre de baixo para cima ou da esquerda para a direita
                angulo -= 180.0 if angulo > 0 else -180.0
            _novo_texto(doc, pav_nome, x, y, z, conteudo, angulo)
            total += 1
        for x, y, sigla in siglas:
            _novo_texto(doc, pav_nome, x + ALTURA_TEXTO, y + ALTURA_TEXTO, z, sigla)
            total += 1
    doc.recompute()
    return total


def materiais_por_pavimento(doc):
    """[(pavimento, itens de ``core.pecas_eletroduto.materiais``)] das peças e da fixação."""
    return [(pav, regras.materiais(resultado)) for pav, resultado in analisar(doc).items()]
