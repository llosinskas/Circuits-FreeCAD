"""Caixas 3D de interruptores, tomadas e pontos de iluminação."""
import FreeCAD as App
import Part

from freecad.Circuits.core.simbolos import CATALOGO, ENERGIA, QUADRO, TOMADA
from freecad.Circuits.services import pavimentos
from freecad.Circuits.services.tomadas import listar_tomadas

COR_INTERRUPTOR = (0.9, 0.85, 0.7)
COR_TOMADA = (0.7, 0.85, 0.95)
COR_ILUMINACAO = (1.0, 0.95, 0.6)
COR_ENERGIA = (0.95, 0.75, 0.7)
COR_QUADRO = (0.75, 0.9, 0.75)
TIPOS_COM_CAIXA = ("Switch", "Lighting", "Outlet", "Ponto")


def _valor(propriedade):
    return propriedade.Value if hasattr(propriedade, "Value") else float(propriedade)


def listar_alvos(doc):
    """Devolve (objetos FeaturePython, tomadas em Sketch) que podem receber caixa."""
    objetos = [
        obj for obj in doc.Objects
        if hasattr(obj, "Proxy") and hasattr(obj.Proxy, "Type") and obj.Proxy.Type in TIPOS_COM_CAIXA
    ]
    tomadas = [obj for obj in listar_tomadas(doc) if obj not in objetos]
    return objetos, tomadas


def _criar_caixa(doc, obj, largura, profundidade, altura, elevacao, label, cor):
    """Cria ou substitui a caixa do objeto. Devolve True se foi criada."""
    if largura <= 0 or profundidade <= 0 or altura <= 0:
        App.Console.PrintWarning(f"Dimensões inválidas para {obj.Label}, ignorando.\n")
        return False

    pos = obj.Placement.Base
    origem = App.Vector(pos.x - largura / 2.0, pos.y - profundidade / 2.0, elevacao - altura / 2.0)

    nome = f"{obj.Name}_3D"
    if doc.getObject(nome):
        doc.removeObject(nome)

    caixa = doc.addObject("Part::Feature", nome)
    caixa.Shape = Part.makeBox(largura, profundidade, altura, origem)
    caixa.Label = label
    caixa.ViewObject.ShapeColor = cor
    caixa.ViewObject.Transparency = 30
    return True


def _rotulo_e_cor(obj):
    tipo = obj.Proxy.Type
    if tipo == "Switch":
        return f"Caixa Interruptor ({obj.Label})", COR_INTERRUPTOR
    if tipo == "Outlet":
        return f"Caixa Tomada ({obj.Label})", COR_TOMADA
    if tipo == "Ponto":
        categoria = CATALOGO[obj.Simbolo]["categoria"]
        cor = {TOMADA: COR_TOMADA, ENERGIA: COR_ENERGIA, QUADRO: COR_QUADRO}.get(categoria, COR_ILUMINACAO)
        return f"Caixa {categoria} ({obj.Label})", cor
    return f"Caixa Iluminação ({obj.Label})", COR_ILUMINACAO


def gerar_caixas(doc, objetos, tomadas):
    """Gera as caixas dos alvos de ``listar_alvos``. Devolve quantas foram criadas."""
    criadas = 0

    for obj in objetos:
        try:
            label, cor = _rotulo_e_cor(obj)
            criadas += _criar_caixa(
                doc, obj,
                _valor(obj.CaixaLargura), _valor(obj.CaixaProfundidade), _valor(obj.CaixaAltura),
                _valor(obj.Altura3D) + pavimentos.elevacao_do_objeto(doc, obj),
                label, cor,
            )
        except Exception as e:
            App.Console.PrintError(f"Erro ao gerar 3D para {obj.Label}: {e}\n")

    for obj in tomadas:
        try:
            criadas += _criar_caixa(
                doc, obj,
                float(getattr(obj, "CaixaLargura", 60.0)),
                float(getattr(obj, "CaixaProfundidade", 40.0)),
                float(getattr(obj, "CaixaAltura", 100.0)),
                float(getattr(obj, "altura_piso", 30.0)) + pavimentos.elevacao_do_objeto(doc, obj),
                f"Caixa Tomada ({obj.Label})", COR_TOMADA,
            )
        except Exception as e:
            App.Console.PrintError(f"Erro ao gerar 3D para {obj.Label}: {e}\n")

    doc.recompute()
    return criadas
