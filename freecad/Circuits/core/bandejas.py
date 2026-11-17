"""Bandejas: eletrocalhas e leitos para cabos, sem FreeCAD.

A partir das linhas desenhadas na planta (uma por trecho de bandeja), monta a
rede de cada pavimento, identifica as conexões principais em cada nó e
posiciona os suportes ao longo dos trechos retos:

- ponta solta: terminal de fechamento;
- dois trechos com mudança de direção: curva horizontal (90°, 45° ou o ângulo medido);
- dois trechos alinhados: emenda;
- três trechos: tê horizontal; quatro: cruzeta horizontal;
- ponta de um trecho sobre o meio de outro: o outro é dividido e vira tê;
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
        if float(trecho["largura"] or 0) < float(principal["largura"] or 0) - 1e-6:
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

    conexoes, verticais = [], []
    for indice in range(len(rede.nos)):
        pecas, do_no = _pecas_do_no(rede, indice)
        conexoes += pecas
        verticais += do_no

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
            especificacao += f" para {float(conexao['para_largura']):g} mm"
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
