"""Rede de eletrodutos em planta: encaixe nas caixas, caminhos dos circuitos, fios e verticais.

Sem FreeCAD. Coordenadas e alturas em mm; comprimentos devolvidos em m.

Como a fiação é estimada:

- os eletrodutos desenhados formam uma rede (grafo); vértices a menos de
  ``TOLERANCIA_CONEXAO_MM`` são o mesmo nó, e um eletroduto que termina sobre
  o trecho de outro faz uma derivação em T;
- cada caixa (ponto, interruptor ou quadro) se liga ao nó mais próximo, e a
  diferença entre a altura do eletroduto e a da caixa é a vertical dela;
- cada circuito sai do quadro e percorre a união dos caminhos mais curtos até
  os seus pontos; fase vai até os pontos e interruptores, neutro e terra só
  até os pontos;
- cada letra de comando leva um retorno do interruptor até as luminárias, e
  dois condutores a mais entre interruptores paralelos e intermediários;
- cada ponta de fio ganha ``FOLGA_PONTA_MM`` de sobra para as ligações.
"""
import heapq
import math

TOLERANCIA_CONEXAO_MM = 50.0
TOLERANCIA_ENCAIXE_MM = 300.0
FOLGA_PONTA_MM = 300.0
FUNCOES = ("fase", "neutro", "terra", "retorno")


def distancia(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def projetar(ponto, a, b):
    """Projeção do ponto no trecho AB.

    Returns:
        (ponto projetado, posição t de 0 a 1 ao longo do trecho, distância até o trecho).
    """
    dx, dy = b[0] - a[0], b[1] - a[1]
    quadrado = dx * dx + dy * dy
    if quadrado == 0:
        return tuple(a), 0.0, distancia(ponto, a)
    t = max(0.0, min(1.0, ((ponto[0] - a[0]) * dx + (ponto[1] - a[1]) * dy) / quadrado))
    projetado = (a[0] + t * dx, a[1] + t * dy)
    return projetado, t, distancia(ponto, projetado)


def encaixar(pontos, caixas, tolerancia=TOLERANCIA_ENCAIXE_MM):
    """Puxa o traçado de um eletroduto para as caixas próximas.

    Um vértice a até ``tolerancia`` de uma caixa vai para cima dela; uma caixa
    a até ``tolerancia`` do meio de um trecho ganha um vértice novo nesse trecho.

    Args:
        pontos: vértices do eletroduto, (x, y), em ordem.
        caixas: posições (x, y) das caixas.
    Returns:
        (novos vértices, índices das caixas encaixadas, em ordem).
    """
    novos = [tuple(p) for p in pontos]
    usadas = set()
    for i, vertice in enumerate(novos):
        livres = [(distancia(vertice, caixa), j) for j, caixa in enumerate(caixas) if j not in usadas]
        if livres:
            d, j = min(livres)
            if d <= tolerancia:
                novos[i] = tuple(caixas[j])
                usadas.add(j)

    insercoes = {}
    for j, caixa in enumerate(caixas):
        if j in usadas:
            continue
        melhor = None
        for i in range(len(novos) - 1):
            _, t, d = projetar(caixa, novos[i], novos[i + 1])
            if 0 < t < 1 and d <= tolerancia and (melhor is None or d < melhor[2]):
                melhor = (i, t, d)
        if melhor is not None:
            insercoes.setdefault(melhor[0], []).append((melhor[1], j))
            usadas.add(j)

    resultado = []
    for i, vertice in enumerate(novos):
        resultado.append(vertice)
        resultado += [tuple(caixas[j]) for _, j in sorted(insercoes.get(i, []))]
    return resultado, sorted(usadas)


class Rede:
    """Grafo dos eletrodutos: nós nos vértices, arestas nos trechos, peso = comprimento [mm]."""

    def __init__(self, tolerancia=TOLERANCIA_CONEXAO_MM):
        self.tolerancia = tolerancia
        self.nos = []
        self.altura = []
        self.diametro = []
        self.vizinhos = []

    @classmethod
    def construir(cls, caminhos, tolerancia=TOLERANCIA_CONEXAO_MM):
        """Monta a rede.

        Args:
            caminhos: dicionários com ``pontos`` [(x, y)], ``altura`` [mm] e ``diametro``.
        """
        rede = cls(tolerancia)
        indices = [[rede._no(p, c["altura"], c["diametro"]) for p in c["pontos"]] for c in caminhos]
        for sequencia in indices:
            for a, b in zip(sequencia, sequencia[1:]):
                if a != b:
                    rede._ligar_trecho(a, b)
        return rede

    def _no(self, ponto, altura, diametro):
        for indice, existente in enumerate(self.nos):
            if distancia(ponto, existente) <= self.tolerancia:
                return indice
        self.nos.append(tuple(ponto))
        self.altura.append(float(altura))
        self.diametro.append(str(diametro))
        self.vizinhos.append({})
        return len(self.nos) - 1

    def _ligar_trecho(self, a, b):
        """Liga A a B passando pelos nós que caem sobre o trecho (derivações em T)."""
        meio = []
        for k, ponto in enumerate(self.nos):
            if k in (a, b):
                continue
            _, t, d = projetar(ponto, self.nos[a], self.nos[b])
            if 0 < t < 1 and d <= self.tolerancia:
                meio.append((t, k))
        sequencia = [a] + [k for _, k in sorted(meio)] + [b]
        for u, v in zip(sequencia, sequencia[1:]):
            comprimento = distancia(self.nos[u], self.nos[v])
            self.vizinhos[u][v] = comprimento
            self.vizinhos[v][u] = comprimento

    def no_mais_proximo(self, ponto):
        """Nó a até a tolerância do ponto, ou None."""
        candidatos = [(distancia(ponto, no), i) for i, no in enumerate(self.nos)]
        if not candidatos:
            return None
        d, indice = min(candidatos)
        return indice if d <= self.tolerancia else None

    def distancias(self, origem):
        """Caminhos mais curtos a partir da origem (Dijkstra): (distância por nó, nó anterior)."""
        dist, anterior = {origem: 0.0}, {}
        fila = [(0.0, origem)]
        while fila:
            atual, no = heapq.heappop(fila)
            if atual > dist[no]:
                continue
            for vizinho, peso in self.vizinhos[no].items():
                novo = atual + peso
                if novo < dist.get(vizinho, math.inf):
                    dist[vizinho], anterior[vizinho] = novo, no
                    heapq.heappush(fila, (novo, vizinho))
        return dist, anterior

    def arvore(self, origem, destinos):
        """União dos caminhos mais curtos da origem até os destinos.

        Returns:
            (comprimento horizontal [mm], destinos sem caminho).
        """
        dist, anterior = self.distancias(origem)
        arestas, sem_caminho = set(), []
        for destino in destinos:
            if destino not in dist:
                sem_caminho.append(destino)
                continue
            no = destino
            while no != origem:
                arestas.add(frozenset((no, anterior[no])))
                no = anterior[no]
        comprimento = sum(self.vizinhos[a][b] for a, b in (tuple(aresta) for aresta in arestas))
        return comprimento, sem_caminho


def _rotulo_condutores(fases, neutro, terra):
    """Condutores do circuito, como 'F+N+T' ou 'F+F+F+T'."""
    return "+".join(["F"] * fases + (["N"] if neutro else []) + (["T"] if terra else []))


def analisar(caminhos, caixas, info_circuito, folga=FOLGA_PONTA_MM, tolerancia=TOLERANCIA_CONEXAO_MM):
    """Fios por seção e função, fiação por circuito e verticais de um pavimento.

    Args:
        caminhos: eletrodutos, como em ``Rede.construir``.
        caixas: dicionários com ``id``, ``nome``, ``x``, ``y``, ``altura`` [mm] e
            ``tipo`` ('ponto', 'interruptor' ou 'quadro'). Pontos e interruptores
            têm ``circuito`` e ``comando``, e os pontos ``quadro`` (referência ao
            quadro, ou vazio para o mais próximo pela rede). Quadros têm ``refs``,
            os nomes pelos quais podem ser referidos.
        info_circuito: função (caixa do quadro, número do circuito, caixas do circuito)
            que devolve {'secao': mm², 'fases': 1 a 3, 'neutro': bool, 'terra': bool}.
    Returns:
        dict com ``fios`` {(seção, função): m}, ``circuitos`` (lista), ``verticais``
        (lista) e ``avisos`` (textos).
    """
    rede = Rede.construir(caminhos, tolerancia)
    ligadas, verticais, avisos = {}, [], []
    for caixa in caixas:
        no = rede.no_mais_proximo((caixa["x"], caixa["y"]))
        if no is None:
            if caixa["tipo"] != "quadro" and (caixa.get("circuito") or caixa.get("comando")):
                avisos.append(f"{caixa['nome']}: sem eletroduto chegando na caixa.")
            continue
        vertical = abs(rede.altura[no] - caixa["altura"])
        ligadas[caixa["id"]] = (no, vertical)
        if vertical > 1:
            verticais.append({
                "pavimento": caixa.get("pavimento", ""),
                "caixa": caixa["nome"],
                "circuito": str(caixa.get("circuito", "")),
                "altura_eletroduto": rede.altura[no],
                "altura_caixa": float(caixa["altura"]),
                "comprimento": vertical / 1000.0,
                "sentido": "descida" if caixa["altura"] < rede.altura[no] else "subida",
                "diametro": rede.diametro[no],
            })

    quadros = [c for c in caixas if c["tipo"] == "quadro" and c["id"] in ligadas]
    fios, circuitos = {}, []

    def somar(secao, funcao, metros):
        if metros > 0:
            fios[(float(secao), funcao)] = fios.get((float(secao), funcao), 0.0) + metros

    def quadro_de(caixa):
        referencia = str(caixa.get("quadro", "")).strip()
        if referencia:
            return next((q for q in quadros if referencia in q.get("refs", ())), None)
        dist, _ = rede.distancias(ligadas[caixa["id"]][0])
        alcancaveis = [(dist[ligadas[q["id"]][0]], q["id"]) for q in quadros if ligadas[q["id"]][0] in dist]
        if not alcancaveis:
            return None
        return next(q for q in quadros if q["id"] == min(alcancaveis)[1])

    def lance(origem, membros):
        """Comprimento de um condutor [m] da origem até todos os membros, com verticais e folgas."""
        no_origem, vertical_origem = ligadas[origem["id"]]
        horizontal, sem_caminho = rede.arvore(no_origem, [ligadas[m["id"]][0] for m in membros])
        alcancados = [m for m in membros if ligadas[m["id"]][0] not in sem_caminho]
        total = horizontal + vertical_origem + sum(ligadas[m["id"]][1] for m in alcancados)
        total += folga * (len(alcancados) + 1)
        return total / 1000.0, horizontal / 1000.0, [m for m in membros if m not in alcancados]

    grupos, info_por_circuito = {}, {}
    for caixa in caixas:
        if caixa["tipo"] == "quadro" or caixa["id"] not in ligadas or not str(caixa.get("circuito", "")).strip():
            continue
        quadro = quadro_de(caixa)
        if quadro is None:
            avisos.append(f"{caixa['nome']}: nenhum quadro ligado pela rede ao circuito {caixa['circuito']}.")
            continue
        grupos.setdefault((quadro["id"], str(caixa["circuito"]).strip()), []).append(caixa)

    for (quadro_id, numero), membros in sorted(grupos.items(), key=lambda item: (item[0][0], item[0][1])):
        quadro = next(q for q in quadros if q["id"] == quadro_id)
        info = info_circuito(quadro, numero, membros)
        pontos = [m for m in membros if m["tipo"] != "interruptor"] or membros
        fase, trajeto, sem_caminho = lance(quadro, membros)
        neutro_terra, _, _ = lance(quadro, pontos)
        avisos += [f"{m['nome']}: a rede não chega até ele a partir de {quadro['nome']}." for m in sem_caminho]
        somar(info["secao"], "fase", fase * info["fases"])
        if info["neutro"]:
            somar(info["secao"], "neutro", neutro_terra)
        if info["terra"]:
            somar(info["secao"], "terra", neutro_terra)
        info_por_circuito[(quadro_id, numero)] = info
        total = fase * info["fases"] + neutro_terra * (int(info["neutro"]) + int(info["terra"]))
        circuitos.append({
            "quadro": quadro["nome"],
            "circuito": numero,
            "secao": float(info["secao"]),
            "pontos": len(membros),
            "condutores": _rotulo_condutores(info["fases"], info["neutro"], info["terra"]),
            "trajeto": round(trajeto, 2),
            "fio": round(total, 2),
        })

    # Retornos: um por letra de comando, do primeiro interruptor até as luminárias.
    comandos = {}
    for caixa in caixas:
        letra = str(caixa.get("comando", "")).strip().lower()
        if letra and caixa["id"] in ligadas and caixa["tipo"] in ("ponto", "interruptor"):
            comandos.setdefault((caixa.get("pavimento", ""), letra), []).append(caixa)
    for (_, letra), membros in sorted(comandos.items()):
        interruptores = [m for m in membros if m["tipo"] == "interruptor"]
        luzes = [m for m in membros if m["tipo"] == "ponto"]
        if not interruptores or not luzes:
            continue
        secao = 1.5
        for luz in luzes:
            quadro = quadro_de(luz) if str(luz.get("circuito", "")).strip() else None
            info = info_por_circuito.get((quadro["id"], str(luz["circuito"]).strip())) if quadro else None
            if info:
                secao = info["secao"]
                break
        retorno, _, _ = lance(interruptores[0], interruptores[1:] + luzes)
        somar(secao, "retorno", retorno)
        if len(interruptores) > 1:  # paralelo e intermediário: dois condutores entre os interruptores
            entre, _, _ = lance(interruptores[0], interruptores[1:])
            somar(secao, "retorno", 2 * entre)

    return {"fios": fios, "circuitos": circuitos, "verticais": verticais, "avisos": avisos}


def juntar(resultados):
    """Soma os resultados de vários pavimentos."""
    total = {"fios": {}, "circuitos": [], "verticais": [], "avisos": []}
    for resultado in resultados:
        for chave, metros in resultado["fios"].items():
            total["fios"][chave] = total["fios"].get(chave, 0.0) + metros
        for campo in ("circuitos", "verticais", "avisos"):
            total[campo] += resultado[campo]
    return total
