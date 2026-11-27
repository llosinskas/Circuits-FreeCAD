"""Condutores de aterramento desenhados na planta."""
from freecad.Circuits.services import pavimentos
from freecad.Circuits.services.estilo import pintar_linha

SECOES = ["16", "25", "35", "50", "70"]  # mm², cobre nu
SECAO_PADRAO = "50"
COR_ATERRAMENTO = (0.0, 0.55, 0.0)


def eh_condutor(obj):
    return hasattr(obj, "Points") and hasattr(obj, "SecaoAterramento")


def listar_condutores(doc):
    return [obj for obj in doc.Objects if eh_condutor(obj)]


def marcar_condutores(doc, objetos, secao=SECAO_PADRAO):
    """Marca as linhas como condutores de aterramento de cobre nu, na seção dada.

    As linhas vão para a pasta Aterramento do pavimento ativo (se ainda não estão
    num pavimento) e ficam verdes.

    Returns:
        Quantidade de linhas marcadas; objetos que não são linhas são ignorados.
    """
    linhas = [obj for obj in objetos if hasattr(obj, "Points")]
    destino = pavimentos.pavimento_para_insercao(doc) if linhas else None
    doc.openTransaction("Condutor de aterramento")
    try:
        for obj in linhas:
            if not hasattr(obj, "SecaoAterramento"):
                obj.addProperty("App::PropertyEnumeration", "SecaoAterramento", "Aterramento",
                                "Seção do condutor de cobre nu [mm²]")
                obj.SecaoAterramento = SECOES
            obj.SecaoAterramento = str(secao)
            if pavimentos.pavimento_do_objeto(doc, obj) is None:
                pavimentos.arquivar(doc, obj, destino)  # mesmo pavimento em que os símbolos entram
            pintar_linha(obj, COR_ATERRAMENTO)
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    return len(linhas)


# --- cálculo gravado no projeto e levantamento para o memorial ---------------------------------------------

MARCA_CALCULO = "calculo_aterramento"
PRIMEIRA_LINHA = 3
# (chave de ``core.functions.Predial.aterramento.dimensionar``, rótulo)
ENTRADAS = [
    ("resistividade", "Resistividade do solo [Ω·m]"),
    ("resistencia_alvo", "Resistência desejada [Ω]"),
    ("hastes", "Número de hastes (0 = calcular)"),
    ("espacamento", "Espaçamento entre hastes [m]"),
    ("comprimento_haste", "Comprimento da haste [m]"),
    ("diametro_haste", "Diâmetro da haste [mm]"),
]
SIMBOLOS = {"haste_aterramento": "hastes", "caixa_inspecao": "caixas_inspecao", "bep": "bep"}


def planilha(doc):
    """A planilha do cálculo de aterramento do projeto, ou None."""
    return next((obj for obj in doc.Objects if hasattr(obj, MARCA_CALCULO)), None)


def gravar_calculo(doc, dados):
    """Grava as entradas do cálculo da resistência de terra numa planilha do projeto (cria na primeira vez).

    O memorial do relatório refaz o cálculo com elas. Returns: a planilha.
    """
    folha = planilha(doc)
    if folha is None:
        folha = doc.addObject("Spreadsheet::Sheet", "Aterramento")
        folha.Label = "Cálculo de aterramento"
        folha.addProperty("App::PropertyString", MARCA_CALCULO, "Aterramento", "Entradas do cálculo de aterramento")
        setattr(folha, MARCA_CALCULO, "1")
        folha.set("A1", "'Cálculo da resistência de aterramento (gravado por Resistência de terra; edite a coluna B)")
        folha.set("A2", "'Entrada")
        folha.set("B2", "'Valor")
        folha.set("C2", "'Chave")
        try:
            pavimento = pavimentos.pavimento_para_insercao(doc)
            if pavimento is not None:
                pavimentos.pasta(doc, pavimento, "aterramento").addObject(folha)
        except Exception:
            pass  # sem pavimento, a planilha fica na raiz
        try:
            folha.setColumnWidth("A", 260)
        except Exception:
            pass
    for linha, (chave, rotulo) in enumerate(ENTRADAS, start=PRIMEIRA_LINHA):
        folha.set(f"A{linha}", f"'{rotulo}")
        folha.set(f"B{linha}", str(float(dados.get(chave, 0) or 0)))
        folha.set(f"C{linha}", f"'{chave}")
    doc.recompute()
    return folha


def ler_calculo(doc):
    """Entradas gravadas do cálculo ({chave: valor}), ou None se o projeto não tem o cálculo."""
    folha = planilha(doc)
    if folha is None:
        return None
    dados = {}
    for linha in range(PRIMEIRA_LINHA, PRIMEIRA_LINHA + len(ENTRADAS)):
        try:
            chave = str(folha.getContents(f"C{linha}")).lstrip("'")
            valor = folha.get(f"B{linha}")
        except Exception:
            continue
        try:
            dados[chave] = float(str(valor).replace(",", "."))
        except ValueError:
            continue
    dados["hastes"] = int(dados.get("hastes", 0))
    return dados


def levantamento(doc):
    """Hastes, caixas de inspeção e BEP da planta e os metros de condutor de cobre nu por seção."""
    dados = {"hastes": 0, "caixas_inspecao": 0, "bep": 0, "condutores": {}}
    for obj in doc.Objects:
        chave = SIMBOLOS.get(getattr(obj, "Simbolo", ""))
        if chave and getattr(getattr(obj, "Proxy", None), "Type", "") == "Ponto":
            dados[chave] += 1
    for obj in listar_condutores(doc):
        try:
            metros = obj.Shape.Length / 1000.0
        except Exception:
            continue
        secao = str(obj.SecaoAterramento)
        dados["condutores"][secao] = dados["condutores"].get(secao, 0.0) + metros
    return dados
