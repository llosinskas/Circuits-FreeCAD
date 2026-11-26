"""Geração do diagrama unifilar a partir das planilhas de quadro."""
import math

import Draft
import FreeCAD as App
import Part

from freecad.Circuits.core import multifilar as desenho_multifilar
from freecad.Circuits.core import quadro as regras_quadro
from freecad.Circuits.core.functions.Predial import gerador as regras_gerador
from freecad.Circuits.core import simbolos
from freecad.Circuits.core import unifilar as desenho
from freecad.Circuits.services import gerador as servico_gerador
from freecad.Circuits.services import pavimentos, planilhas
from freecad.Circuits.services.cabos import desenhar_cabo_unifilar
from freecad.Circuits.services.estilo import pintar_sketch

ALTURA_PADRAO = 100
ESPACAMENTO_CIRCUITOS = 5  # distância entre circuitos, em alturas de texto
ALTURA_CABECALHO = 16  # espaço do cabeçalho e dos dados do quadro, em alturas de texto


def add_texto(texto, posicao, angulo, h, grupo):
    objeto = Draft.make_text(str(texto), placement=posicao, screen=None, height=h, line_spacing=None)
    objeto.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), angulo)
    grupo.addObject(objeto)


def desenhar_dps(doc, posicao, h, grupo):
    sketch = doc.addObject("Sketcher::SketchObject", "dps")
    pintar_sketch(sketch)
    sketch.Placement = App.Placement(posicao, App.Rotation(0, 0, 0))

    def linha(p1, p2):
        sketch.addGeometry(Part.LineSegment(p1, p2), False)

    linha(App.Vector(0, 0), App.Vector(0, -0.5 * h))
    # Corpo
    q1 = App.Vector(-h, -0.5 * h)
    q2 = App.Vector(h, -0.5 * h)
    q3 = App.Vector(-h, -4 * h)
    q4 = App.Vector(h, -4 * h)
    linha(q1, q2)
    linha(q1, q3)
    linha(q2, q4)
    linha(q3, q4)
    # Triângulo
    t1 = App.Vector(-h / 2, -h)
    t2 = App.Vector(h / 2, -h)
    t3 = App.Vector(0, -2 * h)
    linha(t1, t2)
    linha(t1, t3)
    linha(t2, t3)
    # Aterramento
    linha(App.Vector(0, -4 * h), App.Vector(0, -4.5 * h))
    linha(App.Vector(-h / 2, -4.5 * h), App.Vector(h / 2, -4.5 * h))
    linha(App.Vector(-h / 4, -4.75 * h), App.Vector(h / 4, -4.75 * h))
    linha(App.Vector(-h / 8, -5 * h), App.Vector(h / 8, -5 * h))

    grupo.addObject(sketch)


def desenhar_quadro(doc, h, grupo, planilha):
    """Desenha a entrada, o disjuntor geral e os dados do quadro."""
    try:
        dados = planilhas.ler_quadro(planilha)  # campo vazio não derruba o cabeçalho (alias perdido)
        identificacao = dados["indentificacao_painel"]
        bitola = dados["bitola"]
        origem = dados["origem"]
        descricao = dados["descricao"]
        tensao = dados["tensao"]
        numero_fases = int(float(dados["numero_fases"].replace(",", ".") or 3))  # número, como dava o get
        curva_disjuntor = dados["curva_disjuntor"]
        corrente_nominal = dados["corrente_nominal_disjuntor"]
        corrente_cc = dados["corrente_curto_circuito"]
        potencia_instalada = dados["potencia_instalada"]
        potencia_demanda = dados["potencia_demanda"]
        material = dados["material_quadro"]
        tem_dps = dados["DPS"]

        add_texto(origem, App.Vector(-h * 0.5, 0.5 * h, 0), 90, h, grupo)
        add_texto(f"#{bitola}", App.Vector(5 * h, h, 0), 0, h, grupo)
        add_texto(f"{curva_disjuntor} {corrente_nominal}A", App.Vector(10 * h, 5 * h, 0), 0, h, grupo)
        add_texto(f"{corrente_cc}kA", App.Vector(13 * h, 3 * h, 0), 0, h, grupo)
        add_texto(f"Material: {material}", App.Vector(0, -2 * h, 0), 0, h, grupo)
        add_texto(f"Potência Instalada:{potencia_instalada} kW", App.Vector(0, -3 * h, 0), 0, h, grupo)
        add_texto(f"Demanda:{potencia_demanda} kW", App.Vector(0, -4 * h, 0), 0, h, grupo)
        curto = dados["curto_circuito"]
        add_texto(f"Nível de curto circuito no ponto {curto} kA", App.Vector(0, -5 * h, 0), 0, h, grupo)
        add_texto(f"{descricao}", App.Vector(0, -6 * h, 0), 0, h, grupo)
        add_texto(identificacao, App.Vector(0, 5 * h, 0), 0, h, grupo)
        add_texto(f"{tensao}V", App.Vector(5 * h, 5 * h, 0), 0, h, grupo)

        if tem_dps == "True":
            classe_dps = dados["classe_DPS"]
            tensao_dps = dados["tensao_DPS"]
            corrente_dps = dados["corrente_DPS"]
            desenhar_dps(doc, App.Vector(15 * h, 5 / 2 * h, 0), h, grupo)
            add_texto(f"Classe: {classe_dps}", App.Vector(h * 17, 0, 0), 0, h, grupo)
            add_texto(f"{tensao_dps}V", App.Vector(h * 17, -h, 0), 0, h, grupo)
            add_texto(f"{corrente_dps}kA", App.Vector(h * 17, -2 * h, 0), 0, h, grupo)
    except Exception as e:
        print(f"Erro ao acessar o valor da planilha do quadro: {e}")

    # Linhas de entrada e saída
    for p1, p2 in (
        (App.Vector(0, 0, 0), App.Vector(0, 5 * h, 0)),
        (App.Vector(0, 5 / 2 * h, 0), App.Vector(10 * h, 5 / 2 * h, 0)),
        (App.Vector(13 * h, 5 / 2 * h, 0), App.Vector(18 * h, 5 / 2 * h, 0)),
    ):
        grupo.addObject(Draft.make_line(p1, p2))

    # Terminais e arco do disjuntor
    pl = App.Placement()
    pl.Base = App.Vector(10 * h, 5 / 2 * h, 0)
    grupo.addObject(Draft.make_circle(radius=h / 10, placement=pl, face=True, support=None))
    pl.Base = App.Vector(13 * h, 5 / 2 * h, 0)
    grupo.addObject(Draft.make_circle(radius=h / 10, placement=pl, face=True, support=None))
    pl.Base = App.Vector(11.5 * h, 5 / 2 * h, 0)
    grupo.addObject(Draft.make_circle(radius=1.5 * h, placement=pl, startangle=0, endangle=180))

    dados = planilhas.ler_quadro(planilha)
    neutro = dados["neutro"] == "True"
    terra = dados["terra"] == "True"
    desenhar_cabo_unifilar(doc, numero_fases, terra, neutro, h, App.Vector(5 * h, 2 * h, 0), grupo)

    fator = {1: 0, 2: -0.25, 3: -0.5}.get(numero_fases, 1)
    desenhar_cabo_unifilar(doc, numero_fases, False, False, h, App.Vector(11 * h + fator * h, 3.5 * h, 0), grupo)


def tem_medicao(doc, origem):
    """O quadro é alimentado por uma medição.

    Vale quando a origem do quadro é a sigla de um símbolo de medição da planta
    (quadro de medição ou medição agrupada), ou quando começa com QM, CM ou "medi".
    """
    origem = str(origem).strip().lower()
    if not origem:
        return False
    if origem.startswith(("qm", "cm", "medi")):
        return True
    for obj in doc.Objects:
        if getattr(getattr(obj, "Proxy", None), "Type", "") != "Ponto":
            continue
        if "medidores" in simbolos.CATALOGO[obj.Simbolo] and str(obj.Descricao).strip().lower() == origem:
            return True
    return False


def desenhar_medidor(h, grupo):
    """Medidor de energia na entrada do quadro: círculo com 'kWh' sobre a linha de entrada."""
    pl = App.Placement()
    pl.Base = App.Vector(2.5 * h, 5 / 2 * h, 0)
    grupo.addObject(Draft.make_circle(radius=0.9 * h, placement=pl, face=False, support=None))
    add_texto("kWh", App.Vector(1.9 * h, 2.3 * h, 0), 0, 0.45 * h, grupo)
    add_texto("Medição", App.Vector(1.4 * h, 3.6 * h, 0), 0, 0.5 * h, grupo)


def desenhar_barramentos(h, grupo, dados, circuitos):
    """Identificação do barramento de fases e as barras de neutro e de terra do quadro."""
    corrente = regras_quadro.corrente_do_barramento(dados)
    if corrente:
        add_texto(f"Barramento {corrente} A", App.Vector(18.3 * h, 4 * h, 0), 0, 0.5 * h, grupo)

    # As barras ficam embaixo do último circuito, ligadas ao barramento vertical.
    y = 5 / 2 * h - (max(circuitos, 1) - 1) * ESPACAMENTO_CIRCUITOS * h
    barras = []
    if regras_quadro.verdadeiro(dados.get("neutro", "")):
        barras.append("N")
    if regras_quadro.verdadeiro(dados.get("terra", "")):
        barras.append("PE")
    for indice, nome in enumerate(barras, start=1):
        y_barra = y - (1.5 + indice * 1.2) * h
        grupo.addObject(Draft.make_line(App.Vector(19 * h, y_barra, 0), App.Vector(23 * h, y_barra, 0)))
        add_texto(f"Barra {nome}", App.Vector(23.4 * h, y_barra - 0.2 * h, 0), 0, 0.5 * h, grupo)


def desenhar_circuito(doc, circuito, posicao, h, grupo):
    """Ramificação de um circuito: disjuntor com arco, DR, condutores, seta e textos.

    A geometria vem de ``core.unifilar.geometria`` e fica num Sketch; os textos,
    de ``core.unifilar.textos``.

    Args:
        circuito: dicionário de ``planilhas.ler_circuitos_completos``.
        posicao: ponto do barramento onde o circuito começa.
    """
    fases, neutro, terra = desenho.condutores_do_circuito(circuito)
    textos = desenho.textos(circuito)
    forma = desenho.geometria(h, dr=bool(textos.get("dr")), fases=fases, neutro=neutro, terra=terra)

    sketch = doc.addObject("Sketcher::SketchObject", "Circuito")
    pintar_sketch(sketch)
    sketch.Placement = App.Placement(posicao, App.Rotation(0, 0, 0))
    eixo = App.Vector(0, 0, 1)
    for x1, y1, x2, y2 in forma["linhas"]:
        sketch.addGeometry(Part.LineSegment(App.Vector(x1, y1, 0), App.Vector(x2, y2, 0)), False)
    for cx, cy, raio, inicio, fim in forma["arcos"]:
        circulo = Part.Circle(App.Vector(cx, cy, 0), eixo, raio)
        sketch.addGeometry(Part.ArcOfCircle(circulo, math.radians(inicio), math.radians(fim)), False)
    for cx, cy, raio in forma["circulos"]:
        sketch.addGeometry(Part.Circle(App.Vector(cx, cy, 0), eixo, raio), False)
    grupo.addObject(sketch)

    altura = desenho.ALTURA_TEXTO * h
    for chave, texto in textos.items():
        x, y = forma["textos"][chave]
        tamanho = altura * (1.25 if chave == "numero" else 1.0)
        add_texto(texto, posicao + App.Vector(x, y, 0), 0, tamanho, grupo)


def _desenhar_circuitos(doc, h, grupo, quadro):
    """Lê os circuitos da planilha de circuitos do quadro e os desenha descendo pelo barramento.

    O que estiver em branco na planilha (corrente, cabo, disjuntor) é calculado.

    Returns:
        Quantidade de circuitos desenhados.
    """
    desenhados = 0
    espacamento = ESPACAMENTO_CIRCUITOS * h
    for circuito in planilhas.ler_circuitos_completos(quadro):
        posicao = App.Vector(18 * h, 5 / 2 * h - desenhados * espacamento, 0)
        if desenhados > 0:
            anterior = App.Vector(18 * h, 5 / 2 * h - (desenhados - 1) * espacamento, 0)
            grupo.addObject(Draft.make_line(anterior, posicao))
        desenhar_circuito(doc, circuito, posicao, h, grupo)
        desenhados += 1
    return desenhados


def _remover_diagrama_anterior(doc, quadro):
    """Apaga o diagrama já gerado para o quadro, inclusive os de versões antigas."""
    antigos = [
        obj for obj in doc.Objects
        if getattr(obj, "quadro_origem", None) == quadro.Name
    ]
    legado = doc.getObject(f"diagrama_{quadro.Label}")
    if legado and legado not in antigos and not hasattr(legado, "quadro_origem"):
        antigos.append(legado)
    for grupo in antigos:
        nome = grupo.Name
        grupo.removeObjectsFromDocument()
        doc.removeObject(nome)
    if antigos:
        doc.recompute()


def _deslocar(grupo, deslocamento):
    for obj in grupo.Group:
        posicao = obj.Placement
        posicao.Base = posicao.Base + deslocamento
        obj.Placement = posicao


def gerar_diagramas(doc, quadros, h=ALTURA_PADRAO):
    """Recria o diagrama de cada quadro, substituindo o anterior se existir.

    Os diagramas são empilhados de cima para baixo, um por quadro, para não se
    sobreporem. Cada um fica na mesma pasta da planilha do quadro.
    """
    topo = 0.0
    for quadro in quadros:
        _remover_diagrama_anterior(doc, quadro)
        grupo = doc.addObject("App::DocumentObjectGroup", "diagrama")
        grupo.Label = f"diagrama_{quadro.Label}"
        grupo.addProperty("App::PropertyString", "quadro_origem", "Diagrama", "Planilha do quadro que gerou o diagrama")
        grupo.quadro_origem = quadro.Name
        pavimentos.guardar_junto(quadro, grupo)  # na pasta do quadro, se ele estiver num pavimento
        desenhar_quadro(doc, h, grupo, quadro)

        circuitos = 0
        try:
            circuitos = _desenhar_circuitos(doc, h, grupo, quadro)
        except Exception as e:
            App.Console.PrintWarning(f"Não foi possível gerar os circuitos do quadro {quadro.Label}: {e}\n")

        try:
            dados = planilhas.ler_quadro(quadro)
            if tem_medicao(doc, dados["origem"]):
                desenhar_medidor(h, grupo)
            desenhar_barramentos(h, grupo, dados, circuitos)
        except Exception as e:
            App.Console.PrintWarning(f"Não foi possível desenhar os componentes do quadro {quadro.Label}: {e}\n")

        if topo:
            _deslocar(grupo, App.Vector(0, -topo, 0))
        grupo.addProperty("App::PropertyVector", "base_diagrama", "Diagrama",
                          "Onde fica a origem do diagrama: a entrada do quadro está 2,5 alturas de texto acima")
        grupo.base_diagrama = App.Vector(0, -topo, 0)
        topo += (ALTURA_CABECALHO + max(circuitos, 1) * ESPACAMENTO_CIRCUITOS) * h

    doc.recompute()


def _desenhar_forma(doc, forma, grupo, nome):
    """Sketch com as linhas, arcos e círculos de uma forma de ``core.unifilar``, e os textos."""
    sketch = doc.addObject("Sketcher::SketchObject", nome)
    pintar_sketch(sketch)
    eixo = App.Vector(0, 0, 1)
    for x1, y1, x2, y2 in forma["linhas"]:
        sketch.addGeometry(Part.LineSegment(App.Vector(x1, y1, 0), App.Vector(x2, y2, 0)), False)
    for cx, cy, raio, inicio, fim in forma["arcos"]:
        circulo = Part.Circle(App.Vector(cx, cy, 0), eixo, raio)
        sketch.addGeometry(Part.ArcOfCircle(circulo, math.radians(inicio), math.radians(fim)), False)
    for cx, cy, raio in forma["circulos"]:
        sketch.addGeometry(Part.Circle(App.Vector(cx, cy, 0), eixo, raio), False)
    grupo.addObject(sketch)
    for x, y, texto, altura, *angulo in forma["textos"]:
        add_texto(texto, App.Vector(x, y, 0), angulo[0] if angulo else 0, altura, grupo)


POSICAO_GERADOR = (-32, 0)  # em alturas de texto: à esquerda dos diagramas dos quadros


def _quadro_geral(doc, cargas, h):
    """(nome do quadro alimentado pelo QTA, ponto de entrada do diagrama dele) — ver
    ``core.functions.Predial.gerador.quadro_geral``. Sem quadro, (None, None); sem
    diagrama gerado, (nome, None)."""
    quadros = planilhas.listar_quadros(doc)
    origens = []
    for quadro in quadros:
        try:
            origens.append((quadro.Label, planilhas.ler_quadro(quadro).get("origem", "")))
        except Exception:
            origens.append((quadro.Label, ""))
    siglas = [obj.Descricao for obj in doc.Objects
              if getattr(getattr(obj, "Proxy", None), "Type", "") == "Ponto" and getattr(obj, "Simbolo", "") == "qta"]
    nome = regras_gerador.quadro_geral(origens, siglas, cargas)
    if nome is None:
        return None, None
    quadro = next(q for q in quadros if q.Label == nome)
    diagrama = next((obj for obj in doc.Objects if getattr(obj, "quadro_origem", None) == quadro.Name
                     and hasattr(obj, "base_diagrama")), None)
    if diagrama is None:
        return nome, None
    base = diagrama.base_diagrama
    return nome, App.Vector(base.x, base.y + desenho.Y_ENTRADA_QUADRO * h, 0)


def gerar_diagrama_gerador(doc, h=ALTURA_PADRAO):
    """Recria o diagrama da transferência rede/gerador (QTA), se o projeto tiver gerador.

    O projeto tem gerador quando a planilha de cargas do gerador existe com o
    resultado gravado. O diagrama (grupo com a propriedade ``diagrama_gerador``)
    fica à esquerda dos diagramas dos quadros, ou onde o usuário o deixou, e na
    pasta do símbolo do gerador, se houver um na planta.

    Returns:
        O grupo criado, ou None se o projeto não tem gerador calculado.
    """
    folha = servico_gerador.planilha(doc)
    resumo = servico_gerador.ler_resumo(folha) if folha is not None else {}
    posicao = App.Vector(POSICAO_GERADOR[0] * h, POSICAO_GERADOR[1] * h, 0)
    for antigo in [obj for obj in doc.Objects if hasattr(obj, "diagrama_gerador")]:
        sketch = next((o for o in antigo.Group if o.TypeId == "Sketcher::SketchObject"), None)
        if sketch is not None:
            posicao = sketch.Placement.Base  # mantém onde o usuário deixou
        nome = antigo.Name
        antigo.removeObjectsFromDocument()
        doc.removeObject(nome)
    if not resumo:
        if servico_gerador.simbolo_do_gerador(doc) is not None:
            App.Console.PrintWarning("Há um gerador na planta, mas ele ainda não foi calculado: use Cálculos > "
                                     "Gerador diesel e Gravar na planilha para gerar o diagrama da transferência.\n")
        doc.recompute()
        return None
    grupo = doc.addObject("App::DocumentObjectGroup", "diagrama_gerador")
    grupo.Label = "diagrama_gerador_QTA"
    grupo.addProperty("App::PropertyString", "diagrama_gerador", "Diagrama", "Diagrama da transferência rede/gerador")
    grupo.diagrama_gerador = folha.Name
    simbolo = servico_gerador.simbolo_do_gerador(doc)
    if simbolo is not None:
        pavimentos.guardar_junto(simbolo, grupo)
    cargas = servico_gerador.cargas_no_gerador(folha)
    destino, entrada = _quadro_geral(doc, cargas, h)
    saida_ate = None
    if entrada is not None:  # alinha a saída do QTA com a entrada do quadro geral
        posicao = App.Vector(posicao.x, entrada.y - desenho.Y_SAIDA_TRANSFERENCIA * h, 0)
        saida_ate = entrada.x - posicao.x
    forma = desenho.transferencia(resumo, cargas, h, destino=destino, saida_ate=saida_ate)
    _desenhar_forma(doc, forma, grupo, "Transferencia")
    _deslocar(grupo, posicao)
    doc.recompute()
    return grupo


X_MULTIFILAR = 60  # em alturas de texto: os multifilares ficam à direita dos unifilares


def gerar_multifilares(doc, quadros, h=ALTURA_PADRAO):
    """Recria o diagrama multifilar de cada quadro (``core.multifilar``).

    Cada um é um grupo ``multifilar_<quadro>`` com a propriedade ``multifilar_de``
    (nome da planilha do quadro) e ``base_diagrama``, na pasta do quadro. Ficam
    empilhados à direita dos unifilares; o que o usuário moveu volta no mesmo lugar.

    Returns:
        Quantidade de diagramas desenhados.
    """
    topo, feitos = 0.0, 0
    for quadro in quadros:
        posicao = App.Vector(X_MULTIFILAR * h, -topo, 0)
        for antigo in [o for o in doc.Objects if getattr(o, "multifilar_de", None) == quadro.Name]:
            sketch = next((o for o in antigo.Group if o.TypeId == "Sketcher::SketchObject"), None)
            if sketch is not None:
                posicao = sketch.Placement.Base  # mantém onde o usuário deixou
            nome = antigo.Name
            antigo.removeObjectsFromDocument()
            doc.removeObject(nome)
        try:
            dados = planilhas.ler_quadro(quadro)
            circuitos = planilhas.ler_circuitos_completos(quadro)
            forma = desenho_multifilar.geometria(dados, circuitos, h)
        except Exception as e:
            App.Console.PrintWarning(f"Não foi possível montar o multifilar do quadro {quadro.Label}: {e}\n")
            continue
        grupo = doc.addObject("App::DocumentObjectGroup", "multifilar")
        grupo.Label = f"multifilar_{quadro.Label}"
        grupo.addProperty("App::PropertyString", "multifilar_de", "Diagrama", "Planilha do quadro que gerou o diagrama")
        grupo.multifilar_de = quadro.Name
        grupo.addProperty("App::PropertyVector", "base_diagrama", "Diagrama", "Origem do diagrama")
        grupo.base_diagrama = posicao
        pavimentos.guardar_junto(quadro, grupo)
        _desenhar_forma(doc, forma, grupo, "Multifilar")
        _deslocar(grupo, posicao)
        topo += forma["altura"] + 4 * h
        feitos += 1
    doc.recompute()
    return feitos
