"""Planilhas de circuitos e de quadros de distribuição."""
import Spreadsheet  # noqa: F401  (registra o tipo Spreadsheet::Sheet)

from freecad.Circuits.core import planilha as layout
from freecad.Circuits.core import quadro as regras_quadro
from freecad.Circuits.services import pavimentos


def criar_planilha_circuitos(doc):
    planilha = doc.addObject("Spreadsheet::Sheet", "Circuitos")
    for indice, titulo in enumerate(layout.CABECALHO_CIRCUITOS):
        planilha.set(f"{layout.coluna(indice)}1", titulo)
    doc.recompute()
    return planilha


def planilha_geral_circuitos(doc, criar=True):
    """Planilha geral de circuitos (criada por ``criar_planilha_circuitos``), ou None."""
    folha = next(
        (
            o for o in doc.Objects
            if getattr(o, "TypeId", "") == "Spreadsheet::Sheet"
            and not hasattr(o, "circuitos_de")
            and not hasattr(o, "quadro")
            and (o.Name == "Circuitos" or _texto(o, "A1") == "ID")
        ),
        None,
    )
    if folha is None and criar:
        return criar_planilha_circuitos(doc)
    return folha


def adicionar_circuito_geral(doc, dados):
    """Acrescenta uma linha à planilha geral de circuitos (``CABECALHO_CIRCUITOS``)."""
    folha = planilha_geral_circuitos(doc, criar=True)
    linha = max(ultima_linha(folha) + 1, 2)
    chaves = (
        "ID", "Origem", "Destino", "Potencia_kW", "Tensao", "FatorPotencia",
        "PotenciaAparente_kVA", "Corrente", "Comprimento", "Queda",
        "Cabo", "Metodo", "FCA", "FCT", "Disjuntor", "Curva",
        "Fase_R", "Fase_S", "Fase_T",
    )
    for indice, chave in enumerate(chaves):
        valor = dados.get(chave, "")
        if isinstance(valor, bool):
            valor = "S" if valor else "N"
        texto = str(valor).strip()
        if texto:
            folha.set(f"{layout.coluna(indice)}{linha}", f"'{texto}")
    doc.recompute()
    return folha, linha


def criar_planilha_quadro(doc, dados):
    """Cria a planilha de um quadro a partir dos dados do diálogo CriarQuadro."""
    nome_quadro = dados["indentificacao"]
    planilha = next((q for q in listar_quadros(doc) if nome_quadro in (q.Label, q.Name)), None)
    if planilha is None:
        planilha = doc.addObject("Spreadsheet::Sheet", nome_quadro)
        doc.recompute()

    if not hasattr(planilha, "quadro"):
        planilha.addProperty("App::PropertyString", "quadro")
    planilha.quadro = "Quadro"
    planilha.set("A1", nome_quadro)
    planilha.mergeCells(f"A1:{layout.coluna(len(layout.CABECALHO_QUADRO) - 1)}1")
    planilha.set("A4", "Circuitos")
    planilha.mergeCells(f"A4:{layout.coluna(len(layout.CABECALHO_QUADRO) - 1)}4")
    valores = list(dados.values())
    for indice, titulo in enumerate(layout.CABECALHO_QUADRO):
        coluna = layout.coluna(indice)
        planilha.set(f"{coluna}2", titulo)
        valor = str(valores[indice]) if indice < len(valores) else ""
        if valor:  # o valor antes do alias: escrever "" apaga a célula, e o alias junto
            planilha.set(f"{coluna}3", valor)
        planilha.setAlias(f"{coluna}3", titulo)
    return planilha


def completar_cabecalho_quadro(planilha):
    """Escreve na linha 2 os títulos das colunas novas que faltam em quadros antigos (ex.: IDR),
    para o usuário saber onde preencher. Não mexe nos valores da linha 3."""
    for indice, titulo in enumerate(layout.CABECALHO_QUADRO):
        celula = f"{layout.coluna(indice)}2"
        if not _texto(planilha, celula).strip():
            planilha.set(celula, titulo)


def celula_do_campo(planilha, alias):
    """Célula da linha 3 do quadro com o campo: pelo alias ou, se ele se perdeu (planilhas criadas
    antes com o campo vazio), pela posição de ``core.planilha.CABECALHO_QUADRO``."""
    try:
        celula = planilha.getCellFromAlias(alias)
    except Exception:
        celula = None
    return celula or f"{layout.coluna(layout.CABECALHO_QUADRO.index(alias))}3"


def listar_quadros(doc):
    """Planilhas marcadas com a propriedade 'quadro'."""
    return [obj for obj in doc.Objects if hasattr(obj, "quadro")]


def ultima_linha(planilha):
    return layout.ultima_linha(planilha.getUsedCells())


def _texto(planilha, celula):
    """Conteúdo da célula como texto; célula vazia devolve ''."""
    try:
        valor = planilha.get(celula)
    except Exception:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()


def ler_quadro(planilha):
    """Dados da linha 3 do quadro, em texto, pelas chaves de ``CABECALHO_QUADRO`` (pelo alias, ou pela
    posição da coluna quando o alias se perdeu)."""
    return {alias: _texto(planilha, alias) or _texto(planilha, celula_do_campo(planilha, alias))
            for alias in layout.CABECALHO_QUADRO}


def _circuitos_no_quadro(quadro):
    """Circuitos no formato antigo: gravados na própria planilha do quadro, da linha 6 em diante."""
    circuitos = []
    for linha in range(layout.PRIMEIRA_LINHA_CIRCUITOS, ultima_linha(quadro) + 1):
        if not _texto(quadro, f"A{linha}"):
            continue
        circuitos.append({chave: _texto(quadro, f"{coluna}{linha}") for coluna, chave in layout.COLUNAS_CIRCUITO.items()})
    return circuitos


def _limpar_circuitos_do_quadro(quadro):
    """Apaga da planilha do quadro as linhas de circuito do formato antigo (linha 5 em diante)."""
    for celula in list(quadro.getUsedCells()):
        if layout.ultima_linha([celula]) >= layout.LINHA_CABECALHO_CIRCUITOS:
            quadro.clear(celula)


def planilha_de_circuitos(quadro, criar=True):
    """Planilha de circuitos ligada ao quadro pela propriedade ``circuitos_de``.

    Com ``criar``, é criada com os títulos das colunas se não existir, na
    mesma pasta da planilha do quadro. Os circuitos que estavam na planilha do
    quadro (formato antigo) são levados para ela.
    """
    doc = quadro.Document
    for obj in doc.Objects:
        if getattr(obj, "circuitos_de", None) == quadro.Name:
            return obj
    if not criar:
        return None

    planilha = doc.addObject("Spreadsheet::Sheet", f"Circuitos_{quadro.Name}")
    planilha.Label = f"Circuitos {quadro.Label}"
    planilha.addProperty("App::PropertyString", "circuitos_de", "Quadro", "Planilha do quadro a que estes circuitos pertencem")
    planilha.circuitos_de = quadro.Name
    planilha.set(f"A{layout.LINHA_TITULO_CIRCUITOS}", f"'Circuitos do quadro {quadro.Label}")
    planilha.set(f"C{layout.LINHA_TITULO_CIRCUITOS}", f"'{layout.AJUDA_CIRCUITOS}")
    for coluna, _, titulo in layout.PLANILHA_CIRCUITOS:
        planilha.set(f"{coluna}{layout.LINHA_TITULOS_COLUNAS}", f"'{titulo}")

    antigos = _circuitos_no_quadro(quadro)
    for indice, circuito in enumerate(antigos):
        _gravar_linha(planilha, layout.PRIMEIRA_LINHA_PLANILHA_CIRCUITOS + indice, circuito)
    if antigos:
        _limpar_circuitos_do_quadro(quadro)
    pavimentos.guardar_junto(quadro, planilha)
    doc.recompute()
    return planilha


def _gravar_linha(planilha, linha, circuito):
    for coluna, texto in layout.circuito_para_linha(circuito).items():
        planilha.set(f"{coluna}{linha}", f"'{texto}")


def _linhas_da_planilha(planilha):
    """(número da linha, textos por chave) de cada linha preenchida da planilha de circuitos."""
    for linha in range(layout.PRIMEIRA_LINHA_PLANILHA_CIRCUITOS, ultima_linha(planilha) + 1):
        celulas = {chave: _texto(planilha, f"{coluna}{linha}") for coluna, chave, _ in layout.PLANILHA_CIRCUITOS}
        if celulas["N_circuito"]:
            yield linha, celulas


def ler_circuitos(quadro):
    """Circuitos do quadro, em texto, pelas chaves de ``COLUNAS_CIRCUITO``.

    Lê a planilha de circuitos ligada ao quadro; se ela ainda não existe, lê as
    linhas do formato antigo na própria planilha do quadro.
    """
    planilha = planilha_de_circuitos(quadro, criar=False)
    if planilha is None:
        return _circuitos_no_quadro(quadro)
    return [layout.linha_para_circuito(celulas) for _, celulas in _linhas_da_planilha(planilha)]


def ler_circuitos_completos(quadro):
    """Circuitos do quadro com corrente, cabo e disjuntor calculados onde ficaram em branco,
    com os parâmetros do projeto (isolação, temperatura, material, queda máxima)."""
    try:
        from freecad.Circuits.services import parametros
        valores = parametros.ler(quadro.Document)
    except Exception:
        valores = None  # sem documento ou planilha legível: padrões
    return [regras_quadro.completar(circuito, valores) for circuito in ler_circuitos(quadro)]


def gravar_componentes(doc, quadro, itens):
    """Recria a planilha ``Componentes_<quadro>`` com a lista de componentes do quadro.

    Ela fica na mesma pasta da planilha do quadro.
    """
    nome = f"Componentes_{quadro.Name}"
    if doc.getObject(nome):
        doc.removeObject(nome)
    planilha = doc.addObject("Spreadsheet::Sheet", nome)
    planilha.Label = f"Componentes {quadro.Label}"
    planilha.addProperty("App::PropertyString", "componentes_de", "Quadro", "Planilha do quadro que gerou a lista")
    planilha.componentes_de = quadro.Name
    for coluna, titulo in zip("ABCD", ("Item", "Especificação", "Quantidade", "Unidade")):
        planilha.set(f"{coluna}1", titulo)
    for linha, item in enumerate(itens, start=2):
        planilha.set(f"A{linha}", f"'{item['item']}")
        planilha.set(f"B{linha}", f"'{item['especificacao']}")
        planilha.set(f"C{linha}", str(item["quantidade"]))
        planilha.set(f"D{linha}", f"'{item['unidade']}")
    pavimentos.guardar_junto(quadro, planilha)
    doc.recompute()
    return planilha


def linha_do_circuito(quadro, numero):
    """Linha da planilha de circuitos onde o circuito ``numero`` está, ou None."""
    planilha = planilha_de_circuitos(quadro, criar=False)
    if planilha is None:
        return None
    for linha, celulas in _linhas_da_planilha(planilha):
        if celulas["N_circuito"] == str(numero).strip():
            return linha
    return None


def adicionar_circuito(quadro, dados):
    """Grava o circuito na planilha de circuitos do quadro, criando-a se preciso.

    Um circuito com o mesmo número é atualizado no lugar; um novo entra depois
    da última linha usada.

    Returns:
        A linha em que o circuito ficou.
    """
    planilha = planilha_de_circuitos(quadro)
    for coluna, _, titulo in layout.PLANILHA_CIRCUITOS:  # planilhas antigas ganham as colunas novas
        planilha.set(f"{coluna}{layout.LINHA_TITULOS_COLUNAS}", f"'{titulo}")
    linha = linha_do_circuito(quadro, dados["N_circuito"])
    if linha is None:
        linha = max(ultima_linha(planilha) + 1, layout.PRIMEIRA_LINHA_PLANILHA_CIRCUITOS)
    elif "Grupo_DR" not in dados:  # quem não sabe do grupo do DR (Montar circuitos) não o apaga
        coluna = next(col for col, chave, _ in layout.PLANILHA_CIRCUITOS if chave == "Grupo_DR")
        dados = dict(dados, Grupo_DR=_texto(planilha, f"{coluna}{linha}"))
    _gravar_linha(planilha, linha, dados)
    return linha


def gravar_potencia_instalada(planilha, potencia_kw):
    planilha.set(celula_do_campo(planilha, "potencia_instalada"), str(potencia_kw))


def gravar_potencia_demanda(planilha, potencia_kw):
    planilha.set(celula_do_campo(planilha, "potencia_demanda"), str(potencia_kw))


def _potencia_da_linha(celulas):
    """Potência [W] da linha; sem ela, corrente × tensão."""
    potencia = regras_quadro.numero(celulas.get("Potencia"))
    if potencia <= 0:
        potencia = regras_quadro.numero(celulas.get("Corrente")) * regras_quadro.numero(celulas.get("Tensao"))
    return potencia


def balancear_fases(quadro, aplicar=False):
    """Balanceia as fases dos circuitos do quadro (``core.balanceamento``).

    Lê a planilha de circuitos; um circuito com ``*`` na coluna Fases (ex.: ``R*``)
    fica fixo. As fases do quadro vêm de ``numero_fases`` (3 se vazio).

    Args:
        aplicar: grava as fases novas na coluna Fases (mantendo o ``*`` dos fixos).
    Returns:
        O resultado de ``core.balanceamento.balancear``, ou None sem circuitos.
    """
    from freecad.Circuits.core import balanceamento

    planilha = planilha_de_circuitos(quadro, criar=False)
    if planilha is None:
        return None
    linhas = list(_linhas_da_planilha(planilha))
    if not linhas:
        return None
    circuitos, fixos, linha_do = [], [], {}
    for linha, celulas in linhas:
        numero = celulas["N_circuito"]
        linha_do[numero] = linha
        circuitos.append({"numero": numero, "potencia": _potencia_da_linha(celulas), "fases": celulas.get("Fases", "")})
        if "*" in str(celulas.get("Fases", "")):
            fixos.append(numero)
    n_fases = int(regras_quadro.numero(ler_quadro(quadro).get("numero_fases"), 3) or 3)
    resultado = balanceamento.balancear(circuitos, balanceamento.disponiveis(n_fases), fixos)
    if aplicar:
        coluna = next(col for col, chave, _ in layout.PLANILHA_CIRCUITOS if chave == "Fases")
        for numero in resultado["mudados"]:
            marca = "*" if numero in fixos else ""
            planilha.set(f"{coluna}{linha_do[numero]}", f"'{resultado['fases'][numero]}{marca}")
        quadro.Document.recompute()
    return resultado
