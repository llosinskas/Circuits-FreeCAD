"""Bandejas (eletrocalhas e leitos) na planta: marcação, conexões, modelo 3D e suportes.

Uma bandeja é uma linha (Draft Wire) com a propriedade ``TipoBandeja``. Ela
fica na pasta *Bandejas e leitos* do pavimento; o modelo 3D, na subpasta 3D
dessa pasta. As conexões (curvas, tês, cruzetas, terminais) e os suportes
saem da rede de bandejas de cada pavimento (``core.bandejas.analisar``).
"""
import math

import Draft
import FreeCAD as App
import Part

from freecad.Circuits.core import bandejas as regras
from freecad.Circuits.services import pavimentos

COR_BANDEJA = (0.45, 0.45, 0.45)
COR_SUPORTE = (0.75, 0.45, 0.10)


def eh_bandeja(obj):
    return hasattr(obj, "Points") and hasattr(obj, "TipoBandeja")


def listar(doc):
    return [obj for obj in doc.Objects if eh_bandeja(obj)]


def _mm(valor):
    return valor.Value if hasattr(valor, "Value") else float(valor)


def _propriedade(obj, tipo, nome, dica, valor):
    if not hasattr(obj, nome):
        obj.addProperty(tipo, nome, "Bandeja", dica)
    setattr(obj, nome, valor)


def marcar(doc, objetos, tipo=regras.TIPO_PADRAO, largura=regras.LARGURA_PADRAO_MM, aba=regras.ABA_PADRAO_MM,
           altura=regras.ALTURA_PADRAO_MM, tampa=False):
    """Marca as linhas como bandejas e as guarda na pasta Bandejas e leitos do pavimento.

    Returns:
        Linhas marcadas.
    """
    linhas = [obj for obj in objetos if hasattr(obj, "Points")]
    for obj in linhas:
        if not hasattr(obj, "TipoBandeja"):
            obj.addProperty("App::PropertyEnumeration", "TipoBandeja", "Bandeja", "Eletrocalha ou leito para cabos")
            obj.TipoBandeja = list(regras.TIPOS)
        obj.TipoBandeja = tipo
        _propriedade(obj, "App::PropertyLength", "Largura", "Largura da bandeja", float(largura))
        _propriedade(obj, "App::PropertyLength", "Aba", "Altura da aba (lateral) da bandeja", float(aba))
        _propriedade(obj, "App::PropertyDistance", "AlturaBandeja", "Do piso à base da bandeja", float(altura))
        _propriedade(obj, "App::PropertyBool", "Tampa", "Bandeja com tampa", bool(tampa))
        if pavimentos.pavimento_do_objeto(doc, obj) is None:
            pavimentos.arquivar(doc, obj)
        try:
            obj.ViewObject.LineColor = COR_BANDEJA
            obj.ViewObject.LineWidth = 3.0
        except Exception:
            pass
    return linhas


def _pontos(obj):
    return [(v.x, v.y) for v in (obj.Placement.multVec(p) for p in obj.Points)]


def _caminho(obj):
    return {
        "pontos": _pontos(obj), "tipo": str(obj.TipoBandeja), "largura": _mm(obj.Largura), "aba": _mm(obj.Aba),
        "altura": _mm(obj.AlturaBandeja), "tampa": bool(getattr(obj, "Tampa", False)), "nome": obj.Name,
    }


def _nome_pavimento(doc, obj):
    pav = pavimentos.pavimento_do_objeto(doc, obj)
    return pav.Label if pav is not None else ""


def analisar(doc):
    """{nome do pavimento: resultado de ``core.bandejas.analisar``}; '' fora de um pavimento."""
    por_pavimento = {}
    for obj in listar(doc):
        try:
            caminho = _caminho(obj)
        except Exception:
            continue
        por_pavimento.setdefault(_nome_pavimento(doc, obj), []).append(caminho)
    return {pav: regras.analisar(caminhos) for pav, caminhos in por_pavimento.items()}


def pe_direito(doc, nome):
    """Altura de piso a piso do pavimento [mm]; 3000 se ele não existir."""
    pav = pavimentos.por_nome(doc, nome) if nome else None
    return pavimentos.altura(pav) if pav is not None else regras.ALTURA_PADRAO_MM + 200.0


def materiais_por_pavimento(doc):
    """[(pavimento, itens de ``core.bandejas.materiais``)] das bandejas, conexões e suportes."""
    return [(pav, regras.materiais(resultado, pe_direito(doc, pav))) for pav, resultado in analisar(doc).items()]


# --- 3D ----------------------------------------------------------------------

def _solido(blocos, x, y, z, angulo):
    """Blocos do sistema local levados para a posição (x, y, z) e girados em Z."""
    rotacao = App.Rotation(App.Vector(0, 0, 1), angulo)
    solidos = []
    for bx, by, bz, comprimento, largura, altura in blocos:
        if comprimento <= 0 or largura <= 0 or altura <= 0:
            continue
        caixa = Part.makeBox(comprimento, largura, altura, App.Vector(bx, by, bz))
        caixa.Placement = App.Placement(App.Vector(x, y, z), rotacao).multiply(caixa.Placement)
        solidos.append(caixa)
    return solidos


def _forma_3d(obj, cota):
    pontos = _pontos(obj)
    largura, aba, tipo = _mm(obj.Largura), _mm(obj.Aba), str(obj.TipoBandeja)
    solidos = []
    for indice, (a, b) in enumerate(zip(pontos, pontos[1:])):
        comprimento = math.hypot(b[0] - a[0], b[1] - a[1])
        if comprimento <= 0:
            continue
        angulo = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        recuo = largura / 2.0 if indice > 0 else 0.0
        avanco = largura / 2.0 if indice < len(pontos) - 2 else 0.0
        blocos = regras.blocos_do_trecho(comprimento, largura, aba, tipo, recuo, avanco)
        solidos += _solido(blocos, a[0], a[1], cota, angulo)
    return Part.makeCompound(solidos)


def _substituir(doc, nome, forma, cor):
    anterior = doc.getObject(nome)
    if anterior is not None:
        doc.removeObject(nome)
    objeto = doc.addObject("Part::Feature", nome)
    objeto.Shape = forma
    try:
        objeto.ViewObject.ShapeColor = cor
    except Exception:
        pass
    return objeto


def _verticais_por_bandeja(doc):
    """{nome da bandeja: trechos verticais dela}, de ``core.bandejas.analisar``."""
    por_nome = {}
    for resultado in analisar(doc).values():
        for vertical in resultado["verticais"]:
            por_nome.setdefault(vertical["nome"], []).append(vertical)
    return por_nome


def gerar_3d(doc, objetos=None):
    """Recria o modelo 3D de cada bandeja, na cota do piso + ``AlturaBandeja``.

    Os trechos verticais (encontro com uma bandeja em outra altura) entram no
    modelo da bandeja que chega ao nó.

    Returns:
        Quantidade de bandejas modeladas.
    """
    feitas = 0
    verticais = _verticais_por_bandeja(doc)
    for obj in (objetos if objetos is not None else listar(doc)):
        if not eh_bandeja(obj):
            continue
        piso = pavimentos.elevacao_do_objeto(doc, obj)
        cota = piso + _mm(obj.AlturaBandeja)
        forma = _forma_3d(obj, cota)
        subidas = []
        for vertical in verticais.get(obj.Name, []):
            blocos = regras.blocos_da_vertical(vertical["largura"], vertical["aba"], vertical["de"], vertical["ate"])
            subidas += _solido(blocos, vertical["x"], vertical["y"], piso, vertical["angulo"])
        if subidas:
            forma = Part.makeCompound([forma] + subidas)
        modelo = _substituir(doc, f"{obj.Name}_3D", forma, COR_BANDEJA)
        modelo.Label = f"{obj.Label} 3D"
        pavimentos.guardar_3d(doc, obj, modelo)
        feitas += 1
    doc.recompute()
    return feitas


# --- conexões na planta ----------------------------------------------------

def _remover_marcados(doc, propriedade):
    for obj in [o for o in doc.Objects if hasattr(o, propriedade)]:
        doc.removeObject(obj.Name)


def _pasta_de(doc, pav_nome):
    pav = pavimentos.por_nome(doc, pav_nome) if pav_nome else None
    return pavimentos.pasta(doc, pav, "bandejas") if pav is not None else None


def anotar_conexoes(doc, resultados=None):
    """Recria os textos das conexões na planta, na pasta das bandejas: um por nó, com as siglas
    das peças dele (C90, C45, T, X, TF, R, CVE, CVI), por exemplo "T + R".

    Returns:
        Quantidade de nós identificados.
    """
    resultados = resultados if resultados is not None else analisar(doc)
    _remover_marcados(doc, "conexao_bandeja")
    total = 0
    for pav, resultado in resultados.items():
        pasta = _pasta_de(doc, pav)
        cota = pavimentos.elevacao(pavimentos.por_nome(doc, pav)) if pasta is not None else 0.0
        largura_no = {}
        for conexao in resultado["conexoes"]:
            posicao_no = (conexao["x"], conexao["y"])
            largura_no[posicao_no] = max(largura_no.get(posicao_no, 0.0), float(conexao["largura"]))
        for (x, y), rotulo in regras.rotulos_por_no(resultado["conexoes"]).items():
            largura = largura_no[(x, y)]
            altura_texto = max(80.0, largura * 0.5)
            posicao = App.Vector(x + largura * 0.6, y + altura_texto * 0.3, cota)
            texto = Draft.make_text([rotulo], placement=App.Placement(posicao, App.Rotation()), height=altura_texto)
            texto.addProperty("App::PropertyString", "conexao_bandeja", "Bandeja", "Peças da bandeja neste ponto")
            texto.conexao_bandeja = rotulo
            if pasta is not None:
                pasta.addObject(texto)
            total += 1
    doc.recompute()
    return total


# --- suportes ----------------------------------------------------------------

def gerar_suportes(doc):
    """Recria os suportes de cada pavimento: traços na planta e o modelo 3D.

    Um objeto 2D (``Suportes <pavimento>``, na pasta Bandejas e leitos) e um 3D
    (na subpasta 3D dela) por pavimento, com a propriedade ``suportes_de``.

    Returns:
        {nome do pavimento: quantidade de suportes}.
    """
    _remover_marcados(doc, "suportes_de")
    contagem = {}
    for pav_nome, resultado in analisar(doc).items():
        suportes = resultado["suportes"]
        if not suportes:
            continue
        pav = pavimentos.por_nome(doc, pav_nome) if pav_nome else None
        cota = pavimentos.elevacao(pav) if pav is not None else 0.0
        laje = pe_direito(doc, pav_nome)
        linhas, solidos = [], []
        for suporte in suportes:
            angulo = math.radians(suporte["angulo"])
            meia = (float(suporte["largura"]) + regras.FOLGA_PERFILADO_MM) / 2.0
            nx, ny = -math.sin(angulo) * meia, math.cos(angulo) * meia
            linhas.append(Part.makeLine(App.Vector(suporte["x"] - nx, suporte["y"] - ny, cota),
                                        App.Vector(suporte["x"] + nx, suporte["y"] + ny, cota)))
            if suporte.get("vertical"):
                continue  # suporte de parede do trecho vertical: só no quantitativo
            blocos = regras.blocos_do_suporte(suporte["largura"], suporte["altura"], laje)
            solidos += _solido(blocos, suporte["x"], suporte["y"], cota, suporte["angulo"])

        sufixo = pav_nome or "sem pavimento"
        planta = _substituir(doc, f"Suportes_{len(contagem)}", Part.makeCompound(linhas), COR_SUPORTE)
        planta.Label = f"Suportes {sufixo}"
        modelo = _substituir(doc, f"Suportes_{len(contagem)}_3D", Part.makeCompound(solidos), COR_SUPORTE)
        modelo.Label = f"Suportes {sufixo} 3D"
        for objeto in (planta, modelo):
            objeto.addProperty("App::PropertyString", "suportes_de", "Bandeja", "Pavimento destes suportes")
            objeto.suportes_de = pav_nome
            objeto.addProperty("App::PropertyInteger", "Quantidade", "Bandeja", "Quantidade de suportes")
            objeto.Quantidade = len(suportes)
        try:
            planta.ViewObject.LineColor = COR_SUPORTE
            planta.ViewObject.LineWidth = 2.0
        except Exception:
            pass
        pasta = _pasta_de(doc, pav_nome)
        if pasta is not None:
            pasta.addObject(planta)
            pavimentos.guardar_3d(doc, planta, modelo)
        contagem[pav_nome] = len(suportes)
    doc.recompute()
    return contagem
