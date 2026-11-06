"""Tubos 3D de eletrodutos gerados a partir de linhas guia."""
import FreeCAD as App
import Part

from freecad.Circuits.core.tables.eletrodutos import COR_PADRAO, CORES, DIAMETRO_PADRAO, DIAMETROS_EXTERNOS
from freecad.Circuits.services.tomadas import listar_tomadas

TOLERANCIA_TOMADA_MM = 10.0
FATOR_RAIO_CURVA_FLEXIVEL = 15


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
        obj.FilletRadius = raio * FATOR_RAIO_CURVA_FLEXIVEL if obj.Tipo == "Flexível" else 0.0


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


def _descidas_para_tomadas(obj, tomadas, raio):
    """Tubos verticais entre a altura do eletroduto e as tomadas sob seus pontos."""
    descidas = []
    pontos = obj.Points if hasattr(obj, "Points") else [v.Point for v in obj.Shape.Vertexes]
    atendidas = set()

    for ponto in pontos:
        for tomada in tomadas:
            if tomada.Name in atendidas:
                continue
            tx, ty = tomada.Placement.Base.x, tomada.Placement.Base.y
            if (App.Vector(ponto.x, ponto.y, 0) - App.Vector(tx, ty, 0)).Length >= TOLERANCIA_TOMADA_MM:
                continue
            atendidas.add(tomada.Name)

            z_tomada = float(tomada.altura_piso) if hasattr(tomada, "altura_piso") else 0.0
            topo = App.Vector(tx, ty, obj.Altura3D.Value)
            base = App.Vector(tx, ty, z_tomada)
            if (topo - base).Length <= 1e-2:
                continue

            linha = Part.Wire([Part.makeLine(topo, base)])
            direcao = base - topo
            direcao.normalize()
            perfil = Part.Wire([Part.makeCircle(raio, topo, direcao)])
            try:
                descidas.append(linha.makePipe(perfil))
            except Exception as e:
                App.Console.PrintWarning(f"Falha ao gerar descida para {tomada.Name}: {e}\n")
    return descidas


def _gerar_tubo(doc, obj, tomadas):
    """Gera o tubo de um caminho. Devolve True se o objeto 3D foi criado."""
    if not hasattr(obj, "Shape") or obj.Shape.isNull() or len(obj.Shape.Edges) == 0:
        return False

    raio = DIAMETROS_EXTERNOS.get(obj.Diametro, DIAMETRO_PADRAO) / 2.0
    cor = CORES.get(obj.Cor, COR_PADRAO)

    fio = _como_wire(obj)
    if fio is None:
        return False

    deslocamento = obj.Altura3D.Value - fio.Vertexes[0].Point.z
    if abs(deslocamento) > 1e-4:
        fio.translate(App.Vector(0, 0, deslocamento))

    primeira_aresta = fio.Edges[0]
    if primeira_aresta.Length < 1e-5:
        return False

    inicio = primeira_aresta.valueAt(primeira_aresta.FirstParameter)
    direcao = primeira_aresta.tangentAt(primeira_aresta.FirstParameter)
    perfil = Part.Wire([Part.makeCircle(raio, inicio, direcao)])

    nome = f"{obj.Name}_3D"
    if doc.getObject(nome):
        doc.removeObject(nome)

    try:
        tubos = [Part.Wire(fio).makePipeShell([perfil], True, True)]
        tubos += _descidas_para_tomadas(obj, tomadas, raio)
        forma = Part.makeCompound(tubos) if len(tubos) > 1 else tubos[0]

        tubo = doc.addObject("Part::Feature", nome)
        tubo.Shape = forma
        tubo.Label = f"Eletroduto 3D ({obj.Diametro})"
        tubo.ViewObject.ShapeColor = cor
        return True
    except Exception as e:
        App.Console.PrintError(f"Erro ao gerar tubo 3D para {obj.Name}: {e}\n")
        return False


def gerar_tubos(doc, caminhos):
    """Gera o tubo 3D de cada caminho. Devolve quantos foram criados."""
    for obj in caminhos:
        _preparar_caminho(obj)
    doc.recompute()  # as curvas dos Wires precisam estar atualizadas antes da varredura

    tomadas = listar_tomadas(doc)
    criados = sum(1 for obj in caminhos if _gerar_tubo(doc, obj, tomadas))
    doc.recompute()
    return criados


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
