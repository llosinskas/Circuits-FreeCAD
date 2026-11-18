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


def configurar_suportes(
    objetos,
    tipo_suporte=regras.TIPO_SUPORTE_PADRAO,
    vao_suporte=0.0,
    distancia_no=regras.DISTANCIA_SUPORTE_CONEXAO,
    pendente=regras.PENDENTE_PADRAO_MM,
    folga_perfilado=regras.FOLGA_PERFILADO_MM,
):
    """Grava nas bandejas os ajustes de suporte (tipo, vão, distância às conexões, comprimento do pendente e folga)."""
    for obj in objetos:
        if not hasattr(obj, "Points"):
            continue
        if not hasattr(obj, "TipoSuporte"):
            obj.addProperty("App::PropertyEnumeration", "TipoSuporte", "Suportes", "Tipo de suporte da bandeja")
            obj.TipoSuporte = list(regras.TIPOS_SUPORTE)
        obj.TipoSuporte = tipo_suporte if tipo_suporte in regras.TIPOS_SUPORTE else regras.TIPO_SUPORTE_PADRAO
        vao_padrao = regras.VAO_SUPORTE.get(str(getattr(obj, "TipoBandeja", regras.TIPO_PADRAO)), 1500.0)
        _propriedade(obj, "App::PropertyLength", "VaoSuporte", "Espaçamento máximo entre suportes", float(vao_suporte or vao_padrao))
        _propriedade(obj, "App::PropertyLength", "DistanciaConexao", "Distância do suporte às conexões/pontas", float(distancia_no))
        _propriedade(obj, "App::PropertyLength", "ComprimentoPendente", "Comprimento dos pendentes/tirantes (0 = até a laje)", float(pendente))
        _propriedade(obj, "App::PropertyLength", "FolgaPerfilado", "Folga lateral total do perfilado além da largura da bandeja", float(folga_perfilado))


def marcar(doc, objetos, tipo=regras.TIPO_PADRAO, largura=regras.LARGURA_PADRAO_MM, aba=regras.ABA_PADRAO_MM,
           altura=regras.ALTURA_PADRAO_MM, tampa=False):
    """Marca as linhas como bandejas e as guarda na pasta Bandejas e leitos do pavimento.

    Returns:
        Linhas marcadas.
    """
    linhas = [obj for obj in objetos if hasattr(obj, "Points")]
    destino = pavimentos.pavimento_para_insercao(doc) if linhas else None
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
            pavimentos.arquivar(doc, obj, destino)  # mesmo pavimento em que os símbolos entram
        try:
            obj.ViewObject.LineColor = COR_BANDEJA
            obj.ViewObject.LineWidth = 3.0
        except Exception:
            pass
    return linhas


def _pontos(obj):
    return [(v.x, v.y) for v in (obj.Placement.multVec(p) for p in obj.Points)]


def _caminho(obj):
    dados = {
        "pontos": _pontos(obj), "tipo": str(obj.TipoBandeja), "largura": _mm(obj.Largura), "aba": _mm(obj.Aba),
        "altura": _mm(obj.AlturaBandeja), "tampa": bool(getattr(obj, "Tampa", False)), "nome": obj.Name,
    }
    if hasattr(obj, "TipoSuporte") and obj.TipoSuporte:
        dados["tipo_suporte"] = str(obj.TipoSuporte)
    if hasattr(obj, "VaoSuporte") and obj.VaoSuporte is not None:
        dados["vao_suporte"] = _mm(obj.VaoSuporte)
    if hasattr(obj, "DistanciaConexao") and obj.DistanciaConexao is not None:
        dados["distancia_no"] = _mm(obj.DistanciaConexao)
    if hasattr(obj, "ComprimentoPendente") and obj.ComprimentoPendente is not None:
        dados["pendente"] = _mm(obj.ComprimentoPendente)
    if hasattr(obj, "FolgaPerfilado") and obj.FolgaPerfilado is not None:
        dados["folga_perfilado"] = _mm(obj.FolgaPerfilado)
    return dados


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


def materiais_por_pavimento(doc, sem_terminal=None):
    """[(pavimento, itens de ``core.bandejas.materiais``)] das bandejas, conexões e suportes.

    Args:
        sem_terminal: {pavimento: [(x, y)]} das pontas que são prumadas (sem terminal).
    """
    sem_terminal = sem_terminal or {}
    return [(pav, regras.materiais(resultado, pe_direito(doc, pav), sem_terminal=sem_terminal.get(pav, ())))
            for pav, resultado in analisar(doc).items()]


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


def _gravar_pontos(obj, pontos_xy):
    """Grava os vértices (x, y globais) de volta na linha, mantendo a cota."""
    z = obj.Placement.multVec(obj.Points[0]).z if obj.Points else 0.0
    inversa = obj.Placement.inverse()
    obj.Points = [inversa.multVec(App.Vector(x, y, z)) for x, y in pontos_xy]


def encaixar(doc, objetos=None):
    """Junta as pontas soltas das bandejas às vizinhas do mesmo pavimento (``core.bandejas.encaixar``).

    Args:
        objetos: bandejas recém-marcadas; só os pavimentos delas são tratados.
            None trata todos.
    Returns:
        Quantidade de junções feitas.
    """
    por_pavimento = {}
    for obj in listar(doc):
        por_pavimento.setdefault(_nome_pavimento(doc, obj), []).append(obj)
    alvo = {obj.Name for obj in objetos} if objetos is not None else None
    juncoes = 0
    for objs in por_pavimento.values():
        if alvo is not None and not any(obj.Name in alvo for obj in objs):
            continue
        antes = [_pontos(obj) for obj in objs]
        novos, feitas = regras.encaixar(antes)
        for obj, pontos, ajustados in zip(objs, antes, novos):
            if [(float(x), float(y)) for x, y in pontos] != ajustados:
                _gravar_pontos(obj, ajustados)
        juncoes += feitas
    return juncoes


def _cota_do_piso(doc, pav_nome):
    pav = pavimentos.por_nome(doc, pav_nome) if pav_nome else None
    return pavimentos.elevacao(pav) if pav is not None else 0.0


def _setor(cx, cy, z, raio_externo, raio_interno, altura, inicio, varredura):
    """Pedaço de anel (fundo ou aba da curva), de ``inicio`` a ``inicio + varredura`` graus."""
    centro, eixo = App.Vector(cx, cy, z), App.Vector(0, 0, 1)
    solido = Part.makeCylinder(raio_externo, altura, centro, eixo, varredura)
    if raio_interno > 0:
        solido = solido.cut(Part.makeCylinder(raio_interno, altura, centro, eixo, varredura))
    solido.rotate(centro, eixo, inicio)
    return solido


def _curva_3d(conexao, cota):
    """Curva horizontal: fundo e abas em arco, tangentes aos trechos recortados."""
    cx, cy, raio, inicio, varredura = conexao["arco"]
    meia, aba, e = float(conexao["largura"]) / 2, float(conexao["aba"]), regras.ESPESSURA_MM
    return [
        _setor(cx, cy, cota, raio + meia, raio - meia, e, inicio, varredura),
        _setor(cx, cy, cota, raio + meia, raio + meia - e, aba, inicio, varredura),
        _setor(cx, cy, cota, raio - meia + e, raio - meia, aba, inicio, varredura),
    ]


def _derivacao_3d(conexao, cota):
    """Tê ou cruzeta: fundo quadrado na largura da principal e abas nos lados sem derivação."""
    blocos = regras.blocos_da_derivacao(conexao["quadrado"], conexao["aba"])
    return _solido(blocos, conexao["x"], conexao["y"], cota, conexao["quadrado"]["angulo"])


def _reducao_3d(conexao, cota):
    """Redução: fundo em trapézio e abas inclinadas, de ``core.bandejas.faces_da_reducao``."""
    trapezio = conexao["trapezio"]
    giro = App.Rotation(App.Vector(0, 0, 1), trapezio["angulo"])
    origem = App.Vector(trapezio["x"], trapezio["y"], cota)
    solidos = []
    for face in regras.faces_da_reducao(trapezio):
        pontos = [origem + giro.multVec(App.Vector(*p)) for p in face["pontos"]]
        poligono = Part.makePolygon(pontos + pontos[:1])
        solidos.append(Part.Face(poligono).extrude(giro.multVec(App.Vector(*face["espessura"]))))
    return solidos


def gerar_3d(doc, objetos=None):
    """Recria o modelo 3D das bandejas e das peças, na cota do piso + ``AlturaBandeja``.

    Cada bandeja vira ``<nome>_3D`` com os trechos retos já recortados nos nós,
    e os trechos verticais que chegam nela. As curvas (em arco), as reduções,
    os tês e as cruzetas de cada pavimento ficam num objeto só, com a propriedade
    ``conexoes_3d_de``, recriado a cada uso.

    Returns:
        Quantidade de bandejas modeladas.
    """
    resultados = analisar(doc)
    trechos, verticais = {}, {}
    for resultado in resultados.values():
        for trecho in resultado["trechos"]:
            trechos.setdefault(trecho["nome"], []).append(trecho)
        for vertical in resultado["verticais"]:
            verticais.setdefault(vertical["nome"], []).append(vertical)

    feitas = 0
    for obj in (objetos if objetos is not None else listar(doc)):
        if not eh_bandeja(obj):
            continue
        piso = pavimentos.elevacao_do_objeto(doc, obj)
        cota = piso + _mm(obj.AlturaBandeja)
        largura, aba, tipo = _mm(obj.Largura), _mm(obj.Aba), str(obj.TipoBandeja)
        solidos = []
        for trecho in trechos.get(obj.Name, []):
            util = trecho["comprimento"] - trecho["recuo_inicio"] - trecho["recuo_fim"]
            if util <= 0:
                continue
            ux = (trecho["x2"] - trecho["x1"]) / trecho["comprimento"]
            uy = (trecho["y2"] - trecho["y1"]) / trecho["comprimento"]
            angulo = math.degrees(math.atan2(uy, ux))
            blocos = regras.blocos_do_trecho(util, largura, aba, tipo)
            solidos += _solido(blocos, trecho["x1"] + ux * trecho["recuo_inicio"],
                               trecho["y1"] + uy * trecho["recuo_inicio"], cota, angulo)
        for vertical in verticais.get(obj.Name, []):
            blocos = regras.blocos_da_vertical(vertical["largura"], vertical["aba"], vertical["de"], vertical["ate"])
            solidos += _solido(blocos, vertical["x"], vertical["y"], piso, vertical["angulo"])
        modelo = _substituir(doc, f"{obj.Name}_3D", Part.makeCompound(solidos), COR_BANDEJA)
        modelo.Label = f"{obj.Label} 3D"
        pavimentos.guardar_3d(doc, obj, modelo)
        feitas += 1

    _remover_marcados(doc, "conexoes_3d_de")
    por_pavimento = {}
    for obj in listar(doc):
        por_pavimento.setdefault(_nome_pavimento(doc, obj), obj)
    for indice, (pav_nome, resultado) in enumerate(resultados.items()):
        piso = _cota_do_piso(doc, pav_nome)
        solidos = []
        for conexao in resultado["conexoes"]:
            cota = piso + float(conexao["altura"] or 0)
            if "trapezio" in conexao:
                solidos += _reducao_3d(conexao, cota)
            if "arco" in conexao:
                solidos += _curva_3d(conexao, cota)
            elif "quadrado" in conexao:
                solidos += _derivacao_3d(conexao, cota)
        if not solidos:
            continue
        pecas_3d = _substituir(doc, f"Conexoes_bandejas_{indice}", Part.makeCompound(solidos), COR_BANDEJA)
        pecas_3d.Label = f"Conexões {pav_nome or 'sem pavimento'} 3D"
        pecas_3d.addProperty("App::PropertyString", "conexoes_3d_de", "Bandeja", "Pavimento destas curvas e tês")
        pecas_3d.conexoes_3d_de = pav_nome
        if pav_nome in por_pavimento:
            pavimentos.guardar_3d(doc, por_pavimento[pav_nome], pecas_3d)
    doc.recompute()
    return feitas


def desenhar_contorno(doc):
    """Recria, por pavimento, a bandeja em linha dupla na planta (``core.bandejas.contorno_2d``).

    O contorno fica no piso do pavimento, na pasta Bandejas e leitos, com a
    propriedade ``contorno_bandejas_de``.

    Returns:
        Quantidade de contornos desenhados.
    """
    _remover_marcados(doc, "contorno_bandejas_de")
    feitos = 0
    for indice, (pav_nome, resultado) in enumerate(analisar(doc).items()):
        z = _cota_do_piso(doc, pav_nome)
        contorno = regras.contorno_2d(resultado)
        arestas = [Part.makeLine(App.Vector(x1, y1, z), App.Vector(x2, y2, z))
                   for x1, y1, x2, y2 in contorno["linhas"]]
        for cx, cy, raio, inicio, varredura in contorno["arcos"]:
            circulo = Part.Circle(App.Vector(cx, cy, z), App.Vector(0, 0, 1), raio)
            arco = Part.ArcOfCircle(circulo, math.radians(inicio), math.radians(inicio + varredura))
            arestas.append(arco.toShape())
        if not arestas:
            continue
        desenho = _substituir(doc, f"Contorno_bandejas_{indice}", Part.makeCompound(arestas), COR_BANDEJA)
        desenho.Label = f"Contorno bandejas {pav_nome or 'sem pavimento'}"
        desenho.addProperty("App::PropertyString", "contorno_bandejas_de", "Bandeja", "Pavimento deste contorno")
        desenho.contorno_bandejas_de = pav_nome
        try:
            desenho.ViewObject.LineColor = COR_BANDEJA
        except Exception:
            pass
        pasta = _pasta_de(doc, pav_nome)
        if pasta is not None:
            pasta.addObject(desenho)
        feitos += 1
    doc.recompute()
    return feitos


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
            folga = float(suporte["folga_perfilado"]) if suporte.get("folga_perfilado") is not None else regras.FOLGA_PERFILADO_MM
            meia = (float(suporte["largura"]) + folga) / 2.0
            nx, ny = -math.sin(angulo) * meia, math.cos(angulo) * meia
            linhas.append(Part.makeLine(App.Vector(suporte["x"] - nx, suporte["y"] - ny, cota),
                                        App.Vector(suporte["x"] + nx, suporte["y"] + ny, cota)))
            if suporte.get("vertical"):
                continue  # suporte de parede do trecho vertical: só no quantitativo
            blocos = regras.blocos_do_suporte(
                suporte["largura"],
                suporte["altura"],
                laje,
                pendente_mm=suporte.get("pendente", 0.0),
                folga_perfilado_mm=folga,
                tipo_suporte=suporte.get("tipo_suporte", regras.TIPO_SUPORTE_PADRAO),
            )
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
