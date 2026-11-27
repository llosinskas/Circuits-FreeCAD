"""Simbologia 2D de cabos (fase, neutro e terra) em Sketches, na planta e no unifilar."""
import FreeCAD as App
import Part

from freecad.Circuits.core import identificacao
from freecad.Circuits.core.simbolos import CATALOGO, COMANDO, SEM_CARGA
from freecad.Circuits.core.simbologia import fiacao, lista_de_condutores, posicoes_fase
from freecad.Circuits.objects.ponto import tamanho_do_ponto
from freecad.Circuits.services import pavimentos
from freecad.Circuits.services.documento import create_group
from freecad.Circuits.services.estilo import pintar_sketch
from freecad.Circuits.services.tomadas import escala_da_tomada

ALTURA_SIMBOLO = 100
DESLOCAMENTO = App.Vector(50, 50, 0)


def _linha(sketch, x1, y1, x2, y2):
    sketch.addGeometry(Part.LineSegment(App.Vector(x1, y1), App.Vector(x2, y2)), False)


def _novo_sketch(doc, posicao):
    sketch = doc.addObject("Sketcher::SketchObject", "Cabo")
    pintar_sketch(sketch)
    sketch.Placement = App.Placement(posicao + DESLOCAMENTO, App.Rotation(0, 0, 0))
    return sketch


def _desenhar_fases(sketch, fases, neutro, terra, h):
    for x in posicoes_fase(fases, neutro, terra, h):
        _linha(sketch, x, -h / 2, x, h / 2)


def _desenhar_simbolo_planta(doc, posicao, condutores_, h, grupo, origem):
    """Fiação ao lado de um ponto da planta: a linha e um traço por condutor (``core.simbologia.fiacao``)."""
    sketch = doc.addObject("Sketcher::SketchObject", "Cabo")
    pintar_sketch(sketch)
    sketch.Placement = App.Placement(posicao + App.Vector(h * 0.6, h * 0.9, 0), App.Rotation(0, 0, 0))
    sketch.addProperty("App::PropertyString", "fiacao_de", "Fiação", "Ponto da planta a que este símbolo pertence")
    sketch.fiacao_de = origem
    if not hasattr(sketch, "Condutores"):
        sketch.addProperty("App::PropertyString", "Condutores", "Fiação", "Condutores que chegam à caixa (F, N, R, T)")
    sketch.Condutores = "+".join(condutores_)
    desenho = fiacao(condutores_, h)
    for x1, y1, x2, y2 in desenho["linhas"]:
        _linha(sketch, x1, y1, x2, y2)
    for cx, cy, r in desenho["circulos"]:
        sketch.addGeometry(Part.Circle(App.Vector(cx, cy, 0), App.Vector(0, 0, 1), r), False)
    try:  # sem os vértices do Sketch, que pareceriam a bolinha do neutro
        sketch.ViewObject.PointSize = 1
    except Exception:
        pass
    grupo.addObject(sketch)


def _mm(valor):
    return float(valor.Value) if hasattr(valor, "Value") else float(valor)


def _tamanho_do_interruptor(obj):
    escala = float(getattr(obj, "Escala", 1.0) or 1.0)
    return 2.0 * _mm(getattr(obj, "RaioSimbolo", ALTURA_SIMBOLO / 2)) * (escala if escala > 0 else 1.0)


def condutores_do_ponto(obj):
    """Condutores que chegam à caixa do símbolo e o tamanho do desenho da fiação.

    Usa a mesma regra da identificação (``core.identificacao.condutores_no_ponto``): tomada F+N+T,
    luminária comandada R+N+T, interruptor simples F+R, paralelo F+2R, intermediário 4R...

    Returns:
        (lista de 'F', 'N', 'R', 'T', altura do traço), ou None se o objeto não recebe fiação
        (quadros, caixas de passagem, aterramento e objetos de outro tipo).
    """
    tipo = getattr(getattr(obj, "Proxy", None), "Type", "")
    if tipo == "Ponto":
        categoria = CATALOGO[obj.Simbolo]["categoria"]
        if categoria == COMANDO:  # botão de campainha e fotocélula: como interruptor
            texto = identificacao.condutores_no_ponto("interruptor", tipo_interruptor=CATALOGO[obj.Simbolo]["legenda"])
        elif categoria in SEM_CARGA:  # quadros, passagem e aterramento
            return None
        else:
            texto = identificacao.condutores_no_ponto("ponto", obj.Ligacao, getattr(obj, "Comando", ""))
        return lista_de_condutores(texto), tamanho_do_ponto(obj) / 2
    if tipo == "Switch":
        texto = identificacao.condutores_no_ponto("interruptor", tipo_interruptor=str(getattr(obj, "Tipo", "Simples")))
        return lista_de_condutores(texto), _tamanho_do_interruptor(obj)
    if tipo == "Outlet":
        return lista_de_condutores("2F+T" if str(obj.Tensao) == "Bifásica" else "F+N+T"), ALTURA_SIMBOLO
    if tipo == "Lighting":
        texto = identificacao.condutores_no_ponto("ponto", "F+N", getattr(obj, "Comando", ""))
        return lista_de_condutores(texto), ALTURA_SIMBOLO
    if getattr(obj, "tipo", "") == "tomada":  # tomada em Sketch (TUG)
        partes = ["F"] * max(1, int(obj.Fase)) + (["N"] if bool(obj.neutro) else []) + (["T"] if bool(obj.terra) else [])
        return partes, ALTURA_SIMBOLO * escala_da_tomada(obj)
    return None


def listar_pontos_com_fiacao(doc):
    """Símbolos da planta que recebem fiação: tomadas, pontos de energia e iluminação."""
    return [obj for obj in doc.Objects if condutores_do_ponto(obj) is not None]


def _remover_fiacao(doc):
    for obj in [o for o in doc.Objects if hasattr(o, "fiacao_de")]:
        doc.removeObject(obj.Name)


def desenhar_cabos_planta(doc, pontos=None):
    """Recria o símbolo de fiação de cada ponto da planta.

    Cada desenho vai para a pasta Fiação do pavimento do ponto; pontos fora de
    um pavimento ficam no grupo Cabos.

    A fiação anterior feita por este comando é apagada antes, então repetir o
    comando atualiza o desenho em vez de duplicar.

    Returns:
        Quantidade de pontos que receberam fiação.
    """
    if pontos is None:
        pontos = listar_pontos_com_fiacao(doc)
    _remover_fiacao(doc)
    sem_pavimento = None
    desenhados = 0
    for ponto in pontos:
        dados = condutores_do_ponto(ponto)
        if dados is None:
            continue
        lista, h = dados
        grupo = pavimentos.pasta_do_pavimento(doc, ponto, "fiacao")
        if grupo is None:
            sem_pavimento = sem_pavimento or create_group("Cabos", doc)
            grupo = sem_pavimento
        _desenhar_simbolo_planta(doc, ponto.Placement.Base, lista, h, grupo, ponto.Name)
        desenhados += 1
    doc.recompute()
    return desenhados


def desenhar_cabo_unifilar(doc, fases, terra, neutro, h, posicao, grupo):
    """Símbolo do cabo no diagrama unifilar (traços de neutro e terra diferem da planta)."""
    sketch = _novo_sketch(doc, posicao)
    if terra:
        _linha(sketch, 0, 0, 0, h / 2)
        _linha(sketch, -h / 5, h / 2, h / 5, h / 2)
    if neutro:
        if terra:
            _linha(sketch, h / 2, -h / 2, h / 2, h / 2)
            _linha(sketch, -h / 5 + h / 2, h / 2, h / 2, h / 2)
        else:
            _linha(sketch, 0, -h / 2, 0, h / 2)
            _linha(sketch, -h / 5, h / 2, 0, h / 2)
    _desenhar_fases(sketch, fases, neutro, terra, h)
    grupo.addObject(sketch)
