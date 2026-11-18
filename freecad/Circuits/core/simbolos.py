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
QUADRO = "Quadro"  # quadros e medição: aparecem na planta, mas não são carga de circuito
COMANDO = "Comando"  # botão de campainha e fotocélula: comandam outros pontos, como um interruptor
PASSAGEM = "Passagem"  # caixa de passagem: só um nó da rede de eletrodutos
ATERRAMENTO = "Aterramento"  # haste, caixa de inspeção e BEP

# Categorias sem carga própria: não entram nos circuitos nem na demanda.
SEM_CARGA = (QUADRO, COMANDO, PASSAGEM, ATERRAMENTO)

# Tipo de circuito conforme a NBR 5410: iluminação, tomadas de uso geral (TUG)
# e tomadas de uso específico (TUE), que têm circuito exclusivo.
ILUM, TUG, TUE = "ILUM", "TUG", "TUE"

LIGACOES = {"F+N": 1, "F+F": 2, "3F": 3}  # número de fases de cada ligação


def _ponto(legenda, dica, categoria, tipo, potencia, fp, tensao, ligacao, altura, caixa=(60.0, 40.0, 100.0)):
    return {
        "descricao": legenda,  # texto inicial da propriedade Descricao
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



def _quadro(legenda, dica, sigla, altura, caixa, medidores=None):
    """Quadro ou medição: sem carga própria, identificado pela sigla (QD1, QM...)."""
    dados = _ponto(legenda, dica, QUADRO, None, 0, 1.0, 220, "3F", altura, caixa)
    dados["descricao"] = sigla
    if medidores is not None:
        dados["medidores"] = medidores  # quantidade inicial de medidores
    return dados


CATALOGO.update({
    "quadro_distribuicao": _quadro(
        "Quadro distribuição", "Quadro de distribuição e proteção dos circuitos (QD)", "QD", 1500, (400.0, 100.0, 500.0)),
    "quadro_comando": _quadro(
        "Quadro de comando", "Quadro de comando e proteção de motores: bombas, pressurização, portões (QC)",
        "QC", 1500, (600.0, 200.0, 800.0)),
    "quadro_medicao": _quadro(
        "Quadro de medição", "Caixa de medição individual, com um medidor (QM)", "QM", 1600, (300.0, 200.0, 500.0), 1),
    "medicao_agrupada": _quadro(
        "Medição agrupada", "Centro de medição agrupada, com vários medidores (CM)",
        "CM", 1200, (1500.0, 250.0, 1200.0), 6),
    "gerador": _quadro(
        "Grupo gerador", "Grupo motor-gerador diesel (GMG), dimensionado pelo botão Gerador diesel",
        "GMG", 0, (2500.0, 1000.0, 1500.0)),
    "qta": _quadro(
        "Quadro transferência", "Quadro de transferência automática entre a rede e o gerador (QTA)",
        "QTA", 1500, (800.0, 300.0, 1200.0)),
})

CATALOGO.update({
    # Campainha e comando automático de iluminação
    "campainha": _ponto("Campainha", "Campainha ou cigarra, comandada por botão", ENERGIA, ILUM, 20, 1.0, 127, "F+N",
                        2200),
    "botao_campainha": _ponto("Botão de campainha", "Botão (pulsador) que comanda a campainha", COMANDO, ILUM, 0,
                              1.0, 127, "F+N", 1300),
    "fotocelula": _ponto("Fotocélula", "Relé fotoelétrico que liga a iluminação ao anoitecer", COMANDO, ILUM, 0,
                         1.0, 127, "F+N", 2500),
    # Infraestrutura
    "caixa_passagem": _ponto("Caixa de passagem", "Caixa de passagem da rede de eletrodutos", PASSAGEM, None, 0,
                             1.0, 127, "F+N", 2800, (100.0, 100.0, 50.0)),
    # Aterramento: as alturas ficam abaixo do piso (negativas)
    "haste_aterramento": _ponto("Haste de aterramento", "Haste de aterramento cravada no solo", ATERRAMENTO, None,
                                0, 1.0, 127, "F+N", -1200, (16.0, 16.0, 2400.0)),
    "caixa_inspecao": _ponto("Caixa de inspeção", "Caixa de inspeção do aterramento, sobre a haste", ATERRAMENTO,
                             None, 0, 1.0, 127, "F+N", -150, (300.0, 300.0, 300.0)),
    "bep": _ponto("BEP", "Barramento de equipotencialização principal", ATERRAMENTO, None, 0, 1.0, 127, "F+N", 300,
                  (300.0, 60.0, 100.0)),
})

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


def _terra(x, topo, escala=1.0):
    """Símbolo de terra: haste vertical e três traços que diminuem para baixo."""
    base = topo - 0.45 * escala
    return [
        ("linha", x, topo, x, base),
        ("linha", x - 0.35 * escala, base, x + 0.35 * escala, base),
        ("linha", x - 0.22 * escala, base - 0.12 * escala, x + 0.22 * escala, base - 0.12 * escala),
        ("linha", x - 0.09 * escala, base - 0.24 * escala, x + 0.09 * escala, base - 0.24 * escala),
    ]


def _medidor(x):
    """Mostrador de um medidor: círculo com o ponteiro."""
    return [("circulo", x, 0, 0.18), ("linha", x, 0, x + 0.1, 0.1)]


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
    if simbolo == "quadro_distribuicao":
        # Retângulo com a diagonal e a metade de baixo hachurada.
        hachura = [("linha", x, -0.25, x, -0.25 + (0.6 - x) * 0.5 / 1.2) for x in (-0.4, -0.2, 0.0, 0.2, 0.4)]
        return _retangulo(-0.6, -0.25, 0.6, 0.25) + [("linha", -0.6, 0.25, 0.6, -0.25)] + hachura
    if simbolo == "quadro_comando":
        # Retângulo em três painéis, com a diagonal no painel do meio.
        return _retangulo(-0.6, -0.25, 0.6, 0.25) + [
            ("linha", -0.2, -0.25, -0.2, 0.25),
            ("linha", 0.2, -0.25, 0.2, 0.25),
            ("linha", -0.2, -0.25, 0.2, 0.25),
        ]
    if simbolo == "quadro_medicao":
        return _retangulo(-0.45, -0.3, 0.45, 0.3) + _medidor(0.0)
    if simbolo == "medicao_agrupada":
        return _retangulo(-0.8, -0.3, 0.8, 0.3) + _medidor(-0.5) + _medidor(0.0) + _medidor(0.5)
    if simbolo == "gerador":
        # Círculo com a senoide da corrente alternada.
        return [("circulo", 0, 0, 0.5), ("arco", -0.15, 0, 0.15, 0, 180), ("arco", 0.15, 0, 0.15, 180, 360)]
    if simbolo == "qta":
        # Retângulo com as duas entradas (rede e gerador) e a chave que escolhe uma delas.
        return _retangulo(-0.6, -0.3, 0.6, 0.3) + [
            ("linha", -0.6, 0.15, -0.25, 0.15),
            ("linha", -0.6, -0.15, -0.25, -0.15),
            ("linha", -0.25, 0.15, 0.15, 0.0),
            ("linha", -0.25, -0.15, 0.05, -0.2),
            ("linha", 0.15, 0.0, 0.6, 0.0),
        ]
    if simbolo == "campainha":
        # Sino: cúpula com a base e o badalo embaixo.
        return [("arco", 0, 0, 0.45, 0, 180), ("linha", -0.5, 0, 0.5, 0), ("circulo", 0, -0.14, 0.1)]
    if simbolo == "botao_campainha":
        # Quadrado com o botão no meio.
        return _retangulo(-0.35, -0.35, 0.35, 0.35) + [("circulo", 0, 0, 0.14)]
    if simbolo == "fotocelula":
        # Célula com duas setas de luz chegando.
        raios = []
        for dy in (0.0, 0.3):
            raios += [("linha", -0.8, 0.5 + dy, -0.35, 0.05 + dy),
                      ("linha", -0.35, 0.05 + dy, -0.35, 0.2 + dy), ("linha", -0.35, 0.05 + dy, -0.5, 0.05 + dy)]
        return [("circulo", 0, 0, 0.3), ("linha", -0.3, 0, 0.3, 0)] + raios
    if simbolo == "caixa_passagem":
        return _retangulo(-0.4, -0.4, 0.4, 0.4) + [("linha", -0.4, 0, 0.4, 0), ("linha", 0, -0.4, 0, 0.4)]
    if simbolo == "haste_aterramento":
        return _terra(0.0, 0.45)
    if simbolo == "caixa_inspecao":
        return [("circulo", 0, 0, 0.5)] + _terra(0.0, 0.3, escala=0.6)
    if simbolo == "bep":
        terminais = [("linha", x, 0.15, x, 0.35) for x in (-0.4, -0.2, 0.0, 0.2, 0.4)]
        return _retangulo(-0.55, 0.0, 0.55, 0.15) + terminais + _terra(0.0, 0.0, escala=0.6)
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


# Tipo do interruptor (propriedade Tipo do objeto Switch) -> (legenda, dica).
INTERRUPTORES = {
    "Simples": ("Interruptor simples", "Interruptor de uma seção"),
    "Paralelo": ("Interruptor paralelo", "Comanda a luz de dois lugares (three-way)"),
    "Intermediário": ("Interruptor intermediário", "Comanda a luz de três ou mais lugares (four-way)"),
}


def geometria_interruptor(tipo, tamanho=1.0):
    """Primitivas do interruptor, iguais às do objeto Switch: círculo e linha saindo da borda.

    O paralelo tem uma linha a mais, e o intermediário duas. Com ``tamanho`` 200
    dá o mesmo desenho do interruptor padrão (raio 80, linha de 40).
    """
    raio, linha = 0.4 * tamanho, 0.2 * tamanho
    afastamento = raio * 0.2
    primitivas = [("circulo", 0, 0, raio), ("linha", raio, 0, raio + linha, 0)]
    deslocamentos = {"Paralelo": [afastamento], "Intermediário": [afastamento, -afastamento]}.get(tipo, [])
    primitivas += [("linha", raio, dy, raio + linha, dy) for dy in deslocamentos]
    return primitivas


def limites_de(primitivas):
    """Caixa envolvente de uma lista de primitivas: (xmin, ymin, xmax, ymax)."""
    xs, ys = [], []
    for primitiva in primitivas:
        if primitiva[0] == "linha":
            xs += [primitiva[1], primitiva[3]]
            ys += [primitiva[2], primitiva[4]]
        else:  # círculo ou arco: usa o círculo inteiro, que é o pior caso
            _, cx, cy, raio = primitiva[:4]
            xs += [cx - raio, cx + raio]
            ys += [cy - raio, cy + raio]
    return min(xs), min(ys), max(xs), max(ys)


def limites(simbolo, tamanho=1.0):
    """Caixa envolvente do símbolo do catálogo: (xmin, ymin, xmax, ymax)."""
    return limites_de(geometria(simbolo, tamanho))


def posicao_da_caixa(simbolo):
    """Onde fica o volume 3D da caixa em relação ao ponto de inserção.

    - 'parede': tomadas de parede. O ponto de inserção é a face da parede (onde
      o traço do triângulo encosta) e a caixa entra na parede, para trás do
      triângulo, que aponta para o ambiente (+x do símbolo).
    - 'piso': tomada de piso, com o topo da caixa no piso.
    - 'centro': os outros símbolos, com a caixa centrada no ponto.
    """
    dados = CATALOGO.get(simbolo)
    if dados is None or dados["categoria"] != TOMADA:
        return "centro"
    return "piso" if simbolo == "tomada_piso" else "parede"


def caixa_local(posicao, largura, profundidade, altura):
    """Canto e medidas da caixa no sistema do símbolo, com z a partir da cota da caixa.

    Args:
        posicao: de ``posicao_da_caixa``.
        largura, profundidade, altura: medidas da caixa [mm]; na parede, a
            largura corre ao longo da parede (y do símbolo) e a profundidade
            entra nela (−x).
    Returns:
        (x, y, z, comprimento em x, comprimento em y, comprimento em z) [mm].
    """
    largura, profundidade, altura = float(largura), float(profundidade), float(altura)
    if posicao == "parede":
        return (-profundidade, -largura / 2, -altura / 2, profundidade, largura, altura)
    if posicao == "piso":
        return (-largura / 2, -profundidade / 2, -altura, largura, profundidade, altura)
    return (-largura / 2, -profundidade / 2, -altura / 2, largura, profundidade, altura)
