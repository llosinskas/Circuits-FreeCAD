"""Leitura do quantitativo de materiais no documento e exportação em CSV, XLSX e PDF."""
import datetime
import os

from freecad.Circuits.core import exportar as gravacao
from freecad.Circuits.core import quantitativos as regras
from freecad.Circuits.core import quadro as regras_quadro
from freecad.Circuits.core.simbolos import ATERRAMENTO, CATALOGO, COMANDO, PASSAGEM, QUADRO
from freecad.Circuits.services import planilhas, rede
from freecad.Circuits.services.tomadas import listar_tomadas

EXTENSOES = (".csv", ".xlsx", ".pdf")


def _tipo(obj):
    return getattr(getattr(obj, "Proxy", None), "Type", "")


def _mm(valor):
    return valor.Value if hasattr(valor, "Value") else float(valor)


def _ponto(obj):
    dados = CATALOGO[obj.Simbolo]
    categoria = dados["categoria"]
    if categoria == QUADRO:
        return {"grupo": "Quadros", "item": dados["legenda"], "especificacao": str(obj.Descricao), "caixa": None}
    if categoria == PASSAGEM:
        return {"grupo": "Caixas", "item": "", "especificacao": "", "caixa": "passagem"}
    if categoria == ATERRAMENTO:
        especificacao = {"haste_aterramento": "cobreada 5/8\" x 2,40 m"}.get(obj.Simbolo, "")
        return {"grupo": "Aterramento", "item": dados["legenda"], "especificacao": especificacao, "caixa": None}
    if categoria == COMANDO:
        return {"grupo": "Interruptores", "item": dados["legenda"], "especificacao": str(obj.Tensao),
                "caixa": regras.caixa_do_simbolo(obj.Simbolo)}
    return {
        "grupo": "Pontos",
        "item": dados["legenda"],
        "especificacao": f"{obj.Tensao}, {float(obj.Potencia):.0f} VA",
        "caixa": regras.caixa_do_simbolo(obj.Simbolo),
    }


def coletar_pontos(doc):
    """Pontos, interruptores e quadros da planta, no formato de ``core.quantitativos.montar``."""
    pontos = []
    for obj in doc.Objects:
        tipo = _tipo(obj)
        if tipo == "Ponto" and obj.Simbolo in CATALOGO:
            pontos.append(_ponto(obj))
        elif tipo == "Switch":
            pontos.append({"grupo": "Interruptores", "item": "Interruptor", "especificacao": str(obj.Tipo), "caixa": "4x2"})
        elif tipo == "Outlet":
            pontos.append({"grupo": "Pontos", "item": "Tomada (antiga)", "especificacao": str(obj.Tensao), "caixa": "4x2"})
        elif tipo == "Lighting":
            pontos.append({"grupo": "Pontos", "item": "Ponto de iluminação (antigo)", "especificacao": "", "caixa": "octogonal"})
    for _ in listar_tomadas(doc):
        pontos.append({"grupo": "Pontos", "item": "Tomada TUG", "especificacao": "", "caixa": "4x2"})
    return pontos


def coletar_eletrodutos(doc):
    """(diâmetro, comprimento [mm]) de cada caminho de eletroduto: os que têm a propriedade Diametro."""
    eletrodutos = []
    for obj in doc.Objects:
        if not hasattr(obj, "Diametro") or not hasattr(obj, "Shape"):
            continue
        if _tipo(obj) != "ConduitPath" and not hasattr(obj, "Altura3D"):
            continue
        try:
            comprimento = obj.Shape.Length
        except Exception:
            continue
        eletrodutos.append((str(obj.Diametro), float(comprimento)))
    return eletrodutos


def coletar_aterramento(doc):
    """(seção [mm²], comprimento [mm]) de cada condutor de aterramento e um conector por haste."""
    condutores, conectores = [], 0
    for obj in doc.Objects:
        if hasattr(obj, "SecaoAterramento") and hasattr(obj, "Shape"):
            try:
                condutores.append((float(str(obj.SecaoAterramento).replace(",", ".")), float(obj.Shape.Length)))
            except Exception:
                continue
        elif _tipo(obj) == "Ponto" and getattr(obj, "Simbolo", "") == "haste_aterramento":
            conectores += 1
    return condutores, conectores


def coletar_componentes_quadros(doc):
    """Componentes de todos os quadros, lidos das planilhas de dados e de circuitos."""
    componentes = []
    for quadro in planilhas.listar_quadros(doc):
        try:
            componentes += regras_quadro.componentes(planilhas.ler_quadro(quadro), planilhas.ler_circuitos_completos(quadro))
        except ValueError:
            continue  # quadro com valores fora das tabelas: fica de fora, sem impedir o resto
    return componentes


def levantar(doc):
    """Quantitativo e fiação do documento.

    Returns:
        (linhas de ``core.quantitativos.montar``, resultado de ``services.rede.analisar``
        com fios, circuitos, verticais e avisos).
    """
    fiacao = rede.analisar(doc)
    condutores, conectores = coletar_aterramento(doc)
    componentes = coletar_componentes_quadros(doc)
    if conectores:
        componentes = componentes + [{"item": "Conector haste-cabo", "especificacao": "", "quantidade": conectores,
                                      "unidade": "un", "grupo": "Aterramento"}]
    linhas = regras.montar(
        coletar_pontos(doc), coletar_eletrodutos(doc), componentes,
        fios=fiacao["fios"], verticais=fiacao["verticais"], aterramento=condutores,
    )
    return linhas, fiacao


def calcular(doc):
    """Linhas do quantitativo do documento (``core.quantitativos.montar``)."""
    return levantar(doc)[0]


def caminho_padrao(doc):
    """Caminho base sugerido (sem extensão): na pasta do projeto, se ele já foi salvo."""
    nome = f"Quantitativo_{doc.Label}"
    if getattr(doc, "FileName", ""):
        return os.path.join(os.path.dirname(doc.FileName), nome)
    return nome


def _tabela_pdf(tabela, larguras_cm, estilos):
    """Tabela do reportlab a partir de uma lista de listas com cabeçalho."""
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Table, TableStyle

    def texto(valor):
        return f"{valor:.2f}".replace(".", ",") if isinstance(valor, float) else str(valor)

    dados = [tabela[0]] + [[Paragraph(texto(v), estilos["BodyText"]) for v in linha] for linha in tabela[1:]]
    resultado = Table(dados, colWidths=[largura * cm for largura in larguras_cm], repeatRows=1)
    resultado.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3c4043")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f3f4")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9aa0a6")),
    ]))
    return resultado


def exportar_pdf(linhas, caminho, titulo, fiacao=None):
    """Grava o quantitativo em PDF, com uma tabela por grupo.

    Raises:
        RuntimeError: se a biblioteca reportlab não estiver instalada.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as erro:
        raise RuntimeError("A biblioteca reportlab não está instalada; o PDF não foi gerado.") from erro

    estilos = getSampleStyleSheet()
    celula = estilos["BodyText"]
    historia = [
        Paragraph(titulo, estilos["Title"]),
        Paragraph(f"Gerado em {datetime.date.today():%d/%m/%Y}", estilos["Normal"]),
        Spacer(1, 0.5 * cm),
    ]
    if not linhas:
        historia.append(Paragraph("Nenhum material encontrado no projeto.", estilos["Normal"]))
    for grupo in regras.GRUPOS:
        do_grupo = [linha for linha in linhas if linha["grupo"] == grupo]
        if not do_grupo:
            continue
        historia.append(Paragraph(grupo, estilos["Heading2"]))
        dados = [["Item", "Especificação", "Unid.", "Quant."]]
        for linha in do_grupo:
            quantidade = linha["quantidade"]
            texto = f"{quantidade:.2f}".replace(".", ",") if isinstance(quantidade, float) else str(quantidade)
            dados.append([Paragraph(linha["item"], celula), Paragraph(linha["especificacao"], celula), linha["unidade"], texto])
        tabela = Table(dados, colWidths=[5.5 * cm, 8 * cm, 1.5 * cm, 2 * cm], repeatRows=1)
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3c4043")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f3f4")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9aa0a6")),
        ]))
        historia += [tabela, Spacer(1, 0.4 * cm)]
    if fiacao and fiacao["circuitos"]:
        historia += [Paragraph("Fiação por circuito", estilos["Heading2"]),
                     _tabela_pdf(regras.tabela_circuitos(fiacao["circuitos"]), [2.2, 1.8, 1.8, 2.6, 1.6, 2.2, 2.4], estilos),
                     Spacer(1, 0.4 * cm)]
    if fiacao and fiacao["verticais"]:
        historia += [Paragraph("Lista de verticais", estilos["Heading2"]),
                     _tabela_pdf(regras.tabela_verticais(fiacao["verticais"]),
                                 [2.2, 3.2, 1.6, 2.0, 1.8, 1.8, 1.8, 1.6], estilos),
                     Spacer(1, 0.4 * cm)]
    if fiacao and fiacao["avisos"]:
        historia.append(Paragraph("Avisos", estilos["Heading2"]))
        historia += [Paragraph(aviso, estilos["BodyText"]) for aviso in fiacao["avisos"]]
    historia.append(Paragraph(
        "Estimativa gerada a partir do desenho: eletrodutos e verticais com perdas incluídas; fios pelo caminho mais "
        "curto na rede de eletrodutos, com folga nas caixas. Confira antes de comprar.", estilos["Italic"]))
    SimpleDocTemplate(caminho, pagesize=A4, title=titulo).build(historia)
    return caminho


def exportar(doc, caminho_base, linhas=None, fiacao=None):
    """Grava o quantitativo em CSV, XLSX e PDF com o mesmo nome base.

    O XLSX tem as abas Quantitativo, Verticais e Fiação por circuito; os CSV das
    verticais e da fiação são gravados ao lado, com os sufixos _verticais e _circuitos.

    Returns:
        (arquivos gravados, avisos): lista de caminhos e lista de textos.
    """
    if linhas is None or fiacao is None:
        linhas, fiacao = levantar(doc)
    base, extensao = os.path.splitext(caminho_base)
    if extensao.lower() not in EXTENSOES:
        base = caminho_base
    tabela = regras.como_tabela(linhas)
    verticais = regras.tabela_verticais(fiacao["verticais"])
    circuitos = regras.tabela_circuitos(fiacao["circuitos"])
    gravados = [
        gravacao.para_csv(tabela, base + ".csv"),
        gravacao.para_csv(verticais, base + "_verticais.csv"),
        gravacao.para_csv(circuitos, base + "_circuitos.csv"),
        gravacao.para_xlsx_abas(
            [("Quantitativo", tabela), ("Verticais", verticais), ("Fiação por circuito", circuitos)], base + ".xlsx"
        ),
    ]
    avisos = []
    try:
        gravados.append(exportar_pdf(linhas, base + ".pdf", f"Quantitativo de materiais - {doc.Label}", fiacao))
    except RuntimeError as erro:
        avisos.append(str(erro))
    return gravados, avisos
