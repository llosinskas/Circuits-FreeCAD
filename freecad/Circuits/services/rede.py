"""Rede de eletrodutos do documento: encaixe nas caixas, fiação dos circuitos e verticais."""
import FreeCAD as App

from freecad.Circuits.core import quantitativos as tabelas
from freecad.Circuits.core import rede as regras
from freecad.Circuits.core import quadro as regras_quadro
from freecad.Circuits.core.circuitos import SECAO_MINIMA
from freecad.Circuits.core.simbolos import ATERRAMENTO, CATALOGO, COMANDO, ILUM, LIGACOES, PASSAGEM, QUADRO
from freecad.Circuits.services import pavimentos, planilhas
from freecad.Circuits.services.alinhamento import listar_simbolos
from freecad.Circuits.services.eletrodutos import _preparar_caminho

ALTURA_ELETRODUTO_PADRAO = 2800.0  # mm, eletroduto no teto
QUADROS_DE_ORIGEM = ("quadro_distribuicao", "quadro_comando")  # medição não é origem de circuito


def _mm(valor):
    return valor.Value if hasattr(valor, "Value") else float(valor)


def _tipo(obj):
    return getattr(getattr(obj, "Proxy", None), "Type", "")


def eh_eletroduto(obj):
    """Caminho de eletroduto: ConduitPath, ou Draft Wire já marcado como eletroduto."""
    if _tipo(obj) == "ConduitPath":
        return True
    return all(hasattr(obj, nome) for nome in ("Points", "Diametro", "Altura3D"))


def listar_eletrodutos(doc):
    return [obj for obj in doc.Objects if eh_eletroduto(obj)]


def _pavimento(doc, obj):
    pav = pavimentos.pavimento_do_objeto(doc, obj)
    return pav.Label if pav is not None else ""


def _pontos(obj):
    """Vértices do caminho em coordenadas globais, (x, y)."""
    return [(v.x, v.y) for v in (obj.Placement.multVec(p) for p in obj.Points)]


def _gravar_pontos(obj, pontos_xy):
    """Grava os vértices (x, y globais) de volta nas coordenadas do objeto, mantendo a cota."""
    z = obj.Placement.multVec(obj.Points[0]).z if obj.Points else 0.0
    inversa = obj.Placement.inverse()
    obj.Points = [inversa.multVec(App.Vector(x, y, z)) for x, y in pontos_xy]


# --- caixas ------------------------------------------------------------------

def _caixa(doc, obj):
    """Caixa da rede para um símbolo da planta, ou None se ele não recebe eletroduto."""
    tipo = _tipo(obj)
    base = {
        "id": obj.Name, "nome": obj.Label, "x": obj.Placement.Base.x, "y": obj.Placement.Base.y,
        "pavimento": _pavimento(doc, obj), "circuito": "", "comando": "", "quadro": "",
        "fases": 1, "tipo_circuito": ILUM,
    }
    if tipo == "Ponto":
        dados = CATALOGO[obj.Simbolo]
        base["altura"] = _mm(obj.Altura3D)
        if dados["categoria"] == QUADRO:
            if obj.Simbolo not in QUADROS_DE_ORIGEM:
                return None
            planilha = doc.getObject(obj.Planilha) if getattr(obj, "Planilha", "") else None
            refs = {str(obj.Descricao).strip(), obj.Label, obj.Name}
            if planilha is not None:
                refs |= {planilha.Name, planilha.Label}
            base.update(tipo="quadro", refs=refs - {""}, planilha=planilha)
            return base
        if dados["categoria"] == ATERRAMENTO:
            return None  # o aterramento tem condutor próprio, fora da rede de eletrodutos
        if dados["categoria"] == PASSAGEM:
            base.update(tipo="passagem")  # nó da rede: recebe eletrodutos, mas não é ponta de circuito
            return base
        if dados["categoria"] == COMANDO:  # botão de campainha e fotocélula se comportam como interruptor
            base.update(tipo="interruptor", circuito=str(obj.Circuito).strip(),
                        comando=str(getattr(obj, "Comando", "")).strip())
            return base
        base.update(
            tipo="ponto", circuito=str(obj.Circuito).strip(), comando=str(getattr(obj, "Comando", "")).strip(),
            quadro=str(getattr(obj, "Quadro", "")).strip(), fases=LIGACOES.get(obj.Ligacao, 1),
            tipo_circuito=dados["tipo_circuito"],
        )
        return base
    if tipo == "Switch":
        base.update(tipo="interruptor", altura=_mm(obj.Altura3D), circuito=str(obj.Circuito).strip(),
                    comando=str(obj.Comando).strip())
        return base
    if tipo == "Lighting":
        base.update(tipo="ponto", altura=_mm(obj.Altura3D), circuito=str(obj.Circuito).strip(),
                    comando=str(getattr(obj, "Comando", "")).strip())
        return base
    if tipo == "Outlet":
        base.update(tipo="ponto", altura=_mm(obj.Altura3D), circuito=str(obj.Circuito).strip(), tipo_circuito="TUG",
                    fases=2 if str(obj.Tensao) == "Bifásica" else 1)
        return base
    if getattr(obj, "tipo", "") == "tomada":
        base.update(tipo="ponto", altura=float(getattr(obj, "altura_piso", 300.0)), circuito=str(obj.Circuito).strip(),
                    tipo_circuito="TUG", fases=int(getattr(obj, "Fase", 1)) or 1)
        return base
    return None


def listar_caixas(doc):
    caixas = []
    for obj in listar_simbolos(doc):
        try:
            caixa = _caixa(doc, obj)
        except Exception as erro:
            App.Console.PrintWarning(f"{obj.Label} ficou fora da rede: {erro}\n")
            continue
        if caixa is not None:
            caixas.append(caixa)
    return caixas


def _mesmo_pavimento(a, b):
    return not a or not b or a == b


# --- encaixe ---------------------------------------------------------------------

def conectar(doc, objetos=(), tolerancia=regras.TOLERANCIA_ENCAIXE_MM):
    """Marca os caminhos como eletrodutos e encaixa os vértices deles nas caixas próximas.

    Args:
        objetos: linhas selecionadas (Draft Wire ou ConduitPath); vazio usa todos
            os eletrodutos do documento.
    Returns:
        (eletrodutos tratados, caixas ligadas, nomes das caixas com circuito que
        continuam sem eletroduto).
    """
    caminhos = [obj for obj in objetos if hasattr(obj, "Points")] or listar_eletrodutos(doc)
    caixas = listar_caixas(doc)
    ligadas = set()
    doc.openTransaction("Conectar eletrodutos às caixas")
    try:
        for obj in caminhos:
            _preparar_caminho(obj)
            if pavimentos.pavimento_do_objeto(doc, obj) is None:
                pavimentos.arquivar(doc, obj)  # vai para a pasta Eletrodutos do pavimento ativo
            pav = _pavimento(doc, obj)
            proximas = [c for c in caixas if _mesmo_pavimento(c["pavimento"], pav)]
            novos, encaixadas = regras.encaixar(_pontos(obj), [(c["x"], c["y"]) for c in proximas], tolerancia)
            if novos != _pontos(obj):
                _gravar_pontos(obj, novos)
            ligadas |= {proximas[i]["id"] for i in encaixadas}
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    resultado = analisar(doc)
    soltas = [aviso.split(":")[0] for aviso in resultado["avisos"] if "sem eletroduto" in aviso]
    return len(caminhos), len(ligadas), soltas


# --- fiação e verticais ------------------------------------------------------------

def _planilha_do_quadro(doc, quadro):
    if quadro.get("planilha") is not None:
        return quadro["planilha"]
    return next((p for p in planilhas.listar_quadros(doc) if p.Label in quadro["refs"] or p.Name in quadro["refs"]), None)


def _info_circuito(doc, cache):
    """Função que diz seção e condutores de um circuito, pela planilha do quadro ou pelos pontos."""

    def info(quadro, numero, membros):
        chave = quadro["id"]
        if chave not in cache:
            planilha = _planilha_do_quadro(doc, quadro)
            cache[chave] = {c["N_circuito"]: c for c in planilhas.ler_circuitos_completos(planilha)} if planilha else {}
        linha = cache[chave].get(numero)
        tipos = {m.get("tipo_circuito") for m in membros if m["tipo"] != "interruptor"}
        secao_minima = SECAO_MINIMA[ILUM] if tipos <= {ILUM} else SECAO_MINIMA["TUG"]
        if linha is not None:
            fases = max(1, sum(linha[f"Fase_{f}"] == "True" for f in "RST"))
            secao = regras_quadro.numero(linha["Cabo"]) or secao_minima
            neutro = linha["Neutro"] == "True" or fases == 1
        else:
            fases = max(m.get("fases", 1) for m in membros)
            secao, neutro = secao_minima, fases == 1
        return {"secao": secao, "fases": fases, "neutro": neutro, "terra": True}

    return info


def analisar(doc):
    """Fios, fiação por circuito e verticais de todos os pavimentos (``core.rede.analisar``)."""
    caminhos_por_pav = {}
    for obj in listar_eletrodutos(doc):
        try:
            pontos = _pontos(obj)
        except Exception:
            continue
        altura = _mm(obj.Altura3D) if hasattr(obj, "Altura3D") else ALTURA_ELETRODUTO_PADRAO
        caminho = {"pontos": pontos, "altura": altura, "diametro": str(getattr(obj, "Diametro", "3/4"))}
        caminhos_por_pav.setdefault(_pavimento(doc, obj), []).append(caminho)

    caixas = listar_caixas(doc)
    pavs = set(caminhos_por_pav) | {c["pavimento"] for c in caixas}
    cache, resultados = {}, []
    for pav in sorted(pavs):
        caminhos = caminhos_por_pav.get(pav, []) + (caminhos_por_pav.get("", []) if pav else [])
        do_pav = [c for c in caixas if c["pavimento"] == pav]
        if not do_pav:
            continue
        resultados.append(regras.analisar(caminhos, do_pav, _info_circuito(doc, cache)))
    return regras.juntar(resultados)


def gravar_planilha_verticais(doc, verticais):
    """Recria a planilha 'Verticais' do documento com a lista de verticais."""
    nome = "Verticais"
    anterior = next((o for o in doc.Objects if hasattr(o, "lista_de_verticais")), None)
    if anterior is not None:
        doc.removeObject(anterior.Name)
    planilha = doc.addObject("Spreadsheet::Sheet", nome)
    planilha.addProperty("App::PropertyString", "lista_de_verticais", "Rede", "Marca a lista de verticais do projeto")
    planilha.lista_de_verticais = "Verticais"
    for linha, valores in enumerate(tabelas.tabela_verticais(verticais), start=1):
        for coluna, valor in zip("ABCDEFGH", valores):
            texto = f"{valor:.2f}" if isinstance(valor, float) else f"'{valor}"
            planilha.set(f"{coluna}{linha}", texto)
    doc.recompute()
    return planilha
