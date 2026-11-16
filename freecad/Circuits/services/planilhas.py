"""Planilhas de circuitos e de quadros de distribuição."""
import Spreadsheet  # noqa: F401  (registra o tipo Spreadsheet::Sheet)

from freecad.Circuits.core import planilha as layout


def criar_planilha_circuitos(doc):
    planilha = doc.addObject("Spreadsheet::Sheet", "Circuitos")
    for indice, titulo in enumerate(layout.CABECALHO_CIRCUITOS):
        planilha.set(f"{layout.coluna(indice)}1", titulo)
    doc.recompute()
    return planilha


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
    planilha.mergeCells("A1:S1")
    for indice, titulo in enumerate(layout.CABECALHO_QUADRO):
        coluna = layout.coluna(indice)
        planilha.set(f"{coluna}2", titulo)
        planilha.setAlias(f"{coluna}3", titulo)
    planilha.set("A4", "Circuitos")
    planilha.mergeCells("A4:S4")
    for indice, valor in enumerate(dados.values()):
        planilha.set(f"{layout.coluna(indice)}3", str(valor))
    return planilha


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


def linha_do_circuito(planilha, numero):
    """Linha onde o circuito ``numero`` está gravado, ou None."""
    for linha in range(layout.PRIMEIRA_LINHA_CIRCUITOS, ultima_linha(planilha) + 1):
        if _texto(planilha, f"A{linha}") == str(numero).strip():
            return linha
    return None


def adicionar_circuito(planilha, dados):
    """Grava o cabeçalho de circuitos e a linha do circuito.

    Um circuito com o mesmo número é atualizado no lugar; um novo entra depois
    da última linha usada.
    """
    for indice, titulo in enumerate(layout.CABECALHO_CIRCUITO_QUADRO):
        planilha.set(f"{layout.coluna(indice)}{layout.LINHA_CABECALHO_CIRCUITOS}", titulo)

    linha = linha_do_circuito(planilha, dados["N_circuito"])
    if linha is None:
        linha = max(ultima_linha(planilha) + 1, layout.PRIMEIRA_LINHA_CIRCUITOS)
    for coluna, chave in layout.COLUNAS_CIRCUITO.items():
        planilha.set(f"{coluna}{linha}", f"'{dados[chave]}")
    return linha


def gravar_potencia_instalada(planilha, potencia_kw):
    planilha.set(planilha.getCellFromAlias("potencia_instalada"), str(potencia_kw))


def gravar_potencia_demanda(planilha, potencia_kw):
    planilha.set(planilha.getCellFromAlias("potencia_demanda"), str(potencia_kw))
