"""Pavimentos do projeto e as pastas dos símbolos dentro de cada um.

Um pavimento é um nível da bancada BIM (BuildingPart do tipo "Building Storey")
ou, quando o projeto não tem níveis, uma pasta criada pela bancada. Os níveis do
BIM têm a cota e a altura lidas do próprio BIM e nunca são alterados aqui.
"""
import FreeCAD as App

from freecad.Circuits.core import pavimentos as regras
from freecad.Circuits.core.simbolos import CATALOGO

GRUPO_MAE = "Pontos_eletricos"  # criado por Novo projeto; os pavimentos ficam dentro dele, se existir


def _mm(valor):
    return valor.Value if hasattr(valor, "Value") else float(valor)


def _pai(obj):
    """Pasta (grupo) que contém o objeto, ou None."""
    pegar = getattr(obj, "getParentGroup", None)
    try:
        return pegar() if pegar else None
    except Exception:
        return None


def _rotular(obj, desejado, alternativo):
    """Dá o nome à pasta; se o FreeCAD recusar por já existir outra igual, usa o alternativo."""
    obj.Label = desejado
    if obj.Label != desejado:
        obj.Label = alternativo


# --- pavimentos ------------------------------------------------------------

def eh_nivel_bim(obj):
    """Nível da bancada BIM: um BuildingPart do tipo Building Storey."""
    return getattr(obj, "IfcType", "") == "Building Storey" and hasattr(obj, "Group")


def eh_pavimento(obj):
    return hasattr(obj, "AlturaPavimento") or eh_nivel_bim(obj)


def elevacao(pav):
    """Cota do piso do pavimento [mm]. Num nível do BIM é a posição Z dele."""
    return float(pav.Placement.Base.z) if eh_nivel_bim(pav) else _mm(pav.Elevacao)


def altura(pav):
    """Altura de piso a piso [mm]. Num nível do BIM vem da propriedade Height, ou vale o padrão se for zero."""
    if eh_nivel_bim(pav):
        altura_bim = _mm(pav.Height) if hasattr(pav, "Height") else 0.0
        return altura_bim if altura_bim > 0 else regras.ALTURA_PADRAO_MM
    return _mm(pav.AlturaPavimento)


def listar(doc):
    """Pavimentos do documento (níveis do BIM e pastas da bancada), do mais baixo para o mais alto."""
    return sorted((obj for obj in doc.Objects if eh_pavimento(obj)), key=elevacao)


def por_nome(doc, nome):
    nome = regras.nome_do_pavimento(nome)
    return next((pav for pav in listar(doc) if pav.Label == nome), None)


def ativo(doc):
    return next((pav for pav in listar(doc) if getattr(pav, "Ativo", False)), None)


def ativar(doc, pavimento):
    """Torna este o pavimento onde os próximos símbolos são inseridos."""
    for pav in listar(doc):
        if pav.Name == pavimento.Name:
            if not hasattr(pav, "Ativo"):  # nível do BIM: a marca é acrescentada só quando ele é ativado
                pav.addProperty("App::PropertyBool", "Ativo", "Pavimento", "Pavimento onde os próximos símbolos entram")
            pav.Ativo = True
        elif hasattr(pav, "Ativo"):
            pav.Ativo = False


def definir(doc, nome, elevacao_mm=0.0, altura_mm=regras.ALTURA_PADRAO_MM):
    """Cria o pavimento (ou atualiza o de mesmo nome) e o torna o ativo.

    Um nível do BIM só é ativado: a cota e a altura dele são do BIM e não mudam aqui.
    """
    nome = regras.nome_do_pavimento(nome)
    pav = por_nome(doc, nome)
    doc.openTransaction("Definir pavimento")
    try:
        if pav is not None and eh_nivel_bim(pav):
            ativar(doc, pav)
            doc.commitTransaction()
            return pav
        if pav is None:
            pav = doc.addObject("App::DocumentObjectGroup", "Pavimento")
            pav.Label = nome
            pav.addProperty("App::PropertyDistance", "Elevacao", "Pavimento", "Cota do piso do pavimento")
            pav.addProperty("App::PropertyDistance", "AlturaPavimento", "Pavimento", "Altura de piso a piso")
            pav.addProperty("App::PropertyBool", "Ativo", "Pavimento", "Pavimento onde os próximos símbolos entram")
            mae = doc.getObject(GRUPO_MAE)
            if mae is not None:
                mae.addObject(pav)
        pav.Elevacao = float(elevacao_mm)
        pav.AlturaPavimento = float(altura_mm)
        ativar(doc, pav)
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    return pav


def _nivel_ativo_no_bim(doc):
    """Nível que a bancada BIM marcou como ativo (duplo clique no nível), ou None."""
    try:
        import FreeCADGui as Gui

        nivel = Gui.ActiveDocument.ActiveView.getActiveObject("Arch")
    except Exception:
        return None
    return nivel if nivel is not None and nivel in doc.Objects and eh_pavimento(nivel) else None


def _pavimento_selecionado(doc, selecao):
    """Pavimento selecionado na árvore: ele mesmo, ou uma das pastas dele."""
    for obj in selecao:
        if obj not in doc.Objects:
            continue
        if eh_pavimento(obj):
            return obj
        if hasattr(obj, "pasta"):
            pai = _pai(obj)
            if pai is not None and eh_pavimento(pai):
                return pai
    return None


def pavimento_para_insercao(doc, selecao=()):
    """Pavimento em que o próximo símbolo entra, que passa a ser o ativo.

    Na ordem: o nível ativo da bancada BIM; o pavimento (ou uma pasta dele)
    selecionado na árvore; o pavimento ativo da bancada; e, sem nenhum, o mais
    baixo ou um Térreo novo.
    """
    escolhido = _nivel_ativo_no_bim(doc) or _pavimento_selecionado(doc, selecao)
    if escolhido is not None:
        if not getattr(escolhido, "Ativo", False):
            ativar(doc, escolhido)
        return escolhido
    return garantir_ativo(doc)


def criar_nivel_bim(doc, nome, elevacao_mm=0.0, altura_mm=regras.ALTURA_PADRAO_MM):
    """Cria um nível da bancada BIM (ou ativa o de mesmo nome) e o torna o pavimento ativo.

    O nível entra no edifício do BIM (objeto do tipo Building), se o projeto tiver um.

    Raises:
        RuntimeError: se a bancada BIM não estiver disponível neste FreeCAD.
    """
    nome = regras.nome_do_pavimento(nome)
    existente = por_nome(doc, nome)
    if existente is not None:
        ativar(doc, existente)
        return existente
    try:
        import Arch
    except ImportError as erro:
        raise RuntimeError("A bancada BIM não está disponível neste FreeCAD.") from erro

    doc.openTransaction("Adicionar nível do BIM")
    try:
        nivel = Arch.makeBuildingPart()
        nivel.IfcType = "Building Storey"
        nivel.Label = nome
        posicao = nivel.Placement
        posicao.Base = App.Vector(posicao.Base.x, posicao.Base.y, float(elevacao_mm))
        nivel.Placement = posicao
        if hasattr(nivel, "Height"):
            nivel.Height = float(altura_mm)
        edificio = next((obj for obj in doc.Objects if getattr(obj, "IfcType", "") == "Building"), None)
        if edificio is not None and hasattr(edificio, "addObject"):
            edificio.addObject(nivel)
        ativar(doc, nivel)
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    return nivel


def garantir_ativo(doc):
    """Pavimento ativo; sem nenhum ativo, ativa o mais baixo, e sem pavimentos cria o Térreo.

    Num projeto com níveis do BIM, o ativo é um deles, e o Térreo não é criado.
    """
    pav = ativo(doc)
    if pav is not None:
        return pav
    existentes = listar(doc)
    if existentes:
        ativar(doc, existentes[0])
        return existentes[0]
    return definir(doc, regras.PAVIMENTO_PADRAO)


def resumo(doc):
    """Dados dos pavimentos para os diálogos: nome, cota e altura em mm e se é o ativo."""
    return [
        {
            "nome": pav.Label,
            "elevacao_mm": elevacao(pav),
            "altura_mm": altura(pav),
            "ativo": bool(getattr(pav, "Ativo", False)),
            "bim": eh_nivel_bim(pav),
        }
        for pav in listar(doc)
    ]


def sugestao_novo(doc):
    """Nome, cota e altura sugeridos para o próximo pavimento."""
    return regras.sugerir_novo([(d["nome"], d["elevacao_mm"], d["altura_mm"]) for d in resumo(doc)])


# --- pastas dos símbolos -----------------------------------------------------

def chave_do_objeto(obj):
    """Chave da pasta do símbolo, ou None se o objeto não é um símbolo da planta."""
    tipo = getattr(getattr(obj, "Proxy", None), "Type", "")
    if tipo == "Ponto":
        return regras.pasta_do_objeto(tipo, obj.Simbolo)
    if getattr(obj, "tipo", "") == "tomada":
        return regras.pasta_do_objeto("tomada")
    # Linhas do Draft (Proxy.Type == "Wire") marcadas pela bancada: a marca decide, não o tipo.
    if hasattr(obj, "Points") and tipo != "ConduitPath":
        if hasattr(obj, "TipoAmbiente"):
            return regras.pasta_do_objeto("ambiente")  # contorno de ambiente
        if hasattr(obj, "TipoBandeja"):
            return regras.pasta_do_objeto("bandeja")  # eletrocalha ou leito
        if hasattr(obj, "SecaoAterramento"):
            return regras.pasta_do_objeto("condutor_aterramento")
        if hasattr(obj, "Diametro") and hasattr(obj, "Altura3D"):
            return regras.pasta_do_objeto("eletroduto")
    return regras.pasta_do_objeto(tipo)


def pasta(doc, pavimento, chave):
    """Subpasta do pavimento para a chave, criada se ainda não existir."""
    for filho in pavimento.Group:
        if getattr(filho, "pasta", None) == chave:
            return filho
    grupo = doc.addObject("App::DocumentObjectGroup", f"Pasta_{chave}")
    grupo.addProperty("App::PropertyString", "pasta", "Pavimento", "Tipo de símbolo desta pasta")
    grupo.pasta = chave
    rotulo = regras.PASTAS[chave]
    _rotular(grupo, rotulo, f"{pavimento.Label} - {rotulo}")
    pavimento.addObject(grupo)
    return grupo


def pasta_do_pavimento(doc, obj, chave):
    """Pasta ``chave`` do pavimento do objeto (ex.: Térreo > Fiação), ou None fora de um pavimento."""
    pav = pavimento_do_objeto(doc, obj)
    return pasta(doc, pav, chave) if pav is not None else None


def guardar_junto(referencia, obj):
    """Põe o objeto na mesma pasta da referência (ex.: a planilha do quadro ao lado do símbolo).

    Returns:
        A pasta, ou None se a referência não está em pasta nenhuma (o objeto fica onde está).
    """
    destino = _pai(referencia)
    if destino is None:
        return None
    anterior = _pai(obj)
    if anterior is destino:
        return destino
    if anterior is not None:
        anterior.removeObject(obj)
    destino.addObject(obj)
    return destino


def pasta_3d(doc, obj):
    """Subpasta "<tipo> 3D" dentro da pasta do símbolo (ex.: Térreo > Tomadas > Tomadas 3D).

    É onde ficam as caixas e os tubos 3D gerados a partir do símbolo ou do
    eletroduto. Criada se ainda não existir.

    Returns:
        A subpasta, ou None se o objeto não está numa pasta de pavimento.
    """
    pasta_do_simbolo = _pai(obj)
    if pasta_do_simbolo is None or not hasattr(pasta_do_simbolo, "pasta"):
        return None
    chave = pasta_do_simbolo.pasta
    for filho in pasta_do_simbolo.Group:
        if getattr(filho, "pasta_3d", None) == chave:
            return filho
    grupo = doc.addObject("App::DocumentObjectGroup", f"Pasta_{chave}_3D")
    grupo.addProperty("App::PropertyString", "pasta_3d", "Pavimento", "Modelo 3D gerado dos objetos desta pasta")
    grupo.pasta_3d = chave
    rotulo = f"{regras.PASTAS.get(chave, chave)} 3D"
    pavimento = _pai(pasta_do_simbolo)
    _rotular(grupo, rotulo, f"{pavimento.Label} - {rotulo}" if pavimento is not None else f"{pasta_do_simbolo.Label} 3D")
    pasta_do_simbolo.addObject(grupo)
    return grupo


def guardar_3d(doc, origem, objeto_3d):
    """Põe o objeto 3D na subpasta 3D da pasta do símbolo de origem. Devolve a pasta, ou None."""
    destino = pasta_3d(doc, origem)
    if destino is not None:
        destino.addObject(objeto_3d)
    return destino


def altura_de_montagem(obj):
    """Altura da caixa em relação ao piso [mm]: Altura3D, ou altura_piso na tomada em Sketch."""
    if hasattr(obj, "Altura3D"):
        return _mm(obj.Altura3D)
    if hasattr(obj, "altura_piso"):
        return float(obj.altura_piso)
    return 0.0


def cota_no_desenho(doc, obj, pavimento=None):
    """Z do símbolo 2D na planta [mm]: a cota do piso do pavimento."""
    pavimento = pavimento or pavimento_do_objeto(doc, obj)
    return regras.cota_de_desenho(elevacao(pavimento) if pavimento is not None else 0.0)


def cota_3d(doc, obj):
    """Z da caixa 3D do símbolo [mm]: a cota do piso do pavimento + a altura de montagem."""
    return regras.cota_3d(elevacao_do_objeto(doc, obj), altura_de_montagem(obj))


def ajustar_cota(doc, obj, pavimento=None):
    """Põe o símbolo 2D na cota do piso do pavimento.

    Pontos e interruptores guardam a cota do piso em ``CotaPiso`` e passam a
    acompanhar as mudanças dela sozinhos; nos demais, o Z é ajustado aqui.
    """
    pavimento = pavimento or pavimento_do_objeto(doc, obj)
    piso = elevacao(pavimento) if pavimento is not None else 0.0
    if hasattr(obj, "CotaPiso"):
        obj.CotaPiso = piso
    if hasattr(obj, "Placement"):
        z = regras.cota_de_desenho(piso)
        base = obj.Placement.Base
        if abs(base.z - z) > 1e-6:
            posicao = obj.Placement
            posicao.Base = App.Vector(base.x, base.y, z)
            obj.Placement = posicao


def ajustar_cotas(doc):
    """Ajusta o Z de todos os símbolos do documento (veja ``ajustar_cota``). Devolve quantos."""
    simbolos = [
        obj for obj in doc.Objects
        if chave_do_objeto(obj) not in (None, "eletrodutos") and not hasattr(obj, "SecaoAterramento")
    ]
    doc.openTransaction("Ajustar cotas dos símbolos")
    try:
        for obj in simbolos:
            ajustar_cota(doc, obj)
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    return len(simbolos)


def _marcar(obj, nome):
    """Guarda o nome do pavimento no próprio símbolo, para ele saber onde está."""
    if not hasattr(obj, "Pavimento"):
        obj.addProperty("App::PropertyString", "Pavimento", "Elétrica", "Pavimento onde o símbolo está")
    obj.Pavimento = nome


def arquivar(doc, obj, pavimento=None):
    """Coloca o símbolo na pasta do tipo dele, dentro do pavimento (o ativo, se não for dado).

    Se o símbolo já estava em outra pasta, sai dela.

    Returns:
        A pasta onde o símbolo ficou, ou None se o objeto não é um símbolo da planta.
    """
    chave = chave_do_objeto(obj)
    if chave is None:
        return None
    pavimento = pavimento or garantir_ativo(doc)
    destino = pasta(doc, pavimento, chave)
    atual = _pai(obj)
    if atual is None or atual.Name != destino.Name:
        if atual is not None:
            atual.removeObject(obj)
        destino.addObject(obj)
    _marcar(obj, pavimento.Label)
    if chave not in ("eletrodutos", "bandejas") and not hasattr(obj, "SecaoAterramento"):  # linhas têm a cota do próprio traçado
        ajustar_cota(doc, obj, pavimento)
    return destino


def _subir(obj, diferenca):
    """Desloca o objeto na vertical, mantendo a posição em planta."""
    if abs(diferenca) < 1e-6 or not hasattr(obj, "Placement"):
        return
    posicao = obj.Placement
    base = posicao.Base
    posicao.Base = App.Vector(base.x, base.y, base.z + diferenca)
    obj.Placement = posicao


def mover(doc, objetos, pavimento):
    """Move os símbolos para as pastas do pavimento, em uma única operação de desfazer.

    Os símbolos vão para a cota do pavimento novo mais a altura de montagem; os
    eletrodutos sobem ou descem a diferença entre as cotas dos dois pavimentos.

    Returns:
        Quantidade de símbolos movidos; objetos que não são símbolos são ignorados.
    """
    movidos = 0
    doc.openTransaction("Mover para pavimento")
    try:
        for obj in objetos:
            if chave_do_objeto(obj) is None:
                continue
            antes = elevacao_do_objeto(doc, obj)
            if arquivar(doc, obj, pavimento) is not None:  # símbolos: arquivar já ajusta a cota
                if chave_do_objeto(obj) in ("eletrodutos", "bandejas") or hasattr(obj, "SecaoAterramento"):
                    _subir(obj, elevacao(pavimento) - antes)
                movidos += 1
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    return movidos


def pavimento_do_objeto(doc, obj):
    """Pavimento onde o símbolo está: o da pasta em que ele fica, ou o do nome guardado nele."""
    pasta_do_simbolo = _pai(obj)
    pav = _pai(pasta_do_simbolo) if pasta_do_simbolo is not None else None
    if pav is not None and eh_pavimento(pav):
        return pav
    nome = getattr(obj, "Pavimento", "")
    return por_nome(doc, nome) if nome else None


def elevacao_do_objeto(doc, obj):
    """Cota do piso do pavimento do símbolo [mm]; fora de qualquer pavimento vale 0."""
    pav = pavimento_do_objeto(doc, obj)
    return elevacao(pav) if pav is not None else 0.0
