"""Bandejas: eletrocalhas e leitos para cabos, sem FreeCAD.

A partir das linhas desenhadas na planta (uma por trecho de bandeja), monta a
rede de cada pavimento, identifica as conexões principais em cada nó e
posiciona os suportes ao longo dos trechos retos:

- ponta solta: terminal de fechamento;
- dois trechos com mudança de direção: curva horizontal (90°, 45° ou o ângulo medido);
- dois trechos alinhados: emenda;
- três trechos: tê horizontal; quatro: cruzeta horizontal;
- ponta de um trecho sobre o meio de outro: o outro é dividido e vira tê.

Suportes: um a ``DISTANCIA_SUPORTE_CONEXAO`` de cada nó e os intermediários
com vão de no máximo ``VAO_SUPORTE``. Cada suporte é um trapézio suspenso
(perfilado sob a bandeja e dois tirantes até a laje).

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
FOLGA_PERFILADO_MM = 100.0  # o perfilado passa 5 cm de cada lado da bandeja
PERDA_BANDEJA = 0.05

TERMINAL = "Terminal de fechamento"
EMENDA = "Emenda"
CURVA = "Curva horizontal"
TE = "Tê horizontal"
CRUZETA = "Cruzeta horizontal"
DERIVACAO = "Derivação especial"
GRUPO = "Bandejas e leitos"
GRUPO_SUPORTES = "Suportes"


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


def analisar(caminhos, tolerancia=TOLERANCIA_MM):
    """Conexões, trechos e suportes das bandejas de um pavimento.

    Args:
        caminhos: dicionários com ``pontos`` [(x, y) mm], ``tipo`` (chave de
            ``TIPOS``), ``largura`` e ``aba`` [mm], ``altura`` (do piso à base,
            mm), ``tampa`` (bool) e ``nome``.
    Returns:
        Dicionário com ``conexoes`` (x, y, peca, tipo, largura, aba, angulo),
        ``trechos`` (tipo, largura, aba, tampa, comprimento mm, x1, y1, x2, y2,
        altura) e ``suportes`` (x, y, angulo, tipo, largura, altura).
    """
    rede = Rede(tolerancia)
    for caminho in caminhos:
        dados = {chave: caminho.get(chave) for chave in ("tipo", "largura", "aba", "altura", "tampa", "nome")}
        rede.adicionar(caminho["pontos"], dados)
    rede.dividir_derivacoes()

    conexoes = []
    for indice, (x, y) in enumerate(rede.nos):
        peca = conexao_do_no(rede, indice)
        if peca is None or peca == EMENDA:
            continue
        ligados = rede.ligados(indice)
        principal = max(ligados, key=lambda t: float(t["largura"] or 0))
        conexoes.append({
            "x": x, "y": y, "peca": peca, "tipo": principal["tipo"], "largura": principal["largura"],
            "aba": principal["aba"], "altura": principal["altura"], "angulo": rede.direcao(principal, indice),
        })

    trechos, suportes = [], []
    for trecho in rede.trechos:
        (x1, y1), (x2, y2) = rede.nos[trecho["a"]], rede.nos[trecho["b"]]
        comprimento = rede.comprimento(trecho)
        angulo = math.degrees(math.atan2(y2 - y1, x2 - x1))
        trechos.append({
            "tipo": trecho["tipo"], "largura": trecho["largura"], "aba": trecho["aba"], "tampa": bool(trecho["tampa"]),
            "altura": trecho["altura"], "comprimento": comprimento, "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "nome": trecho["nome"],
        })
        vao = VAO_SUPORTE.get(trecho["tipo"], VAO_SUPORTE[TIPO_PADRAO])
        for distancia in _suportes_do_trecho(comprimento, vao):
            t = distancia / comprimento
            suportes.append({
                "x": x1 + (x2 - x1) * t, "y": y1 + (y2 - y1) * t, "angulo": angulo, "tipo": trecho["tipo"],
                "largura": trecho["largura"], "altura": trecho["altura"], "nome": trecho["nome"],
            })
    return {"conexoes": conexoes, "trechos": trechos, "suportes": suportes}


def materiais(resultado, pe_direito_mm=3000.0, com_suportes=True):
    """Itens do quantitativo das bandejas, no formato dos componentes de ``core.quantitativos.montar``.

    Args:
        resultado: saída de ``analisar``.
        pe_direito_mm: do piso à laje de cima; o tirante vai da laje à base da bandeja.
        com_suportes: inclui os materiais dos suportes.
    """
    somas = {}

    def somar(grupo, item, especificacao, unidade, quantidade):
        chave = (grupo, item, especificacao, unidade)
        somas[chave] = somas.get(chave, 0) + quantidade

    for trecho in resultado["trechos"]:
        secao = medida(trecho["largura"], trecho["aba"])
        metros = trecho["comprimento"] / 1000.0 * (1 + PERDA_BANDEJA)
        somar(GRUPO, nome_do_tipo(trecho["tipo"]), f"{secao}, barras de 3 m (inclui {PERDA_BANDEJA:.0%} de perdas)",
              "m", metros)
        emendas = max(0, math.ceil(trecho["comprimento"] / COMPRIMENTO_BARRA_MM - 1e-9) - 1)
        if emendas:
            somar(GRUPO, "Emenda (par de talas)", secao, "un", emendas)
        if trecho["tampa"]:
            somar(GRUPO, "Tampa de encaixe", f"largura {float(trecho['largura']):g} mm", "m", metros)
    for conexao in resultado["conexoes"]:
        secao = medida(conexao["largura"], conexao["aba"])
        somar(GRUPO, conexao["peca"], f"{nome_do_tipo(conexao['tipo'])} {secao}", "un", 1)
        if conexao["peca"] != TERMINAL:  # cada lado da peça é ligado ao trecho por um par de talas
            lados = {TE: 3, CRUZETA: 4}.get(conexao["peca"], 2)
            somar(GRUPO, "Emenda (par de talas)", secao, "un", lados)

    if com_suportes:
        for suporte in resultado["suportes"]:
            tirante = max(0.0, pe_direito_mm - float(suporte["altura"])) / 1000.0
            perfilado = (float(suporte["largura"]) + FOLGA_PERFILADO_MM) / 1000.0
            somar(GRUPO_SUPORTES, "Suporte suspenso (trapézio)", f"para largura {float(suporte['largura']):g} mm", "un", 1)
            somar(GRUPO_SUPORTES, "Perfilado 38x38 mm", "", "m", perfilado)
            somar(GRUPO_SUPORTES, "Vergalhão roscado 3/8\"", "tirante até a laje", "m", 2 * tirante)
            somar(GRUPO_SUPORTES, "Chumbador 3/8\"", "na laje", "un", 2)
            somar(GRUPO_SUPORTES, "Porca e arruela 3/8\"", "", "un", 4)

    return [
        {"grupo": grupo, "item": item, "especificacao": especificacao, "unidade": unidade,
         "quantidade": round(quantidade, 2) if unidade == "m" else int(round(quantidade))}
        for (grupo, item, especificacao, unidade), quantidade in sorted(somas.items())
    ]


def rotulo_da_conexao(peca):
    """Sigla da peça para o texto na planta: C90, C45, T, X, TF."""
    if peca.startswith(CURVA):
        return "C" + peca[len(CURVA):].strip().rstrip("°")
    return {TE: "T", CRUZETA: "X", TERMINAL: "TF", DERIVACAO: "D"}.get(peca, peca)


ESPESSURA_MM = 3.0
PASSO_TRAVESSA_MM = 300.0
LARGURA_TRAVESSA_MM = 30.0


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
