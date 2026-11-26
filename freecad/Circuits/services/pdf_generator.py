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


class PDFGenerator:
    def __init__(self, doc, file_path, opcoes):
        self.doc = doc
        self.file_path = file_path
        self.opcoes = opcoes
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(name='SubTitle', parent=self.styles['Heading2'], spaceAfter=10))

    def generate(self):
        doc_pdf = SimpleDocTemplate(
            self.file_path,
            pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm
        )
        
        story = []
        
        # Capa
        projeto = self.opcoes.get("projeto", "Projeto Elétrico")
        autor = self.opcoes.get("autor", "Não especificado")
        if not projeto: projeto = "Projeto Elétrico"
        
        story.append(Paragraph(f"<b>{projeto}</b>", self.styles['Title']))
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(f"Autor: {autor}", self.styles['Normal']))
        story.append(Spacer(1, 2*cm))
        
        # 1. Quantitativo de Materiais
        if self.opcoes.get("materiais"):
            story.append(Paragraph("Quantitativo de Materiais", self.styles['Heading1']))
            table_data = self._get_materiais_table()
            
            if len(table_data) > 1:
                t = Table(table_data, colWidths=[10*cm, 3*cm, 3*cm])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4a86e8")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(t)
            else:
                story.append(Paragraph("Nenhum material encontrado no projeto.", self.styles['Normal']))
            story.append(Spacer(1, 1*cm))
        
        # 2. Cálculos / Planilhas
        if self.opcoes.get("calculos"):
            story.append(PageBreak())
            story.append(Paragraph("Cálculos e Demandas", self.styles['Heading1']))
            calc_data = self._get_calculos_table()
            if len(calc_data) > 1:
                t2 = Table(calc_data)
                t2.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#38761d")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(t2)
            else:
                story.append(Paragraph("Nenhum quadro de cálculo encontrado.", self.styles['Normal']))
            story.append(Spacer(1, 1*cm))
            
        # Para capturar imagens, precisamos manipular a interface gráfica
        view = Gui.ActiveDocument.ActiveView if Gui.ActiveDocument else None
        temporarios = []

        if view and (self.opcoes.get("diagramas") or self.opcoes.get("cortes")):
            # Estado da vista para restaurar no fim
            vis_state = {}
            for obj in self.doc.Objects:
                if hasattr(obj, "ViewObject") and obj.ViewObject:
                    vis_state[obj.Name] = obj.ViewObject.Visibility
            try:
                camera = view.getCamera()
            except Exception:
                camera = None

            temp_dir = os.path.dirname(self.file_path)
            diagramas = listar_diagramas(self.doc)
            dos_diagramas = {o.Name for _, grupo in diagramas for o in [grupo] + descendentes(grupo)}

            # 3. Diagramas: um por página, com a vista enquadrada só nele
            if self.opcoes.get("diagramas"):
                story.append(PageBreak())
                story.append(Paragraph("Diagramas", self.styles['Heading1']))
                if not diagramas:
                    story.append(Paragraph("Nenhum diagrama gerado: use Quadros e documentos > Diagramas.",
                                           self.styles['Normal']))
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
                    story.append(Paragraph(titulo, self.styles['SubTitle']))
                    story.append(Image(img_path, width=17 * cm, height=23 * cm, kind='proportional'))

            # 4. Cortes (Modelo 3D)
            if self.opcoes.get("cortes"):
                story.append(PageBreak())
                story.append(Paragraph("Vistas 3D e Cortes", self.styles['Heading1']))

                try:
                    # Mostrar o modelo, sem os diagramas e sem os Sketches
                    for obj in self.doc.Objects:
                        if hasattr(obj, "ViewObject") and obj.ViewObject:
                            obj.ViewObject.Visibility = visivel_no_corte(obj, dos_diagramas)

                    Gui.updateGui()
                    view.viewIsometric()
                    view.fitAll()
                    Gui.updateGui()

                    img_path = os.path.join(temp_dir, "temp_corte.png")
                    temporarios.append(img_path)
                    view.saveImage(img_path, 1024, 768, "White")
                    story.append(Image(img_path, width=15*cm, height=10*cm, kind='proportional'))
                except Exception as erro:  # a vista 3D não impede o resto do relatório
                    App.Console.PrintWarning(f"Relatório: não foi possível capturar a vista 3D: {erro}\n")
                    story.append(Paragraph("Não foi possível capturar a vista 3D.", self.styles['Normal']))

            # Restaurar a visibilidade e a câmera
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

        # Constrói o PDF
        doc_pdf.build(story)
        
        # Limpar temporários
        for p in temporarios:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

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
