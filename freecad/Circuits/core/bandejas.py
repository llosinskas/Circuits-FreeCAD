"""Bandejas: eletrocalhas e leitos para cabos, sem FreeCAD.

A partir das linhas desenhadas na planta (uma por trecho de bandeja), monta a
rede de cada pavimento, identifica as conexões principais em cada nó e
posiciona os suportes ao longo dos trechos retos:

- ponta solta: terminal de fechamento;
- dois trechos com mudança de direção: curva horizontal (90°, 45° ou o ângulo medido);
- dois trechos alinhados: emenda;
- três trechos: tê horizontal; quatro: cruzeta horizontal;
- ponta de um trecho sobre o meio de outro: o outro é dividido e vira tê;
- dois trechos que se cruzam no meio, na mesma altura: os dois são divididos e viram cruzeta;
- trecho mais estreito que a bandeja principal do nó: redução;
- trecho em outra altura: curvas verticais externa e interna e o trecho
  vertical entre as duas alturas.

Suportes: um a ``DISTANCIA_SUPORTE_CONEXAO`` de cada nó e os intermediários
com vão de no máximo ``VAO_SUPORTE``. Cada suporte é um trapézio suspenso
(perfilado sob a bandeja e dois tirantes até a laje); nos trechos verticais,
suportes de parede. A fixação soma os parafusos das emendas e dos terminais
e os grampos da bandeja no perfilado.

Regras de catálogo usuais, não de um fabricante: confira o vão com o
fabricante e o peso dos cabos.

Unidades: mm na entrada e nas posições; m nos materiais.
"""
import math

TIPOS = {
    "eletrocalha_perfurada": "Eletrocalha perfurada",
    "eletrocalha_lisa": "Eletrocalha lisa",
    "leito": "Leito para cabos",
}
TIPO_PADRAO = "eletrocalha_perfurada"
LARGURAS_MM = [50, 75, 100, 150, 200, 300, 400, 500, 600, 800]
ABAS_MM = [50, 75, 100, 150]
LARGURA_PADRAO_MM = 200
ABA_PADRAO_MM = 50
ALTURA_PADRAO_MM = 2800.0  # do piso à base da bandeja

COMPRIMENTO_BARRA_MM = 3000.0
VAO_SUPORTE = {"eletrocalha_perfurada": 1500.0, "eletrocalha_lisa": 1500.0, "leito": 2000.0}
DISTANCIA_SUPORTE_CONEXAO = 500.0
TOLERANCIA_MM = 50.0
TOLERANCIA_JUNCAO_MM = 300.0  # ponta solta até esta distância de outra bandeja é encaixada nela
RAIO_CURVA_FATOR = 1.0  # raio da linha de centro da curva, em larguras da bandeja
COMPRIMENTO_REDUCAO_MM = 300.0  # comprimento usual de catálogo da redução
FOLGA_PERFILADO_MM = 100.0  # o perfilado passa 5 cm de cada lado da bandeja
PERDA_BANDEJA = 0.05

TERMINAL = "Terminal de fechamento"
EMENDA = "Emenda"
CURVA = "Curva horizontal"
TE = "Tê horizontal"
CRUZETA = "Cruzeta horizontal"
DERIVACAO = "Derivação especial"
REDUCAO = "Redução"
CURVA_VERTICAL_EXTERNA = "Curva vertical externa 90°"
CURVA_VERTICAL_INTERNA = "Curva vertical interna 90°"
GRUPO = "Bandejas e leitos"
GRUPO_SUPORTES = "Suportes"
GRUPO_FIXACAO = "Fixação"
PARAFUSO = "Parafuso cabeça lentilha 1/4\" x 5/8\" com porca e arruela"
PARAFUSOS_POR_EMENDA = 8  # 4 em cada tala
PARAFUSOS_POR_TERMINAL = 4
TOLERANCIA_ALTURA_MM = 10.0


def nome_do_tipo(tipo):
    return TIPOS.get(tipo, str(tipo))


def medida(largura, aba):
    """Texto da seção: 200x50 mm."""
    return f"{float(largura):g}x{float(aba):g} mm"


def _distancia(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _projecao(p, a, b):
    """(t ao longo de a→b de 0 a 1, distância do ponto à reta)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    comprimento2 = dx * dx + dy * dy
    if comprimento2 == 0:
        return 0.0, _distancia(p, a)
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / comprimento2
    t = max(0.0, min(1.0, t))
    return t, _distancia(p, (a[0] + t * dx, a[1] + t * dy))


class Rede:
    """Nós (vértices unidos pela tolerância) e trechos retos entre eles."""

    def __init__(self, tolerancia=TOLERANCIA_MM):
        self.tolerancia = tolerancia
        self.nos = []  # (x, y)
        self.trechos = []  # dicionários: a, b (índices de nós), dados da bandeja

    def no(self, ponto):
        for indice, existente in enumerate(self.nos):
            if _distancia(existente, ponto) <= self.tolerancia:
                return indice
        self.nos.append((float(ponto[0]), float(ponto[1])))
        return len(self.nos) - 1

    def adicionar(self, pontos, dados):
        for a, b in zip(pontos, pontos[1:]):
            ia, ib = self.no(a), self.no(b)
            if ia != ib:
                self.trechos.append(dict(dados, a=ia, b=ib))

    def dividir_derivacoes(self):
        """Divide o trecho onde a ponta de outro chega no meio dele (derivação em tê)."""
        mudou = True
        while mudou:
            mudou = False
            for indice, no in enumerate(self.nos):
                for trecho in list(self.trechos):
                    if indice in (trecho["a"], trecho["b"]):
                        continue
                    t, distancia = _projecao(no, self.nos[trecho["a"]], self.nos[trecho["b"]])
                    if distancia <= self.tolerancia and 0.0 < t < 1.0:
                        self.trechos.remove(trecho)
                        self.trechos.append(dict(trecho, b=indice))
                        self.trechos.append(dict(trecho, a=indice))
                        mudou = True
                        break
                if mudou:
                    break

    def dividir_cruzamentos(self):
        """Divide os dois trechos onde eles se cruzam no meio, na mesma altura (vira cruzeta).

        Trechos em alturas diferentes (mais de ``TOLERANCIA_ALTURA_MM``) passam
        um sob o outro e não se ligam.
        """
        mudou = True
        while mudou:
            mudou = False
            for i, t1 in enumerate(self.trechos):
                for t2 in self.trechos[i + 1:]:
                    if {t1["a"], t1["b"]} & {t2["a"], t2["b"]}:
                        continue
                    if abs(float(t1["altura"] or 0) - float(t2["altura"] or 0)) > TOLERANCIA_ALTURA_MM:
                        continue
                    ponto = self._cruzamento(t1, t2)
                    if ponto is None:
                        continue
                    novo = self.no(ponto)
                    for trecho in (t1, t2):
                        self.trechos.remove(trecho)
                        self.trechos += [dict(trecho, b=novo), dict(trecho, a=novo)]
                    mudou = True
                    break
                if mudou:
                    break

    def _cruzamento(self, t1, t2):
        """Ponto onde os trechos se cruzam, longe das pontas dos dois, ou None."""
        (ax, ay), (bx, by) = self.nos[t1["a"]], self.nos[t1["b"]]
        (cx, cy), (dx, dy) = self.nos[t2["a"]], self.nos[t2["b"]]
        r, s = (bx - ax, by - ay), (dx - cx, dy - cy)
        denominador = r[0] * s[1] - r[1] * s[0]
        if abs(denominador) < 1e-9:
            return None  # paralelos
        t = ((cx - ax) * s[1] - (cy - ay) * s[0]) / denominador
        u = ((cx - ax) * r[1] - (cy - ay) * r[0]) / denominador
        folga1 = self.tolerancia / math.hypot(*r)
        folga2 = self.tolerancia / math.hypot(*s)
        if folga1 < t < 1 - folga1 and folga2 < u < 1 - folga2:
            return (ax + t * r[0], ay + t * r[1])
        return None

    def ligados(self, indice):
        return [t for t in self.trechos if indice in (t["a"], t["b"])]

    def direcao(self, trecho, de):
        """Ângulo [graus] do trecho saindo do nó ``de``."""
        outro = trecho["b"] if trecho["a"] == de else trecho["a"]
        (x0, y0), (x1, y1) = self.nos[de], self.nos[outro]
        return math.degrees(math.atan2(y1 - y0, x1 - x0))

    def comprimento(self, trecho):
        return _distancia(self.nos[trecho["a"]], self.nos[trecho["b"]])


def _desvio(angulo_1, angulo_2):
    """Mudança de direção [graus, 0 a 180] entre dois trechos que saem do mesmo nó."""
    entre = abs((angulo_1 - angulo_2 + 180.0) % 360.0 - 180.0)
    return 180.0 - entre


def nome_da_curva(desvio):
    """Curva comercial para a mudança de direção: 90°, 45° ou o ângulo medido."""
    if 75.0 <= desvio <= 105.0:
        return f"{CURVA} 90°"
    if 30.0 <= desvio <= 60.0:
        return f"{CURVA} 45°"
    return f"{CURVA} {desvio:.0f}°"


def conexao_do_no(rede, indice):
    """Nome da peça no nó, ou None (nó sem trechos)."""
    trechos = rede.ligados(indice)
    if not trechos:
        return None
    if len(trechos) == 1:
        return TERMINAL
    if len(trechos) == 2:
        desvio = _desvio(rede.direcao(trechos[0], indice), rede.direcao(trechos[1], indice))
        return EMENDA if desvio < 5.0 else nome_da_curva(desvio)
    return {3: TE, 4: CRUZETA}.get(len(trechos), DERIVACAO)


def _suportes_do_trecho(comprimento, vao, distancia_no=DISTANCIA_SUPORTE_CONEXAO):
    """Distâncias [mm] dos suportes a partir do início do trecho."""
    if comprimento <= 0:
        return []
    if comprimento <= 2 * distancia_no:
        return [comprimento / 2.0]
    primeiro, ultimo = distancia_no, comprimento - distancia_no
    intervalos = max(1, math.ceil((ultimo - primeiro) / vao - 1e-9))
    passo = (ultimo - primeiro) / intervalos
    return [primeiro + passo * i for i in range(intervalos + 1)]


def _secao_de(trecho):
    return float(trecho["largura"] or 0), float(trecho["aba"] or 0)


def _pecas_do_no(rede, indice):
    """Peças do nó: a horizontal (terminal, curva, tê, cruzeta), as reduções e as curvas verticais.

    A bandeja principal do nó é a mais larga; a peça horizontal tem a seção
    dela. Cada trecho mais estreito leva uma redução (da principal para ele), e
    cada trecho em outra altura leva um par de curvas verticais (externa no
    alto, interna embaixo) e o trecho vertical entre as duas alturas.

    Returns:
        (peças, verticais): listas de dicionários.
    """
    ligados = rede.ligados(indice)
    if not ligados:
        return [], []
    x, y = rede.nos[indice]
    principal = max(ligados, key=lambda t: (_secao_de(t), -ligados.index(t)))

    def peca(nome, trecho, **extra):
        return dict({"x": x, "y": y, "no": indice, "peca": nome, "tipo": trecho["tipo"], "largura": trecho["largura"],
                     "aba": trecho["aba"], "altura": trecho["altura"], "angulo": rede.direcao(trecho, indice)}, **extra)

    pecas, verticais = [], []
    horizontal = conexao_do_no(rede, indice)
    if horizontal != EMENDA:
        pecas.append(peca(horizontal, principal))
    altura_principal = float(principal["altura"] or 0)
    for trecho in ligados:
        if trecho is principal:
            continue
        if _secao_de(trecho) < _secao_de(principal):  # mais estreito, ou com aba mais baixa
            pecas.append(peca(REDUCAO, principal, para_largura=trecho["largura"], para_aba=trecho["aba"]))
        diferenca = float(trecho["altura"] or 0) - altura_principal
        if abs(diferenca) > TOLERANCIA_ALTURA_MM:
            pecas.append(peca(CURVA_VERTICAL_EXTERNA, trecho))
            pecas.append(peca(CURVA_VERTICAL_INTERNA, trecho))
            verticais.append({
                "x": x, "y": y, "tipo": trecho["tipo"], "largura": trecho["largura"], "aba": trecho["aba"],
                "de": min(altura_principal, float(trecho["altura"])), "ate": max(altura_principal, float(trecho["altura"])),
                "comprimento": abs(diferenca), "angulo": rede.direcao(trecho, indice), "nome": trecho["nome"],
                "sentido": "sobe" if diferenca > 0 else "desce",
            })
    return pecas, verticais


def encaixar(caminhos, tolerancia=TOLERANCIA_JUNCAO_MM):
    """Junta as pontas soltas às bandejas vizinhas.

    Cada ponta (primeiro ou último vértice) que não está ligada a outra bandeja
    e fica a até ``tolerancia`` dela é levada ao vértice mais próximo (vira
    curva, tê ou cruzeta) ou, sem vértice perto, ao ponto mais próximo do
    trecho (vira tê). Os vértices do meio não mudam.

    Args:
        caminhos: listas de (x, y) [mm], uma por bandeja.
    Returns:
        (novas listas de pontos, quantidade de junções feitas).
    """
    novos = [[(float(x), float(y)) for x, y in pontos] for pontos in caminhos]
    juncoes = 0
    for i, pontos in enumerate(novos):
        if len(pontos) < 2:
            continue
        for ponta in (0, len(pontos) - 1):
            p = pontos[ponta]
            outros = [c for j, c in enumerate(novos) if j != i and len(c) >= 2]
            vertices = [v for c in outros for v in c]
            no_meio = []
            for c in outros:
                for a, b in zip(c, c[1:]):
                    t, distancia = _projecao(p, a, b)
                    if 0.0 < t < 1.0:
                        no_meio.append((distancia, (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)))
            vertice = min(vertices, key=lambda v: _distancia(p, v), default=None)
            meio = min(no_meio, default=None)
            ja_ligada = (vertice is not None and _distancia(p, vertice) <= TOLERANCIA_MM) or \
                (meio is not None and meio[0] <= TOLERANCIA_MM)
            if ja_ligada:
                continue
            if vertice is not None and _distancia(p, vertice) <= tolerancia:
                pontos[ponta] = vertice
            elif meio is not None and meio[0] <= tolerancia:
                pontos[ponta] = (round(meio[1][0], 6), round(meio[1][1], 6))
            else:
                continue
            juncoes += 1
    return novos, juncoes


def _unitario(angulo_graus):
    a = math.radians(angulo_graus)
    return math.cos(a), math.sin(a)


def _peca_horizontal(rede, indice):
    """Recorte dos trechos no nó [mm] e a forma da peça.

    Curva: tangente T = R·tg(desvio/2), com R = ``RAIO_CURVA_FATOR`` · largura,
    e o arco (cx, cy, raio, ângulo inicial, varredura) da linha de centro.
    Tê e cruzeta: meia largura da principal e o quadrado da derivação com os
    lados fechados (normais, em graus, sem trecho chegando).

    Returns:
        (recorte, extras) — extras vai para o dicionário da peça.
    """
    ligados = rede.ligados(indice)
    if len(ligados) < 2:
        return 0.0, {}
    principal = max(ligados, key=lambda t: (_secao_de(t), -ligados.index(t)))
    largura = float(principal["largura"] or 0)
    direcoes = [rede.direcao(t, indice) for t in ligados]
    x, y = rede.nos[indice]
    if len(ligados) == 2:
        desvio = _desvio(*direcoes)
        if desvio < 5.0:
            return 0.0, {}
        raio = RAIO_CURVA_FATOR * largura
        recorte = raio * math.tan(math.radians(desvio) / 2)
        (u1x, u1y), (u2x, u2y) = _unitario(direcoes[0]), _unitario(direcoes[1])
        p1, p2 = (x + recorte * u1x, y + recorte * u1y), (x + recorte * u2x, y + recorte * u2y)
        bx, by = u1x + u2x, u1y + u2y
        norma = math.hypot(bx, by) or 1.0
        distancia = math.hypot(raio, recorte)
        cx, cy = x + bx / norma * distancia, y + by / norma * distancia
        a1 = math.degrees(math.atan2(p1[1] - cy, p1[0] - cx))
        a2 = math.degrees(math.atan2(p2[1] - cy, p2[0] - cx))
        varredura = (a2 - a1) % 360.0
        if varredura > 180.0:
            a1, varredura = a2, 360.0 - varredura
        return recorte, {"arco": (cx, cy, raio, a1, varredura)}
    base = rede.direcao(principal, indice)
    fechados, aberturas = [], {}
    for k in range(4):
        normal = round((base + 90.0 * k) % 360.0, 6)
        chegando = [float(t["largura"] or 0) for t, d in zip(ligados, direcoes)
                    if abs((d - normal + 180.0) % 360.0 - 180.0) <= 10.0]
        if not chegando:
            fechados.append(normal)
        elif max(chegando) < largura - 1e-6:
            aberturas[normal] = max(chegando)  # ramal mais estreito: o resto do lado é fechado
    return largura / 2.0, {"quadrado": {"lado": largura, "angulo": base, "fechados": fechados,
                                        "aberturas": aberturas}}


def _trapezio_da_reducao(rede, indice, recorte):
    """Redução entre dois trechos de seções diferentes: (trecho estreito, trapézio), ou None.

    Só nos nós de dois trechos (emenda ou curva): a peça fica no começo do
    trecho estreito, logo depois da curva (``recorte``) ou do nó. Nos tês e nas
    cruzetas a boca da peça já sai na largura do ramal.
    """
    ligados = rede.ligados(indice)
    if len(ligados) != 2:
        return None
    principal = max(ligados, key=lambda t: (_secao_de(t), -ligados.index(t)))
    estreito = next(t for t in ligados if t is not principal)
    if _secao_de(estreito) >= _secao_de(principal):
        return None
    angulo = rede.direcao(estreito, indice)
    ux, uy = _unitario(angulo)
    x, y = rede.nos[indice]
    return estreito, {
        "x": x + ux * recorte, "y": y + uy * recorte, "angulo": angulo, "comprimento": COMPRIMENTO_REDUCAO_MM,
        "largura_de": float(principal["largura"]), "largura_para": float(estreito["largura"]),
        "aba_de": float(principal["aba"]), "aba_para": float(estreito["aba"]),
    }


def analisar(caminhos, tolerancia=TOLERANCIA_MM):
    """Conexões, trechos, verticais e suportes das bandejas de um pavimento.

    Args:
        caminhos: dicionários com ``pontos`` [(x, y) mm], ``tipo`` (chave de
            ``TIPOS``), ``largura`` e ``aba`` [mm], ``altura`` (do piso à base,
            mm), ``tampa`` (bool) e ``nome``.
    Returns:
        Dicionário com ``conexoes`` (x, y, no, peca, tipo, largura, aba, angulo;
        nas reduções também para_largura e para_aba), ``trechos`` (tipo, largura,
        aba, tampa, comprimento mm, x1, y1, x2, y2, altura), ``verticais`` (x, y,
        tipo, largura, aba, de, ate, comprimento mm, angulo, nome, sentido) e
        ``suportes`` (x, y, angulo, tipo, largura, altura; nos verticais,
        ``vertical`` = True).
    """
    rede = Rede(tolerancia)
    for caminho in caminhos:
        dados = {chave: caminho.get(chave) for chave in ("tipo", "largura", "aba", "altura", "tampa", "nome")}
        rede.adicionar(caminho["pontos"], dados)
    rede.dividir_derivacoes()
    rede.dividir_cruzamentos()

    conexoes, verticais, recortes, reducoes = [], [], {}, {}
    for indice in range(len(rede.nos)):
        pecas, do_no = _pecas_do_no(rede, indice)
        recortes[indice], extras = _peca_horizontal(rede, indice)
        for peca in pecas:
            if peca["peca"].startswith(CURVA) or peca["peca"] in (TE, CRUZETA, DERIVACAO):
                peca.update(extras)
        reducao = _trapezio_da_reducao(rede, indice, recortes[indice])
        if reducao is not None:
            estreito, trapezio = reducao
            reducoes[(indice, id(estreito))] = trapezio["comprimento"]
            next(p for p in pecas if p["peca"] == REDUCAO)["trapezio"] = trapezio
        conexoes += pecas
        verticais += do_no

    trechos, suportes = [], []
    for trecho in rede.trechos:
        (x1, y1), (x2, y2) = rede.nos[trecho["a"]], rede.nos[trecho["b"]]
        comprimento = rede.comprimento(trecho)
        angulo = math.degrees(math.atan2(y2 - y1, x2 - x1))
        inicio = recortes[trecho["a"]] + reducoes.get((trecho["a"], id(trecho)), 0.0)
        fim = recortes[trecho["b"]] + reducoes.get((trecho["b"], id(trecho)), 0.0)
        if inicio + fim > comprimento > 0:  # trecho curto demais para as duas peças: divide o que há
            inicio, fim = comprimento * inicio / (inicio + fim), comprimento * fim / (inicio + fim)
        trechos.append({
            "tipo": trecho["tipo"], "largura": trecho["largura"], "aba": trecho["aba"], "tampa": bool(trecho["tampa"]),
            "altura": trecho["altura"], "comprimento": comprimento, "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "nome": trecho["nome"], "recuo_inicio": inicio, "recuo_fim": fim,
        })
        vao = VAO_SUPORTE.get(trecho["tipo"], VAO_SUPORTE[TIPO_PADRAO])
        for distancia in _suportes_do_trecho(comprimento, vao):
            t = distancia / comprimento
            suportes.append({
                "x": x1 + (x2 - x1) * t, "y": y1 + (y2 - y1) * t, "angulo": angulo, "tipo": trecho["tipo"],
                "largura": trecho["largura"], "altura": trecho["altura"], "nome": trecho["nome"],
            })
    for vertical in verticais:
        vao = VAO_SUPORTE.get(vertical["tipo"], VAO_SUPORTE[TIPO_PADRAO])
        for _ in range(max(1, math.ceil(vertical["comprimento"] / vao - 1e-9))):
            suportes.append({"x": vertical["x"], "y": vertical["y"], "angulo": vertical["angulo"],
                             "tipo": vertical["tipo"], "largura": vertical["largura"], "altura": vertical["de"],
                             "nome": vertical["nome"], "vertical": True})
    return {"conexoes": conexoes, "trechos": trechos, "verticais": verticais, "suportes": suportes}


def _lados(peca):
    """Quantos lados da peça são ligados a um trecho por uma emenda."""
    if peca == TERMINAL:
        return 0
    return {TE: 3, CRUZETA: 4}.get(peca, 2)


def materiais(resultado, pe_direito_mm=3000.0, com_suportes=True):
    """Itens do quantitativo das bandejas, no formato dos componentes de ``core.quantitativos.montar``.

    Grupos: "Bandejas e leitos" (metros, peças, emendas, tampa), "Suportes"
    (suspensos e de parede, perfilado, tirantes, chumbadores) e "Fixação"
    (parafusos das emendas e das peças, grampos da bandeja no perfilado).

    Args:
        resultado: saída de ``analisar``.
        pe_direito_mm: do piso à laje de cima; o tirante vai da laje à base da bandeja.
        com_suportes: inclui os materiais dos suportes e da fixação deles.
    """
    somas = {}

    def somar(grupo, item, especificacao, unidade, quantidade):
        chave = (grupo, item, especificacao, unidade)
        somas[chave] = somas.get(chave, 0) + quantidade

    emendas = 0
    for trecho in resultado["trechos"] + resultado.get("verticais", []):
        secao = medida(trecho["largura"], trecho["aba"])
        metros = trecho["comprimento"] / 1000.0 * (1 + PERDA_BANDEJA)
        somar(GRUPO, nome_do_tipo(trecho["tipo"]), f"{secao}, barras de 3 m (inclui {PERDA_BANDEJA:.0%} de perdas)",
              "m", metros)
        no_meio = max(0, math.ceil(trecho["comprimento"] / COMPRIMENTO_BARRA_MM - 1e-9) - 1)
        if no_meio:
            somar(GRUPO, "Emenda (par de talas)", secao, "un", no_meio)
            emendas += no_meio
        if trecho.get("tampa"):
            somar(GRUPO, "Tampa de encaixe", f"largura {float(trecho['largura']):g} mm", "m", metros)
    for conexao in resultado["conexoes"]:
        secao = medida(conexao["largura"], conexao["aba"])
        especificacao = f"{nome_do_tipo(conexao['tipo'])} {secao}"
        if conexao["peca"] == REDUCAO:
            especificacao += f" para {medida(conexao['para_largura'], conexao['para_aba'])}"
        somar(GRUPO, conexao["peca"], especificacao, "un", 1)
        lados = _lados(conexao["peca"])
        if lados:
            somar(GRUPO, "Emenda (par de talas)", secao, "un", lados)
            emendas += lados
        else:  # o terminal é parafusado na ponta da bandeja
            somar(GRUPO_FIXACAO, PARAFUSO, "no terminal de fechamento", "un", PARAFUSOS_POR_TERMINAL)
    if emendas:
        somar(GRUPO_FIXACAO, PARAFUSO, "nas emendas", "un", emendas * PARAFUSOS_POR_EMENDA)

    if com_suportes:
        for suporte in resultado["suportes"]:
            largura = float(suporte["largura"])
            if suporte.get("vertical"):
                somar(GRUPO_SUPORTES, "Suporte de parede para trecho vertical", f"para largura {largura:g} mm", "un", 1)
                somar(GRUPO_SUPORTES, "Chumbador 3/8\"", "na parede", "un", 2)
                somar(GRUPO_FIXACAO, PARAFUSO, "bandeja no suporte de parede", "un", 2)
                continue
            tirante = max(0.0, pe_direito_mm - float(suporte["altura"])) / 1000.0
            perfilado = (largura + FOLGA_PERFILADO_MM) / 1000.0
            somar(GRUPO_SUPORTES, "Suporte suspenso (trapézio)", f"para largura {largura:g} mm", "un", 1)
            somar(GRUPO_SUPORTES, "Perfilado 38x38 mm", "", "m", perfilado)
            somar(GRUPO_SUPORTES, "Vergalhão roscado 3/8\"", "tirante até a laje", "m", 2 * tirante)
            somar(GRUPO_SUPORTES, "Chumbador 3/8\"", "na laje", "un", 2)
            somar(GRUPO_SUPORTES, "Porca e arruela 3/8\"", "", "un", 4)
            somar(GRUPO_FIXACAO, "Grampo de fixação da bandeja no perfilado", "com parafuso e porca", "un", 2)

    return [
        {"grupo": grupo, "item": item, "especificacao": especificacao, "unidade": unidade,
         "quantidade": round(quantidade, 2) if unidade == "m" else int(round(quantidade))}
        for (grupo, item, especificacao, unidade), quantidade in sorted(somas.items())
    ]


def rotulo_da_conexao(peca):
    """Sigla da peça para o texto na planta: C90, C45, T, X, TF, R, CVE, CVI."""
    if peca.startswith(CURVA):
        return "C" + peca[len(CURVA):].strip().rstrip("°")
    return {TE: "T", CRUZETA: "X", TERMINAL: "TF", DERIVACAO: "D", REDUCAO: "R",
            CURVA_VERTICAL_EXTERNA: "CVE", CURVA_VERTICAL_INTERNA: "CVI"}.get(peca, peca)


def rotulos_por_no(conexoes):
    """{(x, y): 'C90 + R'}: as siglas de todas as peças de cada nó, juntas."""
    por_no = {}
    for conexao in conexoes:
        siglas = por_no.setdefault((conexao["x"], conexao["y"]), [])
        sigla = rotulo_da_conexao(conexao["peca"])
        if sigla not in siglas:
            siglas.append(sigla)
    return {posicao: " + ".join(siglas) for posicao, siglas in por_no.items()}


def blocos_da_vertical(largura, aba, de, ate):
    """Blocos do trecho vertical no sistema local (x para o lado do trecho que sai do nó, y centrado, z do piso).

    Fundo vertical e duas abas, de ``de`` até ``ate`` (mm, do piso).
    """
    largura, aba, e = float(largura), float(aba), ESPESSURA_MM
    altura = float(ate) - float(de)
    if altura <= 0:
        return []
    return [
        (-e, -largura / 2.0, float(de), e, largura, altura + e),
        (0.0, -largura / 2.0, float(de), aba, e, altura),
        (0.0, largura / 2.0 - e, float(de), aba, e, altura),
    ]


ESPESSURA_MM = 3.0
PASSO_TRAVESSA_MM = 300.0
LARGURA_TRAVESSA_MM = 30.0


def contorno_2d(resultado):
    """Bandejas em linha dupla na planta, a partir de ``analisar``.

    Bordas a meia largura de cada trecho, já recortadas nas peças; dois arcos
    por curva; os lados fechados do quadrado de cada tê; e uma linha fechando
    cada terminal.

    Returns:
        {'linhas': [(x1, y1, x2, y2)], 'arcos': [(cx, cy, raio, ângulo inicial, varredura)]} [mm, graus].
    """
    linhas, arcos = [], []
    for t in resultado["trechos"]:
        comprimento = t["comprimento"]
        if comprimento <= 0:
            continue
        ux, uy = (t["x2"] - t["x1"]) / comprimento, (t["y2"] - t["y1"]) / comprimento
        nx, ny = -uy * float(t["largura"]) / 2, ux * float(t["largura"]) / 2
        sx, sy = t["x1"] + ux * t["recuo_inicio"], t["y1"] + uy * t["recuo_inicio"]
        ex, ey = t["x2"] - ux * t["recuo_fim"], t["y2"] - uy * t["recuo_fim"]
        for lado in (1, -1):
            linhas.append((sx + lado * nx, sy + lado * ny, ex + lado * nx, ey + lado * ny))
    for c in resultado["conexoes"]:
        meia = float(c["largura"]) / 2
        if c["peca"] == TERMINAL:
            ux, uy = _unitario(c["angulo"])
            linhas.append((c["x"] - uy * meia, c["y"] + ux * meia, c["x"] + uy * meia, c["y"] - ux * meia))
        elif "arco" in c:
            cx, cy, raio, inicio, varredura = c["arco"]
            arcos += [(cx, cy, raio - meia, inicio, varredura), (cx, cy, raio + meia, inicio, varredura)]
        if "trapezio" in c:
            t = c["trapezio"]
            ux, uy = _unitario(t["angulo"])
            ex, ey = t["x"] + ux * t["comprimento"], t["y"] + uy * t["comprimento"]
            for lado in (1, -1):
                linhas.append((t["x"] - lado * uy * t["largura_de"] / 2, t["y"] + lado * ux * t["largura_de"] / 2,
                               ex - lado * uy * t["largura_para"] / 2, ey + lado * ux * t["largura_para"] / 2))
        elif "quadrado" in c:
            quadrado = c["quadrado"]
            lados = [(normal, 0.0) for normal in quadrado["fechados"]] + list(quadrado.get("aberturas", {}).items())
            for normal, abertura in lados:
                ux, uy = _unitario(normal)
                mx, my = c["x"] + ux * meia, c["y"] + uy * meia
                tx, ty = -uy, ux  # ao longo do lado
                trechos_do_lado = [(-meia, meia)] if not abertura else [(-meia, -abertura / 2), (abertura / 2, meia)]
                for de, ate in trechos_do_lado:
                    linhas.append((mx + tx * de, my + ty * de, mx + tx * ate, my + ty * ate))
    return {"linhas": [tuple(round(v, 6) for v in linha) for linha in linhas], "arcos": arcos}


def faces_da_reducao(trapezio):
    """Faces do 3D da redução no sistema local (x ao longo do trecho estreito, y centrado, z da base).

    Fundo em trapézio da largura maior para a menor e duas abas inclinadas, da
    aba maior para a menor. Cada face é extrudada pela ``espessura`` (vetor).

    Returns:
        Lista de {'pontos': [(x, y, z)], 'espessura': (dx, dy, dz)}: o fundo e as duas abas.
    """
    comprimento, e = float(trapezio["comprimento"]), ESPESSURA_MM
    de, para = float(trapezio["largura_de"]) / 2, float(trapezio["largura_para"]) / 2
    aba_de, aba_para = float(trapezio["aba_de"]), float(trapezio["aba_para"])
    faces = [{"pontos": [(0.0, -de, 0.0), (comprimento, -para, 0.0), (comprimento, para, 0.0), (0.0, de, 0.0)],
              "espessura": (0.0, 0.0, e)}]
    for lado in (-1, 1):
        dx, dy = comprimento, lado * (para - de)
        norma = math.hypot(dx, dy)
        para_dentro = (dy / norma * lado * e, -dx / norma * lado * e, 0.0)  # perpendicular à aba, para o eixo
        faces.append({"pontos": [(0.0, lado * de, 0.0), (comprimento, lado * para, 0.0),
                                 (comprimento, lado * para, aba_para), (0.0, lado * de, aba_de)],
                      "espessura": para_dentro})
    return faces


def blocos_da_derivacao(quadrado, aba):
    """Blocos do tê ou da cruzeta no sistema local da principal (x ao longo dela, centro no nó).

    Fundo quadrado na largura da principal; aba inteira nos lados sem
    derivação e, nos lados com ramal mais estreito, aba dos dois lados do ramal.

    Returns:
        Lista de (x, y, z, comprimento, largura, altura) [mm].
    """
    lado, aba, e = float(quadrado["lado"]), float(aba), ESPESSURA_MM
    meia = lado / 2
    blocos = [(-meia, -meia, 0.0, lado, lado, e)]
    lados = [(n, 0.0) for n in quadrado["fechados"]] + list(quadrado.get("aberturas", {}).items())
    for normal, abertura in lados:
        k = int(round(((normal - quadrado["angulo"]) % 360.0) / 90.0)) % 4
        trechos = [(-meia, meia)] if not abertura else [(-meia, -abertura / 2), (abertura / 2, meia)]
        for de, ate in trechos:
            if k in (0, 2):  # lado perpendicular ao eixo x, em x = ±meia
                x = meia - e if k == 0 else -meia
                blocos.append((x, de, 0.0, e, ate - de, aba))
            else:  # lado perpendicular ao eixo y, em y = ±meia
                y = meia - e if k == 1 else -meia
                blocos.append((de, y, 0.0, ate - de, e, aba))
    return blocos


def blocos_do_trecho(comprimento, largura, aba, tipo, recuo_inicio=0.0, avanco_fim=0.0):
    """Blocos do modelo 3D de um trecho, no sistema local (x ao longo do trecho, y centrado, z da base).

    Eletrocalha: fundo e duas abas. Leito: duas longarinas e travessas a cada
    ``PASSO_TRAVESSA_MM``. ``recuo_inicio`` e ``avanco_fim`` estendem o trecho
    nos nós (meia largura), para fechar as curvas e as derivações.

    Returns:
        Lista de (x, y, z, comprimento, largura, altura) [mm], canto inferior de cada bloco.
    """
    inicio = -float(recuo_inicio)
    total = float(comprimento) + float(recuo_inicio) + float(avanco_fim)
    largura, aba, e = float(largura), float(aba), ESPESSURA_MM
    lados = [(inicio, -largura / 2.0, 0.0, total, e, aba), (inicio, largura / 2.0 - e, 0.0, total, e, aba)]
    if tipo != "leito":
        return [(inicio, -largura / 2.0, 0.0, total, largura, e)] + lados
    travessas = []
    posicao = inicio + PASSO_TRAVESSA_MM / 2.0
    while posicao + LARGURA_TRAVESSA_MM <= inicio + total:
        travessas.append((posicao, -largura / 2.0, 0.0, LARGURA_TRAVESSA_MM, largura, 2 * e))
        posicao += PASSO_TRAVESSA_MM
    return lados + travessas


def blocos_do_suporte(largura, altura_bandeja, pe_direito):
    """Blocos do suporte suspenso no sistema local da bandeja (x ao longo, y centrado, z do piso).

    Perfilado 38x38 sob a bandeja e dois tirantes de 3/8" (quadrados de 10 mm)
    até a laje.
    """
    largura, base, laje = float(largura), float(altura_bandeja), float(pe_direito)
    perfil = largura + FOLGA_PERFILADO_MM
    blocos = [(-19.0, -perfil / 2.0, base - 38.0, 38.0, perfil, 38.0)]
    if laje > base:
        for y in (-perfil / 2.0 + 15.0, perfil / 2.0 - 25.0):
            blocos.append((-5.0, y, base - 38.0, 10.0, 10.0, laje - base + 38.0))
    return blocos
