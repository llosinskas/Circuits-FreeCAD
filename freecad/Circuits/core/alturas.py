"""Altura de cada trecho do eletroduto, como o "offset" de cada segmento no Revit.

Um eletroduto (Draft Wire) tem ``Altura3D``, a altura do piso até ele, e pode ter
``AlturasTrechos``, uma altura por trecho (entre dois vértices seguidos). Onde dois
trechos seguidos têm alturas diferentes, o eletroduto sobe ou desce naquele vértice:
para a análise, ele é dividido em **lances** de mesma altura que se encontram no
vértice, e a rede (``core.rede``, ``core.pecas_eletroduto``) já trata esse encontro
como uma subida ou descida, com as duas curvas de 90°, o símbolo na planta, a vertical
nos quantitativos e no 3D.

Unidades: mm, alturas a partir do piso do pavimento.
"""
import math

TOLERANCIA_ALTURA_MM = 10.0  # alturas mais próximas que isto são a mesma
TOLERANCIA_PONTO_MM = 50.0


def alturas_dos_trechos(n_trechos, altura, lista=()):
    """Altura de cada um dos ``n_trechos``: ``lista`` se tiver um valor por trecho, senão ``altura``."""
    lista = [float(v) for v in (lista or ())]
    if len(lista) == n_trechos and n_trechos > 0:
        return lista
    return [float(altura)] * max(n_trechos, 0)


def mesma(a, b):
    return abs(float(a) - float(b)) <= TOLERANCIA_ALTURA_MM


def varias_alturas(alturas):
    """O eletroduto muda de altura em algum vértice?"""
    return any(not mesma(a, alturas[0]) for a in alturas[1:])


def lances(pontos, alturas):
    """Divide o eletroduto em lances de mesma altura.

    Args:
        pontos: vértices [(x, y)].
        alturas: uma altura por trecho (``len(pontos) - 1``).
    Returns:
        [{'pontos': [(x, y)], 'altura', 'trechos': (primeiro, último)}]; lances seguidos
        dividem o vértice onde a altura muda.
    """
    resultado = []
    for indice, altura in enumerate(alturas):
        if resultado and mesma(resultado[-1]["altura"], altura):
            resultado[-1]["pontos"].append(tuple(pontos[indice + 1]))
            resultado[-1]["trechos"] = (resultado[-1]["trechos"][0], indice)
        else:
            resultado.append({"pontos": [tuple(pontos[indice]), tuple(pontos[indice + 1])], "altura": float(altura),
                              "trechos": (indice, indice)})
    return resultado


def mudar(alturas, indices, nova):
    """Alturas com os trechos ``indices`` em ``nova`` (os outros ficam como estão)."""
    alvo = set(indices)
    return [float(nova) if i in alvo else float(a) for i, a in enumerate(alturas)]


def trechos_a_partir(n_trechos, vertice, sentido="fim"):
    """Trechos do vértice até a ponta: ``'fim'`` (do vértice para o último ponto) ou ``'inicio'``."""
    if sentido == "inicio":
        return list(range(0, min(max(vertice, 0), n_trechos)))
    return list(range(max(vertice, 0), n_trechos))


def trecho_mais_proximo(pontos, ponto):
    """Índice do trecho mais perto do ponto (meio de uma aresta selecionada)."""
    def distancia(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        quadrado = dx * dx + dy * dy
        t = 0.0 if quadrado == 0 else max(0.0, min(1.0, ((ponto[0] - a[0]) * dx + (ponto[1] - a[1]) * dy) / quadrado))
        return math.hypot(ponto[0] - a[0] - t * dx, ponto[1] - a[1] - t * dy)
    return min(range(len(pontos) - 1), key=lambda i: distancia(pontos[i], pontos[i + 1]))


def vertice_mais_proximo(pontos, ponto):
    return min(range(len(pontos)), key=lambda i: math.hypot(pontos[i][0] - ponto[0], pontos[i][1] - ponto[1]))


def trechos_da_selecao(pontos, arestas=(), vertices=(), sentido="fim"):
    """Trechos que mudam de altura pelo que foi selecionado no eletroduto.

    Args:
        pontos: vértices [(x, y)].
        arestas: pontos do meio das arestas selecionadas: esses trechos.
        vertices: pontos dos vértices selecionados: do vértice até a ponta (``sentido``
            'fim' ou 'inicio'), como mudar o offset a partir de um ponto no Revit.
    Returns:
        Índices dos trechos; sem nada selecionado, todos.
    """
    n = len(pontos) - 1
    trechos = {trecho_mais_proximo(pontos, p) for p in arestas}
    for p in vertices:
        trechos.update(trechos_a_partir(n, vertice_mais_proximo(pontos, p), sentido))
    return sorted(trechos) if (arestas or vertices) else list(range(n))


def trocar_no_no(pontos, alturas, x, y, antiga, nova, tolerancia=TOLERANCIA_PONTO_MM):
    """Troca a altura do lance de altura ``antiga`` que chega no ponto (x, y) por ``nova``.

    Usado pelo editor de descidas: a altura muda só no lance que chega na descida, não no
    eletroduto inteiro. Sem lance na ponta, devolve as alturas como estão.
    """
    for lance in lances(pontos, alturas):
        if not mesma(lance["altura"], antiga):
            continue
        pontas = (lance["pontos"][0], lance["pontos"][-1])
        if any(math.hypot(px - x, py - y) <= tolerancia for px, py in pontas):
            primeiro, ultimo = lance["trechos"]
            return mudar(alturas, range(primeiro, ultimo + 1), nova)
    return list(alturas)


def rotulo(altura_mm):
    """Altura no rótulo do trecho, como o offset do Revit: 2800 -> '+2,80'."""
    metros = float(altura_mm) / 1000.0
    return ("+" if metros >= 0 else "-") + f"{abs(metros):.2f}".replace(".", ",")
