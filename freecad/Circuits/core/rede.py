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

from freecad.Circuits.core.tables.eletrodutos import DIAMETROS_EXTERNOS

TOLERANCIA_ALTURA_MM = 10.0

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
        self.chegando = []  # (altura, diâmetro) de cada eletroduto com vértice no nó
        self.dono = {}  # {frozenset(nó, nó): (nome, tipo)} de cada trecho, quando o caminho tem ``nome``

    @classmethod
    def construir(cls, caminhos, tolerancia=TOLERANCIA_CONEXAO_MM):
        """Monta a rede.

        Args:
            caminhos: dicionários com ``pontos`` [(x, y)], ``altura`` [mm] e ``diametro``;
                opcionalmente ``nome`` (dono dos trechos, em ``dono``) e ``largura`` [mm],
                que faz do caminho uma eletrocalha: a ponta de eletroduto a até meia
                largura (mais a tolerância) da linha de centro dela se liga a ela por um
                trecho do próprio eletroduto (a saída na borda).
        """
        rede = cls(tolerancia)
        indices = [[rede._no(p, c["altura"], c.get("diametro", "")) for p in c["pontos"]] for c in caminhos]
        saidas = rede._saidas_nas_bandejas(caminhos, indices)
        for caminho, sequencia in zip(caminhos, indices):
            dono = (caminho["nome"], "bandeja" if caminho.get("largura") else "eletroduto") \
                if caminho.get("nome") else None
            for a, b in zip(sequencia, sequencia[1:]):
                if a != b:
                    rede._ligar_trecho(a, b, dono)
        for ponta, no, dono in saidas:
            if ponta != no and no not in rede.vizinhos[ponta]:
                comprimento = distancia(rede.nos[ponta], rede.nos[no])
                rede.vizinhos[ponta][no] = rede.vizinhos[no][ponta] = comprimento
                if dono:
                    rede.dono[frozenset((ponta, no))] = dono
        return rede

    def _saidas_nas_bandejas(self, caminhos, indices):
        """Nós na linha de centro das eletrocalhas para as pontas de eletroduto que chegam na borda delas."""
        bandejas = [c for c in caminhos if c.get("largura")]
        if not bandejas:
            return []
        saidas = []
        for caminho, sequencia in zip(caminhos, indices):
            if caminho.get("largura") or not sequencia:
                continue
            dono = (caminho["nome"], "eletroduto") if caminho.get("nome") else None
            for ponta in {sequencia[0], sequencia[-1]}:
                melhor = None
                for bandeja in bandejas:
                    alcance = float(bandeja["largura"]) / 2.0 + self.tolerancia
                    for a, b in zip(bandeja["pontos"], bandeja["pontos"][1:]):
                        projecao, t, d = projetar(self.nos[ponta], a, b)
                        if 0 <= t <= 1 and d <= alcance and (melhor is None or d < melhor[0]):
                            melhor = (d, projecao, bandeja)
                if melhor is not None and melhor[0] > self.tolerancia:
                    no = self._no(melhor[1], melhor[2]["altura"], "")
                    saidas.append((ponta, no, dono))
        return saidas

    def _no(self, ponto, altura, diametro):
        for indice, existente in enumerate(self.nos):
            if distancia(ponto, existente) <= self.tolerancia:
                self.chegando[indice].append((float(altura), str(diametro)))
                return indice
        self.nos.append(tuple(ponto))
        self.altura.append(float(altura))
        self.diametro.append(str(diametro))
        self.vizinhos.append({})
        self.chegando.append([(float(altura), str(diametro))])
        return len(self.nos) - 1

    def transicoes(self):
        """Nós onde chegam eletrodutos de alturas diferentes (ex.: do teto para o piso).

        Returns:
            Lista de {'x', 'y', 'de', 'ate' [mm], 'comprimento' [m], 'diametro'}: a
            vertical entre a menor e a maior altura, no maior diâmetro que chega.
        """
        resultado = []
        for (x, y), chegando in zip(self.nos, self.chegando):
            alturas = [altura for altura, _ in chegando]
            if max(alturas) - min(alturas) <= TOLERANCIA_ALTURA_MM:
                continue
            diametro = max((d for _, d in chegando), key=lambda d: DIAMETROS_EXTERNOS.get(d, 0.0))
            resultado.append({"x": float(x), "y": float(y), "de": min(alturas), "ate": max(alturas),
                              "comprimento": round((max(alturas) - min(alturas)) / 1000.0, 2), "diametro": diametro})
        return resultado

    def _ligar_trecho(self, a, b, dono=None):
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
            if dono:
                self.dono[frozenset((u, v))] = dono

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
        comprimento, sem_caminho, _ = self.arvore_com_arestas(origem, destinos)
        return comprimento, sem_caminho

    def arvore_com_arestas(self, origem, destinos):
        """Como ``arvore``, e também as arestas usadas (conjuntos {nó, nó})."""
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
        return comprimento, sem_caminho, arestas

    def rota(self, origem, destino, anterior=None):
        """Donos dos trechos, em ordem, da origem ao destino pelo caminho mais curto.

        Returns:
            Lista de (nome, tipo) sem repetições seguidas; None se não há caminho.
        """
        if anterior is None:
            _, anterior = self.distancias(origem)
        if destino != origem and destino not in anterior:
            return None
        donos, no = [], destino
        while no != origem:
            dono = self.dono.get(frozenset((no, anterior[no])))
            if dono and (not donos or donos[-1] != dono):
                donos.append(dono)
            no = anterior[no]
        return donos[::-1]


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
        (lista), ``avisos`` (textos), ``trechos`` (cada trecho com dono: ``dono``,
        ``tipo`` 'eletroduto' ou 'bandeja', ``comprimento`` [m] e ``condutores``
        [{'secao', 'funcao', 'circuito'}] que passam nele) e ``rotas`` (por circuito:
        ``quadro``, ``circuito``, ``infraestrutura`` [(nome, tipo)] do quadro aos pontos,
        em ordem, e ``por_ponto`` {nome do ponto: [(nome, tipo)]}).
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
                "x": caixa["x"],
                "y": caixa["y"],
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

    def mais_longe(origem, membros):
        """Do quadro ao ponto mais distante pela rede [m], com a descida no quadro e no ponto."""
        no_origem, vertical_origem = ligadas[origem["id"]]
        dist, _ = rede.distancias(no_origem)
        trechos = [dist[ligadas[m["id"]][0]] + ligadas[m["id"]][1] for m in membros if ligadas[m["id"]][0] in dist]
        return (max(trechos) + vertical_origem) / 1000.0 if trechos else 0.0

    por_aresta = {}

    def passar(arestas, secao, funcao, circuito, quantidade=1):
        """Registra ``quantidade`` condutores nos trechos das arestas."""
        for aresta in arestas:
            por_aresta.setdefault(aresta, []).extend(
                {"secao": float(secao), "funcao": funcao, "circuito": circuito} for _ in range(quantidade))

    def lance(origem, membros):
        """Comprimento de um condutor [m] da origem até todos os membros, com verticais e folgas.

        Returns:
            (total [m], horizontal [m], membros sem caminho, arestas usadas).
        """
        no_origem, vertical_origem = ligadas[origem["id"]]
        horizontal, sem_caminho, arestas = rede.arvore_com_arestas(no_origem, [ligadas[m["id"]][0] for m in membros])
        alcancados = [m for m in membros if ligadas[m["id"]][0] not in sem_caminho]
        total = horizontal + vertical_origem + sum(ligadas[m["id"]][1] for m in alcancados)
        total += folga * (len(alcancados) + 1)
        return total / 1000.0, horizontal / 1000.0, [m for m in membros if m not in alcancados], arestas

    grupos, info_por_circuito = {}, {}
    for caixa in caixas:
        if caixa["tipo"] == "quadro" or caixa["id"] not in ligadas or not str(caixa.get("circuito", "")).strip():
            continue
        quadro = quadro_de(caixa)
        if quadro is None:
            avisos.append(f"{caixa['nome']}: nenhum quadro ligado pela rede ao circuito {caixa['circuito']}.")
            continue
        grupos.setdefault((quadro["id"], str(caixa["circuito"]).strip()), []).append(caixa)

    arestas_por_circuito, circuitos_por_aresta = {}, {}
    for (quadro_id, numero), membros in grupos.items():
        quadro = next(q for q in quadros if q["id"] == quadro_id)
        _, _, arestas = rede.arvore_com_arestas(ligadas[quadro["id"]][0], [ligadas[m["id"]][0] for m in membros])
        arestas_por_circuito[(quadro_id, numero)] = arestas
        for aresta in arestas:
            circuitos_por_aresta[aresta] = circuitos_por_aresta.get(aresta, 0) + 1

    varios_quadros = len({quadro_id for quadro_id, _ in grupos}) > 1
    rotas, rotulo_por_circuito = [], {}
    for (quadro_id, numero), membros in sorted(grupos.items(), key=lambda item: (item[0][0], item[0][1])):
        quadro = next(q for q in quadros if q["id"] == quadro_id)
        rotulo = (f"{quadro['nome']} " if varios_quadros else "") + (f"C{numero}" if numero.isdigit() else numero)
        rotulo_por_circuito[(quadro_id, numero)] = rotulo
        info = info_circuito(quadro, numero, membros)
        pontos = [m for m in membros if m["tipo"] != "interruptor"] or membros
        fase, trajeto, sem_caminho, arestas_fase = lance(quadro, membros)
        neutro_terra, _, _, arestas_pontos = lance(quadro, pontos)
        avisos += [f"{m['nome']}: a rede não chega até ele a partir de {quadro['nome']}." for m in sem_caminho]
        somar(info["secao"], "fase", fase * info["fases"])
        passar(arestas_fase, info["secao"], "fase", rotulo, info["fases"])
        if info["neutro"]:
            somar(info["secao"], "neutro", neutro_terra)
            passar(arestas_pontos, info["secao"], "neutro", rotulo)
        if info["terra"]:
            somar(info["secao"], "terra", neutro_terra)
            passar(arestas_pontos, info["secao"], "terra", rotulo)
        info_por_circuito[(quadro_id, numero)] = info
        _, anterior = rede.distancias(ligadas[quadro["id"]][0])
        por_ponto, ordem = {}, []
        for membro in membros:
            trajeto_membro = rede.rota(ligadas[quadro["id"]][0], ligadas[membro["id"]][0], anterior)
            if trajeto_membro is None:
                continue
            por_ponto[membro["nome"]] = trajeto_membro
            ordem += [dono for dono in trajeto_membro if dono not in ordem]
        rotas.append({"quadro": quadro["nome"], "circuito": numero, "rotulo": rotulo, "infraestrutura": ordem,
                      "por_ponto": por_ponto})
        total = fase * info["fases"] + neutro_terra * (int(info["neutro"]) + int(info["terra"]))
        circuitos.append({
            "quadro": quadro["nome"],
            "circuito": numero,
            "secao": float(info["secao"]),
            "pontos": len(membros),
            "condutores": _rotulo_condutores(info["fases"], info["neutro"], info["terra"]),
            "trajeto": round(trajeto, 2),
            "comprimento": round(mais_longe(quadro, pontos), 2),
            "agrupados": max((circuitos_por_aresta[a] for a in arestas_por_circuito[(quadro_id, numero)]), default=1),
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
        secao, rotulo = 1.5, ""
        for luz in luzes:
            quadro = quadro_de(luz) if str(luz.get("circuito", "")).strip() else None
            info = info_por_circuito.get((quadro["id"], str(luz["circuito"]).strip())) if quadro else None
            if info:
                secao = info["secao"]
                rotulo = rotulo_por_circuito.get((quadro["id"], str(luz["circuito"]).strip()), "")
                break
        retorno, _, _, arestas = lance(interruptores[0], interruptores[1:] + luzes)
        somar(secao, "retorno", retorno)
        passar(arestas, secao, "retorno", rotulo)
        if len(interruptores) > 1:  # paralelo e intermediário: dois condutores entre os interruptores
            entre, _, _, arestas = lance(interruptores[0], interruptores[1:])
            somar(secao, "retorno", 2 * entre)
            passar(arestas, secao, "retorno", rotulo, 2)

    trechos = [
        {"dono": dono[0], "tipo": dono[1], "comprimento": round(rede.vizinhos[a][b] / 1000.0, 3),
         "condutores": por_aresta.get(aresta, [])}
        for aresta, dono in rede.dono.items() for a, b in [tuple(aresta)]
    ]
    return {"fios": fios, "circuitos": circuitos, "verticais": verticais, "avisos": avisos,
            "transicoes": rede.transicoes(), "trechos": trechos, "rotas": rotas}


def juntar(resultados):
    """Soma os resultados de vários pavimentos.

    ``fios_por_pavimento`` guarda os fios de cada um, pela chave ``pavimento``
    do resultado ('' quando não informada).
    """
    total = {"fios": {}, "circuitos": [], "verticais": [], "avisos": [], "fios_por_pavimento": {}, "transicoes": [],
             "trechos": [], "rotas": []}
    for resultado in resultados:
        pavimento = resultado.get("pavimento", "")
        do_pav = total["fios_por_pavimento"].setdefault(pavimento, {})
        for chave, metros in resultado["fios"].items():
            do_pav[chave] = do_pav.get(chave, 0.0) + metros
        for chave, metros in resultado["fios"].items():
            total["fios"][chave] = total["fios"].get(chave, 0.0) + metros
        for campo in ("circuitos", "verticais", "avisos"):
            total[campo] += resultado[campo]
        total["transicoes"] += [dict(t, pavimento=pavimento) for t in resultado.get("transicoes", [])]
        total["trechos"] += [dict(t, pavimento=pavimento) for t in resultado.get("trechos", [])]
        total["rotas"] += [dict(r, pavimento=pavimento) for r in resultado.get("rotas", [])]
    return total
