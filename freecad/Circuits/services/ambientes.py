"""Ambientes em polilinha e a geração automática de tomadas, interruptor e luz (``core.ambientes``).

- ``gerar_ambientes``: um Draft Wire fechado por ambiente, a partir dos espaços da
  bancada BIM (``Arch.Space``) ou das formas fechadas selecionadas (retângulos,
  polilinhas, faces). A polilinha guarda ``NomeAmbiente``, ``TipoAmbiente``,
  ``AreaAmbiente`` (m²), ``PerimetroAmbiente`` (m) e ``ambiente_de`` (o objeto de
  origem), e fica na pasta Ambientes do pavimento, no piso dele.
- ``gerar_pontos``: tomadas, interruptor, luzes (uma no centro ou as do
  luminotécnico) e os equipamentos pedidos (chuveiro, ar-condicionado) no
  ambiente, só quando o usuário pede, com as respostas dele (``opcoes``: porta,
  bancada, chuveiro, ar-condicionado, luminotécnico; ``core.ambientes``). Os
  pontos criados levam ``AmbienteAuto`` = nome da polilinha e são substituídos se
  o comando for repetido.
"""
import Draft
import FreeCAD as App

from freecad.Circuits.core import ambientes as regras
from freecad.Circuits.core import identificacao as regras_identificacao
from freecad.Circuits.objects.ponto import create_ponto
from freecad.Circuits.objects.switch import create_switch
from freecad.Circuits.services import identificacao, pavimentos

TIPOS_DE_SIMBOLO = ("Ponto", "Switch", "Lighting", "Outlet")


def _tipo(obj):
    return getattr(getattr(obj, "Proxy", None), "Type", "")


def eh_espaco(obj):
    return _tipo(obj) == "Space"


def eh_ambiente(obj):
    return hasattr(obj, "TipoAmbiente")


def listar_espacos(doc):
    return [obj for obj in doc.Objects if eh_espaco(obj)]


def listar_ambientes(doc):
    return [obj for obj in doc.Objects if eh_ambiente(obj)]


def _contorno_de_forma(forma):
    """Vértices (x, y) do contorno de baixo da forma: a face mais baixa e maior, ou o primeiro fio fechado."""
    faces = [f for f in forma.Faces if f.BoundBox.ZLength < 1e-3]
    if faces:
        z = min(f.BoundBox.ZMin for f in faces)
        face = max((f for f in faces if abs(f.BoundBox.ZMin - z) < 1e-3), key=lambda f: f.Area)
        return [(v.Point.x, v.Point.y) for v in face.OuterWire.OrderedVertexes]
    if forma.Faces:  # sólido (espaço): a face de baixo
        z = forma.BoundBox.ZMin
        de_baixo = [f for f in forma.Faces if abs(f.BoundBox.ZMax - z) < 1e-3]
        if de_baixo:
            face = max(de_baixo, key=lambda f: f.Area)
            return [(v.Point.x, v.Point.y) for v in face.OuterWire.OrderedVertexes]
    fechados = [w for w in forma.Wires if w.isClosed()]
    if fechados:
        return [(v.Point.x, v.Point.y) for v in fechados[0].OrderedVertexes]
    return []


def contorno(obj):
    """Polígono do objeto em planta [(x, y)] mm, ou [] se ele não é uma forma fechada."""
    if _tipo(obj) in TIPOS_DE_SIMBOLO or eh_ambiente(obj):
        return []
    forma = getattr(obj, "Shape", None)
    if forma is None or forma.isNull():
        return []
    pontos = regras._limpo(_contorno_de_forma(forma))
    return pontos if len(pontos) >= 3 and regras.area_m2(pontos) > 0.1 else []


def _propriedade(obj, tipo, nome, dica, valor):
    if not hasattr(obj, nome):
        obj.addProperty(tipo, nome, "Ambiente", dica)
    setattr(obj, nome, valor)


def _pavimento_de(doc, origem):
    return pavimentos.pavimento_do_objeto(doc, origem) or pavimentos.pavimento_para_insercao(doc)


def criar_ambiente(doc, origem, pontos, nome=None, pavimento=None):
    """Polilinha fechada do ambiente, no piso do pavimento, substituindo a que já existia para a origem."""
    for antigo in [o for o in listar_ambientes(doc) if getattr(o, "ambiente_de", "") == origem.Name]:
        doc.removeObject(antigo.Name)
    pavimento = pavimento or _pavimento_de(doc, origem)
    z = pavimentos.elevacao(pavimento) if pavimento is not None else 0.0
    nome = nome or str(getattr(origem, "Label", origem.Name))
    polilinha = Draft.make_wire([App.Vector(x, y, z) for x, y in pontos], closed=True, face=False)
    polilinha.Label = f"Ambiente {nome}"
    _propriedade(polilinha, "App::PropertyString", "NomeAmbiente", "Nome do ambiente", nome)
    _propriedade(polilinha, "App::PropertyEnumeration", "TipoAmbiente", "Tipo, para a previsão da NBR 5410",
                 list(regras.TIPOS))
    polilinha.TipoAmbiente = regras.tipo_pelo_nome(nome)
    _propriedade(polilinha, "App::PropertyFloat", "AreaAmbiente", "Área [m²]", round(regras.area_m2(pontos), 2))
    _propriedade(polilinha, "App::PropertyFloat", "PerimetroAmbiente", "Perímetro [m]",
                 round(regras.perimetro_m(pontos), 2))
    _propriedade(polilinha, "App::PropertyString", "ambiente_de", "Espaço ou forma que gerou o ambiente", origem.Name)
    try:
        polilinha.ViewObject.LineColor = (0.2, 0.5, 0.2)
        polilinha.ViewObject.DrawStyle = "Dashdot"
    except Exception:
        pass
    if pavimento is not None:
        pavimentos.arquivar(doc, polilinha, pavimento)
    return polilinha


def gerar_ambientes(doc, objetos=None):
    """Polilinhas dos ambientes: das formas fechadas selecionadas ou, sem seleção, de todos os espaços do BIM.

    Returns:
        (polilinhas criadas, nomes dos objetos que não são uma forma fechada).
    """
    origens = list(objetos) if objetos else listar_espacos(doc)
    criadas, ignorados = [], []
    for origem in origens:
        pontos = contorno(origem)
        if not pontos:
            ignorados.append(getattr(origem, "Label", origem.Name))
            continue
        criadas.append(criar_ambiente(doc, origem, pontos))
    doc.recompute()
    return criadas, ignorados


def pontos_do_ambiente(ambiente):
    """Polígono da polilinha do ambiente em coordenadas globais [(x, y)]."""
    return regras._limpo([(v.x, v.y) for v in (ambiente.Placement.multVec(p) for p in ambiente.Points)])


def portas(doc):
    """[(x, y, largura)] do meio de cada porta da bancada BIM (``IfcType`` Door), em planta."""
    resultado = []
    for obj in doc.Objects:
        if str(getattr(obj, "IfcType", "")) != "Door":
            continue
        largura = getattr(obj, "Width", 800.0)
        largura = float(getattr(largura, "Value", largura) or 800.0)
        try:
            meio = obj.Placement.multVec(App.Vector(largura / 2.0, 0, 0))
        except Exception:
            continue
        resultado.append((meio.x, meio.y, largura))
    return resultado


def plano(doc, ambiente, tipo=None, opcoes=None):
    """Posições previstas (``core.ambientes.posicoes``) para o ambiente, com as portas do projeto e as opções."""
    return regras.posicoes(pontos_do_ambiente(ambiente), tipo or ambiente.TipoAmbiente, portas(doc), opcoes)


def paredes(ambiente):
    """Paredes do ambiente para o usuário escolher a porta e a bancada (``core.ambientes.paredes``)."""
    return regras.paredes(pontos_do_ambiente(ambiente))


def pontos_gerados(doc, ambiente):
    return [o for o in doc.Objects if getattr(o, "AmbienteAuto", "") == ambiente.Name]


def _marcar(obj, ambiente):
    _propriedade(obj, "App::PropertyString", "AmbienteAuto", "Ambiente que gerou o ponto automaticamente",
                 ambiente.Name)


def _posicionar(obj, x, y, z, angulo):
    obj.Placement = App.Placement(App.Vector(x, y, z), App.Rotation(App.Vector(0, 0, 1), angulo))


def _criar_ponto(doc, ambiente, pavimento, z, simbolo, x, y, angulo, potencia):
    ponto = create_ponto(simbolo)
    _posicionar(ponto, x, y, z, angulo)
    ponto.Potencia = float(potencia)
    ponto.Circuito = ""
    _marcar(ponto, ambiente)
    pavimentos.arquivar(doc, ponto, pavimento)
    return ponto


def gerar_pontos(doc, ambiente, tipo=None, opcoes=None):
    """Cria tomadas, interruptor, luzes e equipamentos do ambiente, substituindo os gerados antes para ele.

    O tipo escolhido fica gravado no ambiente. Os pontos ficam sem circuito
    (use Definir circuito); o interruptor e as luzes ficam ligados pela mesma letra.

    Returns:
        O plano usado (``core.ambientes.posicoes``).
    """
    if tipo:
        ambiente.TipoAmbiente = tipo
    resultado = plano(doc, ambiente, opcoes=opcoes)
    for antigo in pontos_gerados(doc, ambiente):
        doc.removeObject(antigo.Name)
    pavimento = pavimentos.pavimento_do_objeto(doc, ambiente) or pavimentos.garantir_ativo(doc)
    z = pavimentos.elevacao(pavimento)

    for tomada in resultado["tomadas"]:
        _criar_ponto(doc, ambiente, pavimento, z, tomada["simbolo"], tomada["x"], tomada["y"], tomada["angulo"],
                     tomada["potencia"])
    luzes = [_criar_ponto(doc, ambiente, pavimento, z, luz["simbolo"], luz["x"], luz["y"], 0.0, luz["potencia"])
             for luz in resultado["luzes"]]

    if resultado["interruptor"]:
        dados = resultado["interruptor"]
        interruptor = create_switch("Interruptor")
        _posicionar(interruptor, dados["x"], dados["y"], z, dados["angulo"])
        _marcar(interruptor, ambiente)
        pavimentos.arquivar(doc, interruptor, pavimento)
        novos = {id(interruptor)} | {id(luz) for luz in luzes}
        usados = [getattr(o, "Comando", "") for o in doc.Objects if id(o) not in novos
                  and (identificacao.eh_interruptor(o) or identificacao.eh_ponto_de_luz(o))]
        letra = regras_identificacao.proximo_comando(usados)
        interruptor.Comando = letra
        for luz in luzes:
            luz.Comando = letra

    for equipamento in resultado["equipamentos"]:
        _criar_ponto(doc, ambiente, pavimento, z, equipamento["simbolo"], equipamento["x"], equipamento["y"],
                     equipamento["angulo"], equipamento["potencia"])
    doc.recompute()
    return resultado
