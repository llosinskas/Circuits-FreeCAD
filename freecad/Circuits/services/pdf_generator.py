import os
import time

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.services import estilo, planilhas, quantitativos

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
    from reportlab.lib.units import cm
except ImportError:
    pass  # Será tratado no UI se o reportlab não existir

# (propriedade que marca o grupo do diagrama, título, propriedade com o nome da planilha do quadro)
TIPOS_DE_DIAGRAMA = (
    ("quadro_origem", "Unifilar", "quadro_origem"),
    ("multifilar_de", "Multifilar", "multifilar_de"),
    ("diagrama_gerador", "Transferência rede/gerador (QTA)", None),
)
LARGURA_IMAGEM = 2000  # px
ALTURA_MAXIMA_IMAGEM = 2800  # px


def descendentes(grupo):
    """Todos os objetos dentro do grupo, em qualquer nível."""
    encontrados, pendentes = [], list(getattr(grupo, "Group", []) or [])
    while pendentes:
        obj = pendentes.pop(0)
        if obj in encontrados:
            continue
        encontrados.append(obj)
        pendentes.extend(getattr(obj, "Group", []) or [])
    return encontrados


def listar_diagramas(doc):
    """[(título, grupo)] dos diagramas gerados: unifilares, multifilares e a transferência rede/gerador.

    O título leva o nome do quadro (``Unifilar QD1``), achado pela planilha gravada no grupo.
    """
    diagramas = []
    for marca, nome, referencia in TIPOS_DE_DIAGRAMA:
        for obj in doc.Objects:
            if not hasattr(obj, marca) or not hasattr(obj, "Group"):
                continue
            quadro = doc.getObject(getattr(obj, referencia)) if referencia else None
            diagramas.append((f"{nome} {quadro.Label}" if quadro is not None else nome, obj))
    return diagramas


def visivel_no_corte(obj, dos_diagramas=()):
    """O objeto aparece na vista 3D do relatório: tudo, menos os diagramas e os Sketches.

    Nem todo objeto tem ``Proxy`` (um Sketch comum não tem), então só o tipo e o nome são lidos.
    """
    if obj.Name in dos_diagramas or str(getattr(obj, "Label", "")).startswith("diagrama"):
        return False
    return getattr(obj, "TypeId", "") != "Sketcher::SketchObject"


def _caixa_dos_objetos(objetos):
    """(largura, altura) do retângulo que envolve as formas dos objetos, ou None."""
    caixas = []
    for obj in objetos:
        try:
            caixa = obj.Shape.BoundBox
        except Exception:
            continue
        if caixa.isValid() and (caixa.XLength > 0 or caixa.YLength > 0):
            caixas.append(caixa)
    if not caixas:
        return None
    x1, x2 = min(c.XMin for c in caixas), max(c.XMax for c in caixas)
    y1, y2 = min(c.YMin for c in caixas), max(c.YMax for c in caixas)
    return (x2 - x1, y2 - y1) if x2 > x1 and y2 > y1 else None


ESPERA_CAMERA_S = 3.0


def _esperar_a_camera(view):
    """Atualiza a interface até a câmera olhar de cima (z para baixo), por até ``ESPERA_CAMERA_S``."""
    fim = time.monotonic() + ESPERA_CAMERA_S
    while True:
        Gui.updateGui()
        try:
            direcao = view.getViewDirection()
            if abs(direcao.z + 1.0) < 1e-3 or time.monotonic() > fim:
                return
        except Exception:
            return
        time.sleep(0.05)


def capturar_diagrama(doc, view, grupo, caminho):
    """Grava a imagem de um diagrama: só ele visível, vista de topo e enquadrado nele.

    A imagem tem a proporção do desenho (até ``ALTURA_MAXIMA_IMAGEM``) e fundo branco.
    Quem chama restaura a visibilidade e a câmera.
    """
    # sem a animação de navegação do FreeCAD (ligada por padrão): com ela, a imagem era gravada
    # no meio do giro para o topo, ainda na vista em que o usuário estava
    parametros = App.ParamGet("User parameter:BaseApp/Preferences/View")
    animacao = parametros.GetBool("UseNavigationAnimations", True)
    parametros.SetBool("UseNavigationAnimations", False)
    try:
        _capturar(doc, view, grupo, caminho)
    finally:
        parametros.SetBool("UseNavigationAnimations", animacao)


def _capturar(doc, view, grupo, caminho):
    dentro = [grupo] + descendentes(grupo)
    nomes = {o.Name for o in dentro}
    for obj in dentro:  # projetos gravados antes: o Sketch voltou branco ao abrir e some no fundo branco
        if getattr(obj, "TypeId", "") == estilo.TIPO_SKETCH:
            estilo.pintar_sketch(obj)
    for obj in doc.Objects:
        if hasattr(obj, "ViewObject") and obj.ViewObject:
            obj.ViewObject.Visibility = obj.Name in nomes
    Gui.updateGui()
    view.viewTop()
    _esperar_a_camera(view)
    Gui.Selection.clearSelection()
    for obj in dentro[1:]:
        try:
            Gui.Selection.addSelection(obj)
        except Exception:
            pass
    try:
        Gui.SendMsgToActiveView("ViewSelection")  # enquadra o que está selecionado
    except Exception:
        view.fitAll()
    Gui.Selection.clearSelection()
    _esperar_a_camera(view)
    tamanho = _caixa_dos_objetos(dentro[1:])
    altura = int(LARGURA_IMAGEM * 0.7)
    if tamanho:
        altura = int(min(ALTURA_MAXIMA_IMAGEM, max(600, LARGURA_IMAGEM * tamanho[1] / tamanho[0])))
    view.saveImage(caminho, LARGURA_IMAGEM, altura, "White")


# --- fonte com os símbolos das fórmulas ------------------------------------------------------------

FONTES = (  # (normal, negrito): a primeira que existir; precisam de ≤ ≥ √ Δ Φ κ Σ π →
    ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
    ("arial.ttf", "arialbd.ttf"),
    ("Arial.ttf", "Arial Bold.ttf"),
    ("segoeui.ttf", "segoeuib.ttf"),
)
SUBSTITUTOS = {"≤": "<=", "≥": ">=", "→": "->", "√": "raiz", "Δ": "Delta ", "Φ": "Fi", "κ": "kappa", "Σ": "soma ",
               "π": "pi", "·": "x", "″": "''", "λ": "lambda", "ρ": "rho", "φ": "fi", "—": "-", "−": "-", "×": "x",
               "²": "2", "Ω": "ohm", "°": " graus"}
_FONTE = None


def _pastas_de_fontes():
    pastas = [os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts"),
              "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/TTF", "/usr/share/fonts/dejavu",
              "/Library/Fonts", "/System/Library/Fonts/Supplemental"]
    try:
        pastas.insert(0, os.path.join(App.getHomePath(), "fonts"))
    except Exception:
        pass
    try:
        import matplotlib
        pastas.append(os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf"))
    except Exception:
        pass
    return pastas


def fonte_do_relatorio():
    """(fonte normal, negrito, com_simbolos): a primeira TrueType de ``FONTES`` registrada no reportlab;
    sem nenhuma, Helvetica, e as fórmulas trocam os símbolos por ``SUBSTITUTOS``."""
    global _FONTE
    if _FONTE is not None:
        return _FONTE
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for normal, negrito in FONTES:
        for pasta in _pastas_de_fontes():
            caminho_n, caminho_b = os.path.join(pasta, normal), os.path.join(pasta, negrito)
            if not os.path.isfile(caminho_n):
                continue
            try:
                pdfmetrics.registerFont(TTFont("CircuitsNormal", caminho_n))
                pdfmetrics.registerFont(TTFont("CircuitsNegrito",
                                               caminho_b if os.path.isfile(caminho_b) else caminho_n))
                _FONTE = ("CircuitsNormal", "CircuitsNegrito", True)
                return _FONTE
            except Exception:
                continue
    _FONTE = ("Helvetica", "Helvetica-Bold", False)
    return _FONTE


def _escapar(texto, com_simbolos=True):
    texto = str(texto).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if not com_simbolos:
        for simbolo, troca in SUBSTITUTOS.items():
            texto = texto.replace(simbolo, troca)
    return texto


# --- documento ---------------------------------------------------------------------------------------

class PDFGenerator:
    """Relatório técnico: memorial descritivo e de cálculo (``core.memorial``), quantitativo de materiais,
    diagramas e vista 3D, com capa, sumário, seções numeradas e cabeçalho/rodapé."""

    COR = "#1f4e79"

    def __init__(self, doc, file_path, opcoes):
        self.doc = doc
        self.file_path = file_path
        self.opcoes = opcoes
        self.fonte, self.negrito, self.com_simbolos = fonte_do_relatorio()
        self.styles = getSampleStyleSheet()
        base = dict(fontName=self.fonte)
        self.styles.add(ParagraphStyle(name='SubTitle', parent=self.styles['Heading2'], spaceAfter=10,
                                       fontName=self.negrito))
        self.estilos = {
            "titulo": ParagraphStyle("CTitulo", parent=self.styles["Heading1"], fontName=self.negrito, fontSize=15,
                                     textColor=colors.HexColor(self.COR), spaceBefore=6, spaceAfter=8,
                                     keepWithNext=1),
            "subtitulo": ParagraphStyle("CSubtitulo", parent=self.styles["Heading3"], fontName=self.negrito,
                                        fontSize=10.5, spaceBefore=8, spaceAfter=4, keepWithNext=1),
            "paragrafo": ParagraphStyle("CParagrafo", parent=self.styles["BodyText"], fontSize=9.5, leading=13,
                                        alignment=4, **base),
            "formula": ParagraphStyle("CFormula", parent=self.styles["BodyText"], fontSize=8.8, leading=12,
                                      leftIndent=10, backColor=colors.HexColor("#f2f5f9"), borderPadding=3,
                                      spaceBefore=1, spaceAfter=3, **base),
            "formula_ruim": ParagraphStyle("CFormulaRuim", parent=self.styles["BodyText"], fontSize=8.8, leading=12,
                                           leftIndent=10, backColor=colors.HexColor("#fdecee"), borderPadding=3,
                                           spaceBefore=1, spaceAfter=3, textColor=colors.HexColor("#b00020"),
                                           **base),
            "aviso": ParagraphStyle("CAviso", parent=self.styles["BodyText"], fontSize=8.8, leading=12,
                                    backColor=colors.HexColor("#fff4e0"), borderPadding=3, spaceAfter=4, **base),
            "lista": ParagraphStyle("CLista", parent=self.styles["BodyText"], fontSize=9.2, leading=12.5,
                                    leftIndent=12, bulletIndent=2, **base),
            "celula": ParagraphStyle("CCelula", fontName=self.fonte, fontSize=7.4, leading=9),
            "celula_ruim": ParagraphStyle("CCelulaRuim", fontName=self.negrito, fontSize=7.4, leading=9,
                                          textColor=colors.HexColor("#b00020")),
            "cabecalho": ParagraphStyle("CCabecalho", fontName=self.negrito, fontSize=7.4, leading=9,
                                        textColor=colors.white),
            "capa": ParagraphStyle("CCapa", fontName=self.negrito, fontSize=24, leading=30, alignment=1,
                                   textColor=colors.HexColor(self.COR)),
            "capa2": ParagraphStyle("CCapa2", fontName=self.fonte, fontSize=13, leading=18, alignment=1),
        }
        self.largura_util = A4[0] - 4 * cm
        self.numero_secao = 0

    # -- blocos do memorial ---------------------------------------------------------------------------

    def _p(self, texto, estilo):
        return Paragraph(_escapar(texto, self.com_simbolos), self.estilos[estilo])

    def _titulo(self, texto):
        self.numero_secao += 1
        paragrafo = self._p(f"{self.numero_secao} {texto}", "titulo")
        paragrafo.secao_do_sumario = True
        return paragrafo

    def _tabela(self, cabecalho, linhas, larguras=None):
        colunas = len(cabecalho)
        pesos = larguras or [1] * colunas
        total = float(sum(pesos))
        largura = [self.largura_util * p / total for p in pesos]
        dados = [[self._p(c, "cabecalho") for c in cabecalho]]
        for linha in linhas:
            estilo_celula = "celula_ruim" if "NÃO ATENDE" in " ".join(str(v) for v in linha) else "celula"
            dados.append([self._p(v, estilo_celula) for v in linha] + [""] * (colunas - len(linha)))
        tabela = Table(dados, colWidths=largura, repeatRows=1)
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(self.COR)),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa7b4")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]
        for i in range(1, len(dados)):
            if i % 2 == 0:
                estilo.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f3f6fa")))
            if "NÃO ATENDE" in " ".join(str(v) for v in linhas[i - 1]):
                estilo.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fdecee")))
        tabela.setStyle(TableStyle(estilo))
        return tabela

    def _blocos(self, blocos):
        story = []
        for bloco in blocos:
            tipo = bloco[0]
            if tipo == "tabela":
                if bloco[2]:
                    story += [self._tabela(bloco[1], bloco[2], bloco[3] if len(bloco) > 3 else None), Spacer(1, 5)]
            elif tipo == "lista":
                story += [Paragraph(_escapar(item, self.com_simbolos), self.estilos["lista"], bulletText="•")
                          for item in bloco[1]]
            elif tipo == "desenho":
                story += [self._desenho(bloco[1]), Spacer(1, 6)]
            elif tipo == "formula" and "NÃO ATENDE" in str(bloco[1]):
                story.append(self._p(bloco[1], "formula_ruim"))
            elif tipo in self.estilos:
                story.append(self._p(bloco[1], tipo))
        return story

    LARGURA_DESENHO = 17.0 * cm
    ALTURA_MAX_DESENHO = 21.0 * cm

    def _desenho(self, desenho):
        """Desenho vetorial (``core.centro_medicao.mural``: mm, y para cima) ajustado à largura da página."""
        from reportlab.graphics.shapes import Circle, Drawing, Group, Line, String
        xmin, ymin, xmax, ymax = desenho["limites"]
        largura, altura = max(1.0, xmax - xmin), max(1.0, ymax - ymin)
        escala = min(self.LARGURA_DESENHO / largura, self.ALTURA_MAX_DESENHO / altura)
        figura = Drawing(largura * escala, altura * escala)
        traco = colors.HexColor("#202124")

        def ponto(x, y):
            return (x - xmin) * escala, (y - ymin) * escala

        for x1, y1, x2, y2 in desenho["linhas"]:
            a, b = ponto(x1, y1)
            c, d = ponto(x2, y2)
            figura.add(Line(a, b, c, d, strokeColor=traco, strokeWidth=0.35))
        for cx, cy, raio in desenho["circulos"]:
            a, b = ponto(cx, cy)
            figura.add(Circle(a, b, raio * escala, strokeColor=traco, strokeWidth=0.35, fillColor=None))
        for x, y, conteudo, altura_texto, angulo in desenho["textos"]:
            a, b = ponto(x, y)
            conteudo = str(conteudo)
            if not self.com_simbolos:
                for simbolo, troca in SUBSTITUTOS.items():
                    conteudo = conteudo.replace(simbolo, troca)
            texto = String(0, 0, conteudo, fontName=self.fonte, fontSize=max(2.0, altura_texto * escala),
                           fillColor=colors.HexColor("#1a3c6e"))
            grupo = Group(texto)
            grupo.translate(a, b)
            if angulo:
                grupo.rotate(angulo)
            figura.add(grupo)
        return figura

    # -- capa, sumário, cabeçalho e rodapé ------------------------------------------------------------

    def _capa(self, projeto):
        story = [Spacer(1, 5 * cm), self._p("Memorial descritivo e de cálculo", "capa"), Spacer(1, 0.4 * cm),
                 self._p("Instalações elétricas", "capa2"), Spacer(1, 1.6 * cm),
                 self._p(projeto.get("projeto", ""), "capa2")]
        for chave, rotulo in (("obra", "Obra"), ("cliente", "Cliente"), ("responsavel", "Responsável técnico"),
                              ("registro", "CREA / CFT"), ("data", "Data")):
            if projeto.get(chave):
                story.append(self._p(f"{rotulo}: {projeto[chave]}", "capa2"))
        return story + [PageBreak()]

    def _pagina(self, canvas, documento):
        canvas.saveState()
        canvas.setFont(self.fonte, 7.5)
        canvas.setFillColor(colors.HexColor("#5b6670"))
        largura, altura = A4
        if documento.page > 1:
            canvas.drawString(2 * cm, altura - 1.25 * cm, _escapar(self._cabecalho, self.com_simbolos)
                              .replace("&amp;", "&"))
            canvas.line(2 * cm, altura - 1.35 * cm, largura - 2 * cm, altura - 1.35 * cm)
            canvas.drawRightString(largura - 2 * cm, 1.2 * cm, f"Página {documento.page}")
            canvas.drawString(2 * cm, 1.2 * cm, "Memorial descritivo e de cálculo — gerado pela bancada Circuits"
                              if self.com_simbolos else "Memorial descritivo e de calculo - bancada Circuits")
        canvas.restoreState()

    # -- documento ------------------------------------------------------------------------------------

    def generate(self):
        from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
        from reportlab.platypus.tableofcontents import TableOfContents

        gerador = self

        class Documento(BaseDocTemplate):
            def afterFlowable(self, flowable):
                if getattr(flowable, "secao_do_sumario", False):
                    self.notify("TOCEntry", (0, flowable.getPlainText(), self.page))

        doc_pdf = Documento(self.file_path, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title="Memorial descritivo e de cálculo")
        quadro = Frame(doc_pdf.leftMargin, doc_pdf.bottomMargin, doc_pdf.width, doc_pdf.height, id="corpo")
        doc_pdf.addPageTemplates([PageTemplate(id="pagina", frames=[quadro], onPage=gerador._pagina)])

        from freecad.Circuits.core import memorial as regras_memorial
        from freecad.Circuits.services import memorial as servico_memorial
        dados = servico_memorial.coletar(self.doc)
        projeto = dados["projeto"]
        if self.opcoes.get("projeto"):
            projeto["projeto"] = self.opcoes["projeto"]
        if self.opcoes.get("autor") and not projeto.get("responsavel"):
            projeto["responsavel"] = self.opcoes["autor"]
        self._cabecalho = " · ".join(t for t in (projeto.get("projeto"), projeto.get("obra")) if t)

        story = self._capa(projeto)
        sumario = TableOfContents()
        sumario.levelStyles = [ParagraphStyle("CSumario", fontName=self.fonte, fontSize=10, leading=15,
                                              leftIndent=10)]
        story += [self._p("Sumário", "titulo"), sumario, PageBreak()]

        if self.opcoes.get("calculos", True):
            for titulo, blocos in regras_memorial.montar(dados):
                story.append(self._titulo(titulo))
                story += self._blocos(blocos)
                story.append(Spacer(1, 6))

        if self.opcoes.get("materiais"):
            story.append(PageBreak())
            story.append(self._titulo("Quantitativo de materiais"))
            linhas = self._get_materiais_table()
            if len(linhas) > 1:
                story.append(self._tabela(linhas[0], linhas[1:], [6, 1, 1.2]))
            else:
                story.append(self._p("Nenhum material encontrado no projeto.", "paragrafo"))

        temporarios = self._imagens(story)
        try:
            doc_pdf.multiBuild(story)  # duas passadas: o sumário recebe as páginas
        finally:
            for caminho in temporarios:
                try:
                    os.remove(caminho)
                except OSError:
                    pass

    def _imagens(self, story):
        """Diagramas (um por página) e vista 3D; devolve os arquivos temporários."""
        view = Gui.ActiveDocument.ActiveView if Gui.ActiveDocument else None
        temporarios = []
        if not view or not (self.opcoes.get("diagramas") or self.opcoes.get("cortes")):
            return temporarios
        vis_state = {obj.Name: obj.ViewObject.Visibility for obj in self.doc.Objects
                     if hasattr(obj, "ViewObject") and obj.ViewObject}
        try:
            camera = view.getCamera()
        except Exception:
            camera = None
        temp_dir = os.path.dirname(os.path.abspath(self.file_path))
        diagramas = listar_diagramas(self.doc)
        dos_diagramas = {o.Name for _, grupo in diagramas for o in [grupo] + descendentes(grupo)}
        try:
            if self.opcoes.get("diagramas"):
                story.append(PageBreak())
                story.append(self._titulo("Diagramas"))
                if not diagramas:
                    story.append(self._p("Nenhum diagrama gerado: use Quadros e documentos > Diagramas.",
                                         "paragrafo"))
                for indice, (titulo, grupo) in enumerate(diagramas):
                    img_path = os.path.join(temp_dir, f"temp_diagrama_{indice}.png")
                    temporarios.append(img_path)
                    try:
                        capturar_diagrama(self.doc, view, grupo, img_path)
                    except Exception as erro:
                        App.Console.PrintWarning(f"Relatório: não foi possível capturar {titulo}: {erro}\n")
                        continue
                    if indice:
                        story.append(PageBreak())
                    story.append(self._p(titulo, "subtitulo"))
                    story.append(Image(img_path, width=17 * cm, height=22 * cm, kind='proportional'))
            if self.opcoes.get("cortes"):
                story.append(PageBreak())
                story.append(self._titulo("Vista 3D"))
                try:
                    for obj in self.doc.Objects:
                        if hasattr(obj, "ViewObject") and obj.ViewObject:
                            obj.ViewObject.Visibility = visivel_no_corte(obj, dos_diagramas)
                    Gui.updateGui()
                    view.viewIsometric()
                    view.fitAll()
                    Gui.updateGui()
                    img_path = os.path.join(temp_dir, "temp_corte.png")
                    temporarios.append(img_path)
                    view.saveImage(img_path, 1600, 1100, "White")
                    story.append(Image(img_path, width=17 * cm, height=12 * cm, kind='proportional'))
                except Exception as erro:  # a vista 3D não impede o resto do relatório
                    App.Console.PrintWarning(f"Relatório: não foi possível capturar a vista 3D: {erro}\n")
                    story.append(self._p("Não foi possível capturar a vista 3D.", "paragrafo"))
        finally:
            for obj in self.doc.Objects:
                if obj.Name in vis_state and hasattr(obj, "ViewObject") and obj.ViewObject:
                    obj.ViewObject.Visibility = vis_state[obj.Name]
            if camera:
                try:
                    view.setCamera(camera)
                except Exception:
                    view.viewTop()
                    view.fitAll()
            Gui.updateGui()
        return temporarios

    def _get_materiais_table(self):
        """Quantitativo de materiais, o mesmo do comando Quantitativos."""
        table_data = [["Item / Especificação", "Unidade", "Quantidade"]]
        for linha in quantitativos.calcular(self.doc):
            nome = f"{linha['item']} - {linha['especificacao']}" if linha["especificacao"] else linha["item"]
            quantidade = linha["quantidade"]
            texto = f"{quantidade:.2f}" if isinstance(quantidade, float) else str(quantidade)
            table_data.append([nome, linha["unidade"], texto])
        return table_data

    def _get_calculos_table(self):
        """Lê planilhas de quadro de distribuição"""
        table_data = [["Identificação", "Tensão", "Fases", "Pot. Instalada", "Demanda"]]
        
        for obj in planilhas.listar_quadros(self.doc):
            dados = planilhas.ler_quadro(obj)
            table_data.append([
                dados["indentificacao_painel"] or obj.Label,
                dados["tensao"] or "-",
                dados["numero_fases"] or "-",
                dados["potencia_instalada"] or "-",
                dados["potencia_demanda"] or "-",
            ])

        return table_data
