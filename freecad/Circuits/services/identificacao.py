"""Circuito e comando dos pontos da planta, e a anotação que os mostra no desenho."""
import Draft
import FreeCAD as App

from freecad.Circuits.core import circuitos as calculo
from freecad.Circuits.core import identificacao, simbolos
from freecad.Circuits.services.alinhamento import listar_simbolos

NOME_GRUPO = "Identificacao_pontos"
TAMANHO_PADRAO = 200.0  # mm, quando o símbolo não informa o próprio tamanho


def _tipo(obj):
    return getattr(getattr(obj, "Proxy", None), "Type", "")


def eh_interruptor(obj):
    return _tipo(obj) == "Switch"


def eh_ponto_de_luz(obj):
    """Ponto comandado por interruptor: iluminação e ventilador."""
    if _tipo(obj) == "Lighting":
        return True
    if _tipo(obj) == "Ponto":
        return simbolos.CATALOGO[obj.Simbolo]["tipo_circuito"] == simbolos.ILUM
    return False


def tem_circuito(obj):
    return hasattr(obj, "Circuito")


def circuitos_existentes(doc):
    """Números de circuito já usados na planta, em ordem."""
    return identificacao.ordenar_circuitos(str(obj.Circuito) for obj in listar_simbolos(doc) if tem_circuito(obj))


def _gravar_circuito(obj, circuito):
    """Grava o circuito respeitando o tipo da propriedade. Devolve True se gravou."""
    if isinstance(obj.Circuito, int):  # tomada em Sketch guarda o circuito como número inteiro
        if not str(circuito).isdigit():
            return False
        obj.Circuito = int(circuito)
    else:
        obj.Circuito = str(circuito)
    return True


def definir_circuito(doc, objetos, circuito, quadro=None):
    """Grava o circuito (e o quadro, quando o ponto tem essa propriedade) nos objetos.

    Args:
        quadro: None deixa o quadro como está; '' vale para qualquer quadro.
    Returns:
        Quantidade de objetos alterados.
    """
    circuito = str(circuito).strip()
    alterados = 0
    doc.openTransaction("Definir circuito")
    try:
        for obj in objetos:
            if not tem_circuito(obj) or not _gravar_circuito(obj, circuito):
                continue
            if quadro is not None and hasattr(obj, "Quadro"):
                obj.Quadro = quadro
            alterados += 1
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    atualizar_anotacao(doc)
    return alterados


def ligar_interruptor(doc, objetos):
    """Liga interruptores a pontos de luz: todos recebem a mesma letra de comando.

    Os interruptores também recebem o circuito do primeiro ponto de luz.

    Returns:
        A letra de comando usada.
    Raises:
        ValueError: se a seleção não tiver pelo menos um interruptor e um ponto de luz.
    """
    interruptores = [obj for obj in objetos if eh_interruptor(obj)]
    luzes = [obj for obj in objetos if eh_ponto_de_luz(obj)]
    if not interruptores or not luzes:
        raise ValueError("Selecione pelo menos um interruptor e um ponto de luz (ou ventilador).")

    nomes = {obj.Name for obj in interruptores + luzes}
    fora = [
        obj.Comando for obj in listar_simbolos(doc)
        if obj.Name not in nomes and hasattr(obj, "Comando") and (eh_interruptor(obj) or eh_ponto_de_luz(obj))
    ]
    comando = identificacao.escolher_comando([obj.Comando for obj in interruptores], fora)

    doc.openTransaction("Ligar interruptor")
    try:
        for obj in interruptores + luzes:
            obj.Comando = comando
        for obj in interruptores:
            obj.Circuito = str(luzes[0].Circuito)
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    atualizar_anotacao(doc)
    return comando


def _potencia(obj):
    if _tipo(obj) == "Ponto":
        return float(obj.Potencia)
    if _tipo(obj) in ("Outlet", "Lighting"):
        return calculo.potencia_va(obj.Potencia) * max(1, int(getattr(obj, "QtdPontos", 1)))
    return None


def _tamanho(obj):
    for nome in ("Tamanho", "RaioSimbolo"):
        valor = getattr(obj, nome, None)
        if valor is not None:
            valor = valor.Value if hasattr(valor, "Value") else float(valor)
            return valor * (1.0 if nome == "Tamanho" else 2.0)
    return TAMANHO_PADRAO


def texto_do_objeto(obj):
    """Texto de identificação do símbolo: circuito, comando e potência."""
    comando = getattr(obj, "Comando", "") if (eh_interruptor(obj) or eh_ponto_de_luz(obj)) else ""
    circuito = getattr(obj, "Circuito", "")
    return identificacao.texto_ponto(circuito, comando, _potencia(obj))


def _remover_anotacao(doc):
    anterior = doc.getObject(NOME_GRUPO)
    if anterior is None:
        return False
    anterior.removeObjectsFromDocument()
    doc.removeObject(NOME_GRUPO)
    return True


def anotar(doc):
    """Recria os textos de identificação ao lado de cada símbolo da planta.

    Returns:
        Quantidade de símbolos anotados.
    """
    _remover_anotacao(doc)
    alvos = [(obj, texto_do_objeto(obj)) for obj in listar_simbolos(doc)]
    alvos = [(obj, texto) for obj, texto in alvos if texto]
    if not alvos:
        doc.recompute()
        return 0

    grupo = doc.addObject("App::DocumentObjectGroup", NOME_GRUPO)
    grupo.Label = "Identificação dos pontos"
    for obj, texto in alvos:
        tamanho = _tamanho(obj)
        base = obj.Placement.Base
        # Embaixo e à direita do ponto de inserção, fora do desenho do símbolo.
        posicao = App.Vector(base.x + tamanho * 0.2, base.y - tamanho * 1.1, 0)
        anotacao = Draft.make_text(texto, placement=App.Placement(posicao, App.Rotation()), height=tamanho * 0.45)
        grupo.addObject(anotacao)
    doc.recompute()
    return len(alvos)


def atualizar_anotacao(doc):
    """Refaz a anotação só se ela já existe no documento."""
    if doc.getObject(NOME_GRUPO) is not None:
        anotar(doc)
    else:
        doc.recompute()
