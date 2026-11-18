"""Leitura do quantitativo de materiais no documento e exportação em CSV, XLSX e PDF."""
import datetime
import os

from freecad.Circuits.core import exportar as gravacao
from freecad.Circuits.core import quantitativos as regras
from freecad.Circuits.core import verticais as regras_verticais
from freecad.Circuits.core import quadro as regras_quadro
from freecad.Circuits.core.simbolos import ATERRAMENTO, CATALOGO, COMANDO, PASSAGEM, QUADRO
from freecad.Circuits.services import bandejas, eletrodutos_planta, pavimentos, planilhas, rede, verticais
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


def nome_do_pavimento(doc, obj):
    """Nome do pavimento do objeto, ou '' se ele está fora de um pavimento."""
    try:
        pav = pavimentos.pavimento_do_objeto(doc, obj)
    except Exception:
        return ""
    return pav.Label if pav is not None else ""


def coletar_pontos(doc):
    """Pontos, interruptores e quadros da planta, no formato de ``core.quantitativos.montar``.

    Cada dicionário leva também ``pavimento``, o nome do pavimento do símbolo ('' fora de um).
    """
    pontos = []
    for obj in doc.Objects:
        tipo = _tipo(obj)
        if tipo == "Ponto" and obj.Simbolo in CATALOGO:
            dados = _ponto(obj)
        elif tipo == "Switch":
            dados = {"grupo": "Interruptores", "item": "Interruptor", "especificacao": str(obj.Tipo), "caixa": "4x2"}
        elif tipo == "Outlet":
            dados = {"grupo": "Pontos", "item": "Tomada (antiga)", "especificacao": str(obj.Tensao), "caixa": "4x2"}
        elif tipo == "Lighting":
            dados = {"grupo": "Pontos", "item": "Ponto de iluminação (antigo)", "especificacao": "", "caixa": "octogonal"}
        else:
            continue
        dados["pavimento"] = nome_do_pavimento(doc, obj)
        pontos.append(dados)
    for tomada in listar_tomadas(doc):
        pontos.append({"grupo": "Pontos", "item": "Tomada TUG", "especificacao": "", "caixa": "4x2",
                       "pavimento": nome_do_pavimento(doc, tomada)})
    return pontos


def coletar_eletrodutos(doc):
    """(diâmetro, comprimento [mm]) de cada caminho de eletroduto: os que têm a propriedade Diametro."""
    return [(diametro, comprimento) for _, diametro, comprimento in _eletrodutos(doc)]


def _eletrodutos(doc):
    """(pavimento, diâmetro, comprimento [mm]) de cada caminho de eletroduto."""
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
        eletrodutos.append((nome_do_pavimento(doc, obj), str(obj.Diametro), float(comprimento)))
    return eletrodutos


def coletar_aterramento(doc):
    """(seção [mm²], comprimento [mm]) de cada condutor de aterramento e um conector por haste."""
    condutores, conectores = _aterramento(doc)
    return [(secao, comprimento) for _, secao, comprimento in condutores], sum(conectores.values())


def _aterramento(doc):
    """[(pavimento, seção, comprimento [mm])] dos condutores e {pavimento: conectores} das hastes."""
    condutores, conectores = [], {}
    for obj in doc.Objects:
        if hasattr(obj, "SecaoAterramento") and hasattr(obj, "Shape"):
            try:
                condutores.append((nome_do_pavimento(doc, obj), float(str(obj.SecaoAterramento).replace(",", ".")),
                                   float(obj.Shape.Length)))
            except Exception:
                continue
        elif _tipo(obj) == "Ponto" and getattr(obj, "Simbolo", "") == "haste_aterramento":
            pavimento = nome_do_pavimento(doc, obj)
            conectores[pavimento] = conectores.get(pavimento, 0) + 1
    return condutores, conectores


def _pavimento_do_quadro(doc, quadro):
    """Pavimento da planilha do quadro: o da pasta dela ou o do símbolo ligado a ela (propriedade Planilha)."""
    nome = nome_do_pavimento(doc, quadro)
    if nome:
        return nome
    simbolo = next((obj for obj in doc.Objects if getattr(obj, "Planilha", None) == getattr(quadro, "Name", None)), None)
    return nome_do_pavimento(doc, simbolo) if simbolo is not None else ""


def coletar_componentes_quadros(doc):
    """Componentes de todos os quadros, lidos das planilhas de dados e de circuitos."""
    return [item for _, itens in _componentes_por_quadro(doc) for item in itens]


def _componentes_por_quadro(doc):
    """(pavimento, componentes) de cada quadro."""
    resultado = []
    for quadro in planilhas.listar_quadros(doc):
        try:
            itens = regras_quadro.componentes(planilhas.ler_quadro(quadro), planilhas.ler_circuitos_completos(quadro))
        except ValueError:
            continue  # quadro com valores fora das tabelas: fica de fora, sem impedir o resto
        resultado.append((_pavimento_do_quadro(doc, quadro), itens))
    return resultado


def _bandejas(doc):
    """(pavimento, itens) das bandejas, conexões e suportes (``services.bandejas``), sem terminal nas prumadas."""
    try:
        return bandejas.materiais_por_pavimento(doc, sem_terminal=verticais.pontas_de_prumada(doc, "eletrocalha"))
    except Exception:
        return []


def _prumadas(doc):
    """(verticais de eletroduto, [(pavimento, componentes de eletrocalha)]) das prumadas entre pavimentos."""
    try:
        verticais_eletroduto, componentes = regras_verticais.materiais_prumadas(verticais.prumadas(doc))
    except Exception:
        return [], []
    por_pavimento = {}
    for c in componentes:
        por_pavimento.setdefault(c["pavimento"], []).append({k: v for k, v in c.items() if k != "pavimento"})
    return verticais_eletroduto, list(por_pavimento.items())


def _pecas_eletrodutos(doc):
    """(pavimento, itens) das curvas, luvas, buchas, conduletes e abraçadeiras (``services.eletrodutos_planta``)."""
    try:
        return eletrodutos_planta.materiais_por_pavimento(doc)
    except Exception:
        return []


def _conector(quantidade):
    return {"item": "Conector haste-cabo", "especificacao": "", "quantidade": quantidade, "unidade": "un",
            "grupo": "Aterramento"}


def _ordem_dos_pavimentos(doc, nomes):
    """Nomes na ordem das cotas dos pavimentos; os sem pavimento ('') por último."""
    try:
        ordem = [pav.Label for pav in pavimentos.listar(doc)]
    except Exception:
        ordem = []
    return sorted(nomes, key=lambda nome: (nome == "", ordem.index(nome) if nome in ordem else len(ordem), nome))


def levantar_por_pavimento(doc, fiacao=None):
    """Quantitativo de cada pavimento, separado.

    Args:
        fiacao: resultado de ``services.rede.analisar`` (lido de novo se None).
    Returns:
        Pares (nome do pavimento, linhas de ``core.quantitativos.montar``), em
        ordem de cota; o nome '' reúne o que está fora de um pavimento.
    """
    if fiacao is None:
        fiacao = rede.analisar(doc)
    entradas = {}

    def de(pavimento):
        return entradas.setdefault(pavimento, {"pontos": [], "eletrodutos": [], "componentes": [], "fios": {},
                                               "verticais": [], "aterramento": []})

    for ponto in coletar_pontos(doc):
        de(ponto.get("pavimento", ""))["pontos"].append(ponto)
    for pavimento, diametro, comprimento in _eletrodutos(doc):
        de(pavimento)["eletrodutos"].append((diametro, comprimento))
    prumadas_eletroduto, prumadas_eletrocalha = _prumadas(doc)
    for pavimento, itens in _componentes_por_quadro(doc) + _bandejas(doc) + _pecas_eletrodutos(doc) + prumadas_eletrocalha:
        de(pavimento)["componentes"].extend(itens)
    condutores, conectores = _aterramento(doc)
    for pavimento, secao, comprimento in condutores:
        de(pavimento)["aterramento"].append((secao, comprimento))
    for pavimento, quantidade in conectores.items():
        de(pavimento)["componentes"].append(_conector(quantidade))
    for pavimento, fios in fiacao.get("fios_por_pavimento", {}).items():
        de(pavimento)["fios"] = fios
    # as verticais até as caixas, as mudanças de altura entre eletrodutos e as prumadas (no pavimento de baixo)
    for vertical in fiacao["verticais"] + fiacao.get("transicoes", []) + prumadas_eletroduto:
        de(vertical.get("pavimento", ""))["verticais"].append(vertical)

    resultado = []
    for pavimento in _ordem_dos_pavimentos(doc, entradas):
        dados = entradas[pavimento]
        linhas = regras.montar(dados["pontos"], dados["eletrodutos"], dados["componentes"], fios=dados["fios"],
                               verticais=dados["verticais"], aterramento=dados["aterramento"])
        if linhas:
            resultado.append((pavimento, linhas))
    return resultado


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
        componentes = componentes + [_conector(conectores)]
    prumadas_eletroduto, prumadas_eletrocalha = _prumadas(doc)
    componentes = componentes + [item for _, itens in _bandejas(doc) + _pecas_eletrodutos(doc) + prumadas_eletrocalha
                                 for item in itens]
    linhas = regras.montar(
        coletar_pontos(doc), coletar_eletrodutos(doc), componentes,
        fios=fiacao["fios"], verticais=fiacao["verticais"] + fiacao.get("transicoes", []) + prumadas_eletroduto,
        aterramento=condutores,
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


def exportar_pdf(linhas, caminho, titulo, fiacao=None, por_pavimento=None):
    """Grava o quantitativo em PDF, com uma tabela por grupo.

    Com ``por_pavimento`` (de ``levantar_por_pavimento``), acrescenta o
    quantitativo de cada pavimento, um depois do outro.

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
    if por_pavimento:
        historia.append(Paragraph("Quantitativo por pavimento", estilos["Heading2"]))
        for pavimento, do_pavimento in por_pavimento:
            tabela = [list(regras.COLUNAS[:4]) + ["Quant."]] + [
                [linha["grupo"], linha["item"], linha["especificacao"], linha["unidade"], linha["quantidade"]]
                for linha in do_pavimento
            ]
            historia += [Paragraph(pavimento or regras.SEM_PAVIMENTO, estilos["Heading3"]),
                         _tabela_pdf(tabela, [2.6, 4.4, 6.4, 1.4, 2.2], estilos), Spacer(1, 0.3 * cm)]
    if fiacao and fiacao["circuitos"]:
        historia += [Paragraph("Fiação por circuito", estilos["Heading2"]),
                     _tabela_pdf(regras.tabela_circuitos(fiacao["circuitos"]), [2.2, 2.0, 1.6, 1.6, 2.4, 1.6, 1.8, 2.0],
                                 estilos),
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


def exportar(doc, caminho_base, linhas=None, fiacao=None, por_pavimento=None):
    """Grava o quantitativo em CSV, XLSX e PDF com o mesmo nome base.

    O XLSX tem as abas Quantitativo, Por pavimento, Verticais e Fiação por
    circuito; os CSV dessas três últimas são gravados ao lado, com os sufixos
    _pavimentos, _verticais e _circuitos. ``por_pavimento`` vem de
    ``levantar_por_pavimento`` e é lido do documento se não for dado.

    Returns:
        (arquivos gravados, avisos): lista de caminhos e lista de textos.
    """
    if linhas is None or fiacao is None:
        linhas, fiacao = levantar(doc)
    base, extensao = os.path.splitext(caminho_base)
    if extensao.lower() not in EXTENSOES:
        base = caminho_base
    if por_pavimento is None:
        por_pavimento = levantar_por_pavimento(doc, fiacao)
    tabela = regras.como_tabela(linhas)
    pavimentos_tabela = regras.tabela_por_pavimento(por_pavimento)
    verticais = regras.tabela_verticais(fiacao["verticais"])
    circuitos = regras.tabela_circuitos(fiacao["circuitos"])
    gravados = [
        gravacao.para_csv(tabela, base + ".csv"),
        gravacao.para_csv(pavimentos_tabela, base + "_pavimentos.csv"),
        gravacao.para_csv(verticais, base + "_verticais.csv"),
        gravacao.para_csv(circuitos, base + "_circuitos.csv"),
        gravacao.para_xlsx_abas(
            [("Quantitativo", tabela), ("Por pavimento", pavimentos_tabela), ("Verticais", verticais),
             ("Fiação por circuito", circuitos)], base + ".xlsx"
        ),
    ]
    avisos = []
    try:
        gravados.append(exportar_pdf(linhas, base + ".pdf", f"Quantitativo de materiais - {doc.Label}", fiacao,
                                     por_pavimento))
    except RuntimeError as erro:
        avisos.append(str(erro))
    return gravados, avisos
