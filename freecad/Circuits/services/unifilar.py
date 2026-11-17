"""Geração do diagrama unifilar a partir das planilhas de quadro."""
import Draft
import FreeCAD as App
import Part

from freecad.Circuits.core import quadro as regras_quadro
from freecad.Circuits.core import simbolos
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
        identificacao = planilha.get("indentificacao_painel")
        bitola = planilha.get("bitola")
        origem = planilha.get("origem")
        descricao = planilha.get("descricao")
        tensao = planilha.get("tensao")
        numero_fases = planilha.get("numero_fases")
        curva_disjuntor = planilha.get("curva_disjuntor")
        corrente_nominal = planilha.get("corrente_nominal_disjuntor")
        corrente_cc = planilha.get("corrente_curto_circuito")
        potencia_instalada = planilha.get("potencia_instalada")
        potencia_demanda = planilha.get("potencia_demanda")
        material = planilha.get("material_quadro")
        tem_dps = planilha.get("DPS")

        add_texto(origem, App.Vector(-h * 0.5, 0.5 * h, 0), 90, h, grupo)
        add_texto(f"#{bitola}", App.Vector(5 * h, h, 0), 0, h, grupo)
        add_texto(f"{curva_disjuntor} {corrente_nominal}A", App.Vector(10 * h, 5 * h, 0), 0, h, grupo)
        add_texto(f"{corrente_cc}kA", App.Vector(13 * h, 3 * h, 0), 0, h, grupo)
        add_texto(f"Material: {material}", App.Vector(0, -2 * h, 0), 0, h, grupo)
        add_texto(f"Potência Instalada:{potencia_instalada} kW", App.Vector(0, -3 * h, 0), 0, h, grupo)
        add_texto(f"Demanda:{potencia_demanda} kW", App.Vector(0, -4 * h, 0), 0, h, grupo)
        curto = planilha.get("curto_circuito")
        add_texto(f"Nível de curto circuito no ponto {curto} kA", App.Vector(0, -5 * h, 0), 0, h, grupo)
        add_texto(f"{descricao}", App.Vector(0, -6 * h, 0), 0, h, grupo)
        add_texto(identificacao, App.Vector(0, 5 * h, 0), 0, h, grupo)
        add_texto(f"{tensao}V", App.Vector(5 * h, 5 * h, 0), 0, h, grupo)

        if tem_dps == "True":
            classe_dps = planilha.get("classe_DPS")
            tensao_dps = planilha.get("tensao_DPS")
            corrente_dps = planilha.get("corrente_DPS")
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

    neutro = planilha.get("neutro") == "True"
    terra = planilha.get("terra") == "True"
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


def desenhar_circuito(doc, potencia, dr, bitola, posicao, corrente, comprimento, grupo, protecao="", fases=""):
    """Ramificação horizontal de um circuito, com disjuntor e DR opcional.

    ``protecao`` (ex.: 'C16A') substitui a corrente de projeto ao lado do
    disjuntor; ``fases`` (ex.: 'R' ou 'RS') aparece embaixo dele.
    """
    sketch = doc.addObject("Sketcher::SketchObject", "Circuito")
    pintar_sketch(sketch)
    sketch.Placement = posicao

    def linha(x1, y1, x2, y2):
        sketch.addGeometry(Part.LineSegment(App.Vector(x1, y1), App.Vector(x2, y2)), False)

    tamanho = comprimento * 7
    linha(0, 0, tamanho, 0)
    # Seta na ponta direita
    linha(tamanho, 0, tamanho - comprimento / 3, comprimento / 4)
    linha(tamanho, 0, tamanho - comprimento / 3, -comprimento / 4)
    # Disjuntor do circuito, cruzando a linha
    linha(tamanho / 5, -comprimento / 4, tamanho / 5, comprimento / 4)

    if dr:
        lado = comprimento / 1.5
        x_dr = tamanho / 2
        linha(x_dr - lado / 2, -lado / 2, x_dr + lado / 2, -lado / 2)
        linha(x_dr - lado / 2, lado / 2, x_dr + lado / 2, lado / 2)
        linha(x_dr - lado / 2, -lado / 2, x_dr - lado / 2, lado / 2)
        linha(x_dr + lado / 2, -lado / 2, x_dr + lado / 2, lado / 2)
        add_texto("DR", posicao.Base + App.Vector(x_dr, lado, 0), 0, comprimento / 3, grupo)

    grupo.addObject(sketch)

    y_texto = comprimento / 3
    altura = comprimento / 2.5
    x_disjuntor = tamanho / 5 + comprimento / 4
    if protecao:
        add_texto(protecao, posicao.Base + App.Vector(x_disjuntor, y_texto, 0), 0, altura, grupo)
    elif corrente:
        add_texto(f"{corrente}A", posicao.Base + App.Vector(x_disjuntor, y_texto, 0), 0, altura, grupo)
    if fases:
        add_texto(fases, posicao.Base + App.Vector(x_disjuntor, -y_texto - altura, 0), 0, altura, grupo)
    if bitola:
        add_texto(f"#{bitola}", posicao.Base + App.Vector(tamanho / 2 - comprimento, y_texto, 0), 0, altura, grupo)
    if potencia:
        add_texto(f"{potencia}W", posicao.Base + App.Vector(tamanho - comprimento * 2, y_texto, 0), 0, altura, grupo)


def _desenhar_circuitos(doc, h, grupo, quadro):
    """Lê os circuitos da planilha de circuitos do quadro e os desenha descendo pelo barramento.

    O que estiver em branco na planilha (corrente, cabo, disjuntor) é calculado.

    Returns:
        Quantidade de circuitos desenhados.
    """
    desenhados = 0
    espacamento = ESPACAMENTO_CIRCUITOS * h
    for circuito in planilhas.ler_circuitos_completos(quadro):
        numero = circuito["N_circuito"]
        destino = circuito["Destino"]
        potencia = circuito["Potencia"]
        corrente = circuito["Corrente"]
        bitola = circuito["Cabo"]
        disjuntor = circuito["Disjuntor"]
        dr = circuito["DR"].lower() == "true"
        protecao = f"{circuito['Curva']}{disjuntor}A" if disjuntor else ""
        fases = "".join(fase for fase in "RST" if circuito[f"Fase_{fase}"].lower() == "true")

        posicao = App.Vector(18 * h, 5 / 2 * h - desenhados * espacamento, 0)
        if desenhados > 0:
            anterior = App.Vector(18 * h, 5 / 2 * h - (desenhados - 1) * espacamento, 0)
            grupo.addObject(Draft.make_line(anterior, posicao))

        desenhar_circuito(
            doc, potencia, dr, bitola, App.Placement(posicao, App.Rotation(0, 0, 0)), corrente, h, grupo,
            protecao=protecao, fases=fases,
        )

        ponta = posicao + App.Vector(h * 7 + h / 2, 0, 0)
        add_texto(f"Circ. {numero}", ponta + App.Vector(0, h / 3, 0), 0, h * 0.5, grupo)
        if destino:
            add_texto(destino, ponta + App.Vector(0, -h / 2, 0), 0, h * 0.5, grupo)

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
        topo += (ALTURA_CABECALHO + max(circuitos, 1) * ESPACAMENTO_CIRCUITOS) * h

    doc.recompute()
