"""Quadro de distribuição em 3D com os componentes (``core.quadro_3d``).

Para um símbolo de quadro ligado a uma planilha (propriedade ``Planilha``), recria o ``App::Part``
``<símbolo>_3D`` (propriedade ``quadro_3d_de``) com um ``Part::Feature`` por peça: caixa, placa de
montagem, trilhos, cada dispositivo (disjuntor geral, DPS, IDR, DRs e disjuntores dos circuitos),
alavancas, barramentos, isoladores e porta (transparente). Cada peça guarda ``peca_quadro`` (o tipo),
``Especificacao`` e ``Circuitos``, e tem cor própria (``ShapeColor``, sem cores por face).
O conjunto fica centrado na altura de montagem do símbolo, girado com ele, na subpasta 3D da pasta dele.
"""
import FreeCAD as App
import Part

from freecad.Circuits.core import quadro_3d as regras
from freecad.Circuits.core.simbolos import CATALOGO, QUADRO
from freecad.Circuits.services import pavimentos, planilhas

MARCA = "quadro_3d_de"
TRANSPARENCIA_PORTA = 80


def planilha_do_simbolo(doc, simbolo):
    nome = getattr(simbolo, "Planilha", "") or ""
    folha = doc.getObject(nome) if nome else None
    return folha if folha is not None and hasattr(folha, "quadro") else None


def eh_quadro_com_planilha(doc, obj):
    simbolo = getattr(obj, "Simbolo", None)
    return (simbolo in CATALOGO and CATALOGO[simbolo]["categoria"] == QUADRO
            and simbolo in ("quadro_distribuicao", "quadro_comando", "qta")
            and planilha_do_simbolo(doc, obj) is not None)


def remover(doc, nome):
    """Apaga o objeto ``nome`` e, se for um App::Part, tudo o que está dentro."""
    obj = doc.getObject(nome)
    if obj is None:
        return
    for filho in list(getattr(obj, "Group", []) or []) if obj.TypeId == "App::Part" else []:
        if doc.getObject(filho.Name) is not None and filho.TypeId != "App::Origin":
            remover(doc, filho.Name)
    if doc.getObject(nome) is not None:
        doc.removeObject(nome)


def _forma(blocos):
    solidos = [Part.makeBox(dx, dy, dz, App.Vector(x, y, z)) for (x, y, z), (dx, dy, dz)
               in ((b["origem"], b["dims"]) for b in blocos) if dx > 0 and dy > 0 and dz > 0]
    return Part.makeCompound(solidos) if len(solidos) > 1 else solidos[0]


def _propriedade(obj, tipo, nome, grupo, dica, valor):
    if not hasattr(obj, nome):
        obj.addProperty(tipo, nome, grupo, dica)
    setattr(obj, nome, valor)


def gerar(doc, simbolo):
    """Recria o quadro 3D do símbolo. Devolve o App::Part, ou None se não há planilha ligada."""
    folha = planilha_do_simbolo(doc, simbolo)
    if folha is None:
        return None
    modelo = regras.montar(planilhas.ler_quadro(folha), planilhas.ler_circuitos_completos(folha))
    nome = f"{simbolo.Name}_3D"
    remover(doc, nome)
    conjunto = doc.addObject("App::Part", nome)
    sigla = getattr(simbolo, "Descricao", "") or simbolo.Label
    conjunto.Label = f"Quadro {sigla} 3D"
    _propriedade(conjunto, "App::PropertyString", MARCA, "Quadro", "Símbolo do quadro", simbolo.Name)
    largura, profundidade, altura = modelo["dimensoes"]
    _propriedade(conjunto, "App::PropertyString", "Resumo", "Quadro", "Caixa e módulos",
                 f"{modelo['por_fileira']} módulos x {modelo['fileiras']} fileiras ({modelo['modulos_ocupados']} "
                 f"ocupados, {modelo['reserva']} de reserva); {largura:.0f} x {altura:.0f} x {profundidade:.0f} mm")
    for i, peca in enumerate(modelo["pecas"]):
        objeto = doc.addObject("Part::Feature", f"{simbolo.Name}_peca")
        objeto.Label = f"{sigla} - {peca['rotulo']}"
        objeto.Shape = _forma(peca["blocos"])
        _propriedade(objeto, "App::PropertyString", "peca_quadro", "Quadro", "Tipo da peça do quadro", peca["tipo"])
        _propriedade(objeto, "App::PropertyString", MARCA, "Quadro", "Símbolo do quadro", simbolo.Name)
        _propriedade(objeto, "App::PropertyString", "Especificacao", "Quadro", "Especificação", peca["especificacao"])
        _propriedade(objeto, "App::PropertyStringList", "Circuitos", "Quadro", "Circuitos protegidos", peca["circuitos"])
        try:
            objeto.ViewObject.ShapeColor = peca["cor"]
            if peca["tipo"] == "porta":
                objeto.ViewObject.Transparency = TRANSPARENCIA_PORTA
        except Exception:
            pass
        conjunto.addObject(objeto)
    cota = pavimentos.cota_3d(doc, simbolo)
    base = simbolo.Placement.Base
    conjunto.Placement = App.Placement(App.Vector(base.x, base.y, cota), simbolo.Placement.Rotation)
    pavimentos.guardar_3d(doc, simbolo, conjunto)
    return conjunto


def gerar_todos(doc):
    """Quadro 3D de todo símbolo de quadro ligado a uma planilha. Devolve quantos foram feitos."""
    feitos = 0
    for obj in list(doc.Objects):
        if eh_quadro_com_planilha(doc, obj):
            try:
                feitos += gerar(doc, obj) is not None
            except Exception as erro:
                App.Console.PrintError(f"Quadro 3D de {obj.Label}: {erro}\n")
    doc.recompute()
    return feitos
