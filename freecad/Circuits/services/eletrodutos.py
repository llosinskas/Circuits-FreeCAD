"""Tubos 3D de eletrodutos gerados a partir de linhas guia, e as descidas com curvas entre alturas."""
import math

import FreeCAD as App
import Part

from freecad.Circuits.core import alturas as regras_alturas
from freecad.Circuits.core import pecas_eletroduto
from freecad.Circuits.core.tables.eletrodutos import COR_PADRAO, CORES, DIAMETRO_PADRAO, DIAMETROS_EXTERNOS
from freecad.Circuits.services import pavimentos

FATOR_RAIO_CURVA_FLEXIVEL = pecas_eletroduto.FATOR_RAIO_CURVA_FLEXIVEL
FATOR_RAIO_CURVA_RIGIDO = pecas_eletroduto.FATOR_RAIO_CURVA_RIGIDO  # curva pré-fabricada: 3 diâmetros externos


def listar_caminhos(doc):
    """Objetos ConduitPath do documento."""
    return [obj for obj in doc.Objects if hasattr(obj, "Proxy") and getattr(obj.Proxy, "Type", "") == "ConduitPath"]


def _preparar_caminho(obj):
    """Injeta as propriedades de eletroduto e ajusta a curvatura de Draft Wires."""
    if not hasattr(obj, "Altura3D"):
        obj.addProperty("App::PropertyDistance", "Altura3D", "Conduit", "Altura em Z do eletroduto").Altura3D = 2800.0

    if not hasattr(obj, "Diametro"):
        obj.addProperty("App::PropertyEnumeration", "Diametro", "Conduit", "Tamanho nominal do eletroduto")
        obj.Diametro = list(DIAMETROS_EXTERNOS)
        obj.Diametro = "3/4"

    if not hasattr(obj, "Tipo"):
        obj.addProperty("App::PropertyEnumeration", "Tipo", "Conduit", "Flexível ou Rígido")
        obj.Tipo = ["Flexível", "Rígido"]
        obj.Tipo = "Flexível"

    if not hasattr(obj, "Cor"):
        obj.addProperty("App::PropertyEnumeration", "Cor", "Conduit", "Cor do tubo")
        obj.Cor = list(CORES)
        obj.Cor = "Amarelo"

    if hasattr(obj, "FilletRadius"):
        raio = DIAMETROS_EXTERNOS.get(obj.Diametro, DIAMETRO_PADRAO) / 2.0
        obj.FilletRadius = raio * (FATOR_RAIO_CURVA_FLEXIVEL if obj.Tipo == "Flexível" else FATOR_RAIO_CURVA_RIGIDO)


def _como_wire(obj):
    """Cópia da forma como Wire, ou None se não for possível converter."""
    forma = obj.Shape.copy()
    if forma.ShapeType == "Edge":
        return Part.Wire([forma])
    if forma.ShapeType == "Compound" and len(forma.Wires) > 0:
        return forma.Wires[0]
    if forma.ShapeType != "Wire":
        try:
            return Part.Wire(forma.Edges)
        except Exception as e:
            App.Console.PrintWarning(f"Não foi possível converter a forma de {obj.Name} em Wire: {e}\n")
            return None
    return forma


def _lances(obj):
    """Lances de mesma altura (``core.alturas``) do Draft Wire; um só sem ``AlturasTrechos``."""
    if not hasattr(obj, "Points") or len(obj.Points) < 2:
        return []
    pontos = [(v.x, v.y) for v in (obj.Placement.multVec(p) for p in obj.Points)]
    alturas = regras_alturas.alturas_dos_trechos(len(pontos) - 1, obj.Altura3D.Value, getattr(obj, "AlturasTrechos", ()))
    return regras_alturas.lances(pontos, alturas)


def _raio_da_curva(obj, raio_tubo):
    """Raio das curvas horizontais: o ``FilletRadius`` do Draft Wire ou o do tipo de eletroduto."""
    raio = getattr(getattr(obj, "FilletRadius", 0.0), "Value", getattr(obj, "FilletRadius", 0.0)) or 0.0
    if raio > 0:
        return float(raio)
    return raio_tubo * (FATOR_RAIO_CURVA_FLEXIVEL if getattr(obj, "Tipo", "") == "Flexível" else FATOR_RAIO_CURVA_RIGIDO)


def _arredondar(fio, raio):
    """Curvas nas quinas do lance: a varredura do tubo falha depois de uma quina viva."""
    if len(fio.Edges) < 2 or raio <= 0:
        return fio
    try:
        import DraftGeomUtils

        arredondado = DraftGeomUtils.filletWire(fio, raio)
        return arredondado if arredondado and not arredondado.isNull() else fio
    except Exception as erro:
        App.Console.PrintWarning(f"Curvas do eletroduto não arredondadas: {erro}\n")
        return fio


def _aparar(fio, cortes):
    """Encurta as pontas do fio que estão sobre uma descida, pelo raio da curva.

    Args:
        cortes: [(x, y, comprimento)] — a ponta do fio a até ``TOLERANCIA_MM`` de (x, y),
            em planta, perde ``comprimento`` mm, se o trecho da ponta for reto e mais longo.
    """
    arestas = list(fio.OrderedEdges)
    vertices = [v.Point for v in fio.OrderedVertexes]
    pontas = [(0, vertices[0]), (len(arestas) - 1, vertices[-1])]
    for x, y, corte in cortes:
        for indice, livre in pontas:
            if math.hypot(livre.x - x, livre.y - y) > pecas_eletroduto.TOLERANCIA_MM:
                continue
            aresta = arestas[indice]
            if aresta.Curve.__class__.__name__ not in ("Line", "LineSegment") or aresta.Length <= corte + 1.0:
                break
            a, b = aresta.Vertexes[0].Point, aresta.Vertexes[-1].Point
            outra = b if (a - livre).Length < (b - livre).Length else a
            direcao = outra - livre
            direcao.normalize()
            novo = livre + direcao * corte
            arestas[indice] = Part.makeLine(novo, outra) if indice == 0 else Part.makeLine(outra, novo)
            break
    return Part.Wire(arestas)


def _gerar_tubo(doc, obj, cortes=()):
    """Gera o tubo de um caminho. Devolve True se o objeto 3D foi criado.

    ``cortes``: pontas a encurtar para a curva da descida (``_aparar``). A interligação
    vertical com as caixas dos símbolos (tomadas, luminárias, interruptores) é uma
    descida de ``gerar_descidas``, com a curva de 90° na ponta do eletroduto.
    """
    if not hasattr(obj, "Shape") or obj.Shape.isNull() or len(obj.Shape.Edges) == 0:
        return False

    raio = DIAMETROS_EXTERNOS.get(obj.Diametro, DIAMETRO_PADRAO) / 2.0
    cor = CORES.get(obj.Cor, COR_PADRAO)

    fio = _como_wire(obj)
    if fio is None:
        return False

    # A altura do eletroduto é medida a partir do piso do pavimento dele.
    piso = pavimentos.elevacao_do_objeto(doc, obj)
    cota = obj.Altura3D.Value + piso
    lances = _lances(obj)
    if len(lances) > 1:
        # muda de altura no meio: um tubo reto por lance; a subida entre eles (curvas e vertical) é
        # uma descida de ``gerar_descidas``. As curvas horizontais do Draft (FilletRadius) ficam de fora.
        fios = [_arredondar(Part.makePolygon([App.Vector(x, y, piso + lance["altura"]) for x, y in lance["pontos"]]),
                            _raio_da_curva(obj, raio))
                for lance in lances]
    else:
        deslocamento = cota - fio.Vertexes[0].Point.z
        if abs(deslocamento) > 1e-4:
            fio.translate(App.Vector(0, 0, deslocamento))
        fios = [fio]
    if cortes:
        aparados = []
        for um in fios:
            try:
                aparados.append(_aparar(um, cortes))
            except Exception as e:
                App.Console.PrintWarning(f"Não foi possível encurtar {obj.Name} para a curva da descida: {e}\n")
                aparados.append(um)
        fios = aparados

    nome = f"{obj.Name}_3D"
    if doc.getObject(nome):
        doc.removeObject(nome)

    try:
        tubos = []
        for um in fios:
            primeira_aresta = um.Edges[0]
            if primeira_aresta.Length < 1e-5:
                continue
            inicio = primeira_aresta.valueAt(primeira_aresta.FirstParameter)
            direcao = primeira_aresta.tangentAt(primeira_aresta.FirstParameter)
            perfil = Part.Wire([Part.makeCircle(raio, inicio, direcao)])
            tubos.append(Part.Wire(um).makePipeShell([perfil], True, True))
        if not tubos:
            return False
        forma = Part.makeCompound(tubos) if len(tubos) > 1 else tubos[0]

        tubo = doc.addObject("Part::Feature", nome)
        tubo.Shape = forma
        tubo.Label = f"Eletroduto 3D ({obj.Diametro})"
        tubo.ViewObject.ShapeColor = cor
        pavimentos.guardar_3d(doc, obj, tubo)  # ex.: Térreo > Eletrodutos > Eletrodutos 3D
        return True
    except Exception as e:
        App.Console.PrintError(f"Erro ao gerar tubo 3D para {obj.Name}: {e}\n")
        return False


def gerar_tubos(doc, caminhos):
    """Gera o tubo 3D de cada caminho. Devolve quantos foram criados.

    As linhas que ainda não estão num pavimento entram antes na pasta
    Eletrodutos do pavimento de inserção (nível ativo do BIM, selecionado ou
    ativo), para o tubo 3D ir para a subpasta 3D dela.
    """
    destino = None
    for obj in caminhos:
        _preparar_caminho(obj)
        if pavimentos.pavimento_do_objeto(doc, obj) is None:
            destino = destino or pavimentos.pavimento_para_insercao(doc)
            pavimentos.arquivar(doc, obj, destino)
    doc.recompute()  # as curvas dos Wires precisam estar atualizadas antes da varredura

    descidas = _descidas_do_documento(doc)
    cortes = {}
    for _, descida in descidas:
        for braco in descida["bracos"]:
            if braco["curva"]:
                cortes.setdefault(braco["nome"], []).append((descida["x"], descida["y"], descida["raio"]))
    criados = sum(1 for obj in caminhos if _gerar_tubo(doc, obj, cortes.get(obj.Name, ())))
    gerar_descidas(doc, descidas)
    gerar_saidas_3d(doc)
    doc.recompute()
    return criados


def _descidas_do_documento(doc):
    """[(nome do pavimento, descida de ``core.pecas_eletroduto``)] de todos os pavimentos."""
    from freecad.Circuits.services import eletrodutos_planta  # importa este módulo: só aqui, sem ciclo

    try:
        resultados = eletrodutos_planta.analisar(doc)
    except Exception as e:
        App.Console.PrintWarning(f"Não foi possível analisar as descidas dos eletrodutos: {e}\n")
        return []
    return [(pav, descida) for pav, resultado in resultados.items() for descida in resultado.get("descidas", [])]


def _tubo_reto(raio, a, b):
    eixo = b - a
    if eixo.Length < 1e-3:
        return None
    return Part.makeCylinder(raio, eixo.Length, a, eixo)


def _curva(raio_tubo, raio, no, ux, uy, z, sobe):
    """Curva de 90° do trecho horizontal (chegando ao nó pela direção −u) para a vertical do nó."""
    s = 1.0 if sobe else -1.0
    inicio = App.Vector(no.x + ux * raio, no.y + uy * raio, z)
    centro = inicio + App.Vector(0, 0, s * raio)
    fim = App.Vector(no.x, no.y, z + s * raio)
    meio = centro + App.Vector(-ux, -uy, -s) * (raio / math.sqrt(2.0))
    arco = Part.Wire([Part.Arc(inicio, meio, fim).toShape()])
    perfil = Part.Wire([Part.makeCircle(raio_tubo, inicio, App.Vector(-ux, -uy, 0))])
    return arco.makePipeShell([perfil], True, True)


def solidos_da_descida(descida, cota_piso):
    """Sólidos de uma descida: as curvas de 90° dos eletrodutos que terminam nela e a vertical."""
    raio_tubo = DIAMETROS_EXTERNOS.get(str(descida["diametro"]), DIAMETRO_PADRAO) / 2.0
    raio = float(descida["raio"])
    no = App.Vector(descida["x"], descida["y"], 0)
    baixo, alto = cota_piso + descida["de"], cota_piso + descida["ate"]
    com_curva = raio > 1.5 * raio_tubo
    solidos = []
    for braco in descida["bracos"]:
        if not (braco["curva"] and com_curva):
            continue
        z = cota_piso + braco["altura"]
        sobe = abs(braco["altura"] - descida["de"]) <= pecas_eletroduto.TOLERANCIA_ALTURA_MM
        solidos.append(_curva(raio_tubo, raio, no, braco["ux"], braco["uy"], z, sobe))
        if sobe:
            baixo = z + raio
        else:
            alto = z - raio
    vertical = _tubo_reto(raio_tubo, App.Vector(no.x, no.y, baixo), App.Vector(no.x, no.y, alto))
    if vertical is not None:
        solidos.append(vertical)
    return solidos


def gerar_descidas(doc, descidas=None):
    """Recria o 3D das descidas (objetos com a propriedade ``descida_3d``).

    Returns:
        Quantidade de descidas desenhadas.
    """
    descidas = _descidas_do_documento(doc) if descidas is None else descidas
    for obj in [o for o in doc.Objects if hasattr(o, "descida_3d")]:
        doc.removeObject(obj.Name)
    feitas = 0
    for pav_nome, descida in descidas:
        if descida.get("caixa") and not any(doc.getObject(f"{b['nome']}_3D") for b in descida["bracos"]):
            continue  # a interligação com a caixa só aparece junto com o tubo 3D do eletroduto
        pav = pavimentos.por_nome(doc, pav_nome) if pav_nome else None
        cota = pavimentos.elevacao(pav) if pav is not None else 0.0
        try:
            forma = Part.makeCompound(solidos_da_descida(descida, cota))
        except Exception as e:
            App.Console.PrintWarning(f"Falha ao gerar a descida em ({descida['x']:.0f}; {descida['y']:.0f}): {e}\n")
            continue
        objeto = doc.addObject("Part::Feature", "Descida_3D")
        objeto.Shape = forma
        objeto.Label = (f"Descida 3D Ø{descida['diametro']}\" até {descida['caixa']}" if descida.get("caixa")
                        else f"Descida 3D Ø{descida['diametro']}\"")
        objeto.addProperty("App::PropertyString", "descida_3d", "Conduit",
                           "Descida entre eletrodutos de alturas diferentes ou do eletroduto até a caixa")
        objeto.descida_3d = f"{pav_nome}:{descida['x']:.0f};{descida['y']:.0f}" + (f":{descida['lado']}" if descida.get("caixa") else "")
        origem = doc.getObject(descida["bracos"][0]["nome"])
        try:
            objeto.ViewObject.ShapeColor = CORES.get(getattr(origem, "Cor", ""), COR_PADRAO)
        except Exception:
            pass
        if origem is not None:
            pavimentos.guardar_3d(doc, origem, objeto)
        feitas += 1
    return feitas


def subdividir_linha(doc, obj):
    """Insere um ponto no meio de cada trecho de uma linha, para editar o caminho."""
    if not hasattr(obj, "Points"):
        print("Objeto selecionado não é possível inserir um ponto")
        return
    if len(obj.Points) < 2:
        print("Não é posssível adicionar um ponto de controle!")
        return

    pontos = []
    for atual, proximo in zip(obj.Points, obj.Points[1:]):
        pontos.append(atual)
        pontos.append((atual + proximo) * 0.5)
    pontos.append(obj.Points[-1])

    obj.Points = pontos
    obj.touch()
    doc.recompute()
    print(f"Adicionado pontos de controle na curva: {obj.Label}")


COR_SAIDA = (0.75, 0.75, 0.78)  # aço galvanizado, como a eletrocalha


def _solido(primitiva, cota):
    """Sólido de uma primitiva de ``core.pecas_eletroduto.solidos_da_saida`` (Z somado à cota do piso)."""
    if primitiva[0] == "cilindro":
        _, base, direcao, raio, comprimento = primitiva
        return Part.makeCylinder(raio, comprimento, App.Vector(base[0], base[1], base[2] + cota), App.Vector(*direcao))
    _, centro, normal, lado, espessura = primitiva
    placa = Part.makeBox(lado, lado, espessura)
    placa.translate(App.Vector(-lado / 2.0, -lado / 2.0, -espessura / 2.0))  # centrada na origem
    posicao = App.Placement(App.Vector(centro[0], centro[1], centro[2] + cota),
                            App.Rotation(App.Vector(0, 0, 1), App.Vector(*normal)))
    placa.Placement = posicao.multiply(placa.Placement)  # gira em torno do centro e leva ao lugar
    return placa


def gerar_saidas_3d(doc, resultados=None):
    """Recria a peça 3D de cada saída de eletrocalha: flange, luva e anel (propriedade ``saida_3d``),
    na subpasta 3D da eletrocalha.

    Returns:
        Quantidade de peças desenhadas.
    """
    from freecad.Circuits.services import eletrodutos_planta  # importa este módulo: só aqui, sem ciclo

    for obj in [o for o in doc.Objects if hasattr(o, "saida_3d")]:
        doc.removeObject(obj.Name)
    try:
        resultados = eletrodutos_planta.analisar(doc) if resultados is None else resultados
    except Exception as e:
        App.Console.PrintWarning(f"Não foi possível analisar as saídas das eletrocalhas: {e}\n")
        return 0
    feitas = 0
    for pav_nome, resultado in resultados.items():
        pav = pavimentos.por_nome(doc, pav_nome) if pav_nome else None
        cota = pavimentos.elevacao(pav) if pav is not None else 0.0
        for saida in resultado.get("saidas", []):
            try:
                forma = Part.makeCompound([_solido(p, cota) for p in pecas_eletroduto.solidos_da_saida(saida)])
            except Exception as e:
                App.Console.PrintWarning(f"Falha ao gerar a saída em ({saida['x']:.0f}; {saida['y']:.0f}): {e}\n")
                continue
            objeto = doc.addObject("Part::Feature", "Saida_3D")
            objeto.Shape = forma
            objeto.Label = f"{saida['peca']} Ø{saida['diametro']}\""
            objeto.addProperty("App::PropertyString", "saida_3d", "Conduit", "Peça de saída da eletrocalha")
            objeto.saida_3d = f"{pav_nome}:{saida['x']:.0f};{saida['y']:.0f}"
            try:
                objeto.ViewObject.ShapeColor = COR_SAIDA
            except Exception:
                pass
            bandeja = doc.getObject(saida.get("bandeja") or "")
            if bandeja is not None:
                pavimentos.guardar_3d(doc, bandeja, objeto)  # ex.: Térreo > Bandejas e leitos > Bandejas 3D
            feitas += 1
    return feitas
