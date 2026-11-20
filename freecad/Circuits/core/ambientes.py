"""Ambientes e a previsão automática de pontos pela NBR 5410 (item 9.5.2), sem FreeCAD.

Um ambiente é um polígono fechado em planta [(x, y)] em mm. A previsão dá a
quantidade mínima de tomadas de uso geral (TUG) e a potência de iluminação, e
``posicoes`` espalha os pontos:

- **tomadas** pelo perímetro, espaçadas igualmente, fora das portas e dos cantos,
  viradas para dentro do ambiente;
- **interruptor** ao lado da primeira porta, a ``DISTANCIA_INTERRUPTOR_MM`` do batente;
- **luz** de teto no centro (no centroide ou, em ambiente em L, no ponto mais longe
  das paredes) ou, com o luminotécnico, as luminárias do método dos lúmens numa
  malha dentro do polígono (``luminarias``).

As **opções** de cada ambiente (``posicoes(..., opcoes=)``) respondem ao que a
geração não adivinha:

- ``porta``: None usa as portas do projeto (BIM); ``SEM_PORTA``; ou o índice da
  parede (``paredes``), com ``posicao_porta`` (0 a 1 ao longo dela);
- ``bancada``: índice da parede da pia/bancada (cozinha, copa, área de serviço,
  lavanderia: as tomadas de 600 VA vão acima dela, no mínimo duas, NBR 5410
  9.5.2.2.1 b) ou do lavatório (banheiro: a tomada junto a ele, 9.5.2.2.1 a);
- ``chuveiro``: potência [W] do chuveiro (banheiro), 0 sem chuveiro;
- ``ar_condicionado``: potência [VA] do ar-condicionado, 0 sem;
- ``luminotecnico``: {fluxo [lm], potencia [VA], simbolo, pe_direito [m],
  iluminancia [lx] e plano [m] opcionais}. Sem a chave, vale
  ``LUMINOTECNICO_PADRAO`` (as luzes saem sempre do luminotécnico); só None
  explícito deixa uma luz no centro.

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

from freecad.Circuits.core.functions.Predial import luminotecnico as lumens

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


SEM_PORTA = "sem_porta"
# Lâmpada usada pelo luminotécnico quando o usuário não escolhe outra (LED 12 W, cerca de 1000 lm).
LUMINOTECNICO_PADRAO = {"fluxo": 1000.0, "potencia": 12.0, "simbolo": "luz_teto", "pe_direito": 2.7}
LARGURA_PORTA_MM = 800.0
AFASTAMENTO_CHUVEIRO_MM = 450.0  # do canto do box para dentro
CHUVEIRO_W = 5500.0
# Ar-condicionado split: capacidade -> potência elétrica aproximada [VA] (valores usuais de mercado).
AR_CONDICIONADO = {"9.000 BTU/h": 1000.0, "12.000 BTU/h": 1300.0, "18.000 BTU/h": 1900.0, "24.000 BTU/h": 2600.0}
# Tipos que perguntam pela bancada (pia) e pelo lavatório, pelo chuveiro e pelo ar-condicionado.
COM_AR_CONDICIONADO = ("Sala", "Dormitório", "Escritório")
TOMADAS_NA_BANCADA = 2  # NBR 5410 9.5.2.2.1 b: no mínimo duas acima da bancada da pia

# Iluminância mantida [lux] e plano de trabalho [m] por tipo, para o luminotécnico
# (NBR ISO/CIE 8995-1 e, nas residências, a antiga NBR 5413).
ILUMINACAO_POR_TIPO = {
    "Sala": (150.0, 0.75), "Dormitório": (150.0, 0.75), "Cozinha": (200.0, 0.75), "Copa": (200.0, 0.75),
    "Área de serviço": (200.0, 0.75), "Lavanderia": (200.0, 0.75), "Banheiro": (200.0, 0.75),
    "Varanda": (100.0, 0.0), "Corredor": (100.0, 0.0), "Escritório": (500.0, 0.75), "Garagem": (75.0, 0.0),
    "Outro": (150.0, 0.75),
}


def pergunta_bancada(tipo):
    """'pia' (cozinha e afins), 'lavatório' (banheiro) ou None: o que perguntar sobre a parede da bancada."""
    regra, _ = TIPOS.get(tipo, TIPOS[TIPO_PADRAO])
    return {COZINHA: "pia", BANHEIRO: "lavatório"}.get(regra)


def tem_chuveiro(tipo):
    return TIPOS.get(tipo, TIPOS[TIPO_PADRAO])[0] == BANHEIRO


def tem_ar_condicionado(tipo):
    return tipo in COM_AR_CONDICIONADO


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


_DIRECOES = [(90.0, "de baixo"), (180.0, "da direita"), (-90.0, "de cima"), (270.0, "de cima"),
             (0.0, "da esquerda"), (-180.0, "da direita")]


def paredes(pontos):
    """Paredes do ambiente, na ordem do contorno: [{'indice', 'comprimento' [m], 'rotulo'}].

    O rótulo diz de que lado a parede está, olhando a planta ('Parede 1 – de baixo, 3,00 m').
    """
    contorno = Contorno(pontos)
    resultado = []
    for indice, (a, b) in enumerate(contorno.lados):
        comprimento = math.dist(a, b)
        ux, uy = (b[0] - a[0]) / comprimento, (b[1] - a[1]) / comprimento
        normal = math.degrees(math.atan2(ux, -uy))  # para dentro: a parede está do lado oposto
        lado = next((nome for angulo, nome in _DIRECOES if abs(normal - angulo) <= 30.0), "inclinada")
        texto = f"{comprimento / MM_POR_M:.2f}".replace(".", ",")
        resultado.append({"indice": indice, "comprimento": comprimento / MM_POR_M,
                          "rotulo": f"Parede {indice + 1} – {lado}, {texto} m"})
    return resultado


def ponto_na_parede(pontos, indice, posicao=0.5):
    """(x, y) a ``posicao`` (0 a 1) do comprimento da parede ``indice`` (ordem de ``paredes``)."""
    a, b = Contorno(pontos).lados[indice % len(Contorno(pontos).lados)]
    posicao = max(0.0, min(1.0, float(posicao)))
    return a[0] + (b[0] - a[0]) * posicao, a[1] + (b[1] - a[1]) * posicao


def porta_na_parede(pontos, indice, posicao=0.5, largura=LARGURA_PORTA_MM):
    """Porta informada pelo usuário: (x, y, largura) do meio dela, como as portas do BIM."""
    x, y = ponto_na_parede(pontos, indice, posicao)
    return x, y, float(largura)


# --- luminotécnico no polígono ----------------------------------------------------

def _malha_no_poligono(pontos, nx, ny):
    xs, ys = [p[0] for p in pontos], [p[1] for p in pontos]
    x0, y0 = min(xs), min(ys)
    passo_x, passo_y = (max(xs) - x0) / nx, (max(ys) - y0) / ny
    centros = [(x0 + passo_x * (i + 0.5), y0 + passo_y * (j + 0.5)) for j in range(ny) for i in range(nx)]
    return [c for c in centros if dentro(c, pontos)]


def luminarias(pontos, tipo, fluxo, potencia, pe_direito=2.7, iluminancia=None, plano=None, suspensao=0.0,
               fator_utilizacao_informado=0.0, simbolo="luz_teto"):
    """Luminárias do ambiente pelo método dos lúmens (``core.functions.Predial.luminotecnico``).

    A quantidade sai da área e do perímetro do polígono (K = 2A / (Hu·P)); as
    posições, de uma malha no retângulo envolvente com o espaçamento limitado a
    1,5 × Hu, ficando só os centros dentro do polígono (num ambiente em L a malha
    é refinada até caber a quantidade calculada).

    A potência de cada ponto, para o circuito, é a maior entre a da luminária e a
    parte dela na carga mínima da NBR 5410 (``iluminacao_va`` dividida pelos
    pontos): a norma diz que essa carga vale para dimensionar o circuito, não é a
    potência das lâmpadas (9.5.2.1.2, nota).

    Args:
        pontos: polígono [(x, y)] mm. fluxo [lm] e potencia [VA] de cada luminária.
        iluminancia, plano: None usa ``ILUMINACAO_POR_TIPO``.
    Returns:
        dict de ``luminotecnico.calcular`` mais ``quantidade``, ``nx``, ``ny``,
        ``iluminancia_resultante``, ``espacamento_x``/``_y`` e ``espacamento_maximo`` [m],
        ``potencia_ponto`` e ``carga_nbr`` [VA], ``simbolo`` e ``posicoes`` [(x, y)] mm.
    """
    padrao_e, padrao_plano = ILUMINACAO_POR_TIPO.get(tipo, ILUMINACAO_POR_TIPO[TIPO_PADRAO])
    iluminancia = float(iluminancia or padrao_e)
    plano = padrao_plano if plano is None else float(plano)
    area, perimetro = area_m2(pontos), perimetro_m(pontos)
    base = lumens.calcular(area, perimetro, iluminancia, float(fluxo), pe_direito, plano, suspensao,
                           fator_utilizacao_informado=fator_utilizacao_informado)
    necessarias = max(1, math.ceil(base["quantidade_calculada"] - 1e-9))
    xs, ys = [p[0] for p in pontos], [p[1] for p in pontos]
    comprimento, largura = (max(xs) - min(xs)) / MM_POR_M, (max(ys) - min(ys)) / MM_POR_M
    alvo = necessarias
    for _ in range(200):
        nx, ny = lumens.malha(alvo, comprimento, largura)
        nx, ny = lumens.ajustar_espacamento(nx, ny, comprimento, largura, base["altura_util"])
        posicoes_dentro = _malha_no_poligono(pontos, nx, ny)
        if len(posicoes_dentro) >= necessarias:
            break
        alvo += 1
    if not posicoes_dentro:
        posicoes_dentro = [centro(pontos)]
    quantidade = len(posicoes_dentro)
    carga_nbr = iluminacao_va(area)
    return dict(base, **{
        "quantidade": quantidade, "nx": nx, "ny": ny, "plano_trabalho": plano,
        "iluminancia_resultante": lumens.iluminancia_com(quantidade, base),
        "espacamento_x": comprimento / nx, "espacamento_y": largura / ny,
        "espacamento_maximo": lumens.espacamento_maximo(base["altura_util"]),
        "potencia_luminaria": float(potencia), "carga_nbr": carga_nbr,
        "potencia_ponto": float(max(float(potencia), math.ceil(carga_nbr / quantidade))),
        "simbolo": simbolo, "posicoes": posicoes_dentro,
    })


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


def _intervalo_da_parede(contorno, indice):
    a, b = contorno.lados[indice]
    return contorno.inicios[indice], contorno.inicios[indice] + math.dist(a, b)


def _livre(s, intervalos, total, passo=50.0, limite=40):
    """Primeira posição a partir de ``s`` (andando nos dois sentidos) fora dos intervalos bloqueados."""
    for k in range(limite):
        for sinal in (1.0, -1.0):
            candidato = s + sinal * k * passo
            if not _bloqueado(candidato, intervalos, total):
                return candidato
    return s


def posicoes(pontos, tipo, portas=(), opcoes=None):
    """Onde ficam os pontos do ambiente.

    Args:
        pontos: polígono do ambiente [(x, y)] mm.
        tipo: chave de ``TIPOS``.
        portas: [(x, y, largura)] mm — o meio das portas do projeto; as que estão a até
            ``TOLERANCIA_PORTA_MM`` da borda pertencem ao ambiente.
        opcoes: respostas do usuário (veja o começo do módulo); None usa as portas do projeto.
    Returns:
        {'tomadas': [{x, y, angulo, simbolo, potencia}], 'interruptor': {x, y, angulo} ou None,
         'luz': {x, y, potencia} (a primeira luminária), 'luzes': [{x, y, potencia, simbolo}],
         'equipamentos': [{x, y, angulo, simbolo, potencia}], 'luminotecnico': dict ou None,
         'portas': quantidade de portas do ambiente, 'previsao': de ``previsao``, 'avisos': [textos]}.
        O ângulo vira a frente do símbolo (o +x local) para dentro do ambiente.
    """
    opcoes = dict(opcoes or {})
    contorno = Contorno(pontos)
    area, perimetro = area_m2(pontos), perimetro_m(pontos)
    quantidades = previsao(tipo, area, perimetro)
    avisos = []
    porta = opcoes.get("porta")
    sem_porta = porta == SEM_PORTA
    if sem_porta:
        portas = ()
    elif porta is not None:
        portas = [porta_na_parede(pontos, int(porta), opcoes.get("posicao_porta", 0.5),
                                  opcoes.get("largura_porta", LARGURA_PORTA_MM))]
    bancada = opcoes.get("bancada")
    bancada = int(bancada) % len(contorno.lados) if bancada is not None and pergunta_bancada(tipo) else None
    if bancada is not None and pergunta_bancada(tipo) == "pia" and quantidades["tugs"] < TOMADAS_NA_BANCADA:
        quantidades = dict(quantidades, tugs=TOMADAS_NA_BANCADA,
                           potencias=potencias_das_tugs(tipo, TOMADAS_NA_BANCADA))
        quantidades["total_tug_va"] = sum(quantidades["potencias"])

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
        if not sem_porta:
            avisos.append("sem porta encontrada: interruptor no primeiro canto; informe a parede da porta")

    tomadas = []
    potencias = list(quantidades["potencias"])
    if bancada is not None:  # tomadas de 600 VA (médias) acima da bancada ou junto ao lavatório
        de_600 = [p for p in potencias if p >= VA_TUG_MOLHADA]
        na_bancada = de_600 if de_600 else potencias[:1]
        if pergunta_bancada(tipo) == "pia":
            na_bancada = (de_600 + [p for p in potencias if p < VA_TUG_MOLHADA])[:max(TOMADAS_NA_BANCADA,
                                                                                         len(de_600))]
        for p in na_bancada:
            potencias.remove(p)
        inicio_parede, fim_parede = _intervalo_da_parede(contorno, bancada)
        util = max(0.0, (fim_parede - inicio_parede) - 2 * FOLGA_CANTO_MM)
        for i, potencia in enumerate(na_bancada):
            s = inicio_parede + min(FOLGA_CANTO_MM, (fim_parede - inicio_parede) / 2) + util * (i + 0.5) / len(na_bancada)
            s = _livre(s, intervalos, contorno.total)
            x, y, angulo, _, _ = contorno.ponto(s)
            tomadas.append({"x": x, "y": y, "angulo": angulo, "simbolo": "tomada_media", "potencia": potencia})
        intervalos.append((inicio_parede, fim_parede))

    n = len(potencias)
    inicio = interruptor and contorno.projetar((interruptor["x"], interruptor["y"]))[0] or 0.0
    for i, potencia in enumerate(potencias):
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

    equipamentos = []
    if portas_do_ambiente:
        referencia = contorno.ponto(portas_do_ambiente[0][0])[:2]
    else:
        referencia = (interruptor["x"], interruptor["y"])
    chuveiro = float(opcoes.get("chuveiro") or 0.0)
    if chuveiro > 0 and tem_chuveiro(tipo):  # no canto mais longe da porta, um pouco para dentro
        canto = max(contorno.pontos, key=lambda p: math.dist(p, referencia))
        cx, cy = centro(pontos)
        distancia = math.dist(canto, (cx, cy)) or 1.0
        passo = min(AFASTAMENTO_CHUVEIRO_MM * math.sqrt(2), distancia / 2)
        equipamentos.append({"x": canto[0] + (cx - canto[0]) * passo / distancia,
                             "y": canto[1] + (cy - canto[1]) * passo / distancia,
                             "angulo": 0.0, "simbolo": "chuveiro", "potencia": chuveiro})
    ar = float(opcoes.get("ar_condicionado") or 0.0)
    if ar > 0 and tem_ar_condicionado(tipo):  # no meio da parede mais comprida sem porta
        com_porta = {contorno.ponto(s)[3] for s, _ in portas_do_ambiente}
        candidatas = [i for i in range(len(contorno.lados)) if i not in com_porta] or list(range(len(contorno.lados)))
        parede = max(candidatas, key=lambda i: math.dist(*contorno.lados[i]))
        inicio_parede, fim_parede = _intervalo_da_parede(contorno, parede)
        x, y, angulo, _, _ = contorno.ponto((inicio_parede + fim_parede) / 2)
        equipamentos.append({"x": x, "y": y, "angulo": angulo, "simbolo": "ar_condicionado", "potencia": ar})

    calculo = None
    dados = opcoes.get("luminotecnico", LUMINOTECNICO_PADRAO)
    if dados:
        dados = dict(LUMINOTECNICO_PADRAO, **dados)
        calculo = luminarias(pontos, tipo, dados["fluxo"], dados["potencia"], dados.get("pe_direito", 2.7),
                             dados.get("iluminancia"), dados.get("plano"), dados.get("suspensao", 0.0),
                             simbolo=dados.get("simbolo", "luz_teto"))
        luzes = [{"x": x, "y": y, "potencia": calculo["potencia_ponto"], "simbolo": calculo["simbolo"]}
                 for x, y in calculo["posicoes"]]
        if calculo["iluminancia_resultante"] < calculo["iluminancia"] - 1e-6:
            avisos.append(f"luminotécnico: {calculo['iluminancia_resultante']:.0f} lx abaixo dos "
                          f"{calculo['iluminancia']:.0f} lx")
    else:
        cx, cy = centro(pontos)
        luzes = [{"x": cx, "y": cy, "potencia": quantidades["iluminacao_va"], "simbolo": "luz_teto"}]
    return {"tomadas": tomadas, "interruptor": interruptor, "luz": luzes[0], "luzes": luzes,
            "equipamentos": equipamentos, "luminotecnico": calculo,
            "portas": len(portas_do_ambiente), "previsao": quantidades, "avisos": avisos}
