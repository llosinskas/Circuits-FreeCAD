"""Centro de medição Enel SP no documento: planilha, colunas de medição e busway (``core.centro_medicao``).

- **Planilha "Centro de medição"** (propriedade ``centro_medicao``): um pavimento por
  linha (A a E), os preços de referência nas colunas G a I, o resultado nas K e L e
  os parâmetros do último cálculo nas N e O (usados pelo botão Busway).
- **Colunas de medição**: objeto paramétrico (``objects.coluna_medicao``) que escolhe e
  dimensiona as caixas (P ou metálicas K a O) e desenha os conjuntos em 3D, na pasta
  *Busway e medição* do pavimento; o comando posiciona com o mouse.
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
from freecad.Circuits.objects.coluna_medicao import create_coluna_medicao
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
    projeto = [(p.Label, pavimentos.elevacao(p) / 1000.0, getattr(p, "Unidades", None)) for p in pavimentos.listar(doc)]
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


def criar_colunas(doc, pavimento=None, **valores):
    """Colunas de medição paramétricas (``objects.coluna_medicao``) na pasta *Busway e medição* do pavimento.

    ``valores`` são as entradas do objeto (``Medidores``, ``DemandaPorMedidor``, ``Fases``,
    ``DemandaTotal``, ``Tensao``...). O objeto fica no piso do pavimento.
    """
    coluna = create_coluna_medicao(doc, **valores)
    if pavimento is not None:
        pavimentos.pasta(doc, pavimento, "busway").addObject(coluna)
        posicao = coluna.Placement
        posicao.Base = App.Vector(0, 0, pavimentos.elevacao(pavimento))
        coluna.Placement = posicao
    doc.recompute()
    return coluna


PROPRIEDADES_COLUNA = (
    "Medidores", "MedidoresPorColuna", "DemandaPorMedidor", "DemandaTotal",
    "Fases", "Modelo", "CDPM", "Tensao", "ComprimentoRamal",
    "PosicaoCDPM", "SaidaEletroduto", "AlturaBase",
    "LarguraCaixaP", "ProfundidadeCaixaP", "AlturaCaixaP", "FolgaConjuntos", "ComSuporte", "Representacao",
)


def ler_propriedades_coluna(obj):
    """Lê as propriedades editáveis de um objeto ``ColunaMedicao`` para preencher o diálogo."""
    return {chave: getattr(obj, chave) for chave in PROPRIEDADES_COLUNA if hasattr(obj, chave)}


def atualizar_colunas(doc, obj, **valores):
    """Atualiza as propriedades de ``ColunaMedicao`` preservando a posição do objeto."""
    posicao = App.Placement(obj.Placement)
    for chave, valor in valores.items():
        if hasattr(obj, chave):
            setattr(obj, chave, valor)
    obj.Placement = posicao
    doc.recompute()
    if murais_da_coluna(doc, obj):
        desenhar_mural(doc, obj)  # o mural acompanha as colunas editadas
    return obj


# --- mural (elevação frontal cotada) --------------------------------------------------------------

MARCA_MURAL = "mural_de"
AFASTAMENTO_MURAL_MM = 1500.0  # do fundo das colunas, na planta, até o piso do mural


def eh_coluna(obj):
    return _tipo(obj) == "ColunaMedicao"


def murais_da_coluna(doc, coluna):
    """Grupos do mural das colunas (propriedade ``mural_de`` = nome do objeto)."""
    return [o for o in doc.Objects if getattr(o, MARCA_MURAL, None) == coluna.Name]


def remover_murais_orfaos(doc):
    """Apaga os murais de colunas que não existem mais (recriadas pelo Gerar centro de medição)."""
    for grupo in [o for o in doc.Objects if getattr(o, MARCA_MURAL, None)]:
        if doc.getObject(getattr(grupo, MARCA_MURAL)) is None:
            _apagar_grupo(doc, grupo)


def _apagar_grupo(doc, grupo):
    for filho in list(getattr(grupo, "Group", [])):
        if doc.getObject(filho.Name) is not None:
            doc.removeObject(filho.Name)
    if doc.getObject(grupo.Name) is not None:
        doc.removeObject(grupo.Name)


def desenho_do_mural(coluna):
    """Geometria do mural das colunas (``core.centro_medicao.mural``), com o título e as notas."""
    dados, pecas = coluna.Proxy.pecas(coluna, representacao=regras.REPRESENTACOES[1])
    titulo = f"MURAL DE MEDIÇÃO - {coluna.Label} ({int(getattr(coluna, 'Medidores', 0))} medições)"
    return regras.mural(pecas, titulo, regras.notas_do_mural(dados, getattr(coluna, "MedidoresPorColuna", 3)))


def desenhar_mural(doc, coluna):
    """Recria o mural (elevação frontal cotada, ``core.centro_medicao.mural``) das colunas de medição.

    Desenhado em verdadeira grandeza na planta, no piso do pavimento: acima das colunas na
    primeira vez, ou onde o mural anterior estava (o usuário pode movê-lo). Um ``Part::Feature``
    com as linhas e os círculos e um texto por rótulo, num grupo com ``mural_de`` = nome das
    colunas, na pasta *Busway e medição* do pavimento delas.

    Returns:
        O grupo do mural.
    """
    desenho = desenho_do_mural(coluna)
    origem = None
    for antigo in murais_da_coluna(doc, coluna):
        if origem is None:
            figura = next((o for o in getattr(antigo, "Group", []) if hasattr(o, "Shape") and o.TypeId == "Part::Feature"),
                          None)
            if figura is not None:
                origem = App.Vector(figura.Placement.Base)
        _apagar_grupo(doc, antigo)
    if origem is None:
        caixa = coluna.Shape.BoundBox if not coluna.Shape.isNull() else None
        base = coluna.Placement.Base
        y = (caixa.YMax if caixa is not None else base.y) + AFASTAMENTO_MURAL_MM - desenho["limites"][1]
        origem = App.Vector(base.x, y, base.z)
    grupo = doc.addObject("App::DocumentObjectGroup", "Mural_medicao")
    grupo.Label = f"Mural - {coluna.Label}"
    grupo.addProperty("App::PropertyString", MARCA_MURAL, "Mural", "Colunas de medição deste mural")
    setattr(grupo, MARCA_MURAL, coluna.Name)
    arestas = [Part.makeLine(App.Vector(x1, y1, 0), App.Vector(x2, y2, 0))
               for x1, y1, x2, y2 in desenho["linhas"] if (x1, y1) != (x2, y2)]
    for cx, cy, raio in desenho["circulos"]:
        arestas.append(Part.makeCircle(raio, App.Vector(cx, cy, 0)))
    figura = doc.addObject("Part::Feature", "Mural_desenho")
    figura.Label = f"Mural {coluna.Label}"
    figura.Shape = Part.makeCompound(arestas)
    figura.Placement = App.Placement(origem, App.Rotation())
    grupo.addObject(figura)
    for x, y, conteudo, altura, angulo in desenho["textos"]:
        texto = Draft.make_text([conteudo], placement=App.Placement(origem + App.Vector(x, y, 0),
                                                                    App.Rotation(App.Vector(0, 0, 1), angulo)),
                                height=altura)
        grupo.addObject(texto)
    pasta = pavimentos.pasta_do_pavimento(doc, coluna, "busway")
    if pasta is not None:
        pasta.addObject(grupo)
    doc.recompute()
    return grupo


def desenhar_murais(doc, colunas=None):
    """Murais das colunas dadas (ou de todas); apaga os murais de colunas que não existem mais."""
    remover_murais_orfaos(doc)
    colunas = [c for c in (colunas if colunas is not None else doc.Objects) if eh_coluna(c)]
    return [desenhar_mural(doc, c) for c in colunas]


def valores_da_planilha(andares, parametros=None):
    """Entradas das colunas a partir dos andares da planilha: medidores, maior demanda e fases, demanda total."""
    parametros = parametros or {}
    com_unidades = [a for a in andares if a["unidades"] > 0]
    if not com_unidades:
        return {}
    return {"Medidores": sum(a["unidades"] for a in com_unidades),
            "DemandaPorMedidor": max(a["demanda_a"] for a in com_unidades),
            "Fases": max(a["fases"] for a in com_unidades),
            "DemandaTotal": float(parametros.get("demanda_total_a", 0.0) or 0.0),
            "Tensao": float(parametros.get("tensao", 220.0) or 220.0)}


# --- gerar e recriar o centro de medição -------------------------------------------------------------

MARCA = "gerado_centro_medicao"  # chave do objeto gerado (centro e papel), para recriar no mesmo lugar
SIMBOLOS_ANCORA = ("medicao_agrupada", "quadro_medicao")


def gerados(doc):
    """Objetos criados por ``gerar_centro``, {chave: objeto}."""
    return {getattr(o, MARCA): o for o in doc.Objects if getattr(o, MARCA, "")}


def _ancora(doc, pavimento):
    """Placement do símbolo de medição agrupada (ou quadro de medição) do pavimento, ou None."""
    for obj in doc.Objects:
        if _tipo(obj) == "Ponto" and getattr(obj, "Simbolo", "") in SIMBOLOS_ANCORA:
            if pavimento is None or pavimentos.pavimento_do_objeto(doc, obj) is pavimento:
                return obj.Placement
    return None


def _pavimento_base(doc, andares):
    """Pavimento do centro de medição único: o do andar de cota 0 da planilha, senão o mais baixo do projeto."""
    zero = next((a for a in andares if abs(a["cota"]) < 1e-6), None)
    pavimento = pavimentos.por_nome(doc, zero["nome"]) if zero else None
    if pavimento is None:
        lista = sorted(pavimentos.listar(doc), key=pavimentos.elevacao)
        pavimento = lista[0] if lista else pavimentos.garantir_ativo(doc)
    return pavimento


def _marcar(obj, chave):
    _propriedade(obj, "App::PropertyString", MARCA, "Gerado pelo Centro de medição (recriado no mesmo lugar)", chave)


def _posicao(base, x, y=0.0):
    """Placement de um ponto (x, y) no sistema da âncora ``base``."""
    local = App.Placement(App.Vector(x, y, 0), App.Rotation())
    return base.multiply(local)


def gerar_centro(doc, andares, solucao="convencional", parametros=None):
    """Cria (ou recria) no desenho o centro de medição da solução, a partir dos andares da planilha.

    Para cada centro de ``core.centro_medicao.plano_de_geracao``: as colunas de medição paramétricas
    (as diretas juntas e um conjunto indireto por andar com unidades acima de 100 A), o contorno do
    abrigo em alvenaria com a área e, na solução descentralizada, o ramal de distribuição vertical do
    QDC até o centro, com o texto da seção. Tudo vai para a pasta *Busway e medição* do pavimento do
    centro. Os objetos gerados antes são apagados, e cada um novo volta à posição do antigo com a
    mesma chave; os novos ficam no símbolo de medição agrupada do pavimento, se houver, ou na origem.

    Returns:
        (centros do plano, objetos criados).
    """
    parametros = parametros or {}
    plano = regras.plano_de_geracao(
        andares, solucao, tensao=float(parametros.get("tensao", 220.0) or 220.0),
        distancia_horizontal=float(parametros.get("distancia_horizontal", 15.0) or 15.0),
        demanda_total_a=float(parametros.get("demanda_total_a", 0.0) or 0.0),
        andares_por_centro=int(parametros.get("andares_por_centro", regras.ANDARES_POR_CENTRO)
                               or regras.ANDARES_POR_CENTRO))
    antigos = gerados(doc)
    posicoes = {chave: obj.Placement for chave, obj in antigos.items()}
    for obj in antigos.values():
        try:
            doc.removeObject(obj.Name)
        except Exception:
            pass

    base = _pavimento_base(doc, andares)
    cota_base = pavimentos.elevacao(base) if base is not None else 0.0
    referencia = _ancora(doc, base) or App.Placement()
    criados = []
    for centro in plano:
        pavimento = pavimentos.por_nome(doc, centro["andar"]) if centro["andar"] else base
        pavimento = pavimento or base
        cota = pavimentos.elevacao(pavimento) if pavimento is not None else 0.0
        ancora = App.Placement(_ancora(doc, pavimento) or referencia)
        ancora.Base = App.Vector(ancora.Base.x, ancora.Base.y, cota)
        pasta = pavimentos.pasta(doc, pavimento, "busway") if pavimento is not None else None
        prefixo = f"{solucao} {centro['numero']}"

        for objeto in centro["objetos"]:
            chave = f"{prefixo} {objeto['chave']}"
            coluna = create_coluna_medicao(doc, **objeto["valores"])
            coluna.Label = f"Centro {centro['numero']} – colunas {objeto['chave']}"
            coluna.Placement = posicoes.get(chave) or _posicao(ancora, objeto["x"])
            _marcar(coluna, chave)
            criados.append(coluna)
            if pasta is not None:
                pasta.addObject(coluna)

        abrigo = centro["abrigo"]
        chave = f"{prefixo} abrigo"
        contorno = Draft.make_rectangle(abrigo["largura"], abrigo["profundidade"])
        contorno.Label = f"Centro de medição {centro['numero']}"
        contorno.Placement = posicoes.get(chave) or _posicao(ancora, -abrigo["largura"] / 2.0, abrigo["y0"])
        _propriedade(contorno, "App::PropertyFloat", "AreaAbrigo", "Área do centro de medição abrigado [m²]",
                     round(abrigo["area"], 2))
        _marcar(contorno, chave)
        try:
            contorno.ViewObject.DrawStyle = "Dashed"
        except Exception:
            pass
        criados.append(contorno)
        texto = Draft.make_text([f"CENTRO DE MEDIÇÃO {centro['numero']}", f"{abrigo['area']:.1f} m²".replace(".", ","),
                                 ", ".join(centro["andares"])], App.Vector(0, 0, 0))
        texto.Placement = posicoes.get(f"{prefixo} texto") or _posicao(ancora, -abrigo["largura"] / 2.0 + 100.0,
                                                                       abrigo["y0"] + 200.0)
        _marcar(texto, f"{prefixo} texto")
        criados.append(texto)
        if pasta is not None:
            pasta.addObject(contorno)
            pasta.addObject(texto)

        ramal = centro["ramal"]
        if ramal and ramal["secao"]:
            chave = f"{prefixo} ramal"
            x = -abrigo["largura"] / 2.0 - 200.0 - 100.0 * centro["numero"]
            pe = _posicao(referencia, x, 0.0).Base
            linha = Draft.make_wire([App.Vector(pe.x, pe.y, cota_base), App.Vector(pe.x, pe.y, cota)])
            linha.Label = f"Ramal do centro {centro['numero']}"
            _propriedade(linha, "App::PropertyString", "RamalDistribuicao", "Ramal de distribuição do centro",
                         f"{ramal['paralelos']} × 4 × {ramal['secao']} mm², chave vertical {ramal['chave']} A")
            _marcar(linha, chave)
            criados.append(linha)
            rotulo = Draft.make_text([f"Ramal C{centro['numero']}: {ramal['paralelos']} × 4 × {ramal['secao']} mm²",
                                      f"chave vertical {ramal['chave']} A no QDC"
                                      + (f"; {ramal['qdc_local']} no centro" if ramal["qdc_local"] else "")],
                                     App.Vector(pe.x, pe.y, cota))
            _marcar(rotulo, f"{prefixo} ramal texto")
            criados.append(rotulo)
            if pasta is not None:
                pasta.addObject(linha)
                pasta.addObject(rotulo)
    doc.recompute()
    return plano, criados


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
    lajes = sum(1 for cota in cotas.values() if base + altura < cota < topo)
    _propriedade(vertical, "App::PropertyInteger", "LajesAtravessadas", "Lajes com barreira corta-fogo", lajes)

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
        _propriedade(texto, "App::PropertyStringList", "CaixasMEC", "Caixas MEC do andar (Tabela 30)",
                     [c["tipo"] for c in andar["caixas"]])
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


# --- quantitativos ----------------------------------------------------------------------------------

def _comprimento(pontos):
    return sum(math.dist((a.x, a.y, a.z), (b.x, b.y, b.z)) for a, b in zip(pontos, pontos[1:]))


def materiais_por_pavimento(doc):
    """(pavimento, itens) do busway, das caixas MEC e das colunas de medição do documento.

    O busway (metros, cotovelos, emendas, suportes, corta-fogo) entra no pavimento do
    trecho horizontal; as caixas MEC, no andar de cada uma; as colunas, no pavimento delas.
    """
    nome = lambda obj: getattr(pavimentos.pavimento_do_objeto(doc, obj), "Label", "")  # noqa: E731
    verticais = {getattr(o, "prumada_busway_de", ""): o for o in doc.Objects
                 if eh_busway(o) and getattr(o, "prumada_busway_de", "")}
    por_pavimento = {}
    for obj in doc.Objects:
        if eh_busway(obj) and not getattr(obj, "prumada_busway_de", ""):
            pontos = _pontos(obj)
            vertical = verticais.get(obj.Name)
            trecho = {"nominal": int(obj.CorrenteBusway), "horizontal": _comprimento(pontos) / 1000.0,
                      "vertical": _comprimento(_pontos(vertical)) / 1000.0 if vertical is not None else 0.0,
                      "cotovelos": max(0, len(pontos) - 2) + (1 if vertical is not None else 0),
                      "lajes": int(getattr(vertical, "LajesAtravessadas", 0) or 0) if vertical is not None else 0}
            por_pavimento.setdefault(nome(obj), []).extend(regras.materiais_do_busway([trecho]))
    caixas = {}
    for obj in doc.Objects:
        if getattr(obj, "CaixasMEC", None) and getattr(obj, "prumada_busway_de", ""):
            caixas.setdefault(nome(obj), []).extend(list(obj.CaixasMEC))
        if hasattr(obj, "coluna_medicao"):
            itens = regras.materiais_das_colunas([{
                "caixas": int(obj.coluna_medicao or 0), "cdpms": list(getattr(obj, "CDPMs", []) or []),
                "metalicas": list(getattr(obj, "CaixasMetalicas", []) or []),
                "medicoes_metalicas": int(getattr(obj, "MedicoesMetalicas", 0) or 0),
                "caixas_e": int(getattr(obj, "CaixasE", 0) or 0), "cdpm_e": int(getattr(obj, "CDPMsE", 0) or 0),
                "indiretas": list(getattr(obj, "Indiretas", []) or [])}])
            if itens:
                por_pavimento.setdefault(nome(obj), []).extend(itens)
    for pavimento, tipos in caixas.items():
        por_pavimento.setdefault(pavimento, []).extend(regras.materiais_das_caixas_mec(tipos))
    return list(por_pavimento.items())
