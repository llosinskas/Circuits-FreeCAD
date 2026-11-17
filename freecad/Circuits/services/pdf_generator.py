import os
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.services import planilhas, quantitativos

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
    from reportlab.lib.units import cm
except ImportError:
    pass  # Será tratado no UI se o reportlab não existir

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
        view = Gui.ActiveDocument.ActiveView
        
        if view and (self.opcoes.get("diagramas") or self.opcoes.get("cortes")):
            # Salvar estado de visibilidade
            vis_state = {}
            for obj in self.doc.Objects:
                if hasattr(obj, "ViewObject") and obj.ViewObject:
                    vis_state[obj.Name] = obj.ViewObject.Visibility

            temp_dir = os.path.dirname(self.file_path)
            
            # 3. Diagramas Unifilares
            if self.opcoes.get("diagramas"):
                story.append(PageBreak())
                story.append(Paragraph("Diagramas Unifilares", self.styles['Heading1']))
                
                # Esconder tudo exceto os diagramas
                diagramas_encontrados = False
                for obj in self.doc.Objects:
                    if hasattr(obj, "ViewObject") and obj.ViewObject:
                        if obj.Label.startswith("diagrama"):
                            obj.ViewObject.Visibility = True
                            diagramas_encontrados = True
                        else:
                            obj.ViewObject.Visibility = False
                            
                if diagramas_encontrados:
                    Gui.updateGui()
                    view.fitAll()
                    Gui.updateGui()
                    img_path = os.path.join(temp_dir, "temp_diagrama.png")
                    view.saveImage(img_path, 1024, 768, "Transparent")
                    
                    img = Image(img_path, width=15*cm, height=10*cm, kind='proportional')
                    story.append(img)
                else:
                    story.append(Paragraph("Nenhum diagrama unifilar gerado.", self.styles['Normal']))
                    
                story.append(Spacer(1, 1*cm))

            # 4. Cortes (Modelo 3D)
            if self.opcoes.get("cortes"):
                story.append(PageBreak())
                story.append(Paragraph("Vistas 3D e Cortes", self.styles['Heading1']))
                
                # Mostrar tudo EXCETO diagramas
                for obj in self.doc.Objects:
                    if hasattr(obj, "ViewObject") and obj.ViewObject:
                        if obj.Label.startswith("diagrama"):
                            obj.ViewObject.Visibility = False
                        else:
                            # Tenta focar na arquitetura e eletrodutos/caixas 3D
                            if "Sketch" not in obj.Name or "Feature" in obj.Proxy.__class__.__name__:
                                obj.ViewObject.Visibility = True
                
                Gui.updateGui()
                view.viewIsometric()
                view.fitAll()
                Gui.updateGui()
                
                img_path = os.path.join(temp_dir, "temp_corte.png")
                view.saveImage(img_path, 1024, 768, "Transparent")
                
                img = Image(img_path, width=15*cm, height=10*cm, kind='proportional')
                story.append(img)

            # Restaurar estado original de visibilidade
            for obj in self.doc.Objects:
                if obj.Name in vis_state and hasattr(obj, "ViewObject") and obj.ViewObject:
                    obj.ViewObject.Visibility = vis_state[obj.Name]
            
            # Restaurar View
            view.viewTop()
            view.fitAll()
            Gui.updateGui()

        # Constrói o PDF
        doc_pdf.build(story)
        
        # Limpar temporários
        temp_dir = os.path.dirname(self.file_path)
        for temp_img in ["temp_diagrama.png", "temp_corte.png"]:
            p = os.path.join(temp_dir, temp_img)
            if os.path.exists(p):
                try: os.remove(p)
                except: pass

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
