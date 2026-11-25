"""Ocupação dos eletrodutos e das eletrocalhas pelos cabos que passam neles.

NBR 5410, 6.2.11.1.6: a soma das áreas dos cabos (pelo diâmetro externo) não pode
passar de 53 % da seção interna do eletroduto com um cabo, 31 % com dois e 40 % com
três ou mais.

Na eletrocalha a NBR 5410 não dá uma taxa como a do eletroduto: o módulo informa a
área ocupada em relação à seção útil (largura × aba) e a largura de uma camada
única (soma dos diâmetros), sem reprovar. ``REFERENCIA_BANDEJA`` (40 %) é só um
valor usual de referência, a decidir (``docs/Plano_proximas_etapas.md``).

Os diâmetros são aproximados, de catálogos de mercado; não são de um fabricante.
Unidades: diâmetros em mm, áreas em mm², seções em mm².
"""
import math

TAXAS = {1: 0.53, 2: 0.31}
TAXA_TRES_OU_MAIS = 0.40
REFERENCIA_BANDEJA = 0.40

# Diâmetro interno [mm] por tamanho nominal: PVC rígido roscável (classe A, NBR 15465).
DIAMETROS_INTERNOS = {
    "1/2": 16.1, "3/4": 21.0, "1": 26.8, "1 1/4": 35.0, "1 1/2": 39.8, "2": 50.2, "3": 75.6, "4": 97.8,
}
# Eletroduto flexível corrugado de PVC: a parede ondulada reduz a seção livre.
DIAMETROS_INTERNOS_FLEXIVEL = {"1/2": 15.0, "3/4": 19.0, "1": 25.0, "1 1/4": 33.0}

# Diâmetro externo [mm] do cabo flexível 450/750 V (isolação de PVC) por seção [mm²].
DIAMETRO_CABO = {
    0.5: 2.2, 0.75: 2.5, 1.0: 2.6, 1.5: 2.9, 2.5: 3.6, 4.0: 4.2, 6.0: 4.8, 10.0: 6.4, 16.0: 7.5, 25.0: 9.3,
    35.0: 10.6, 50.0: 12.5, 70.0: 14.6, 95.0: 16.9, 120.0: 18.9, 150.0: 21.0, 185.0: 23.4, 240.0: 26.6,
}


def taxa_maxima(cabos):
    """Fração máxima da seção interna do eletroduto ocupada por ``cabos`` cabos (6.2.11.1.6)."""
    if cabos < 1:
        raise ValueError("sem cabos no eletroduto")
    return TAXAS.get(int(cabos), TAXA_TRES_OU_MAIS)


def area_cabo(diametro):
    """Área [mm²] da seção de um cabo de diâmetro externo ``diametro`` [mm]."""
    return math.pi * float(diametro) ** 2 / 4.0


def area_interna(diametro_interno):
    return math.pi * float(diametro_interno) ** 2 / 4.0


def diametro_do_cabo(secao):
    """Diâmetro externo [mm] do cabo pela seção [mm²]; seção fora da tabela usa a próxima maior."""
    secao = float(secao)
    if secao in DIAMETRO_CABO:
        return DIAMETRO_CABO[secao]
    maiores = [s for s in DIAMETRO_CABO if s >= secao]
    if maiores:
        return DIAMETRO_CABO[min(maiores)]
    return 2.0 * math.sqrt(secao / math.pi) * 1.6  # além da tabela: cobre mais isolação, estimado


def internos_do_tipo(tipo):
    """Tabela de diâmetros internos pelo tipo do eletroduto ('Flexível' ou 'Rígido')."""
    if str(tipo).lower().startswith("flex"):
        return dict(DIAMETROS_INTERNOS, **DIAMETROS_INTERNOS_FLEXIVEL)
    return dict(DIAMETROS_INTERNOS)


def _em_ordem(internos):
    return sorted(internos, key=lambda nominal: internos[nominal])


def taxa(nominal, diametros_cabos, internos=None):
    """Fração da seção interna do eletroduto ``nominal`` ocupada pelos cabos (0 sem cabos)."""
    internos = internos or DIAMETROS_INTERNOS
    if nominal not in internos or not diametros_cabos:
        return 0.0
    return sum(area_cabo(d) for d in diametros_cabos) / area_interna(internos[nominal])


def comporta(nominal, diametros_cabos, internos=None):
    """O eletroduto ``nominal`` comporta os cabos pela taxa máxima? Sem cabos, sim."""
    if not diametros_cabos:
        return True
    internos = internos or DIAMETROS_INTERNOS
    if nominal not in internos:
        return False
    return taxa(nominal, diametros_cabos, internos) <= taxa_maxima(len(diametros_cabos)) + 1e-9


def eletroduto_minimo(diametros_cabos, internos=None):
    """Menor tamanho nominal que comporta os cabos, ou None se nenhum comporta.

    Args:
        diametros_cabos: diâmetro externo de cada cabo [mm].
        internos: {nominal: diâmetro interno [mm]} (padrão ``DIAMETROS_INTERNOS``).
    """
    internos = internos or DIAMETROS_INTERNOS
    return next((n for n in _em_ordem(internos) if comporta(n, diametros_cabos, internos)), None)


def eletroduto_pequeno(nominal, diametros_cabos, internos=None):
    """O eletroduto desenhado (``nominal``) é menor que o necessário?"""
    return not comporta(nominal, diametros_cabos, internos)


def maior(a, b, internos=None):
    """O maior de dois tamanhos nominais (pela tabela de diâmetros internos)."""
    internos = internos or DIAMETROS_INTERNOS
    return a if internos.get(a, 0.0) >= internos.get(b, 0.0) else b


# --- verificação dos trechos da rede ----------------------------------------------------------

def _cabos(condutores):
    return [diametro_do_cabo(c["secao"]) for c in condutores]


def _rotulo(condutores):
    """'4 × #2,5 + 2 × #1,5' pelos condutores de um trecho."""
    contagem = {}
    for c in condutores:
        contagem[float(c["secao"])] = contagem.get(float(c["secao"]), 0) + 1
    partes = [f"{n} × #{secao:g}" for secao, n in sorted(contagem.items(), reverse=True)]
    return " + ".join(partes).replace(".", ",")


def _circuitos(condutores):
    vistos = []
    for c in condutores:
        if c.get("circuito") and c["circuito"] not in vistos:
            vistos.append(c["circuito"])
    return vistos


def verificar_eletroduto(nome, nominal, tipo, trechos):
    """Ocupação de um eletroduto pelo trecho mais cheio.

    Args:
        nome: nome do eletroduto.
        nominal: tamanho desenhado ('3/4').
        tipo: 'Flexível' ou 'Rígido' (diâmetros internos de ``internos_do_tipo``).
        trechos: lista de {'comprimento' [m], 'condutores': [{'secao', 'funcao', 'circuito'}]}.
    Returns:
        dict com ``nome``, ``diametro``, ``tipo``, ``cabos`` (do trecho mais cheio),
        ``condutores`` (rótulo), ``circuitos``, ``area`` [mm²], ``taxa`` e
        ``taxa_maxima`` (frações), ``minimo`` (nominal ou None), ``pequeno``,
        ``comprimento`` [m] e ``avisos``.
    """
    internos = internos_do_tipo(tipo)
    cheio = max(trechos, key=lambda t: sum(area_cabo(d) for d in _cabos(t["condutores"])), default=None)
    condutores = cheio["condutores"] if cheio else []
    cabos = _cabos(condutores)
    minimo = eletroduto_minimo(cabos, internos) if cabos else None
    todos = [c for t in trechos for c in t["condutores"]]
    resultado = {
        "nome": nome, "diametro": str(nominal), "tipo": str(tipo), "cabos": len(cabos),
        "condutores": _rotulo(condutores), "circuitos": _circuitos(todos),
        "area": round(sum(area_cabo(d) for d in cabos), 1),
        "taxa": round(taxa(str(nominal), cabos, internos), 3),
        "taxa_maxima": taxa_maxima(len(cabos)) if cabos else 0.0,
        "minimo": minimo, "pequeno": bool(cabos) and eletroduto_pequeno(str(nominal), cabos, internos),
        "comprimento": round(sum(t["comprimento"] for t in trechos), 2), "avisos": [],
    }
    if cabos and minimo is None:
        resultado["avisos"].append(f"{nome}: nenhum eletroduto da tabela comporta {len(cabos)} cabos; divida o trajeto.")
    elif resultado["pequeno"]:
        resultado["avisos"].append(
            f"{nome}: Ø{nominal}\" com {len(cabos)} cabos ocupa {resultado['taxa']:.0%} "
            f"(máximo {resultado['taxa_maxima']:.0%}); use Ø{minimo}\".")
    return resultado


def verificar_bandeja(nome, largura, aba, trechos):
    """Ocupação informativa de uma eletrocalha ou leito pelo trecho mais cheio.

    Returns:
        dict com ``nome``, ``largura``, ``aba`` [mm], ``cabos``, ``condutores``,
        ``circuitos``, ``area`` [mm²], ``taxa`` (da seção útil largura × aba),
        ``camada_unica`` (soma dos diâmetros [mm]), ``acima_referencia`` e
        ``comprimento`` [m].
    """
    cheio = max(trechos, key=lambda t: sum(area_cabo(d) for d in _cabos(t["condutores"])), default=None)
    condutores = cheio["condutores"] if cheio else []
    cabos = _cabos(condutores)
    area = sum(area_cabo(d) for d in cabos)
    util = float(largura) * float(aba)
    fracao = area / util if util > 0 else 0.0
    todos = [c for t in trechos for c in t["condutores"]]
    return {
        "nome": nome, "largura": float(largura), "aba": float(aba), "cabos": len(cabos),
        "condutores": _rotulo(condutores), "circuitos": _circuitos(todos), "area": round(area, 1),
        "taxa": round(fracao, 3), "camada_unica": round(sum(cabos), 1),
        "acima_referencia": fracao > REFERENCIA_BANDEJA,
        "comprimento": round(sum(t["comprimento"] for t in trechos), 2),
    }


def agrupar_trechos(trechos):
    """{(tipo, nome): [trechos]} pelos donos dos trechos da rede (``core.rede.analisar``)."""
    grupos = {}
    for trecho in trechos:
        if trecho.get("dono"):
            grupos.setdefault((trecho.get("tipo", "eletroduto"), trecho["dono"]), []).append(trecho)
    return grupos


# --- identificação dos fios por trecho, na planta -----------------------------------------------

LETRAS_FUNCAO = (("fase", "F"), ("neutro", "N"), ("retorno", "R"), ("terra", "T"))


def condutores_do_circuito(condutores):
    """'F+N+T', '2F+T', 'F+2R' pelos condutores de um circuito num trecho."""
    partes = []
    for funcao, letra in LETRAS_FUNCAO:
        n = sum(1 for c in condutores if c["funcao"] == funcao)
        if n:
            partes.append(f"{n}{letra}" if n > 1 else letra)
    return "+".join(partes)


def texto_dos_fios(condutores, tipo="eletroduto"):
    """Linhas do texto de um trecho: ``C1 #2,5 F+N+T`` por circuito (seções diferentes, linhas
    separadas); na eletrocalha, uma linha só com os circuitos e o total de cabos."""
    if not condutores:
        return []
    if tipo == "bandeja":
        circuitos = _circuitos(condutores) or ["sem circuito"]
        return [f"{', '.join(circuitos)} · {len(condutores)} cabos"]
    grupos = {}
    for c in condutores:
        grupos.setdefault((c.get("circuito", ""), float(c["secao"])), []).append(c)
    linhas = []
    for (circuito, secao), lista in grupos.items():
        rotulo = f"{circuito} " if circuito else ""
        linhas.append(f"{rotulo}#{secao:g} {condutores_do_circuito(lista)}".replace(".", ","))
    return linhas


def identificacao_dos_trechos(trechos, afastamento=120.0):
    """Onde escrever os fios de cada eletroduto e eletrocalha na planta.

    Num mesmo dono, trechos com os mesmos condutores levam um texto só, no meio do mais
    longo, do lado direito da linha (o diâmetro ``Ø`` fica do lado esquerdo).

    Returns:
        [{'dono', 'tipo', 'pavimento', 'x', 'y', 'angulo' (graus, sempre legível), 'linhas'}].
    """
    escolhidos = {}
    for trecho in trechos:
        linhas = texto_dos_fios(trecho["condutores"], trecho.get("tipo", "eletroduto"))
        if not linhas or "de" not in trecho:
            continue
        chave = (trecho.get("pavimento", ""), trecho["dono"], tuple(linhas))
        if chave not in escolhidos or trecho["comprimento"] > escolhidos[chave][0]["comprimento"]:
            escolhidos[chave] = (trecho, linhas)
    resultado = []
    for (pavimento, dono, _), (trecho, linhas) in sorted(escolhidos.items()):
        (ax, ay), (bx, by) = trecho["de"], trecho["ate"]
        comprimento = math.hypot(bx - ax, by - ay)
        if comprimento <= 0:
            continue
        ux, uy = (bx - ax) / comprimento, (by - ay) / comprimento
        if ux < -1e-9 or (abs(ux) <= 1e-9 and uy < 0):  # texto da esquerda para a direita ou de baixo para cima
            ux, uy = -ux, -uy
        mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
        resultado.append({
            "dono": dono, "tipo": trecho.get("tipo", "eletroduto"), "pavimento": pavimento,
            "x": round(mx + uy * afastamento, 6), "y": round(my - ux * afastamento, 6),
            "angulo": round(math.degrees(math.atan2(uy, ux)), 6), "linhas": linhas,
        })
    return resultado


CABECALHO = ("Infraestrutura", "Tipo", "Desenhado", "Cabos no trecho mais cheio", "Condutores", "Circuitos",
             "Área dos cabos [mm²]", "Ocupação", "Máxima", "Sugerido", "Situação")


def tabela(eletrodutos, bandejas_=()):
    """Linhas da planilha de ocupação: cabeçalho e uma linha por eletroduto e eletrocalha."""
    linhas = [CABECALHO]
    for e in sorted(eletrodutos, key=lambda e: (not e["pequeno"], e["nome"])):
        if e["cabos"] == 0:
            situacao = "sem cabos"
        elif e["minimo"] is None:
            situacao = "nenhum comporta"
        else:
            situacao = f"aumentar para {e['minimo']}" if e["pequeno"] else "ok"
        linhas.append((e["nome"], f"Eletroduto {e['tipo'].lower()}", e["diametro"], e["cabos"], e["condutores"],
                       ", ".join(e["circuitos"]), e["area"], f"{e['taxa']:.0%}",
                       f"{e['taxa_maxima']:.0%}" if e["cabos"] else "", e["minimo"] or "", situacao))
    for b in sorted(bandejas_, key=lambda b: b["nome"]):
        linhas.append((b["nome"], "Eletrocalha/leito", f"{b['largura']:.0f} × {b['aba']:.0f}", b["cabos"],
                       b["condutores"], ", ".join(b["circuitos"]), b["area"], f"{b['taxa']:.0%}",
                       f"{REFERENCIA_BANDEJA:.0%} (ref.)", f"camada única {b['camada_unica']:.0f} mm",
                       "acima da referência" if b["acima_referencia"] else "ok"))
    return linhas
