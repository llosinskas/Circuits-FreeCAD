"""Ambientes e a previsão automática de pontos pela NBR 5410 (item 9.5.2), sem FreeCAD.

Um ambiente é um polígono fechado em planta [(x, y)] em mm. A previsão dá a
quantidade mínima de tomadas de uso geral (TUG) e a potência de iluminação, e
``posicoes`` espalha os pontos:

- **tomadas** pelo perímetro, espaçadas igualmente, fora das portas e dos cantos,
  viradas para dentro do ambiente;
- **interruptor** ao lado da primeira porta, a ``DISTANCIA_INTERRUPTOR_MM`` do batente;
- **luz** de teto no centro (no centroide ou, em ambiente em L, no ponto mais longe
  das paredes).

Regras mínimas da NBR 5410:2004, 9.5.2 (confira com a norma e com o cliente):

- iluminação: 100 VA até 6 m²; acima, 100 VA nos primeiros 6 m² e mais 60 VA a
  cada 4 m² inteiros;
- TUG: banheiro, 1 junto ao lavatório; cozinha, copa, área de serviço e
  lavanderia, 1 a cada 3,5 m de perímetro (ou fração); varanda, 1; sala e
  dormitório, 1 a cada 5 m (ou fração); demais, 1 até 6 m² e 1 a cada 5 m acima;
- potência das TUG: nas áreas molhadas, 600 VA até 3 pontos e 100 VA nos demais
  (com mais de 6 pontos, 600 VA em 2); nos outros ambientes, 100 VA.

Unidades: coordenadas em mm, área em m², perímetro em m, potência em VA, ângulos em graus.
"""
import math

MM_POR_M = 1000.0
COZINHA, BANHEIRO, VARANDA, SALA, DEMAIS = "cozinha", "banheiro", "varanda", "sala", "demais"

# tipo -> (regra das TUG, área molhada)
TIPOS = {
    "Sala": (SALA, False),
    "Dormitório": (SALA, False),
    "Cozinha": (COZINHA, True),
    "Copa": (COZINHA, True),
    "Área de serviço": (COZINHA, True),
    "Lavanderia": (COZINHA, True),
    "Banheiro": (BANHEIRO, True),
    "Varanda": (VARANDA, False),
    "Corredor": (DEMAIS, False),
    "Escritório": (DEMAIS, False),
    "Garagem": (DEMAIS, False),
    "Outro": (DEMAIS, False),
}
TIPO_PADRAO = "Outro"
# palavra no nome do espaço -> tipo (a primeira que aparecer)
PALAVRAS = [
    (("banh", "wc", "lavabo"), "Banheiro"),
    (("cozinha",), "Cozinha"),
    (("copa",), "Copa"),
    (("serviço", "servico", "a.s.", "a. s."), "Área de serviço"),
    (("lavand",), "Lavanderia"),
    (("varanda", "sacada", "terraço", "terraco", "balcão"), "Varanda"),
    (("dorm", "quarto", "suíte", "suite"), "Dormitório"),
    (("sala", "estar", "jantar", "living"), "Sala"),
    (("corredor", "circula", "hall"), "Corredor"),
    (("escrit", "home office"), "Escritório"),
    (("garag",), "Garagem"),
]

PERIMETRO_POR_TUG_COZINHA = 3.5  # m
PERIMETRO_POR_TUG_SALA = 5.0  # m
AREA_TUG_UNICA = 6.0  # m²: até isto, uma TUG nos demais ambientes
VA_ILUMINACAO_BASE = 100.0
VA_ILUMINACAO_ACRESCIMO = 60.0  # a cada 4 m² inteiros acima de 6 m²
VA_TUG = 100.0
VA_TUG_MOLHADA = 600.0

DISTANCIA_INTERRUPTOR_MM = 150.0  # do batente da porta ao interruptor
FOLGA_PORTA_MM = 200.0  # tomada não fica a menos disto da porta
FOLGA_CANTO_MM = 300.0  # tomada não fica a menos disto de um canto
FOLGA_INTERRUPTOR_MM = 300.0  # tomada não fica a menos disto do interruptor
TOLERANCIA_PORTA_MM = 300.0  # a porta pertence ao ambiente se estiver a até isto da borda


def tipo_pelo_nome(nome):
    """Tipo do ambiente pelo nome do espaço ('Cozinha 01' → 'Cozinha'); sem palavra conhecida, 'Outro'."""
    texto = str(nome).lower()
    for palavras, tipo in PALAVRAS:
        if any(p in texto for p in palavras):
            return tipo
    return TIPO_PADRAO


# --- geometria do polígono ---------------------------------------------------

def _limpo(pontos):
    """Sem o último ponto repetido e sem pontos colados."""
    lista = []
    for x, y in pontos:
        if not lista or math.dist(lista[-1], (x, y)) > 1e-6:
            lista.append((float(x), float(y)))
    if len(lista) > 1 and math.dist(lista[0], lista[-1]) <= 1e-6:
        lista.pop()
    return lista


def area_assinada(pontos):
    pontos = _limpo(pontos)
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pontos, pontos[1:] + pontos[:1])) / 2.0


def anti_horario(pontos):
    """O polígono no sentido anti-horário (o lado de dentro fica à esquerda de cada lado)."""
    pontos = _limpo(pontos)
    return pontos if area_assinada(pontos) >= 0 else pontos[::-1]


def area_m2(pontos):
    return abs(area_assinada(pontos)) / MM_POR_M ** 2


def perimetro_m(pontos):
    pontos = _limpo(pontos)
    return sum(math.dist(a, b) for a, b in zip(pontos, pontos[1:] + pontos[:1])) / MM_POR_M


def dentro(ponto, pontos):
    """O ponto está dentro do polígono (raio horizontal)."""
    x, y = ponto
    pontos = _limpo(pontos)
    resultado = False
    for (x1, y1), (x2, y2) in zip(pontos, pontos[1:] + pontos[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            resultado = not resultado
    return resultado


def _distancia_ao_segmento(ponto, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    comprimento2 = dx * dx + dy * dy
    t = 0.0 if comprimento2 == 0 else max(0.0, min(1.0, ((ponto[0] - a[0]) * dx + (ponto[1] - a[1]) * dy) / comprimento2))
    return math.dist(ponto, (a[0] + t * dx, a[1] + t * dy)), t


def centro(pontos):
    """Ponto central do ambiente: o centroide, se cair dentro; senão, o ponto mais longe das paredes."""
    pontos = anti_horario(pontos)
    area = area_assinada(pontos)
    if abs(area) > 1e-9:
        cx = sum((x1 + x2) * (x1 * y2 - x2 * y1) for (x1, y1), (x2, y2) in zip(pontos, pontos[1:] + pontos[:1]))
        cy = sum((y1 + y2) * (x1 * y2 - x2 * y1) for (x1, y1), (x2, y2) in zip(pontos, pontos[1:] + pontos[:1]))
        centroide = (cx / (6 * area), cy / (6 * area))
        if dentro(centroide, pontos):
            return centroide
    xs, ys = [p[0] for p in pontos], [p[1] for p in pontos]
    melhor, folga = None, -1.0
    passos = 24
    for i in range(1, passos):
        for j in range(1, passos):
            p = (min(xs) + (max(xs) - min(xs)) * i / passos, min(ys) + (max(ys) - min(ys)) * j / passos)
            if not dentro(p, pontos):
                continue
            d = min(_distancia_ao_segmento(p, a, b)[0] for a, b in zip(pontos, pontos[1:] + pontos[:1]))
            if d > folga:
                melhor, folga = p, d
    return melhor or (sum(xs) / len(xs), sum(ys) / len(ys))


class Contorno:
    """Percorre o perímetro (anti-horário) pela distância a partir do primeiro vértice [mm]."""

    def __init__(self, pontos):
        self.pontos = anti_horario(pontos)
        self.lados = list(zip(self.pontos, self.pontos[1:] + self.pontos[:1]))
        self.inicios, total = [], 0.0
        for a, b in self.lados:
            self.inicios.append(total)
            total += math.dist(a, b)
        self.total = total

    def ponto(self, s):
        """(x, y, ângulo da normal para dentro [graus], lado, distância ao vértice mais perto) em ``s``."""
        s %= self.total
        for indice, ((a, b), inicio) in enumerate(zip(self.lados, self.inicios)):
            comprimento = math.dist(a, b)
            if s <= inicio + comprimento + 1e-9 or indice == len(self.lados) - 1:
                t = s - inicio
                ux, uy = (b[0] - a[0]) / comprimento, (b[1] - a[1]) / comprimento
                angulo = math.degrees(math.atan2(ux, -uy))  # normal à esquerda (-uy, ux)
                return a[0] + ux * t, a[1] + uy * t, angulo, indice, min(t, comprimento - t)
        raise ValueError("contorno vazio")

    def projetar(self, ponto):
        """(s, distância) do ponto do perímetro mais perto de ``ponto``."""
        melhor = None
        for (a, b), inicio in zip(self.lados, self.inicios):
            d, t = _distancia_ao_segmento(ponto, a, b)
            if melhor is None or d < melhor[1]:
                melhor = (inicio + t * math.dist(a, b), d)
        return melhor


# --- previsão pela NBR 5410 ----------------------------------------------------

def iluminacao_va(area):
    """Potência mínima de iluminação [VA] pela área [m²]."""
    if area <= AREA_TUG_UNICA:
        return VA_ILUMINACAO_BASE
    return VA_ILUMINACAO_BASE + VA_ILUMINACAO_ACRESCIMO * int((area - AREA_TUG_UNICA) // 4.0 + 1e-9)


def quantidade_de_tugs(tipo, area, perimetro):
    """Número mínimo de TUG do ambiente."""
    regra, _ = TIPOS.get(tipo, TIPOS[TIPO_PADRAO])
    if regra == COZINHA:
        return max(1, math.ceil(perimetro / PERIMETRO_POR_TUG_COZINHA - 1e-9))
    if regra in (BANHEIRO, VARANDA):
        return 1
    if regra == SALA:
        return max(1, math.ceil(perimetro / PERIMETRO_POR_TUG_SALA - 1e-9))
    return 1 if area <= AREA_TUG_UNICA else math.ceil(perimetro / PERIMETRO_POR_TUG_SALA - 1e-9)


def potencias_das_tugs(tipo, quantidade):
    """Potência de cada TUG [VA], a 600 VA primeiro."""
    _, molhada = TIPOS.get(tipo, TIPOS[TIPO_PADRAO])
    if not molhada:
        return [VA_TUG] * quantidade
    de_600 = 2 if quantidade > 6 else 3
    return [VA_TUG_MOLHADA] * min(quantidade, de_600) + [VA_TUG] * max(0, quantidade - de_600)


def simbolo_da_tomada(tipo, potencia):
    """Tomada média (bancada, lavatório) nas de 600 VA das áreas molhadas; baixa nas outras."""
    _, molhada = TIPOS.get(tipo, TIPOS[TIPO_PADRAO])
    return "tomada_media" if molhada and potencia >= VA_TUG_MOLHADA else "tomada_baixa"


def previsao(tipo, area, perimetro):
    """Quantidades mínimas do ambiente: {'tugs', 'potencias' [VA], 'iluminacao_va', 'total_tug_va'}."""
    quantidade = quantidade_de_tugs(tipo, area, perimetro)
    potencias = potencias_das_tugs(tipo, quantidade)
    return {"tugs": quantidade, "potencias": potencias, "iluminacao_va": iluminacao_va(area),
            "total_tug_va": sum(potencias)}


# --- posições ------------------------------------------------------------------

def _bloqueado(s, intervalos, total):
    for inicio, fim in intervalos:
        for desloc in (0.0, total, -total):
            if inicio <= s + desloc <= fim:
                return inicio, fim
    return None


def posicoes(pontos, tipo, portas=()):
    """Onde ficam os pontos do ambiente.

    Args:
        pontos: polígono do ambiente [(x, y)] mm.
        tipo: chave de ``TIPOS``.
        portas: [(x, y, largura)] mm — o meio das portas; as que estão a até
            ``TOLERANCIA_PORTA_MM`` da borda pertencem ao ambiente.
    Returns:
        {'tomadas': [{x, y, angulo, simbolo, potencia}], 'interruptor': {x, y, angulo} ou None,
         'luz': {x, y, potencia}, 'portas': quantidade de portas do ambiente,
         'previsao': de ``previsao``, 'avisos': [textos]}. O ângulo vira a frente do
        símbolo (o +x local) para dentro do ambiente.
    """
    contorno = Contorno(pontos)
    area, perimetro = area_m2(pontos), perimetro_m(pontos)
    quantidades = previsao(tipo, area, perimetro)
    avisos = []

    intervalos = []  # trechos do perímetro sem tomada: portas e interruptor
    portas_do_ambiente = []
    for x, y, largura in portas:
        s, distancia = contorno.projetar((x, y))
        if distancia <= TOLERANCIA_PORTA_MM:
            portas_do_ambiente.append((s, float(largura)))
            intervalos.append((s - largura / 2.0 - FOLGA_PORTA_MM, s + largura / 2.0 + FOLGA_PORTA_MM))

    interruptor = None
    if portas_do_ambiente:
        s_porta, largura = portas_do_ambiente[0]
        for sinal in (1.0, -1.0):  # do lado da fechadura que couber, sem cair em outra porta ou num canto
            s = s_porta + sinal * (largura / 2.0 + DISTANCIA_INTERRUPTOR_MM)
            x, y, angulo, _, ao_canto = contorno.ponto(s)
            outras = intervalos[1:]
            if ao_canto >= 50.0 and not _bloqueado(s, outras, contorno.total):
                break
        interruptor = {"x": x, "y": y, "angulo": angulo}
        intervalos.append((s - FOLGA_INTERRUPTOR_MM, s + FOLGA_INTERRUPTOR_MM))
    else:
        x, y, angulo, _, _ = contorno.ponto(FOLGA_CANTO_MM)
        interruptor = {"x": x, "y": y, "angulo": angulo}
        intervalos.append((FOLGA_CANTO_MM - FOLGA_INTERRUPTOR_MM, FOLGA_CANTO_MM + FOLGA_INTERRUPTOR_MM))
        avisos.append("sem porta encontrada: interruptor no primeiro canto; mova-o para perto da porta")

    tomadas = []
    n = quantidades["tugs"]
    inicio = interruptor and contorno.projetar((interruptor["x"], interruptor["y"]))[0] or 0.0
    for i, potencia in enumerate(quantidades["potencias"]):
        s = inicio + (i + 0.5) * contorno.total / n
        for _ in range(8):  # foge das portas, do interruptor e dos cantos
            bloqueio = _bloqueado(s, intervalos, contorno.total)
            if bloqueio:
                s = bloqueio[1] + 1.0
                continue
            _, _, _, lado, ao_canto = contorno.ponto(s)
            a, b = contorno.lados[lado]
            if ao_canto < FOLGA_CANTO_MM and math.dist(a, b) > 2 * FOLGA_CANTO_MM:
                inicio_lado = contorno.inicios[lado]
                t = (s % contorno.total) - inicio_lado
                s = inicio_lado + (FOLGA_CANTO_MM if t < math.dist(a, b) / 2 else math.dist(a, b) - FOLGA_CANTO_MM)
                continue
            break
        x, y, angulo, _, _ = contorno.ponto(s)
        tomadas.append({"x": x, "y": y, "angulo": angulo, "simbolo": simbolo_da_tomada(tipo, potencia),
                        "potencia": potencia})
    cx, cy = centro(pontos)
    return {"tomadas": tomadas, "interruptor": interruptor,
            "luz": {"x": cx, "y": cy, "potencia": quantidades["iluminacao_va"]},
            "portas": len(portas_do_ambiente), "previsao": quantidades, "avisos": avisos}
