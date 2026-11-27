"""Folhas de desenho no TechDraw: carimbo, vistas da planta e dos detalhes, cortes e arrumação.

Cada folha é uma ``TechDraw::DrawPage`` com a propriedade ``folha_circuits`` (formato) e o
modelo SVG de ``core.folhas.modelo_svg`` (carimbo NBR com campos editáveis).

As vistas 2D (planta de um pavimento, diagramas, legenda, notas, detalhes das verticais,
qualquer grupo ou objeto) são ``TechDraw::DrawViewSymbol`` com o SVG do
``Draft.get_svg`` de cada objeto 2D, como faz o DrawViewDraft, mas sem as subpastas 3D.
O desenho fica guardado na vista: ``atualizar`` refaz o SVG a partir do modelo,
mantendo o lugar. Cada vista guarda em ``vista_circuits`` (JSON) o que mostra.

O corte é uma ``TechDraw::DrawViewSection`` do modelo 3D, feita a partir de uma linha
desenhada na planta; a vista de cima do 3D, base dos cortes, fica escondida na folha.
O detalhe é a planta recortada por um círculo (ou outra forma fechada) desenhado nela,
numa escala maior.
"""
import datetime
import json
import os
import re

import Draft
import FreeCAD as App

from freecad.Circuits.core import folhas as regras
from freecad.Circuits.services import parametros as servico_parametros
from freecad.Circuits.services import pavimentos

MARCA_FOLHA = "folha_circuits"
MARCA_VISTA = "vista_circuits"
MARCA_TITULO = "titulo_de"
MARCA_BASE = "base_dos_cortes"
MARCA_CORTE = "linha_de_corte"
MARCA_DETALHE = "regiao_de_detalhe"
MARCA_MARCA = "marca_de_folha"  # setas e letras dos cortes e detalhes na planta
ALTURA_TEXTO_TITULO = 3.5  # mm na folha
ESCALA_BASE_CORTES = 1e-5  # a vista de cima, base dos cortes, vira um ponto no canto da folha
CAMPOS_COPIADOS = ("Obra", "Cliente", "Desenho", "Responsavel", "Registro", "Revisao")
MARCAS_3D = ("pasta_3d", "descida_3d", "saida_3d", "prumada_3d", "conexoes_3d_de")


# --- folhas e carimbo ---------------------------------------------------------------------------

def _mm(valor):
    """Número em mm de uma propriedade de comprimento (X e Y das vistas são grandezas)."""
    return float(getattr(valor, "Value", valor))


def listar_folhas(doc):
    return [obj for obj in doc.Objects if hasattr(obj, MARCA_FOLHA)]


def _folha_de(obj):
    if hasattr(obj, MARCA_FOLHA):
        return obj
    return next((pai for pai in getattr(obj, "InList", []) if hasattr(pai, MARCA_FOLHA)), None)


def folha_ativa(doc, selecao=()):
    """Folha selecionada (ou a da vista selecionada); senão a última criada; None sem folhas."""
    for obj in selecao:
        folha = _folha_de(obj)
        if folha is not None:
            return folha
    folhas = listar_folhas(doc)
    return folhas[-1] if folhas else None


def caminho_modelo(formato):
    """Grava (se mudou) e devolve o modelo SVG do formato na pasta de dados do usuário."""
    pasta = os.path.join(App.getUserAppDataDir(), "Circuits", "Folhas")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"Circuits_{formato}.svg")
    conteudo = regras.modelo_svg(formato)
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            igual = arquivo.read() == conteudo
    except OSError:
        igual = False
    if not igual:
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(conteudo)
    return caminho


def textos_do_carimbo(folha):
    try:
        return dict(folha.Template.EditableTexts)
    except Exception:
        return {}


def preencher(folha, valores):
    """Grava os valores nos campos do carimbo que existem no modelo."""
    textos = textos_do_carimbo(folha)
    if not textos:
        return
    for chave, valor in valores.items():
        if chave in textos:
            textos[chave] = str(valor)
    folha.Template.EditableTexts = textos


def valores_iniciais(doc, titulo):
    """Carimbo da folha nova: projeto e data do documento; obra, cliente e responsável da última folha."""
    valores = {"Projeto": doc.Label, "Titulo": titulo, "Data": datetime.date.today().strftime("%d/%m/%Y"),
               "Revisao": "00", "Desenho": getattr(doc, "CreatedBy", "") or ""}
    anteriores = listar_folhas(doc)
    if anteriores:
        textos = textos_do_carimbo(anteriores[-1])
        valores.update({chave: textos[chave] for chave in CAMPOS_COPIADOS if textos.get(chave, "").strip()})
    return valores


ATUALIZANDO_CARIMBOS = False  # o observador ignora as mudanças feitas por ``atualizar_carimbos``


def _garantir_propriedades(folha):
    """Propriedades do carimbo próprias da folha (título, data, revisão), grupo "Carimbo".

    Nas folhas antigas, nascem com o que estava escrito no carimbo.
    """
    textos = textos_do_carimbo(folha)
    for campo, prop in regras.CARIMBO_DA_FOLHA.items():
        if hasattr(folha, prop):
            continue
        dicas = {"CarimboTitulo": "Conteúdo da folha no carimbo", "CarimboData": "Data no carimbo",
                 "CarimboRevisao": "Revisão no carimbo"}
        folha.addProperty("App::PropertyString", prop, "Carimbo", dicas[prop])
        setattr(folha, prop, textos.get(campo, ""))


def _levar_carimbos_antigos_ao_projeto(doc, folhas):
    """Projetos de antes do carimbo paramétrico: o que estava escrito nos carimbos (obra, cliente...)
    vira o parâmetro do projeto, se ele estiver em branco."""
    atuais = servico_parametros.textos(doc)
    novos = {}
    for folha in reversed(folhas):  # vale a última folha, como fazia a cópia para a folha nova
        textos = textos_do_carimbo(folha)
        for campo, chave in regras.CARIMBO_DO_PROJETO.items():
            valor = textos.get(campo, "").strip()
            if campo == "Projeto" and valor == doc.Label:
                continue
            if valor and not atuais.get(chave, "").strip() and chave not in novos:
                novos[chave] = valor
    if novos:
        servico_parametros.gravar(doc, novos)


def atualizar_carimbos(doc, folhas=None):
    """Reescreve o carimbo de todas as folhas a partir das fontes (carimbo paramétrico):

    - projeto, obra, cliente, desenho, responsável e registro: da planilha *Parâmetros do projeto*
      (``core.folhas.CARIMBO_DO_PROJETO``); o projeto em branco é o nome do documento;
    - conteúdo, data e revisão: das propriedades ``CarimboTitulo``, ``CarimboData`` e
      ``CarimboRevisao`` de cada folha;
    - folha: 01/03, 02/03... na ordem de criação; a escala continua com ``organizar``.

    Só grava o que mudou. Returns: quantas folhas mudaram.
    """
    global ATUALIZANDO_CARIMBOS
    todas = listar_folhas(doc)
    if not todas:
        return 0
    ATUALIZANDO_CARIMBOS = True
    try:
        servico_parametros.completar(doc)
        for folha in todas:
            _garantir_propriedades(folha)
        _levar_carimbos_antigos_ao_projeto(doc, todas)
        parametros = servico_parametros.textos(doc)
        mudaram = 0
        for numero, folha in enumerate(todas, start=1):
            if folhas is not None and folha not in folhas:
                continue
            dados = {prop: getattr(folha, prop, "") for prop in regras.CARIMBO_DA_FOLHA.values()}
            valores = regras.valores_do_carimbo(parametros, doc.Label, dados, numero, len(todas))
            textos = textos_do_carimbo(folha)
            if textos and any(textos.get(campo) != valor for campo, valor in valores.items() if campo in textos):
                preencher(folha, valores)
                mudaram += 1
        return mudaram
    finally:
        ATUALIZANDO_CARIMBOS = False


def sincronizar_do_carimbo(doc, folha):
    """O usuário editou o carimbo na folha (dois cliques no campo): leva o texto para a fonte
    (parâmetro do projeto ou propriedade da folha) e atualiza todas as folhas.

    Returns:
        ({chave do parâmetro: texto}, {propriedade: texto}) do que voltou para as fontes.
    """
    global ATUALIZANDO_CARIMBOS
    todas = listar_folhas(doc)
    if folha not in todas:
        return {}, {}
    _garantir_propriedades(folha)
    numero = todas.index(folha) + 1
    dados = {prop: getattr(folha, prop, "") for prop in regras.CARIMBO_DA_FOLHA.values()}
    calculados = regras.valores_do_carimbo(servico_parametros.textos(doc), doc.Label, dados, numero, len(todas))
    no_projeto, na_folha = regras.mudancas_no_carimbo(textos_do_carimbo(folha), calculados, doc.Label)
    ATUALIZANDO_CARIMBOS = True
    try:
        if no_projeto:
            servico_parametros.gravar(doc, no_projeto)
        for prop, valor in na_folha.items():
            setattr(folha, prop, valor)
    finally:
        ATUALIZANDO_CARIMBOS = False
    atualizar_carimbos(doc)
    return no_projeto, na_folha


def renumerar(doc):
    """Escreve 01/03, 02/03... no campo Folha de cada folha (e o resto do carimbo, pelas fontes)."""
    atualizar_carimbos(doc)


def nova_folha(doc, formato=regras.FORMATO_PADRAO, titulo="Planta baixa"):
    """Cria a folha com o carimbo da bancada e a numeração de todas as folhas."""
    try:
        import TechDraw  # noqa: F401  (registra os tipos TechDraw::)
    except ImportError:
        pass
    valores = valores_iniciais(doc, titulo)  # antes de criar: copia da última folha, não desta
    folha = doc.addObject("TechDraw::DrawPage", "Folha")
    modelo = doc.addObject("TechDraw::DrawSVGTemplate", "Carimbo")
    modelo.Template = caminho_modelo(formato)
    folha.Template = modelo
    folha.addProperty("App::PropertyString", MARCA_FOLHA, "Circuits", "Formato da folha da bancada")
    setattr(folha, MARCA_FOLHA, formato)
    folha.Label = f"Folha {len(listar_folhas(doc)):02d} - {titulo}"
    preencher(folha, valores)  # o que veio da folha anterior vai para os parâmetros, se faltar lá
    _garantir_propriedades(folha)
    renumerar(doc)
    doc.recompute()
    return folha


# --- conteúdo 2D --------------------------------------------------------------------------------

def _visivel(obj):
    try:
        return bool(obj.ViewObject.Visibility)
    except Exception:
        return True


def _eh_grupo(obj):
    """Pastas, grupos, App::Part e níveis do BIM: o conteúdo entra, o objeto não."""
    return hasattr(obj, "Group")


def _eh_3d_da_bancada(obj):
    return any(hasattr(obj, marca) for marca in MARCAS_3D) or obj.Name.endswith("_3D")


def objetos_2d(fontes):
    """Objetos desenháveis dentro das fontes (grupos abertos recursivamente), sem as subpastas 3D,
    os objetos 3D da bancada, as folhas e os escondidos."""
    vistos, resultado = set(), []

    def visitar(obj):
        if obj is None or obj.Name in vistos:
            return
        vistos.add(obj.Name)
        if obj.TypeId.startswith("TechDraw::") or _eh_3d_da_bancada(obj):
            return
        if _eh_grupo(obj):
            for filho in getattr(obj, "Group", []):
                visitar(filho)
            return
        if _visivel(obj):
            resultado.append(obj)

    for fonte in fontes:
        visitar(fonte)
    return resultado


def _get_svg():
    return getattr(Draft, "get_svg", None) or getattr(Draft, "getSVG")


def svg_do_objeto(obj, fator):
    """Corpo SVG do objeto visto de cima, em mm do modelo (``Draft.get_svg`` do TechDraw)."""
    try:
        return _get_svg()(obj, scale=fator, linewidth=0.35, direction=App.Vector(0, 0, 1), techdraw=True) or ""
    except Exception as erro:
        App.Console.PrintWarning(f"{obj.Label} ficou fora da folha: {erro}\n")
        return ""


def conteudo(doc, info, fator):
    """(SVG completo, limites do desenho no modelo) da vista 2D descrita em ``info``."""
    objetos = objetos_2d([doc.getObject(n) for n in info["fontes"]])
    corpos = [svg_do_objeto(obj, fator) for obj in objetos]
    return regras.montar_simbolo(corpos), regras.limites_do_svg("".join(corpos))


def _info(vista):
    try:
        return json.loads(getattr(vista, MARCA_VISTA))
    except Exception:
        return {}


def _gravar_info(vista, info):
    if not hasattr(vista, MARCA_VISTA):
        vista.addProperty("App::PropertyString", MARCA_VISTA, "Circuits", "O que a vista da bancada mostra (JSON)")
    setattr(vista, MARCA_VISTA, json.dumps(info, ensure_ascii=False))


def _vistas(folha):
    return [v for v in getattr(folha, "Views", []) if hasattr(v, MARCA_VISTA)]


def _titulo(doc, folha, vista):
    existente = next((v for v in getattr(folha, "Views", []) if getattr(v, MARCA_TITULO, None) == vista.Name), None)
    if existente is not None:
        return existente
    titulo = doc.addObject("TechDraw::DrawViewAnnotation", "Titulo")
    titulo.addProperty("App::PropertyString", MARCA_TITULO, "Circuits", "Vista de que este texto é o título")
    setattr(titulo, MARCA_TITULO, vista.Name)
    titulo.TextSize = ALTURA_TEXTO_TITULO
    folha.addView(titulo)
    return titulo


def _nova_vista(doc, folha, tipo_td, nome, rotulo, info):
    vista = doc.addObject(tipo_td, nome)
    _gravar_info(vista, info)
    vista.Label = rotulo
    if hasattr(vista, "ScaleType"):
        vista.ScaleType = "Custom"
    folha.addView(vista)
    _titulo(doc, folha, vista)
    return vista


def _rotulo_da_fonte(doc, obj):
    if pavimentos.eh_pavimento(obj):
        return f"Planta baixa - {obj.Label}"
    return obj.Label.replace("_", " ")


def _eh_planilha(obj):
    return obj.TypeId == "Spreadsheet::Sheet"


def _celula_final(planilha):
    try:
        usadas = planilha.getUsedCells()
    except Exception:
        return "J30", 10, 30
    if not usadas:
        return "A1", 1, 1
    colunas, linhas = [], []
    for celula in usadas:
        letras, numero = re.match(r"([A-Z]+)(\d+)", celula).groups()
        valor = 0
        for letra in letras:
            valor = valor * 26 + ord(letra) - 64
        colunas.append(valor)
        linhas.append(int(numero))
    ultima, k = "", max(colunas)
    while k:
        k, resto = divmod(k - 1, 26)
        ultima = chr(65 + resto) + ultima
    return f"{ultima}{max(linhas)}", max(colunas), max(linhas)


def inserir(doc, folha, objetos):
    """Põe os objetos na folha: planilha vira tabela; o resto, desenho 2D (pavimento = planta).

    Returns:
        Vistas criadas.
    """
    criadas = []
    for obj in objetos:
        if obj is None or obj.TypeId.startswith("TechDraw::"):
            continue
        if _eh_planilha(obj):
            final, colunas, linhas = _celula_final(obj)
            info = {"tipo": "tabela", "fontes": [obj.Name], "largura": 25.0 * colunas, "altura": 6.0 * linhas}
            vista = _nova_vista(doc, folha, "TechDraw::DrawViewSpreadsheet", "Tabela", obj.Label, info)
            vista.Source = obj
            vista.CellStart, vista.CellEnd = "A1", final
        else:
            info = {"tipo": "desenho", "fontes": [obj.Name]}
            vista = _nova_vista(doc, folha, "TechDraw::DrawViewSymbol", "Vista", _rotulo_da_fonte(doc, obj), info)
        criadas.append(vista)
    return criadas


# --- detalhes e cortes ------------------------------------------------------------------------

def _pavimento_ou_documento(doc, obj):
    pav = pavimentos.pavimento_do_objeto(doc, obj)
    return [pav] if pav is not None else [o for o in doc.Objects if not o.InList]


def _marca_na_planta(doc, referencia, obj, valor):
    obj.addProperty("App::PropertyString", MARCA_MARCA, "Circuits", "Seta ou letra de corte/detalhe na planta")
    setattr(obj, MARCA_MARCA, valor)
    pavimentos.guardar_junto(referencia, obj)


def _limites_xy(obj):
    caixa = obj.Shape.BoundBox
    return caixa.XMin, caixa.YMin, caixa.XMax, caixa.YMax


def inserir_detalhe(doc, folha, regiao):
    """Detalhe da planta dentro da forma fechada ``regiao`` (círculo, retângulo...), ampliado."""
    usados = [_info(v).get("detalhe", "") for f in listar_folhas(doc) for v in _vistas(f)]
    nome = regras.proximo_detalhe(usados)
    if not hasattr(regiao, MARCA_DETALHE):
        regiao.addProperty("App::PropertyString", MARCA_DETALHE, "Circuits", "Região de um detalhe da folha")
    setattr(regiao, MARCA_DETALHE, nome)
    fontes = [o.Name for o in _pavimento_ou_documento(doc, regiao)]
    info = {"tipo": "detalhe", "fontes": fontes, "regiao": regiao.Name, "detalhe": nome}
    # recorte do TechDraw (retangular, pela caixa da região) com a planta inteira dentro
    vista = _nova_vista(doc, folha, "TechDraw::DrawViewClip", "Detalhe", f"Detalhe {nome}", info)
    vista.ShowFrame = True
    desenho = doc.addObject("TechDraw::DrawViewSymbol", "Detalhe_desenho")
    desenho.Label = f"Desenho do detalhe {nome}"
    desenho.ScaleType = "Custom"
    folha.addView(desenho)
    vista.addView(desenho)
    try:
        xmin, ymin, xmax, ymax = _limites_xy(regiao)
        altura = max(xmax - xmin, ymax - ymin) / 8.0
        z = regiao.Shape.BoundBox.ZMin
        texto = Draft.make_text([nome], placement=App.Vector(xmax, ymax, z), height=altura)
        _marca_na_planta(doc, regiao, texto, nome)
    except Exception as erro:
        App.Console.PrintWarning(f"Marca do detalhe {nome} não desenhada na planta: {erro}\n")
    return vista


def solidos_do_modelo(doc):
    """Objetos 3D visíveis (com sólidos) que entram nos cortes."""
    resultado = []
    for obj in doc.Objects:
        if obj.TypeId.startswith("TechDraw::") or obj.TypeId in ("App::Part", "App::Link") or _eh_grupo(obj):
            continue
        forma = getattr(obj, "Shape", None)
        try:
            if forma is None or forma.isNull() or not forma.Solids or not _visivel(obj):
                continue
        except Exception:
            continue
        resultado.append(obj)
    return resultado


def _limites_3d(objetos):
    caixas = [o.Shape.BoundBox for o in objetos]
    return (min(c.XMin for c in caixas), min(c.YMin for c in caixas), min(c.ZMin for c in caixas),
            max(c.XMax for c in caixas), max(c.YMax for c in caixas), max(c.ZMax for c in caixas))


def _base_dos_cortes(doc, folha, solidos):
    base = next((v for v in getattr(folha, "Views", []) if hasattr(v, MARCA_BASE)), None)
    if base is None:
        base = doc.addObject("TechDraw::DrawViewPart", "Base_cortes")
        base.addProperty("App::PropertyBool", MARCA_BASE, "Circuits", "Vista de cima do 3D, base dos cortes")
        setattr(base, MARCA_BASE, True)
        base.Label = "Base dos cortes (escondida)"
        folha.addView(base)
    base.Source = solidos
    base.Direction = App.Vector(0, 0, 1)
    # O TechDraw exporta a vista mesmo escondida (no PDF, as faces brancas cobriam a folha):
    # fica minúscula, no canto da margem, sem a linha de corte (conferido no FreeCAD 1.0.2).
    base.ScaleType = "Custom"
    base.Scale = ESCALA_BASE_CORTES
    x0, y0, _, _ = regras.area_util(getattr(folha, MARCA_FOLHA, regras.FORMATO_PADRAO))
    base.X, base.Y = x0, y0
    for propriedade, valor in (("ShowSectionLine", False), ("Visibility", False)):
        try:
            setattr(base.ViewObject, propriedade, valor)
        except Exception:
            pass
    return base


def _pontos_da_linha(linha):
    pontos = [linha.Placement.multVec(p) for p in linha.Points]
    return (pontos[0].x, pontos[0].y), (pontos[-1].x, pontos[-1].y), pontos[0].z


def inserir_corte(doc, folha, linha):
    """Corte do modelo 3D pela linha desenhada na planta (as setas olham para a direita dela).

    Returns:
        A vista do corte, ou None se não há sólidos no modelo.
    """
    solidos = solidos_do_modelo(doc)
    if not solidos:
        return None
    p1, p2, z = _pontos_da_linha(linha)
    limites = _limites_3d(solidos)
    plano = regras.corte(p1, p2, ((limites[0] + limites[3]) / 2.0, (limites[1] + limites[4]) / 2.0))
    usadas = [getattr(o, MARCA_CORTE) for o in doc.Objects if hasattr(o, MARCA_CORTE)]
    letra = getattr(linha, MARCA_CORTE, "") or regras.proxima_letra(usadas)
    if not hasattr(linha, MARCA_CORTE):
        linha.addProperty("App::PropertyString", MARCA_CORTE, "Circuits", "Letra do corte desenhado na folha")
    setattr(linha, MARCA_CORTE, letra)
    largura, altura = regras.tamanho_do_corte(limites, plano)
    base = _base_dos_cortes(doc, folha, solidos)
    info = {"tipo": "corte", "fontes": [linha.Name], "letra": letra, "largura": largura, "altura": altura}
    vista = _nova_vista(doc, folha, "TechDraw::DrawViewSection", "Corte", regras.titulo_do_corte(letra), info)
    vista.BaseView = base
    vista.Source = solidos
    vista.SectionNormal = App.Vector(*plano["normal"])
    vista.Direction = App.Vector(*plano["normal"])
    vista.SectionOrigin = App.Vector(plano["origem"][0], plano["origem"][1], (limites[2] + limites[5]) / 2.0)
    vista.SectionSymbol = letra
    # A hachura SVG do TechDraw sai no PDF como um bloco branco por cima da folha (FreeCAD 1.0.2):
    # superfície cortada em cor sólida.
    for propriedade, valor in (("XDirection", App.Vector(*plano["xdirecao"])), ("SectionDirection", "Aligned"),
                               ("CutSurfaceDisplay", "Color")):
        try:
            setattr(vista, propriedade, valor)
        except Exception:
            pass
    _desenhar_marcas_do_corte(doc, linha, p1, p2, z, letra)
    return vista


def _desenhar_marcas_do_corte(doc, linha, p1, p2, z, letra):
    for obj in [o for o in doc.Objects if getattr(o, MARCA_MARCA, None) == f"corte {letra}"]:
        doc.removeObject(obj.Name)
    tamanho = max(regras.corte(p1, p2)["comprimento"] / 15.0, 150.0)
    marcas = regras.marcas_do_corte(p1, p2, letra, tamanho)
    for pontos in marcas["setas"]:
        seta = Draft.make_wire([App.Vector(x, y, z) for x, y in pontos], closed=False, face=False)
        _marca_na_planta(doc, linha, seta, f"corte {letra}")
    for x, y, texto in marcas["letras"]:
        objeto = Draft.make_text([texto], placement=App.Vector(x, y, z), height=tamanho * 0.6)
        _marca_na_planta(doc, linha, objeto, f"corte {letra}")


# --- arrumação e atualização ------------------------------------------------------------------

def _regiao(doc, info):
    regiao = doc.getObject(info.get("regiao", ""))
    return _limites_xy(regiao) if regiao is not None else None


def _desenho_do_detalhe(clip):
    return next((v for v in getattr(clip, "Views", []) if v.TypeId == "TechDraw::DrawViewSymbol"), None)


def _tamanho(doc, vista, info):
    """(largura, altura) no modelo para ``core.folhas.organizar``."""
    if info["tipo"] == "desenho":
        _, limites = conteudo(doc, info, 1.0)
        return None if limites is None else (limites[2] - limites[0], limites[3] - limites[1])
    if info["tipo"] == "detalhe":
        regiao = _regiao(doc, info)
        return None if regiao is None else (regiao[2] - regiao[0], regiao[3] - regiao[1])
    return info.get("largura", 100.0), info.get("altura", 100.0)


def _aplicar_desenho(doc, vista, info, fator, centro):
    """Refaz o SVG da vista (ou do desenho dentro do recorte do detalhe) e põe o centro em ``centro``."""
    svg, limites = conteudo(doc, info, fator)
    if limites is None:
        return
    if info["tipo"] == "detalhe":
        desenho, regiao = _desenho_do_detalhe(vista), _regiao(doc, info)
        if desenho is None or regiao is None:
            return
        desenho.Symbol, desenho.Scale = svg, fator
        desenho.X, desenho.Y = regras.deslocamento_do_detalhe(limites, regiao, fator)
        vista.Width, vista.Height = (regiao[2] - regiao[0]) * fator, (regiao[3] - regiao[1]) * fator
    else:
        vista.Symbol, vista.Scale = svg, fator
    vista.X, vista.Y = centro  # o TechDraw centra o desenho do símbolo no X, Y
    info.update(limites=list(limites), fator=fator)
    _gravar_info(vista, info)


def organizar(doc, folha, escala=None):
    """Escolhe a escala e arruma todas as vistas da bancada na folha (``core.folhas.organizar``).

    Returns:
        O resultado de ``core.folhas.organizar`` (``cabe`` False: use um formato maior).
    """
    formato = getattr(folha, MARCA_FOLHA, regras.FORMATO_PADRAO)
    entradas, vistas = [], []
    for vista in _vistas(folha):
        info = _info(vista)
        tamanho_ = _tamanho(doc, vista, info)
        if tamanho_ is None:
            continue
        entradas.append({"nome": vista.Name, "largura": tamanho_[0], "altura": tamanho_[1],
                         "tipo": info["tipo"], "titulo": vista.Label})
        vistas.append((vista, info))
    resultado = regras.organizar(entradas, formato, escala)
    for (vista, info), arranjo in zip(vistas, resultado["vistas"]):
        centro = (arranjo["x"], arranjo["y"])
        if info["tipo"] in ("desenho", "detalhe"):
            _aplicar_desenho(doc, vista, info, arranjo["fator"], centro)
        else:
            vista.Scale = arranjo["fator"]
            vista.X, vista.Y = centro
            info.update(fator=arranjo["fator"])
            _gravar_info(vista, info)
        titulo = _titulo(doc, folha, vista)
        titulo.Text = regras.titulo_da_vista(vista.Label, arranjo["escala"], info["tipo"])
        titulo.X, titulo.Y = arranjo["titulo_x"], arranjo["titulo_y"]
    escalas = {round(a["escala"]) for a, (_, info) in zip(resultado["vistas"], vistas) if info["tipo"] != "tabela"}
    if escalas:
        texto = regras.texto_escala(resultado["escala"]) + (" e indicadas" if len(escalas) > 1 else "")
        preencher(folha, {"Escala": texto})
    doc.recompute()
    return resultado


def atualizar(doc, folhas=None):
    """Refaz o desenho das vistas 2D a partir do modelo, mantendo o lugar e a escala de cada uma.

    Returns:
        Quantidade de vistas refeitas.
    """
    total = 0
    for folha in folhas or listar_folhas(doc):
        for vista in _vistas(folha):
            info = _info(vista)
            if info.get("tipo") not in ("desenho", "detalhe") or "fator" not in info:
                continue
            # no lugar atual, mesmo que o usuário tenha arrastado a vista
            _aplicar_desenho(doc, vista, info, info["fator"], (_mm(vista.X), _mm(vista.Y)))
            total += 1
    atualizar_carimbos(doc)
    doc.recompute()
    return total
