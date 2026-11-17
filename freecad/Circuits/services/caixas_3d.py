"""Caixas 3D de interruptores, tomadas e pontos de iluminação."""
import FreeCAD as App
import Part

from freecad.Circuits.core.simbolos import (ATERRAMENTO, CATALOGO, ENERGIA, PASSAGEM, QUADRO, TOMADA, caixa_local,
                                            posicao_da_caixa)
from freecad.Circuits.services import pavimentos
from freecad.Circuits.services.tomadas import listar_tomadas

COR_INTERRUPTOR = (0.9, 0.85, 0.7)
COR_TOMADA = (0.7, 0.85, 0.95)
COR_ILUMINACAO = (1.0, 0.95, 0.6)
COR_ENERGIA = (0.95, 0.75, 0.7)
COR_QUADRO = (0.75, 0.9, 0.75)
COR_PASSAGEM = (0.8, 0.8, 0.8)
COR_ATERRAMENTO = (0.45, 0.65, 0.35)
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
    """Cria ou substitui a caixa do objeto. Devolve True se foi criada.

    A caixa é montada no sistema do símbolo (``core.simbolos.caixa_local``) e
    girada com ele: nas tomadas de parede ela fica atrás do ponto de inserção,
    dentro da parede; na tomada de piso, embaixo do piso; nos outros, centrada.
    """
    if largura <= 0 or profundidade <= 0 or altura <= 0:
        App.Console.PrintWarning(f"Dimensões inválidas para {obj.Label}, ignorando.\n")
        return False

    pos = obj.Placement.Base
    x, y, z, dx, dy, dz = caixa_local(posicao_da_caixa(getattr(obj, "Simbolo", "")), largura, profundidade, altura)

    nome = f"{obj.Name}_3D"
    if doc.getObject(nome):
        doc.removeObject(nome)

    caixa = doc.addObject("Part::Feature", nome)
    caixa.Shape = Part.makeBox(dx, dy, dz, App.Vector(x, y, z))
    caixa.Placement = App.Placement(App.Vector(pos.x, pos.y, elevacao), obj.Placement.Rotation)
    caixa.Label = label
    caixa.ViewObject.ShapeColor = cor
    caixa.ViewObject.Transparency = 30
    pavimentos.guardar_3d(doc, obj, caixa)  # ex.: Térreo > Tomadas > Tomadas 3D
    return True


def _rotulo_e_cor(obj):
    tipo = obj.Proxy.Type
    if tipo == "Switch":
        return f"Caixa Interruptor ({obj.Label})", COR_INTERRUPTOR
    if tipo == "Outlet":
        return f"Caixa Tomada ({obj.Label})", COR_TOMADA
    if tipo == "Ponto":
        categoria = CATALOGO[obj.Simbolo]["categoria"]
        cor = {
            TOMADA: COR_TOMADA, ENERGIA: COR_ENERGIA, QUADRO: COR_QUADRO,
            PASSAGEM: COR_PASSAGEM, ATERRAMENTO: COR_ATERRAMENTO,
        }.get(categoria, COR_ILUMINACAO)
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
                pavimentos.cota_3d(doc, obj),  # piso do pavimento + altura de montagem
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
                pavimentos.cota_3d(doc, obj),
                f"Caixa Tomada ({obj.Label})", COR_TOMADA,
            )
        except Exception as e:
            App.Console.PrintError(f"Erro ao gerar 3D para {obj.Label}: {e}\n")

    doc.recompute()
    return criadas
