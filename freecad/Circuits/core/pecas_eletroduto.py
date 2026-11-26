"""Eletrodutos com a dinâmica das eletrocalhas: peças nos nós, caixas nas derivações e materiais, sem FreeCAD.

Usa a mesma rede e o mesmo encaixe das bandejas (``core.bandejas.Rede`` e
``encaixar``). Em cada nó:

- em cima de uma caixa: bucha e arruela em cada eletroduto rígido que chega;
- uma ponta sem caixa: aviso de ponta solta;
- dois eletrodutos: no rígido, curva pré-fabricada (90°, 45° ou o ângulo
  medido) ou luva, se alinhados; o flexível só dobra, sem peça;
- três ou mais: derivação. Embutido pede uma caixa de passagem (criada pela
  bancada); aparente leva condulete (T, X ou múltiplo);
- eletrodutos em alturas diferentes (ex.: do teto para o piso): **descida**.
  A vertical vai da menor à maior altura, e cada eletroduto que termina no nó
  sozinho na sua altura faz uma curva de 90° para dentro dela (``descidas``);
  no rígido, a curva entra nas peças.

O rígido leva luva entre as barras de 3 m; o aparente, abraçadeira a cada
``ESPACO_ABRACADEIRA_MM`` e uma na ponta de cada trecho.

Na planta: o diâmetro escrito no trecho mais longo de cada eletroduto, a
sigla das curvas e conduletes, e o eletroduto do piso tracejado.

Regras usuais de obra e catálogo, não de uma norma: confira com o fabricante.
Unidades: mm.
"""
import math

from freecad.Circuits.core import bandejas
from freecad.Circuits.core.tables.eletrodutos import DIAMETRO_PADRAO, DIAMETROS_EXTERNOS

encaixar = bandejas.encaixar  # junta as pontas soltas, como nas eletrocalhas

TETO = "Embutido no teto ou parede"
PISO = "Embutido no piso"
APARENTE = "Aparente"
INSTALACOES = [TETO, PISO, APARENTE]
ALTURA_PADRAO = {TETO: 2800.0, PISO: -50.0, APARENTE: 2800.0}  # do piso ao eixo do eletroduto [mm]
TIPOS = ["Flexível", "Rígido"]
MATERIAIS = ["PVC", "Aço galvanizado"]

TOLERANCIA_MM = 50.0
TOLERANCIA_ALTURA_MM = 10.0  # alturas mais próximas que isto são a mesma
# Raio da curva na linha de centro, em raios externos do tubo (os mesmos do 3D horizontal)
FATOR_RAIO_CURVA_RIGIDO = 6  # curva pré-fabricada: 3 diâmetros
FATOR_RAIO_CURVA_FLEXIVEL = 15
COMPRIMENTO_BARRA_MM = 3000.0
ESPACO_ABRACADEIRA_MM = 1500.0

CURVA = "Curva"
CURVA_VERTICAL = "Curva 90° vertical"
SAIDA_HORIZONTAL = "Saída horizontal para eletroduto"  # na lateral (aba) da eletrocalha
SAIDA_VERTICAL = "Saída vertical para eletroduto"  # no fundo da eletrocalha
GRUPO_BANDEJAS = "Bandejas e leitos"
TOLERANCIA_SAIDA_MM = 50.0  # ponta a até isto da borda da eletrocalha é saída
TOLERANCIA_ENCAIXE_BANDEJA_MM = 300.0  # ponta a até isto da borda vai para a eletrocalha
# Peça de saída no 3D: flange quadrada encostada na eletrocalha e luva com anel para o eletroduto [mm]
ABA_FLANGE_MM = 20.0  # a flange passa o diâmetro externo do eletroduto disto de cada lado
ESPESSURA_FLANGE_MM = 3.0
FOLGA_LUVA_MM = 2.0  # a luva abraça o eletroduto
COMPRIMENTO_LUVA_MIN_MM = 40.0
ANEL_MM = 8.0  # anel (porca) no fim da luva
LUVA = "Luva"
BUCHA = "Bucha e arruela"
CONDULETE = "Condulete"
GRUPO = "Eletrodutos"
GRUPO_FIXACAO = "Fixação"


def tracejado(instalacao):
    """Na planta, o eletroduto embutido no piso é tracejado; o do teto e o aparente, contínuos."""
    return instalacao == PISO


def especificacao(trecho):
    """'PVC rígido 3/4"', 'Aço galvanizado 1"' ou 'PVC flexível 3/4"'."""
    if trecho["material"] == "Aço galvanizado":
        return f'Aço galvanizado {trecho["diametro"]}"'
    return f'PVC {"rígido" if trecho["tipo"] == "Rígido" else "flexível"} {trecho["diametro"]}"'


def _diametro_externo(diametro):
    return DIAMETROS_EXTERNOS.get(str(diametro), DIAMETRO_PADRAO)


def _nome_da_curva(desvio):
    nome = bandejas.nome_da_curva(desvio)  # "Curva horizontal 90°"
    return CURVA + nome[len(bandejas.CURVA):]


def raio_da_curva(diametro, tipo):
    """Raio da curva na linha de centro [mm]: rígido pré-fabricado ou flexível dobrado."""
    fator = FATOR_RAIO_CURVA_RIGIDO if tipo == "Rígido" else FATOR_RAIO_CURVA_FLEXIVEL
    return _diametro_externo(diametro) / 2.0 * fator


def _ponta(caminho, ponto):
    """'inicio' ou 'fim' se o caminho termina no ponto; None se passa por ele."""
    pontos = caminho["pontos"] if caminho else []
    if pontos and math.dist(pontos[0], ponto) <= TOLERANCIA_MM:
        return "inicio"
    if pontos and math.dist(pontos[-1], ponto) <= TOLERANCIA_MM:
        return "fim"
    return None


def _bracos(rede, indice, ligados, por_nome):
    """Eletrodutos que chegam ao nó, com a direção saindo dele, a altura e se terminam ali."""
    x, y = rede.nos[indice]
    bracos = []
    for t in ligados:
        angulo = math.radians(rede.direcao(t, indice))
        bracos.append({"nome": t["nome"], "ponta": _ponta(por_nome.get(t["nome"]), (x, y)),
                       "ux": math.cos(angulo), "uy": math.sin(angulo), "altura": float(t["altura"] or 0),
                       "diametro": t["diametro"], "tipo": t["tipo"], "material": t["material"],
                       "instalacao": t["instalacao"], "comprimento": rede.comprimento(t), "curva": False})
    return bracos


def _curvas_e_raio(bracos, de, ate, extremos):
    """Marca a curva de 90° no eletroduto que termina sozinho em cada altura de ``extremos`` e
    devolve (principal, raio): o raio cabe na vertical e no trecho reto que chega."""
    principal = max(bracos, key=lambda b: _diametro_externo(b["diametro"]))
    nas_pontas = []
    for altura in extremos:
        mesma = [b for b in bracos if abs(b["altura"] - altura) <= TOLERANCIA_ALTURA_MM]
        if len(mesma) == 1 and mesma[0]["ponta"]:
            mesma[0]["curva"] = True
            nas_pontas.append(mesma[0])
    raio = raio_da_curva(principal["diametro"], principal["tipo"])
    if nas_pontas:
        raio = min([raio, (ate - de) / len(nas_pontas)] + [0.9 * b["comprimento"] for b in nas_pontas])
    return principal, round(raio, 1)


def _descida(rede, indice, ligados, por_nome):
    """Descida no nó, se chegam eletrodutos em alturas diferentes; senão None.

    Cada eletroduto que termina no nó sozinho na menor ou na maior altura faz
    uma curva de 90° até a vertical; os que passam pelo nó, ou dividem a altura
    com outro (derivação), chegam à vertical sem curva.
    """
    x, y = rede.nos[indice]
    bracos = _bracos(rede, indice, ligados, por_nome)
    alturas = [b["altura"] for b in bracos]
    de, ate = min(alturas), max(alturas)
    if ate - de <= TOLERANCIA_ALTURA_MM:
        return None
    principal, raio = _curvas_e_raio(bracos, de, ate, (de, ate))
    return {"x": x, "y": y, "de": de, "ate": ate, "diametro": principal["diametro"], "tipo": principal["tipo"],
            "raio": raio, "bracos": bracos}


def limites_da_caixa(altura, altura_caixa=100.0, posicao="centro"):
    """(base, topo) da caixa 3D do símbolo, do piso [mm].

    Args:
        altura: altura de montagem do símbolo (``Altura3D``): o centro da caixa, ou o topo
            na tomada de piso (``core.simbolos.posicao_da_caixa`` 'piso').
        altura_caixa: altura da caixa [mm].
    """
    altura, altura_caixa = float(altura), float(altura_caixa)
    if posicao == "piso":
        return altura - altura_caixa, altura
    return altura - altura_caixa / 2, altura + altura_caixa / 2


def descidas_na_caixa(rede, indice, ligados, por_nome, caixa):
    """Interligação vertical dos eletrodutos com a caixa do símbolo: [descida], uma por lado.

    O eletroduto acima da caixa (ex.: no teto, a 2,80 m) desce até o topo dela (a tomada
    a 0,40 m); o de baixo (no piso) sobe até a base. Quem termina no nó sozinho na altura
    mais longe da caixa faz a curva de 90°; os outros chegam à vertical sem curva.

    Args:
        caixa: {'altura', 'altura_caixa', 'posicao', 'nome'} (``services.rede.listar_caixas``).
    Returns:
        Descidas no formato de ``_descida``, com ``caixa`` = nome do símbolo.
    """
    if caixa.get("altura") is None:
        return []
    x, y = rede.nos[indice]
    base, topo = limites_da_caixa(caixa["altura"], caixa.get("altura_caixa", 100.0), caixa.get("posicao", "centro"))
    resultado = []
    for acima in (True, False):
        bracos = [b for b in _bracos(rede, indice, ligados, por_nome)
                  if (b["altura"] > topo + TOLERANCIA_ALTURA_MM if acima else b["altura"] < base - TOLERANCIA_ALTURA_MM)]
        if not bracos:
            continue
        alturas = [b["altura"] for b in bracos]
        de, ate = (topo, max(alturas)) if acima else (min(alturas), base)
        principal, raio = _curvas_e_raio(bracos, de, ate, (ate,) if acima else (de,))
        resultado.append({"x": x, "y": y, "de": de, "ate": ate, "diametro": principal["diametro"],
                          "tipo": principal["tipo"], "raio": raio, "bracos": bracos,
                          "caixa": str(caixa.get("nome", "")), "lado": "cima" if acima else "baixo"})
    return resultado


def _na_bandeja(ponto, bandejas, folga):
    """Trecho de eletrocalha mais perto do ponto, com o ponto a até ``folga`` da borda.

    Returns:
        (bandeja, projeção na linha de centro, normal (nx, ny) apontando para o lado
        do ponto, distância à linha de centro) ou None.
    """
    melhor = None
    for bandeja in bandejas:
        for a, b in zip(bandeja["pontos"], bandeja["pontos"][1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            comprimento = math.hypot(dx, dy)
            if comprimento < 1e-9:
                continue
            ux, uy = dx / comprimento, dy / comprimento
            t = (ponto[0] - a[0]) * ux + (ponto[1] - a[1]) * uy
            if t < -1e-6 or t > comprimento + 1e-6:
                continue
            projecao = (a[0] + ux * t, a[1] + uy * t)
            lado = (ponto[0] - projecao[0]) * -uy + (ponto[1] - projecao[1]) * ux
            distancia = abs(lado)
            if distancia > float(bandeja["largura"]) / 2.0 + folga:
                continue
            normal = (-uy, ux) if lado >= 0 else (uy, -ux)
            if melhor is None or distancia < melhor[3]:
                melhor = (bandeja, projecao, normal, distancia)
    return melhor


def saidas(caminhos, bandejas):
    """Saídas de eletrocalha: pontas de eletroduto que chegam a uma eletrocalha do mesmo pavimento.

    Na altura da eletrocalha (da base até o topo da aba), a saída é **horizontal**,
    na lateral, e o ponto da saída fica na borda. Fora dessa altura é **vertical**:
    o eletroduto faz curva de 90° e sobe até o fundo (ou desce até o topo da aba)
    no ponto da ponta, e a saída vira uma ``descida``.

    Args:
        caminhos: eletrodutos, como em ``analisar``.
        bandejas: dicionários com ``pontos``, ``largura``, ``aba``, ``altura`` (da base) e ``nome``.
    Returns:
        [{x, y (ponto da saída), tipo 'horizontal' ou 'vertical', peca, eletroduto,
          bandeja, diametro, tipo_eletroduto, material, instalacao, ponta (x, y),
          'descida' (só na vertical, como em ``_descida``)}].
    """
    resultado = []
    for caminho in caminhos:
        pontos = caminho["pontos"]
        if len(pontos) < 2:
            continue
        for ponta, vizinho, nome_ponta in ((pontos[0], pontos[1], "inicio"), (pontos[-1], pontos[-2], "fim")):
            achado = _na_bandeja(ponta, bandejas, TOLERANCIA_SAIDA_MM)
            if achado is None:
                continue
            bandeja, projecao, normal, _ = achado
            altura = float(caminho.get("altura") or 0)
            base, topo = float(bandeja["altura"]), float(bandeja["altura"]) + float(bandeja.get("aba") or 0)
            horizontal = base - TOLERANCIA_ALTURA_MM <= altura <= topo + TOLERANCIA_ALTURA_MM
            saida = {"tipo": "horizontal" if horizontal else "vertical",
                     "peca": SAIDA_HORIZONTAL if horizontal else SAIDA_VERTICAL,
                     "eletroduto": caminho.get("nome"), "bandeja": bandeja.get("nome"),
                     "diametro": caminho.get("diametro"), "tipo_eletroduto": caminho.get("tipo"),
                     "material": caminho.get("material"), "instalacao": caminho.get("instalacao"),
                     "ponta": (float(ponta[0]), float(ponta[1]))}
            saida["normal"] = (float(normal[0]), float(normal[1]))
            if horizontal:
                meia = float(bandeja["largura"]) / 2.0
                saida["x"], saida["y"] = projecao[0] + normal[0] * meia, projecao[1] + normal[1] * meia
                saida["z"] = min(max(altura, base), topo) if topo > base else altura
            else:
                saida["x"], saida["y"] = float(ponta[0]), float(ponta[1])
                saida["z"], saida["sentido"] = (base, -1.0) if altura < base else (topo, 1.0)
                comprimento = math.hypot(vizinho[0] - ponta[0], vizinho[1] - ponta[1]) or 1.0
                de, ate = (altura, base) if altura < base else (topo, altura)
                raio = min(raio_da_curva(caminho.get("diametro"), caminho.get("tipo")), ate - de,
                           0.9 * comprimento)
                saida["descida"] = {
                    "x": saida["x"], "y": saida["y"], "de": de, "ate": ate, "diametro": caminho.get("diametro"),
                    "tipo": caminho.get("tipo"), "raio": round(raio, 1), "bandeja": bandeja.get("nome"),
                    "bracos": [{"nome": caminho.get("nome"), "ponta": nome_ponta,
                                "ux": (vizinho[0] - ponta[0]) / comprimento, "uy": (vizinho[1] - ponta[1]) / comprimento,
                                "altura": altura, "diametro": caminho.get("diametro"), "tipo": caminho.get("tipo"),
                                "material": caminho.get("material"), "instalacao": caminho.get("instalacao"),
                                "comprimento": comprimento, "curva": True}],
                }
            resultado.append(saida)
    return resultado


def encaixar_nas_bandejas(caminhos, bandejas, tolerancia=TOLERANCIA_ENCAIXE_BANDEJA_MM):
    """Leva à eletrocalha as pontas de eletroduto que pararam perto dela.

    A ponta a até ``tolerancia`` da borda vai para a borda, se o eletroduto está na
    altura da eletrocalha (saída horizontal), ou para a linha de centro, se está
    acima ou abaixo (saída vertical) e caiu fora da largura. Pontas que já estão
    sobre a eletrocalha, na saída vertical, ficam onde estão.

    Returns:
        (novos pontos de cada caminho, quantidade de pontas movidas).
    """
    novos, movidas = [], 0
    for caminho in caminhos:
        pontos = [(float(x), float(y)) for x, y in caminho["pontos"]]
        for indice in ((0, len(pontos) - 1) if len(pontos) > 1 else ()):
            achado = _na_bandeja(pontos[indice], bandejas, tolerancia)
            if achado is None:
                continue
            bandeja, projecao, normal, distancia = achado
            meia = float(bandeja["largura"]) / 2.0
            altura = float(caminho.get("altura") or 0)
            base, topo = float(bandeja["altura"]), float(bandeja["altura"]) + float(bandeja.get("aba") or 0)
            if base - TOLERANCIA_ALTURA_MM <= altura <= topo + TOLERANCIA_ALTURA_MM:
                alvo = (projecao[0] + normal[0] * meia, projecao[1] + normal[1] * meia)
            elif distancia > meia:
                alvo = projecao
            else:
                continue
            if math.dist(alvo, pontos[indice]) > 1e-3:
                pontos[indice] = (round(alvo[0], 6), round(alvo[1], 6))
                movidas += 1
        novos.append(pontos)
    return novos, movidas


def analisar(caminhos, caixas=(), eletrocalhas=()):
    """Peças, caixas de passagem que faltam e avisos dos eletrodutos de um pavimento.

    Args:
        caminhos: dicionários com ``pontos`` [(x, y)], ``tipo`` ('Flexível' ou
            'Rígido'), ``material``, ``instalacao``, ``diametro``, ``altura`` e ``nome``.
        caixas: caixas da planta (pontos, quadros, passagens): posições (x, y) ou
            dicionários com ``x``, ``y`` e, para a interligação vertical
            (``descidas_na_caixa``), ``altura``, ``altura_caixa``, ``posicao`` e ``nome``.
        eletrocalhas: eletrocalhas do pavimento, para as saídas (``saidas``).
    Returns:
        {'pecas': [{x, y, peca, diametro, tipo, material, instalacao}],
         'trechos': [{comprimento, diametro, tipo, material, instalacao, x1, y1, x2, y2, nome}],
         'caixas_novas': [{x, y, diametro}], 'avisos': [textos],
         'pontas_soltas': [{x, y, diametro, altura, nome}]} — pontas sem caixa, que podem
        ser prumadas para outro pavimento (``core.verticais.ligacoes_entre_pavimentos``),
         'descidas': [{x, y, de, ate, diametro, tipo, raio, bracos}]} — ver ``_descida``, mais
         as das caixas (com ``caixa``, ``descidas_na_caixa``) e as das saídas verticais de
         eletrocalha, e 'saidas' — ver ``saidas``.
    """
    lista_saidas = saidas(caminhos, eletrocalhas)
    lista_caixas = [dict(c) if isinstance(c, dict) else {"x": c[0], "y": c[1]} for c in caixas]
    por_nome = {c.get("nome"): c for c in caminhos}
    rede = bandejas.Rede(TOLERANCIA_MM)
    for caminho in caminhos:
        dados = {chave: caminho.get(chave) for chave in ("tipo", "material", "instalacao", "diametro", "altura", "nome")}
        dados.update(largura=_diametro_externo(caminho.get("diametro")), aba=0.0, tampa=False)
        rede.adicionar(caminho["pontos"], dados)
    rede.dividir_derivacoes()

    pecas, caixas_novas, avisos, pontas_soltas, descidas = [], [], [], [], []
    for indice, (x, y) in enumerate(rede.nos):
        ligados = rede.ligados(indice)
        if not ligados:
            continue
        principal = max(ligados, key=lambda t: _diametro_externo(t["diametro"]))

        def peca(nome, trecho):
            return {"x": x, "y": y, "peca": nome, "diametro": trecho["diametro"], "tipo": trecho["tipo"],
                    "material": trecho["material"], "instalacao": trecho["instalacao"]}

        caixa = next((c for c in lista_caixas if math.hypot(c["x"] - x, c["y"] - y) <= TOLERANCIA_MM), None)
        if caixa is not None:
            pecas += [peca(BUCHA, t) for t in ligados if t["tipo"] == "Rígido"]
            for descida in descidas_na_caixa(rede, indice, ligados, por_nome, caixa):
                descidas.append(descida)
                pecas += [peca(CURVA_VERTICAL, b) for b in descida["bracos"] if b["curva"] and b["tipo"] == "Rígido"]
            continue
        descida = _descida(rede, indice, ligados, por_nome) if len(ligados) > 1 else None
        if descida:
            descidas.append(descida)
            pecas += [peca(CURVA_VERTICAL, b) for b in descida["bracos"] if b["curva"] and b["tipo"] == "Rígido"]
            if len(ligados) == 2:
                continue  # as duas curvas e a vertical fazem a ligação
        if len(ligados) == 1 and any(math.dist(s["ponta"], (x, y)) <= TOLERANCIA_MM for s in lista_saidas):
            continue  # a ponta chega a uma eletrocalha: é saída, não ponta solta
        if len(ligados) == 1:
            pontas_soltas.append({"x": x, "y": y, "diametro": ligados[0]["diametro"],
                                  "altura": float(ligados[0]["altura"] or 0), "nome": ligados[0]["nome"]})
            avisos.append(f"Eletroduto {ligados[0]['nome']}: ponta solta em ({x / 1000:.2f}; {y / 1000:.2f}) m, "
                          "sem caixa.")
        elif len(ligados) == 2:
            if principal["tipo"] != "Rígido":
                continue  # o flexível dobra no lugar
            desvio = bandejas._desvio(*(rede.direcao(t, indice) for t in ligados))
            pecas.append(peca(LUVA if desvio < 5.0 else _nome_da_curva(desvio), principal))
        elif principal["instalacao"] == APARENTE:
            pecas.append(peca(f"{CONDULETE} {({3: 'T', 4: 'X'}).get(len(ligados), 'múltiplo')}", principal))
        else:
            caixas_novas.append({"x": x, "y": y, "diametro": principal["diametro"]})

    trechos = []
    for trecho in rede.trechos:
        (x1, y1), (x2, y2) = rede.nos[trecho["a"]], rede.nos[trecho["b"]]
        comprimento = rede.comprimento(trecho)
        trechos.append({chave: trecho[chave] for chave in ("diametro", "tipo", "material", "instalacao", "nome")})
        trechos[-1].update(comprimento=comprimento, x1=x1, y1=y1, x2=x2, y2=y2)
        if trecho["tipo"] == "Rígido":
            luvas = max(0, math.ceil(comprimento / COMPRIMENTO_BARRA_MM - 1e-9) - 1)
            ux, uy = (x2 - x1) / comprimento, (y2 - y1) / comprimento
            for k in range(1, luvas + 1):
                d = k * COMPRIMENTO_BARRA_MM
                pecas.append({"x": x1 + ux * d, "y": y1 + uy * d, "peca": LUVA, "diametro": trecho["diametro"],
                              "tipo": trecho["tipo"], "material": trecho["material"],
                              "instalacao": trecho["instalacao"]})
    for s in lista_saidas:
        base = {"x": s["x"], "y": s["y"], "diametro": s["diametro"], "tipo": s["tipo_eletroduto"],
                "material": s["material"], "instalacao": s["instalacao"]}
        pecas.append(dict(base, peca=s["peca"]))
        if s["tipo_eletroduto"] == "Rígido":
            pecas.append(dict(base, peca=BUCHA))
            if s["tipo"] == "vertical":
                pecas.append(dict(base, peca=CURVA_VERTICAL))
        if s.get("descida"):
            descidas.append(s["descida"])
    return {"pecas": pecas, "trechos": trechos, "caixas_novas": caixas_novas, "avisos": avisos,
            "pontas_soltas": pontas_soltas, "descidas": descidas, "saidas": lista_saidas}


def materiais(resultado):
    """Peças e fixação dos eletrodutos, no formato dos componentes de ``core.quantitativos.montar``."""
    somas = {}

    def somar(grupo, item, especificacao_, unidade, quantidade):
        chave = (grupo, item, especificacao_, unidade)
        somas[chave] = somas.get(chave, 0) + quantidade

    for p in resultado["pecas"]:
        if p["peca"] in (SAIDA_HORIZONTAL, SAIDA_VERTICAL):
            somar(GRUPO_BANDEJAS, p["peca"], f'Ø{p["diametro"]}"', "un", 1)
        else:
            somar(GRUPO, p["peca"], especificacao(p), "un", 1)
    for t in resultado["trechos"]:
        if t["instalacao"] == APARENTE and t["comprimento"] > 0:
            quantidade = math.ceil(t["comprimento"] / ESPACO_ABRACADEIRA_MM - 1e-9) + 1
            somar(GRUPO_FIXACAO, "Abraçadeira tipo D", f'{t["diametro"]}"', "un", quantidade)
            somar(GRUPO_FIXACAO, "Parafuso com bucha de nylon", "para abraçadeira", "un", quantidade)
    return [{"grupo": g, "item": i, "especificacao": e, "unidade": u, "quantidade": q}
            for (g, i, e, u), q in sorted(somas.items())]


def rotulos(caminhos, afastamento=120.0, evitar=(), distancia_minima=500.0):
    """Texto do diâmetro de cada eletroduto (e a altura do lance, ``rotulo_altura``, se houver),
    no meio do trecho mais longo e afastado da linha.

    Se houver uma peça (``evitar``: posições das siglas) a menos de
    ``distancia_minima`` do meio, o texto vai para 1/4 do trecho.

    Returns:
        [(x, y, ângulo do trecho em graus, 'Ø3/4"')].
    """
    resultado = []
    for caminho in caminhos:
        pontos = caminho["pontos"]
        trechos = [(math.hypot(b[0] - a[0], b[1] - a[1]), a, b) for a, b in zip(pontos, pontos[1:])]
        if not trechos:
            continue
        comprimento, a, b = max(trechos, key=lambda t: t[0])
        if comprimento <= 0:
            continue
        ux, uy = (b[0] - a[0]) / comprimento, (b[1] - a[1]) / comprimento
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if any(math.hypot(px - mx, py - my) < distancia_minima for px, py in evitar):
            mx, my = a[0] + (b[0] - a[0]) / 4, a[1] + (b[1] - a[1]) / 4
        resultado.append((round(mx - uy * afastamento, 6), round(my + ux * afastamento, 6),
                          math.degrees(math.atan2(uy, ux)),
                          f'Ø{caminho["diametro"]}"' + (f' {caminho["rotulo_altura"]}' if caminho.get("rotulo_altura") else "")))
    return resultado


def solidos_da_saida(saida):
    """Primitivas 3D da peça de saída, com Z a partir do piso do pavimento.

    Horizontal: flange encostada na aba, do lado de fora, e a luva saindo para fora
    da eletrocalha. Vertical: flange embaixo do fundo (ou em cima da aba, se o
    eletroduto vem de cima) e a luva para baixo (ou para cima).

    Returns:
        [('placa', centro (x, y, z), normal (x, y, z), lado, espessura),
         ('cilindro', base (x, y, z), direção (x, y, z), raio, comprimento)] — flange, luva e anel.
    """
    externo = _diametro_externo(saida.get("diametro"))
    lado = externo + 2 * ABA_FLANGE_MM
    comprimento = max(COMPRIMENTO_LUVA_MIN_MM, externo)
    raio = externo / 2.0 + FOLGA_LUVA_MM
    x, y, z = float(saida["x"]), float(saida["y"]), float(saida["z"])
    if saida["tipo"] == "horizontal":
        direcao = (saida["normal"][0], saida["normal"][1], 0.0)
    else:
        direcao = (0.0, 0.0, float(saida.get("sentido", -1.0)))

    def andar(distancia):
        return (x + direcao[0] * distancia, y + direcao[1] * distancia, z + direcao[2] * distancia)

    return [
        ("placa", andar(ESPESSURA_FLANGE_MM / 2.0), direcao, lado, ESPESSURA_FLANGE_MM),
        ("cilindro", andar(ESPESSURA_FLANGE_MM), direcao, raio, comprimento),
        ("cilindro", andar(ESPESSURA_FLANGE_MM + comprimento - ANEL_MM), direcao, raio + 3.0, ANEL_MM),
    ]


SIGLA_SAIDA = {"horizontal": "SH", "vertical": "SV"}


def marcas_de_saida(resultado):
    """Pontos das saídas de eletrocalha na planta: [(x, y, 'SH Ø3/4"')] (SH horizontal, SV vertical)."""
    return [(s["x"], s["y"], f'{SIGLA_SAIDA[s["tipo"]]} Ø{s["diametro"]}"') for s in resultado.get("saidas", [])]


def siglas(resultado):
    """Siglas das peças que aparecem na planta: curvas (C90, C45) e conduletes (CT, CX).

    Returns:
        [(x, y, sigla)], uma por nó.
    """
    por_no = {}
    for p in resultado["pecas"]:
        if p["peca"] == CURVA_VERTICAL:
            continue  # a descida tem o símbolo de subida e descida
        if p["peca"].startswith(CURVA):
            sigla = "C" + p["peca"][len(CURVA):].strip().rstrip("°")
        elif p["peca"].startswith(CONDULETE):
            sigla = "C" + {"T": "T", "X": "X"}.get(p["peca"].split()[-1], "M")
        else:
            continue
        por_no.setdefault((p["x"], p["y"]), sigla)
    return [(x, y, s) for (x, y), s in por_no.items()]
