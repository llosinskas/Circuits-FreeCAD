"""Centro de medição Enel SP no documento: planilha, colunas de medição e busway (``core.centro_medicao``).

- **Planilha "Centro de medição"** (propriedade ``centro_medicao``): um pavimento por
  linha (A a E), os preços de referência nas colunas G a I, o resultado nas K e L e
  os parâmetros do último cálculo nas N e O (usados pelo botão Busway).
- **Coluna de medição**: um ``App::Part`` (propriedade ``coluna_medicao``) com os
  agrupamentos de caixas P e a CDPM em 3D, lado a lado, na pasta *Busway e medição*
  do pavimento; o comando posiciona com o mouse.
- **Busway**: as linhas desenhadas do QDC ao shaft são marcadas como busway
  (``CorrenteBusway``, ``AlturaBusway``, ``KBusway``) e, do fim de cada uma, sobe a
  prumada: um Draft Wire vertical marcado do mesmo jeito, o 3D (invólucro, plug-ins,
  caixas MEC) e um texto por andar atendido, tudo na pasta *Busway e medição*.
"""
import math

import Draft
import FreeCAD as App
import Part
import Spreadsheet  # noqa: F401  (registra o tipo Spreadsheet::Sheet)

from freecad.Circuits.core import centro_medicao as regras
from freecad.Circuits.services import pavimentos, planilhas

COLUNA_PARAMETRO, COLUNA_PARAMETRO_VALOR = "N", "O"
COR_P, COR_CDPM, COR_BUSWAY, COR_MEC = (0.85, 0.92, 1.0), (0.75, 0.75, 0.78), (0.95, 0.75, 0.3), (0.7, 0.8, 0.95)


def _tipo(obj):
    return getattr(getattr(obj, "Proxy", None), "Type", "")


def planilha(doc):
    """A planilha do centro de medição do documento, ou None."""
    return next((obj for obj in doc.Objects if hasattr(obj, "centro_medicao")), None)


def _texto(folha, celula):
    try:
        conteudo = folha.getContents(celula)
    except Exception:
        return ""
    return str(conteudo or "").lstrip("'=").strip()


def criar(doc):
    """Cria a planilha com os pavimentos do projeto e os preços de referência.

    Returns:
        (planilha, quantidade de pavimentos do projeto usados).
    """
    folha = doc.addObject("Spreadsheet::Sheet", "Centro_medicao")
    folha.Label = "Centro de medição"
    folha.addProperty("App::PropertyString", "centro_medicao", "Medição", "Dados do centro de medição (Enel SP)")
    folha.centro_medicao = "1"
    folha.set("A1", f"'{regras.AJUDA}")
    for coluna, _, titulo in regras.COLUNAS:
        folha.set(f"{coluna}{regras.LINHA_TITULOS}", f"'{titulo}")
    projeto = [(p.Label, pavimentos.elevacao(p) / 1000.0) for p in pavimentos.listar(doc)]
    for linha, dados in enumerate(regras.linhas_dos_pavimentos(projeto), start=regras.PRIMEIRA_LINHA):
        folha.set(f"A{linha}", f"'{dados['nome']}")
        folha.set(f"B{linha}", f"'{str(dados['cota']).replace('.', ',')}")
        folha.set(f"C{linha}", f"'{dados['unidades']}")
        folha.set(f"D{linha}", f"'{str(regras.DEMANDA_PADRAO).replace('.', ',')}")
        folha.set(f"E{linha}", f"'{regras.FASES_PADRAO}")
    folha.set(f"{regras.COLUNA_PRECO_CHAVE}{regras.LINHA_TITULOS}", "'Chave")
    folha.set(f"{regras.COLUNA_PRECO_ROTULO}{regras.LINHA_TITULOS}", "'Item")
    folha.set(f"{regras.COLUNA_PRECO_VALOR}{regras.LINHA_TITULOS}", "'Preço [R$]")
    for linha, (chave, (rotulo, valor)) in enumerate(regras.PRECOS.items(), start=regras.PRIMEIRA_LINHA):
        folha.set(f"{regras.COLUNA_PRECO_CHAVE}{linha}", f"'{chave}")
        folha.set(f"{regras.COLUNA_PRECO_ROTULO}{linha}", f"'{rotulo}")
        folha.set(f"{regras.COLUNA_PRECO_VALOR}{linha}", f"'{str(valor).replace('.', ',')}")
    try:
        folha.setColumnWidth("A", 150)
        folha.setColumnWidth("H", 320)
    except Exception:
        pass
    doc.recompute()
    return folha, len(projeto)


def ler_andares(folha):
    """Andares da planilha (``core.centro_medicao.andar``), sem as linhas em branco.

    Raises:
        ValueError: com o número da linha, se um valor for inválido.
    """
    andares = []
    for linha in range(regras.PRIMEIRA_LINHA, planilhas.ultima_linha(folha) + 1):
        celulas = {chave: _texto(folha, f"{coluna}{linha}") for coluna, chave, _ in regras.COLUNAS}
        if not celulas["nome"] and not celulas["unidades"]:
            continue
        try:
            andares.append(regras.andar_da_linha(celulas))
        except ValueError as erro:
            raise ValueError(f"Planilha {folha.Label}, linha {linha}: {erro}") from erro
    return andares


def ler_precos(folha):
    """{chave: preço} das colunas G e I; as chaves que faltam ficam com o preço de referência."""
    precos = regras.precos_padrao()
    for linha in range(regras.PRIMEIRA_LINHA, planilhas.ultima_linha(folha) + 1):
        chave = _texto(folha, f"{regras.COLUNA_PRECO_CHAVE}{linha}")
        if chave:
            try:
                precos[chave] = float(_texto(folha, f"{regras.COLUNA_PRECO_VALOR}{linha}").replace(",", "."))
            except ValueError:
                pass
    return precos


def gravar_resultado(folha, resultado, parametros):
    """Grava o resumo nas colunas K e L e os parâmetros usados nas N e O."""
    folha.set(f"{regras.COLUNA_RESULTADO_ROTULO}{regras.LINHA_TITULOS}", "'Resultado")
    for linha, (rotulo, valor) in enumerate(regras.resumo(resultado), start=regras.PRIMEIRA_LINHA):
        folha.set(f"{regras.COLUNA_RESULTADO_ROTULO}{linha}", f"'{rotulo}")
        folha.set(f"{regras.COLUNA_RESULTADO_VALOR}{linha}", f"'{valor}")
    folha.set(f"{COLUNA_PARAMETRO}{regras.LINHA_TITULOS}", "'Parâmetro")
    for linha, (chave, valor) in enumerate(sorted(parametros.items()), start=regras.PRIMEIRA_LINHA):
        folha.set(f"{COLUNA_PARAMETRO}{linha}", f"'{chave}")
        folha.set(f"{COLUNA_PARAMETRO_VALOR}{linha}", f"'{valor}")
    folha.Document.recompute()


def ler_parametros(folha):
    """Parâmetros do último cálculo {chave: float}; vazio se ainda não foi calculado."""
    parametros = {}
    for linha in range(regras.PRIMEIRA_LINHA, planilhas.ultima_linha(folha) + 1):
        chave = _texto(folha, f"{COLUNA_PARAMETRO}{linha}")
        if chave:
            try:
                parametros[chave] = float(_texto(folha, f"{COLUNA_PARAMETRO_VALOR}{linha}").replace(",", "."))
            except ValueError:
                continue
    return parametros


# --- coluna de medição ----------------------------------------------------------------------------

def _caixa(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, App.Vector(x, y, z))


def inserir_colunas(doc, grupos, pavimento=None):
    """Os agrupamentos (``core.centro_medicao.agrupamentos``) lado a lado, num ``App::Part``.

    A origem do Part é o meio da frente do conjunto, no piso; o fundo fica para +y (parede).
    """
    total = sum(g["caixas"] for g in grupos)
    parte = doc.addObject("App::Part", "Colunas_medicao")
    parte.Label = f"Colunas de medição ({total} caixas P)"
    parte.addProperty("App::PropertyInteger", "coluna_medicao", "Medição", "Caixas de medição tipo P")
    parte.coluna_medicao = total
    larguras = [regras.coluna_de_medicao(g["caixas"], g["cdpm"])["largura"] for g in grupos]
    x = -(sum(larguras) + regras.FOLGA_ENTRE_AGRUPAMENTOS_MM * (len(grupos) - 1)) / 2.0
    for numero, (grupo, largura) in enumerate(zip(grupos, larguras), start=1):
        dados = regras.coluna_de_medicao(grupo["caixas"], grupo["cdpm"])
        meio = x + largura / 2.0 - (min(p[1][0] for p in dados["caixas"]) + largura / 2.0)
        for rotulo, (px, py, pz), (dx, dy, dz) in dados["caixas"]:
            corpo = doc.addObject("Part::Feature", "CDPM" if rotulo == "CDPM" else "Caixa_P")
            corpo.Label = f"A{numero} {rotulo}"
            corpo.Shape = _caixa(meio + px, py, pz, dx, dy, dz)
            try:
                corpo.ViewObject.ShapeColor = COR_CDPM if rotulo == "CDPM" else COR_P
                corpo.ViewObject.Transparency = 0 if rotulo == "CDPM" else 40
            except Exception:
                pass
            parte.addObject(corpo)
        x += largura + regras.FOLGA_ENTRE_AGRUPAMENTOS_MM
    if pavimento is not None:
        pavimentos.pasta(doc, pavimento, "busway").addObject(parte)
        posicao = parte.Placement
        posicao.Base = App.Vector(0, 0, pavimentos.elevacao(pavimento))
        parte.Placement = posicao
    doc.recompute()
    return parte


# --- busway ---------------------------------------------------------------------------------------

def eh_busway(obj):
    return hasattr(obj, "CorrenteBusway")


def linhas_desenhadas(objetos):
    """Linhas do Draft (Wire) da seleção que servem de trecho horizontal de busway."""
    return [o for o in objetos if hasattr(o, "Points") and len(getattr(o, "Points", [])) >= 2
            and _tipo(o) != "ConduitPath"]


def _propriedade(obj, tipo, nome, dica, valor):
    if not hasattr(obj, nome):
        obj.addProperty(tipo, nome, "Busway", dica)
    setattr(obj, nome, valor)


def marcar(obj, nominal, altura_mm=None, k=None):
    """Marca a linha como busway (corrente nominal [A], altura da base ao piso [mm], k)."""
    _propriedade(obj, "App::PropertyInteger", "CorrenteBusway", "Corrente nominal do busway [A]", int(nominal))
    if altura_mm is not None:
        _propriedade(obj, "App::PropertyLength", "AlturaBusway", "Do piso à base do busway [mm]", float(altura_mm))
    _propriedade(obj, "App::PropertyFloat", "KBusway", "Fator de queda k [V/(100 m·A)] (Enel, Tabela 42)",
                 float(k if k is not None else regras.K_BUSWAY.get(int(nominal), 0.0)))
    try:
        obj.ViewObject.LineColor = COR_BUSWAY
        obj.ViewObject.LineWidth = 4.0
    except Exception:
        pass


def _pontos(linha):
    return [linha.Placement.multVec(p) for p in linha.Points]


def _bloco_no_segmento(a, b, largura, altura, z):
    """Caixa de seção largura × altura ao longo do segmento a-b (no plano), com a base em z."""
    dx, dy = b.x - a.x, b.y - a.y
    comprimento = math.hypot(dx, dy)
    if comprimento < 1e-6:
        return None
    caixa = Part.makeBox(comprimento, largura, altura, App.Vector(0, -largura / 2.0, 0))
    caixa.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), math.degrees(math.atan2(dy, dx)))
    caixa.translate(App.Vector(a.x, a.y, z))
    return caixa


def _remover_prumada(doc, linha):
    for obj in list(doc.Objects):
        if getattr(obj, "prumada_busway_de", "") == linha.Name:
            doc.removeObject(obj.Name)


def _cota_absoluta(doc, andar, base_mm):
    pavimento = pavimentos.por_nome(doc, andar["nome"])
    return pavimentos.elevacao(pavimento) if pavimento is not None else base_mm + andar["cota"] * 1000.0


def criar_prumada(doc, linha, dados_linha, andares_mec, base_pavimento, topo_mm):
    """Prumada do busway no fim da ``linha`` horizontal: trecho vertical, 3D e textos por andar.

    Args:
        dados_linha: uma das ``linhas`` de ``core.centro_medicao.busway`` (nominal, k, andares).
        andares_mec: ``andares`` do mesmo resultado (caixas MEC de cada andar).
        topo_mm: cota absoluta do fim da prumada [mm].
    Returns:
        (trecho vertical, objeto 3D, textos).
    """
    _remover_prumada(doc, linha)
    nominal = dados_linha["nominal"]
    marcar(linha, nominal, getattr(linha, "AlturaBusway", None) or 2500.0, dados_linha["k"])
    base = pavimentos.elevacao(base_pavimento) if base_pavimento is not None else 0.0
    altura = float(getattr(getattr(linha, "AlturaBusway", 2500.0), "Value", getattr(linha, "AlturaBusway", 2500.0)))
    pontos = _pontos(linha)
    fim, anterior = pontos[-1], pontos[-2]
    largura, profundidade = regras.secao_busway(nominal)
    atendidos = set(dados_linha["andares"])
    cotas = {a["andar"]: _cota_absoluta(doc, {"nome": a["andar"], "cota": a["cota"]}, base) for a in andares_mec}
    ultimo = max(cotas[n] for n in atendidos)
    topo = topo_mm if dados_linha is not None and max(cotas.values()) == ultimo else ultimo + 2000.0

    vertical = Draft.make_wire([App.Vector(fim.x, fim.y, base + altura), App.Vector(fim.x, fim.y, topo)])
    vertical.Label = f"Prumada busway {nominal} A"
    marcar(vertical, nominal, None, dados_linha["k"])
    _propriedade(vertical, "App::PropertyString", "prumada_busway_de", "Trecho horizontal que alimenta a prumada",
                 linha.Name)

    solidos = []
    for a, b in zip(pontos, pontos[1:]):
        bloco = _bloco_no_segmento(a, b, largura, profundidade, base + altura)
        if bloco is not None:
            solidos.append(bloco)
    solidos.append(Part.makeBox(largura, profundidade, topo - base - altura,
                                App.Vector(fim.x - largura / 2.0, fim.y - profundidade / 2.0, base + altura)))
    ux, uy = fim.x - anterior.x, fim.y - anterior.y
    norma = math.hypot(ux, uy) or 1.0
    nx, ny = -uy / norma, ux / norma  # as caixas ficam à esquerda do sentido do trecho horizontal
    textos = []
    for andar in andares_mec:
        if andar["andar"] not in atendidos:
            continue
        cota = cotas[andar["andar"]]
        deslocamento = profundidade / 2.0 + 50.0
        for i, caixa in enumerate(andar["caixas"]):
            _, _, lx, ly, lz = regras.MEC[caixa["tipo"]]
            cx = fim.x + nx * (deslocamento + ly / 2.0) + (i - (len(andar["caixas"]) - 1) / 2.0) * (lx + 100.0) * ny
            cy = fim.y + ny * (deslocamento + ly / 2.0) - (i - (len(andar["caixas"]) - 1) / 2.0) * (lx + 100.0) * nx
            mec = Part.makeBox(lx, ly, lz, App.Vector(-lx / 2.0, -ly / 2.0, 0))
            mec.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), math.degrees(math.atan2(ny, nx)) - 90.0)
            mec.translate(App.Vector(cx, cy, cota + regras.ALTURA_MEC_MM))
            solidos.append(mec)
            plug = Part.makeBox(200.0, 150.0, 300.0, App.Vector(fim.x - 100.0, fim.y - 75.0,
                                                                cota + regras.ALTURA_DERIVACAO_MM + i * 350.0))
            solidos.append(plug)
        resumo = " + ".join(f"{c['tipo']} ({c['medicoes']})" for c in andar["caixas"])
        texto = Draft.make_text([f"BW {nominal} A", resumo],
                                App.Vector(fim.x + nx * 600.0, fim.y + ny * 600.0, cota))
        _propriedade(texto, "App::PropertyString", "prumada_busway_de", "Trecho horizontal que alimenta a prumada",
                     linha.Name)
        pavimento = pavimentos.por_nome(doc, andar["andar"])
        if pavimento is not None:
            pavimentos.pasta(doc, pavimento, "busway").addObject(texto)
        textos.append(texto)

    corpo = doc.addObject("Part::Feature", "Busway_3D")
    corpo.Label = f"Busway {nominal} A 3D"
    corpo.Shape = Part.makeCompound(solidos)
    _propriedade(corpo, "App::PropertyString", "prumada_busway_de", "Trecho horizontal que alimenta a prumada",
                 linha.Name)
    try:
        corpo.ViewObject.ShapeColor = COR_BUSWAY
    except Exception:
        pass
    if base_pavimento is not None:
        pavimentos.arquivar(doc, linha, base_pavimento)
        pasta = pavimentos.pasta(doc, base_pavimento, "busway")
        pasta.addObject(vertical)
        pasta.addObject(corpo)
    doc.recompute()
    return vertical, corpo, textos
