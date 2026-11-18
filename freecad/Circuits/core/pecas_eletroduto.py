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


def _descida(rede, indice, ligados, por_nome):
    """Descida no nó, se chegam eletrodutos em alturas diferentes; senão None.

    Cada eletroduto que termina no nó sozinho na menor ou na maior altura faz
    uma curva de 90° até a vertical; os que passam pelo nó, ou dividem a altura
    com outro (derivação), chegam à vertical sem curva.
    """
    x, y = rede.nos[indice]
    bracos = []
    for t in ligados:
        angulo = math.radians(rede.direcao(t, indice))
        bracos.append({"nome": t["nome"], "ponta": _ponta(por_nome.get(t["nome"]), (x, y)),
                       "ux": math.cos(angulo), "uy": math.sin(angulo), "altura": float(t["altura"] or 0),
                       "diametro": t["diametro"], "tipo": t["tipo"], "material": t["material"],
                       "instalacao": t["instalacao"], "comprimento": rede.comprimento(t), "curva": False})
    alturas = [b["altura"] for b in bracos]
    de, ate = min(alturas), max(alturas)
    if ate - de <= TOLERANCIA_ALTURA_MM:
        return None
    principal = max(bracos, key=lambda b: _diametro_externo(b["diametro"]))
    nas_pontas = []
    for altura in (de, ate):
        mesma = [b for b in bracos if abs(b["altura"] - altura) <= TOLERANCIA_ALTURA_MM]
        if len(mesma) == 1 and mesma[0]["ponta"]:
            mesma[0]["curva"] = True
            nas_pontas.append(mesma[0])
    raio = raio_da_curva(principal["diametro"], principal["tipo"])
    if nas_pontas:  # a curva cabe na vertical e no trecho reto que chega
        raio = min([raio, (ate - de) / len(nas_pontas)] + [0.9 * b["comprimento"] for b in nas_pontas])
    return {"x": x, "y": y, "de": de, "ate": ate, "diametro": principal["diametro"], "tipo": principal["tipo"],
            "raio": round(raio, 1), "bracos": bracos}


def analisar(caminhos, caixas=()):
    """Peças, caixas de passagem que faltam e avisos dos eletrodutos de um pavimento.

    Args:
        caminhos: dicionários com ``pontos`` [(x, y)], ``tipo`` ('Flexível' ou
            'Rígido'), ``material``, ``instalacao``, ``diametro``, ``altura`` e ``nome``.
        caixas: posições (x, y) das caixas da planta (pontos, quadros, passagens).
    Returns:
        {'pecas': [{x, y, peca, diametro, tipo, material, instalacao}],
         'trechos': [{comprimento, diametro, tipo, material, instalacao, x1, y1, x2, y2, nome}],
         'caixas_novas': [{x, y, diametro}], 'avisos': [textos],
         'pontas_soltas': [{x, y, diametro, altura, nome}]} — pontas sem caixa, que podem
        ser prumadas para outro pavimento (``core.verticais.ligacoes_entre_pavimentos``),
         'descidas': [{x, y, de, ate, diametro, tipo, raio, bracos}]} — ver ``_descida``.
    """
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

        if any(math.hypot(cx - x, cy - y) <= TOLERANCIA_MM for cx, cy in caixas):
            pecas += [peca(BUCHA, t) for t in ligados if t["tipo"] == "Rígido"]
            continue
        descida = _descida(rede, indice, ligados, por_nome) if len(ligados) > 1 else None
        if descida:
            descidas.append(descida)
            pecas += [peca(CURVA_VERTICAL, b) for b in descida["bracos"] if b["curva"] and b["tipo"] == "Rígido"]
            if len(ligados) == 2:
                continue  # as duas curvas e a vertical fazem a ligação
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
    return {"pecas": pecas, "trechos": trechos, "caixas_novas": caixas_novas, "avisos": avisos,
            "pontas_soltas": pontas_soltas, "descidas": descidas}


def materiais(resultado):
    """Peças e fixação dos eletrodutos, no formato dos componentes de ``core.quantitativos.montar``."""
    somas = {}

    def somar(grupo, item, especificacao_, unidade, quantidade):
        chave = (grupo, item, especificacao_, unidade)
        somas[chave] = somas.get(chave, 0) + quantidade

    for p in resultado["pecas"]:
        somar(GRUPO, p["peca"], especificacao(p), "un", 1)
    for t in resultado["trechos"]:
        if t["instalacao"] == APARENTE and t["comprimento"] > 0:
            quantidade = math.ceil(t["comprimento"] / ESPACO_ABRACADEIRA_MM - 1e-9) + 1
            somar(GRUPO_FIXACAO, "Abraçadeira tipo D", f'{t["diametro"]}"', "un", quantidade)
            somar(GRUPO_FIXACAO, "Parafuso com bucha de nylon", "para abraçadeira", "un", quantidade)
    return [{"grupo": g, "item": i, "especificacao": e, "unidade": u, "quantidade": q}
            for (g, i, e, u), q in sorted(somas.items())]


def rotulos(caminhos, afastamento=120.0, evitar=(), distancia_minima=500.0):
    """Texto do diâmetro de cada eletroduto, no meio do trecho mais longo e afastado da linha.

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
                          math.degrees(math.atan2(uy, ux)), f'Ø{caminho["diametro"]}"'))
    return resultado


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
