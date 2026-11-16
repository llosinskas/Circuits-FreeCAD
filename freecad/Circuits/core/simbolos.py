"""Catálogo e geometria dos símbolos de pontos elétricos em planta, sem FreeCAD.

Cada símbolo é descrito em coordenadas unitárias (1.0 = tamanho do símbolo) e
devolvido como uma lista de primitivas, para ser desenhado por qualquer camada:

    ("linha", x1, y1, x2, y2)
    ("circulo", cx, cy, raio)
    ("arco", cx, cy, raio, angulo_inicial, angulo_final)   # graus, anti-horário

A origem (0, 0) é o ponto de inserção: o encosto na parede, para tomadas e
arandelas, ou o centro, para pontos de teto.
"""
import math

TOMADA = "Tomada"
ENERGIA = "Energia"
ILUMINACAO = "Iluminação"

# Tipo de circuito conforme a NBR 5410: iluminação, tomadas de uso geral (TUG)
# e tomadas de uso específico (TUE), que têm circuito exclusivo.
ILUM, TUG, TUE = "ILUM", "TUG", "TUE"

LIGACOES = {"F+N": 1, "F+F": 2, "3F": 3}  # número de fases de cada ligação


def _ponto(legenda, dica, categoria, tipo, potencia, fp, tensao, ligacao, altura, caixa=(60.0, 40.0, 100.0)):
    return {
        "legenda": legenda,
        "dica": dica,
        "categoria": categoria,
        "tipo_circuito": tipo,
        "potencia_va": potencia,
        "fator_potencia": fp,
        "tensao": tensao,  # V
        "ligacao": ligacao,
        "altura_mm": altura,  # altura de montagem em relação ao piso
        "caixa_mm": caixa,  # largura, profundidade, altura da caixa 3D
    }


# A ordem deste dicionário é a ordem dos botões nas barras.
CATALOGO = {
    "tomada_baixa": _ponto("Tomada baixa", "Tomada a 0,30 m do piso", TOMADA, TUG, 100, 0.8, 127, "F+N", 300),
    "tomada_media": _ponto("Tomada média", "Tomada a 1,30 m do piso", TOMADA, TUG, 100, 0.8, 127, "F+N", 1300),
    "tomada_alta": _ponto("Tomada alta", "Tomada a 2,00 m do piso", TOMADA, TUG, 100, 0.8, 127, "F+N", 2000),
    "tomada_piso": _ponto("Tomada de piso", "Tomada em caixa de piso", TOMADA, TUG, 100, 0.8, 127, "F+N", 0),
    "chuveiro": _ponto("Chuveiro", "Ponto para chuveiro elétrico, em circuito exclusivo", ENERGIA, TUE, 5500, 1.0, 220, "F+F", 2200),
    "ar_condicionado": _ponto("Ar-condicionado", "Ponto para ar-condicionado, em circuito exclusivo", ENERGIA, TUE, 1500, 0.9, 220, "F+F", 2200),
    "ventilador": _ponto("Ventilador", "Ponto para ventilador de teto", ENERGIA, ILUM, 100, 0.8, 127, "F+N", 2800, (100.0, 100.0, 50.0)),
    "ponto_forca": _ponto("Ponto de força", "Ponto de força para equipamento de uso específico", ENERGIA, TUE, 1000, 0.9, 220, "F+F", 300),
    "luz_teto": _ponto("Luz de teto", "Ponto de luz no teto", ILUMINACAO, ILUM, 100, 1.0, 127, "F+N", 2800, (100.0, 100.0, 50.0)),
    "arandela": _ponto("Arandela", "Ponto de luz na parede", ILUMINACAO, ILUM, 100, 1.0, 127, "F+N", 2100),
    "fluorescente": _ponto("Luminária tubular", "Luminária tubular (fluorescente ou LED) no teto", ILUMINACAO, ILUM, 40, 0.9, 127, "F+N", 2800, (1200.0, 100.0, 50.0)),
    "embutida": _ponto("Luz embutida", "Luminária embutida ou spot no forro", ILUMINACAO, ILUM, 20, 1.0, 127, "F+N", 2800, (100.0, 100.0, 50.0)),
    "emergencia": _ponto("Luz de emergência", "Luminária de emergência autônoma", ILUMINACAO, ILUM, 30, 0.9, 127, "F+N", 2300),
}

_BASE = 1 / 3  # posição X da base do triângulo de tomada
_MEIA = 1 / 4  # meia altura da base do triângulo


def _triangulo():
    return [
        ("linha", 0, 0, _BASE, 0),
        ("linha", _BASE, _MEIA, _BASE, -_MEIA),
        ("linha", _BASE, _MEIA, 1, 0),
        ("linha", _BASE, -_MEIA, 1, 0),
    ]


def _hachura_triangulo(so_metade):
    """Traços verticais dentro do triângulo: cheio (alta) ou só embaixo (média)."""
    linhas = []
    for passo in range(1, 6):
        x = _BASE + passo * (1 - _BASE) / 6
        meia = _MEIA * (1 - x) / (1 - _BASE)
        linhas.append(("linha", x, -meia, x, 0 if so_metade else meia))
    if so_metade:
        linhas.append(("linha", _BASE, 0, 1, 0))
    return linhas


def _retangulo(x1, y1, x2, y2):
    return [
        ("linha", x1, y1, x2, y1),
        ("linha", x2, y1, x2, y2),
        ("linha", x2, y2, x1, y2),
        ("linha", x1, y2, x1, y1),
    ]


def _polar(raio, graus):
    return raio * math.cos(math.radians(graus)), raio * math.sin(math.radians(graus))


def _pas_ventilador():
    linhas = []
    for graus in (90, 210, 330):
        ponta = _polar(0.42, graus)
        for lado in (-40, 40):
            raiz = _polar(0.1, graus + lado)
            linhas.append(("linha", raiz[0], raiz[1], ponta[0], ponta[1]))
    return linhas


def _unitario(simbolo):
    if simbolo == "tomada_baixa":
        return _triangulo()
    if simbolo == "tomada_media":
        return _triangulo() + _hachura_triangulo(so_metade=True)
    if simbolo == "tomada_alta":
        return _triangulo() + _hachura_triangulo(so_metade=False)
    if simbolo == "tomada_piso":
        return _triangulo() + _retangulo(0.2, -0.4, 1.1, 0.4)
    if simbolo == "chuveiro":
        return [
            ("circulo", 0, 0, 0.5),
            ("linha", -0.22, 0.15, 0.22, 0.15),
            ("linha", -0.15, 0.15, -0.25, -0.25),
            ("linha", 0, 0.15, 0, -0.3),
            ("linha", 0.15, 0.15, 0.25, -0.25),
        ]
    if simbolo == "ar_condicionado":
        return _retangulo(-0.6, -0.25, 0.6, 0.25) + [
            ("linha", -0.45, 0.08, 0.45, 0.08),
            ("linha", -0.45, -0.08, 0.45, -0.08),
        ]
    if simbolo == "ventilador":
        return [("circulo", 0, 0, 0.5), ("circulo", 0, 0, 0.1)] + _pas_ventilador()
    if simbolo == "ponto_forca":
        return _retangulo(-0.4, -0.4, 0.4, 0.4) + [
            ("linha", -0.4, -0.4, 0.4, 0.4),
            ("linha", -0.4, 0.4, 0.4, -0.4),
        ]
    if simbolo == "luz_teto":
        return [("circulo", 0, 0, 0.5), ("linha", -0.5, 0, 0.5, 0), ("linha", 0, -0.5, 0, 0.5)]
    if simbolo == "arandela":
        return [("arco", 0, 0, 0.5, 0, 180), ("linha", -0.5, 0, 0.5, 0), ("linha", 0, 0, 0, 0.5)]
    if simbolo == "fluorescente":
        return _retangulo(-0.6, -0.15, 0.6, 0.15) + [("linha", -0.6, 0, 0.6, 0)]
    if simbolo == "embutida":
        return _retangulo(-0.4, -0.4, 0.4, 0.4) + [("circulo", 0, 0, 0.28)]
    if simbolo == "emergencia":
        return _retangulo(-0.5, -0.28, 0.5, 0.28) + [
            ("linha", -0.5, -0.28, 0.5, 0.28),
            ("linha", -0.5, 0.28, 0.5, -0.28),
        ]
    raise KeyError(f"Símbolo desconhecido: {simbolo}")


def geometria(simbolo, tamanho=1.0):
    """Primitivas do símbolo, escaladas para ``tamanho`` (mesma unidade do desenho)."""
    escaladas = []
    for primitiva in _unitario(simbolo):
        tipo = primitiva[0]
        if tipo == "arco":  # os ângulos não escalam
            escaladas.append((tipo, *(v * tamanho for v in primitiva[1:4]), primitiva[4], primitiva[5]))
        else:
            escaladas.append((tipo, *(v * tamanho for v in primitiva[1:])))
    return escaladas


def limites(simbolo, tamanho=1.0):
    """Caixa envolvente do símbolo: (xmin, ymin, xmax, ymax)."""
    xs, ys = [], []
    for primitiva in geometria(simbolo, tamanho):
        if primitiva[0] == "linha":
            xs += [primitiva[1], primitiva[3]]
            ys += [primitiva[2], primitiva[4]]
        else:  # círculo ou arco: usa o círculo inteiro, que é o pior caso
            _, cx, cy, raio = primitiva[:4]
            xs += [cx - raio, cx + raio]
            ys += [cy - raio, cy + raio]
    return min(xs), min(ys), max(xs), max(ys)
