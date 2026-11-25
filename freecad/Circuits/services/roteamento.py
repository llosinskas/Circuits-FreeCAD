"""Roteamento dos cabos pela infraestrutura e ocupação dos eletrodutos (``core.rede``, ``core.ocupacao``).

Cada circuito é seguido do quadro aos pontos pelos eletrodutos e pelas eletrocalhas
de cada pavimento (a ponta de eletroduto que para na borda de uma eletrocalha entra
nela). O resultado diz por onde cada cabo passa (``rotas``) e quantos condutores há
em cada trecho, de onde sai o eletroduto mínimo pela taxa de ocupação.
"""
import Draft
import FreeCAD as App

from freecad.Circuits.core import ocupacao as regras
from freecad.Circuits.core import rede as regras_rede
from freecad.Circuits.services import bandejas, pavimentos, rede

MARCA_PLANILHA = "ocupacao_eletrodutos"
MARCA_FIOS = "fios_trecho"
ALTURA_TEXTO_FIOS = 100.0  # mm


def _caminho_eletroduto(obj):
    altura = rede._mm(obj.Altura3D) if hasattr(obj, "Altura3D") else rede.ALTURA_ELETRODUTO_PADRAO
    return {"pontos": rede._pontos(obj), "altura": altura, "diametro": str(getattr(obj, "Diametro", "3/4")),
            "nome": obj.Name}


def _caminho_bandeja(obj):
    dados = bandejas._caminho(obj)
    return {"pontos": dados["pontos"], "altura": dados["altura"], "diametro": "", "nome": obj.Name,
            "largura": dados["largura"]}


def analisar(doc, com_bandejas=True):
    """Rede de cada pavimento com eletrodutos e eletrocalhas (``core.rede.analisar``, ``juntar``).

    Returns:
        O resultado de ``core.rede.juntar``, com ``trechos`` e ``rotas``.
    """
    caminhos_por_pav = {}
    for obj in rede.listar_eletrodutos(doc):
        try:
            caminhos_por_pav.setdefault(rede._pavimento(doc, obj), []).append(_caminho_eletroduto(obj))
        except Exception:
            continue
    if com_bandejas:
        for obj in bandejas.listar(doc):
            try:
                caminhos_por_pav.setdefault(bandejas._nome_pavimento(doc, obj), []).append(_caminho_bandeja(obj))
            except Exception:
                continue

    caixas = rede.listar_caixas(doc)
    cache, resultados = {}, []
    for pav in sorted(set(caminhos_por_pav) | {c["pavimento"] for c in caixas}):
        caminhos = caminhos_por_pav.get(pav, []) + (caminhos_por_pav.get("", []) if pav else [])
        do_pav = [c for c in caixas if c["pavimento"] == pav]
        if not do_pav:
            continue
        resultado = regras_rede.analisar(caminhos, do_pav, rede._info_circuito(doc, cache))
        resultado["pavimento"] = pav
        resultados.append(resultado)
    return regras_rede.juntar(resultados)


def _rotulo(doc, nome):
    obj = doc.getObject(nome)
    return obj.Label if obj is not None else nome


def ocupacao(doc, resultado=None):
    """Ocupação de cada eletroduto (``core.ocupacao.verificar_eletroduto``) e eletrocalha (informativa).

    Returns:
        dict com ``eletrodutos`` e ``bandejas`` (com ``objeto`` = nome interno e ``nome`` =
        rótulo), ``avisos`` e ``rotas``.
    """
    resultado = resultado or analisar(doc)
    grupos = regras.agrupar_trechos(resultado["trechos"])
    eletrodutos, calhas, avisos = [], [], []
    for (tipo, nome), trechos in sorted(grupos.items()):
        obj = doc.getObject(nome)
        if obj is None:
            continue
        if tipo == "bandeja":
            dados = bandejas._caminho(obj)
            item = regras.verificar_bandeja(obj.Label, dados["largura"], dados["aba"], trechos)
            calhas.append(dict(item, objeto=nome))
            continue
        item = regras.verificar_eletroduto(obj.Label, str(getattr(obj, "Diametro", "3/4")),
                                           str(getattr(obj, "Tipo", "Flexível")), trechos)
        eletrodutos.append(dict(item, objeto=nome))
        avisos += item["avisos"]
    return {"eletrodutos": eletrodutos, "bandejas": calhas, "avisos": avisos, "rotas": resultado["rotas"]}


def gravar_planilha(doc, dados):
    """Recria a planilha 'Ocupacao_eletrodutos' (propriedade ``ocupacao_eletrodutos``)."""
    anterior = next((o for o in doc.Objects if hasattr(o, MARCA_PLANILHA)), None)
    if anterior is not None:
        doc.removeObject(anterior.Name)
    planilha = doc.addObject("Spreadsheet::Sheet", "Ocupacao_eletrodutos")
    planilha.addProperty("App::PropertyString", MARCA_PLANILHA, "Rede", "Marca a planilha de ocupação dos eletrodutos")
    setattr(planilha, MARCA_PLANILHA, "Ocupação dos eletrodutos")
    planilha.Label = "Ocupação dos eletrodutos"
    colunas = "ABCDEFGHIJK"
    for linha, valores in enumerate(regras.tabela(dados["eletrodutos"], dados["bandejas"]), start=1):
        for coluna, valor in zip(colunas, valores):
            texto = f"{valor:.1f}" if isinstance(valor, float) else (str(valor) if isinstance(valor, int)
                                                                       else f"'{valor}")
            planilha.set(f"{coluna}{linha}", texto)
    doc.recompute()
    return planilha


def aplicar_diametros(doc, dados):
    """Aumenta o ``Diametro`` dos eletrodutos menores que o mínimo; nunca diminui.

    Returns:
        Lista de (rótulo, de, para).
    """
    trocados = []
    for item in dados["eletrodutos"]:
        if not item["pequeno"] or not item["minimo"]:
            continue
        obj = doc.getObject(item["objeto"])
        if obj is None:
            continue
        try:
            opcoes = obj.getEnumerationsOfProperty("Diametro")
        except Exception:
            opcoes = None
        if opcoes and item["minimo"] not in opcoes:
            App.Console.PrintWarning(f"{obj.Label}: o diâmetro {item['minimo']} não está na lista do eletroduto.\n")
            continue
        trocados.append((obj.Label, str(obj.Diametro), item["minimo"]))
        obj.Diametro = item["minimo"]
    if trocados:
        doc.recompute()
    return trocados


def rotas_dos_objetos(doc, objetos, resultado=None):
    """Rotas que passam pelos objetos selecionados: pontos (o circuito deles), quadros (todos os
    circuitos dele) e eletrodutos ou eletrocalhas (os circuitos que passam ali). Sem seleção, todas.

    Returns:
        Lista de rotas de ``core.rede.analisar``, cada uma com ``objetos`` (nomes
        internos da infraestrutura, em ordem do quadro aos pontos).
    """
    resultado = resultado or analisar(doc)
    rotas = [dict(r, objetos=[nome for nome, _ in r["infraestrutura"]]) for r in resultado["rotas"]]
    if not objetos:
        return rotas
    rotulos, nomes = {obj.Label for obj in objetos}, {obj.Name for obj in objetos}
    return [r for r in rotas if rotulos & set(r["por_ponto"]) or r["quadro"] in rotulos or nomes & set(r["objetos"])]


def descrever(doc, rota):
    """Texto de uma rota: o circuito e, por ponto, a sequência de eletrodutos e eletrocalhas."""
    titulo = f"{rota['rotulo']} ({rota['quadro']}" + (f", {rota['pavimento']}" if rota.get("pavimento") else "") + ")"
    linhas = [titulo]
    for ponto, trajeto in sorted(rota["por_ponto"].items()):
        passos = [("calha " if tipo == "bandeja" else "") + _rotulo(doc, nome) for nome, tipo in trajeto]
        linhas.append(f"  {rota['quadro']} → " + " → ".join(passos + [ponto]))
    if not rota["por_ponto"]:
        linhas.append("  a rede não chega aos pontos")
    return "\n".join(linhas)


def remover_fios(doc):
    """Apaga os textos de fios por trecho (propriedade ``fios_trecho``). Devolve quantos."""
    textos = [o for o in doc.Objects if hasattr(o, MARCA_FIOS)]
    for obj in textos:
        doc.removeObject(obj.Name)
    return len(textos)


def identificar_fios(doc, resultado=None, altura=ALTURA_TEXTO_FIOS):
    """Recria na planta os fios de cada trecho (``C1 #2,5 F+N+T``), ao lado de cada eletroduto e
    eletrocalha, na pasta Fiação do pavimento e na cota do piso dele.

    Returns:
        Quantidade de textos.
    """
    remover_fios(doc)
    resultado = resultado or analisar(doc)
    total = 0
    for item in regras.identificacao_dos_trechos(resultado["trechos"], afastamento=1.4 * altura):
        pav = pavimentos.por_nome(doc, item["pavimento"]) if item["pavimento"] else None
        z = pavimentos.elevacao(pav) if pav is not None else 0.0
        posicao = App.Placement(App.Vector(item["x"], item["y"], z), App.Rotation(App.Vector(0, 0, 1), item["angulo"]))
        texto = Draft.make_text(item["linhas"], placement=posicao, height=altura)
        texto.addProperty("App::PropertyString", MARCA_FIOS, "Rede", "Fios do trecho de eletroduto ou eletrocalha")
        setattr(texto, MARCA_FIOS, item["dono"])
        texto.Label = f"Fios {_rotulo(doc, item['dono'])}"
        if pav is not None:
            pavimentos.pasta(doc, pav, "fiacao").addObject(texto)
        total += 1
    doc.recompute()
    return total
