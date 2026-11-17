"""Simbologia 2D de cabos (fase, neutro e terra) em Sketches, na planta e no unifilar."""
import FreeCAD as App
import Part

from freecad.Circuits.core.simbolos import CATALOGO, SEM_CARGA
from freecad.Circuits.core.simbologia import condutores, posicoes_fase
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


def _desenhar_simbolo_planta(doc, posicao, fases, neutro, terra, h, grupo, origem):
    """Traços de terra, neutro e fases ao lado de um ponto da planta."""
    sketch = doc.addObject("Sketcher::SketchObject", "Cabo")
    pintar_sketch(sketch)
    sketch.Placement = App.Placement(posicao + App.Vector(h / 2, h / 2, 0), App.Rotation(0, 0, 0))
    sketch.addProperty("App::PropertyString", "fiacao_de", "Fiação", "Ponto da planta a que este símbolo pertence")
    sketch.fiacao_de = origem
    if terra:
        _linha(sketch, 0, 0, 0, h / 2)
        _linha(sketch, -h / 5, h / 2, 0, h / 2)
    if neutro:
        if terra:
            _linha(sketch, h / 2, 0, h / 2, h / 2)
            _linha(sketch, h / 2 - h / 5, h / 2, h / 2 + h / 5, h / 2)
        else:
            _linha(sketch, 0, 0, 0, h / 2)
            _linha(sketch, -h / 5, h / 2, h / 5, h / 2)
    _desenhar_fases(sketch, fases, neutro, terra, h)
    grupo.addObject(sketch)


def condutores_do_ponto(obj):
    """Dados para desenhar a fiação de um símbolo da planta.

    Returns:
        (fases, neutro, terra, altura do símbolo de fiação), ou None se o
        objeto não recebe fiação (quadros, interruptores e objetos de outro tipo).
    """
    tipo = getattr(getattr(obj, "Proxy", None), "Type", "")
    if tipo == "Ponto":
        if CATALOGO[obj.Simbolo]["categoria"] in SEM_CARGA:  # quadros, comandos, passagem e aterramento
            return None
        fases, neutro = condutores(obj.Ligacao)
        return fases, neutro, True, tamanho_do_ponto(obj) / 2
    if tipo == "Outlet":
        fases, neutro = condutores("F+F" if str(obj.Tensao) == "Bifásica" else "F+N")
        return fases, neutro, True, ALTURA_SIMBOLO
    if tipo == "Lighting":
        return 1, True, True, ALTURA_SIMBOLO
    if getattr(obj, "tipo", "") == "tomada":  # tomada em Sketch (TUG)
        return int(obj.Fase), bool(obj.neutro), bool(obj.terra), ALTURA_SIMBOLO * escala_da_tomada(obj)
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
        fases, neutro, terra, h = dados
        grupo = pavimentos.pasta_do_pavimento(doc, ponto, "fiacao")
        if grupo is None:
            sem_pavimento = sem_pavimento or create_group("Cabos", doc)
            grupo = sem_pavimento
        _desenhar_simbolo_planta(doc, ponto.Placement.Base, fases, neutro, terra, h, grupo, ponto.Name)
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
