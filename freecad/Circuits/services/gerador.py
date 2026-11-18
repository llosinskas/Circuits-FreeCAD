"""Planilha "Cargas do gerador": criação, leitura e resultado (``core.functions.Predial.gerador``).

Uma carga por linha, da linha 3 em diante, nas colunas de ``regras.COLUNAS``.
A planilha é marcada pela propriedade ``cargas_do_gerador``. Ao ser criada,
recebe uma linha por quadro do projeto (potência instalada e fator de demanda
calculados) ou, sem quadros, cargas de exemplo. O resultado do cálculo é
gravado nas colunas K e L.
"""
import Spreadsheet  # noqa: F401  (registra o tipo Spreadsheet::Sheet)

from freecad.Circuits.core.functions.Predial import gerador as regras
from freecad.Circuits.services import planilhas

COLUNA_ROTULO, COLUNA_VALOR = "K", "L"


def planilha(doc):
    """A planilha de cargas do gerador do documento, ou None."""
    return next((obj for obj in doc.Objects if hasattr(obj, "cargas_do_gerador")), None)


def _numero(texto):
    try:
        return float(str(texto).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def quadros_do_projeto(doc):
    """[(nome, potência instalada [kW], demanda [kW] ou None)] de cada quadro.

    Usa a potência instalada e a demanda gravadas pelo botão Demanda; sem elas,
    soma a potência [W] dos circuitos do quadro.
    """
    resultado = []
    for quadro in planilhas.listar_quadros(doc):
        try:
            dados = planilhas.ler_quadro(quadro)
        except Exception:
            dados = {}
        instalada = _numero(dados.get("potencia_instalada"))
        demanda = _numero(dados.get("potencia_demanda"))
        if not instalada:
            try:
                circuitos = planilhas.ler_circuitos(quadro)
            except Exception:
                circuitos = []
            instalada = sum(_numero(c.get("Potencia")) or 0.0 for c in circuitos) / 1000.0
            demanda = None
        resultado.append((quadro.Label, round(instalada, 2), demanda))
    return resultado


def criar(doc):
    """Cria a planilha com os quadros do projeto (ou exemplos).

    Returns:
        (planilha, quantidade de quadros usados).
    """
    folha = doc.addObject("Spreadsheet::Sheet", "Cargas_gerador")
    folha.Label = "Cargas do gerador"
    folha.addProperty("App::PropertyString", "cargas_do_gerador", "Gerador", "Cargas lidas pelo cálculo do gerador")
    folha.cargas_do_gerador = "1"
    folha.set("A1", f"'{regras.AJUDA}")
    for coluna, _, titulo in regras.COLUNAS:
        folha.set(f"{coluna}{regras.LINHA_TITULOS}", f"'{titulo}")
    try:
        folha.setColumnWidth("A", 260)
        folha.setColumnWidth("B", 230)
    except Exception:
        pass
    dos_quadros = regras.linhas_dos_quadros(quadros_do_projeto(doc))
    for linha, dados in enumerate(dos_quadros or regras.EXEMPLOS, start=regras.PRIMEIRA_LINHA):
        for coluna, chave, _ in regras.COLUNAS:
            if dados.get(chave):
                folha.set(f"{coluna}{linha}", f"'{dados[chave]}")
    doc.recompute()
    return folha, len(dos_quadros)


def _texto(folha, celula):
    try:
        conteudo = folha.getContents(celula)
    except Exception:
        return ""
    return str(conteudo or "").lstrip("'=").strip()


def ler_cargas(folha):
    """Cargas da planilha (``regras.carga``), sem as linhas sem descrição e potência.

    Raises:
        ValueError: com o número da linha, se uma carga tiver dado inválido.
    """
    cargas = []
    for linha in range(regras.PRIMEIRA_LINHA, planilhas.ultima_linha(folha) + 1):
        celulas = {chave: _texto(folha, f"{coluna}{linha}") for coluna, chave, _ in regras.COLUNAS}
        if not celulas["descricao"] and not celulas["potencia"]:
            continue
        celulas["descricao"] = celulas["descricao"] or f"Linha {linha}"
        try:
            cargas.append(regras.carga_da_linha(celulas))
        except ValueError as erro:
            raise ValueError(f"Planilha {folha.Label}, linha {linha}: {erro}") from erro
    return cargas


def gravar_resultado(folha, resultado):
    """Grava o resumo do cálculo nas colunas K e L."""
    folha.set(f"{COLUNA_ROTULO}{regras.LINHA_TITULOS}", "'Resultado do cálculo")
    for linha, (rotulo, valor) in enumerate(regras.resumo(resultado), start=regras.PRIMEIRA_LINHA):
        folha.set(f"{COLUNA_ROTULO}{linha}", f"'{rotulo}")
        folha.set(f"{COLUNA_VALOR}{linha}", f"'{valor}")
    folha.Document.recompute()
