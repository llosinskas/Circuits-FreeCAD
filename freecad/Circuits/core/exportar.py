"""Exportação de tabelas para CSV e XLSX só com a biblioteca padrão do Python.

O XLSX é escrito à mão (é um ZIP de arquivos XML), para não depender do
openpyxl, que não vem com o FreeCAD.
"""
import csv
import zipfile
from xml.sax.saxutils import escape


def _texto_csv(valor):
    """Número com vírgula decimal, como o Excel em português espera; o resto como texto."""
    if isinstance(valor, float):
        return f"{valor:.2f}".replace(".", ",")
    return str(valor)


def para_csv(tabela, caminho):
    """Grava a tabela (lista de listas) em CSV separado por ponto e vírgula, em UTF-8 com BOM."""
    with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        for linha in tabela:
            escritor.writerow([_texto_csv(valor) for valor in linha])
    return caminho


def _coluna(indice):
    """Letra da coluna do Excel para um índice a partir de zero (A, B, ..., Z, AA, ...)."""
    letras = ""
    indice += 1
    while indice:
        indice, resto = divmod(indice - 1, 26)
        letras = chr(ord("A") + resto) + letras
    return letras


def _celula(referencia, valor, estilo):
    atributo_estilo = f' s="{estilo}"' if estilo else ""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        texto = escape(str(valor))
        return f'<c r="{referencia}" t="inlineStr"{atributo_estilo}><is><t xml:space="preserve">{texto}</t></is></c>'
    return f'<c r="{referencia}"{atributo_estilo}><v>{valor}</v></c>'


_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '<Override PartName="/xl/styles.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    '</Types>'
)
_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    '</Relationships>'
)
_WORKBOOK_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
    '<Relationship Id="rId2" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    '</Relationships>'
)
# Estilos: 0 = normal, 1 = cabeçalho em negrito, 2 = número com duas casas.
_STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="3">'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    '<xf numFmtId="2" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
    '</cellXfs>'
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
    '</styleSheet>'
)


def para_xlsx(tabela, caminho, nome_aba="Quantitativo"):
    """Grava a tabela (lista de listas) em XLSX, com a primeira linha em negrito.

    Números viram células numéricas (decimais com duas casas); o resto, texto.
    """
    linhas_xml = []
    for numero_linha, linha in enumerate(tabela, start=1):
        celulas = []
        for indice, valor in enumerate(linha):
            estilo = 1 if numero_linha == 1 else 2 if isinstance(valor, float) else 0
            celulas.append(_celula(f"{_coluna(indice)}{numero_linha}", valor, estilo))
        linhas_xml.append(f'<row r="{numero_linha}">{"".join(celulas)}</row>')

    colunas = max((len(linha) for linha in tabela), default=0)
    larguras = []
    for indice in range(colunas):
        maior = max((len(str(linha[indice])) for linha in tabela if indice < len(linha)), default=8)
        largura = min(max(maior + 2, 8), 70)
        larguras.append(f'<col min="{indice + 1}" max="{indice + 1}" width="{largura}" customWidth="1"/>')

    planilha = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        + (f'<cols>{"".join(larguras)}</cols>' if larguras else "")
        + f'<sheetData>{"".join(linhas_xml)}</sheetData>'
        '</worksheet>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{escape(nome_aba[:31])}" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as arquivo:
        arquivo.writestr("[Content_Types].xml", _CONTENT_TYPES)
        arquivo.writestr("_rels/.rels", _RELS)
        arquivo.writestr("xl/workbook.xml", workbook)
        arquivo.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        arquivo.writestr("xl/styles.xml", _STYLES)
        arquivo.writestr("xl/worksheets/sheet1.xml", planilha)
    return caminho
