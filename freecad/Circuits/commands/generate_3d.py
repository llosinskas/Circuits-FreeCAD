import FreeCAD as App
import FreeCADGui as Gui
import Part
import os
import freecad.Circuits as WB

try:
    from PySide2 import QtWidgets
except ImportError:
    try:
        from PySide6 import QtWidgets
    except ImportError:
        from PySide import QtGui as QtWidgets

class Generate3DConduits:
    """Comando para gerar os tubos 3D (Sweeps) a partir dos ConduitPaths."""
    
    def Activated(self):
        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento FreeCAD aberto.")
            return
            
        selected_objs = Gui.Selection.getSelection()
        
        # Retrocompatibilidade se não houver seleção
        if not selected_objs:
            selected_objs = [obj for obj in doc.Objects if hasattr(obj, "Proxy") and getattr(obj.Proxy, "Type", "") == "ConduitPath"]
            
        if not selected_objs:
            QtWidgets.QMessageBox.information(None, "Aviso", "Selecione uma linha (Wire) para gerar o eletroduto 3D.")
            return
            
        tabela_diametros = {
            "1/2": 21.3, "3/4": 26.9, "1": 33.7, "1 1/4": 42.4,
            "1 1/2": 48.3, "2": 60.3, "3": 88.9, "4": 114.3
        }
        
        tabela_cores = {
            "Amarelo": (1.0, 0.8, 0.0), "Preto": (0.1, 0.1, 0.1), "Cinza": (0.6, 0.6, 0.6),
            "Vermelho": (0.8, 0.1, 0.1), "Laranja": (1.0, 0.5, 0.0), "Azul": (0.1, 0.3, 0.8),
            "Branco": (0.95, 0.95, 0.95), "Verde": (0.1, 0.7, 0.2)
        }
            
        # --- PASSO 1: Injetar propriedades e atualizar curvas base (Fillet nativo) ---
        for path_obj in selected_objs:
            if not hasattr(path_obj, "Altura3D"):
                path_obj.addProperty("App::PropertyDistance", "Altura3D", "Conduit", "Altura em Z do eletroduto").Altura3D = 2800.0
                
            if not hasattr(path_obj, "Diametro"):
                path_obj.addProperty("App::PropertyEnumeration", "Diametro", "Conduit", "Tamanho nominal do eletroduto")
                path_obj.Diametro = ["1/2", "3/4", "1", "1 1/4", "1 1/2", "2", "3", "4"]
                path_obj.Diametro = "3/4"
                
            if not hasattr(path_obj, "Tipo"):
                path_obj.addProperty("App::PropertyEnumeration", "Tipo", "Conduit", "Flexível ou Rígido")
                path_obj.Tipo = ["Flexível", "Rígido"]
                path_obj.Tipo = "Flexível"
                
            if not hasattr(path_obj, "Cor"):
                path_obj.addProperty("App::PropertyEnumeration", "Cor", "Conduit", "Cor do tubo")
                path_obj.Cor = list(tabela_cores.keys())
                path_obj.Cor = "Amarelo"
            
            # Se for Draft Wire, aplica Fillet automaticamente
            if hasattr(path_obj, "FilletRadius"):
                diam_ext = tabela_diametros.get(path_obj.Diametro, 26.9)
                raio = diam_ext / 2.0
                if path_obj.Tipo == "Flexível":
                    path_obj.FilletRadius = raio * 15 # Curva suave
                else:
                    path_obj.FilletRadius = 0.0 # Rígido (quina viva)
                    
        # Aplica as mudanças nos Wires antes de ler as curvas
        doc.recompute()
        
        # --- PASSO 2: Geração da Varredura 3D (Pipe) ---
        count = 0
        tomadas = [obj for obj in doc.Objects if hasattr(obj, 'tipo') and getattr(obj, 'tipo') == "tomada"]
        
        for path_obj in selected_objs:
            if not hasattr(path_obj, "Shape") or path_obj.Shape.isNull() or len(path_obj.Shape.Edges) == 0:
                continue
                
            diam_ext = tabela_diametros.get(path_obj.Diametro, 26.9)
            raio = diam_ext / 2.0
            cor_rgb = tabela_cores.get(path_obj.Cor, (0.7, 0.7, 0.7))
            
            # Copia a forma para não alterar o objeto base
            elevated_wire = path_obj.Shape.copy()
            if elevated_wire.ShapeType == "Edge":
                elevated_wire = Part.Wire([elevated_wire])
            elif elevated_wire.ShapeType == "Compound" and len(elevated_wire.Wires) > 0:
                elevated_wire = elevated_wire.Wires[0]
            elif elevated_wire.ShapeType != "Wire":
                try:
                    elevated_wire = Part.Wire(elevated_wire.Edges)
                except Exception as e:
                    App.Console.PrintWarning(f"Não foi possível converter a forma de {path_obj.Name} em Wire: {e}\n")
                    continue
                
            # Eleva o fio para a Altura3D
            z_atual = elevated_wire.Vertexes[0].Point.z
            z_offset = path_obj.Altura3D.Value - z_atual
            if abs(z_offset) > 1e-4:
                elevated_wire.translate(App.Vector(0, 0, z_offset))
            
            first_edge = elevated_wire.Edges[0]
            if first_edge.Length < 1e-5:
                continue
                
            v_start = first_edge.valueAt(first_edge.FirstParameter)
            v_dir = first_edge.tangentAt(first_edge.FirstParameter)
            
            circle = Part.makeCircle(raio, v_start, v_dir)
            profile_wire = Part.Wire([circle])
            
            old_pipe_name = f"{path_obj.Name}_3D"
            if doc.getObject(old_pipe_name):
                doc.removeObject(old_pipe_name)
            
            try:
                pipe = Part.Wire(elevated_wire).makePipeShell([profile_wire], True, True)
                pipes_list = [pipe]
                
                # --- Verifica se deve descer/subir para alguma tomada ---
                pts_to_check = path_obj.Points if hasattr(path_obj, "Points") else [v.Point for v in path_obj.Shape.Vertexes]
                matched_tomadas = set()
                
                for pt in pts_to_check:
                    vx, vy = pt.x, pt.y
                    for t in tomadas:
                        if t.Name in matched_tomadas:
                            continue
                        tx, ty = t.Placement.Base.x, t.Placement.Base.y
                        
                        # Se as coordenadas X e Y baterem (com 10mm de tolerância)
                        if (App.Vector(vx, vy, 0) - App.Vector(tx, ty, 0)).Length < 10.0:
                            matched_tomadas.add(t.Name)
                            
                            z_tomada = float(t.altura_piso) if hasattr(t, "altura_piso") else 0.0
                            z_teto = path_obj.Altura3D.Value
                            
                            p_top = App.Vector(tx, ty, z_teto)
                            p_bottom = App.Vector(tx, ty, z_tomada)
                            
                            if (p_top - p_bottom).Length > 1e-2:
                                drop_edge = Part.makeLine(p_top, p_bottom)
                                drop_wire = Part.Wire([drop_edge])
                                
                                # Garante que o círculo de perfil aponte na direção da linha
                                v_drop = p_bottom - p_top
                                v_drop.normalize()
                                c_drop = Part.makeCircle(raio, p_top, v_drop)
                                p_drop = Part.Wire([c_drop])
                                
                                try:
                                    pipe_drop = drop_wire.makePipe(p_drop)
                                    pipes_list.append(pipe_drop)
                                except Exception as e:
                                    App.Console.PrintWarning(f"Falha ao gerar descida para {t.Name}: {e}\n")
                
                # Combina tudo em um único objeto (Compound)
                if len(pipes_list) > 1:
                    final_shape = Part.makeCompound(pipes_list)
                else:
                    final_shape = pipes_list[0]
                
                pipe_obj = doc.addObject("Part::Feature", old_pipe_name)
                pipe_obj.Shape = final_shape
                pipe_obj.Label = f"Eletroduto 3D ({path_obj.Diametro})"
                pipe_obj.ViewObject.ShapeColor = cor_rgb
                count += 1
            except Exception as e:
                App.Console.PrintError(f"Erro ao gerar tubo 3D para {path_obj.Name}: {e}\n")
                
        doc.recompute()
        App.Console.PrintMessage(f"{count} eletrodutos 3D gerados com sucesso.\n")
        
    def IsActive(self):
        return True
        
    def GetResources(self):
        return {
            'Pixmap': os.path.join(WB.ICON_PATH, 'conduite.svg'), # Pode trocar por um icone de tubo 3D depois
            'MenuText': 'Gerar Eletrodutos 3D',
            'ToolTip': 'Converte caminhos de eletrodutos em tubos 3D'
        }

Gui.addCommand("Generate3DConduits", Generate3DConduits())


class Generate3DSwitches:
    """Comando para gerar caixas 3D a partir dos Interruptores, Pontos de Iluminação e Tomadas.
    
    Lê as propriedades CaixaAltura, CaixaLargura, CaixaProfundidade e Altura3D
    de cada objeto Switch/Lighting/Outlet posicionado na planta e gera um Part::Feature
    (Box) na posição X,Y do símbolo 2D, elevado em Z conforme a Altura3D.
    """
    
    def Activated(self):
        doc = App.activeDocument()
        if not doc:
            QtWidgets.QMessageBox.warning(None, "Erro", "Nenhum documento FreeCAD aberto.")
            return
        
        # Coleta objetos Switch, Lighting e Outlet (FeaturePython)
        targets = []
        for obj in doc.Objects:
            if hasattr(obj, "Proxy") and hasattr(obj.Proxy, "Type"):
                if obj.Proxy.Type in ("Switch", "Lighting", "Outlet"):
                    targets.append(obj)
        
        # Coleta tomadas Sketch (criadas pelo Tugs / ComponentEletric)
        sketch_tomadas = []
        for obj in doc.Objects:
            if hasattr(obj, "tipo") and getattr(obj, "tipo", "") == "tomada":
                # Evita duplicatas se já foi coletado como FeaturePython
                if obj not in targets:
                    sketch_tomadas.append(obj)
        
        all_targets = targets + sketch_tomadas
        
        if not all_targets:
            QtWidgets.QMessageBox.information(
                None, "Aviso",
                "Nenhum interruptor, ponto de iluminação ou tomada encontrado no documento.\n"
                "Insira componentes primeiro usando os botões correspondentes."
            )
            return
        
        count = 0
        
        # --- Processa FeaturePython (Switch, Lighting, Outlet) ---
        for obj in targets:
            try:
                cx = obj.CaixaLargura.Value if hasattr(obj.CaixaLargura, "Value") else float(obj.CaixaLargura)
                cy = obj.CaixaProfundidade.Value if hasattr(obj.CaixaProfundidade, "Value") else float(obj.CaixaProfundidade)
                cz = obj.CaixaAltura.Value if hasattr(obj.CaixaAltura, "Value") else float(obj.CaixaAltura)
                alt = obj.Altura3D.Value if hasattr(obj.Altura3D, "Value") else float(obj.Altura3D)
                
                if cx <= 0 or cy <= 0 or cz <= 0:
                    App.Console.PrintWarning(f"Dimensões inválidas para {obj.Label}, ignorando.\n")
                    continue
                
                pos = obj.Placement.Base
                x = pos.x - cx / 2.0
                y = pos.y - cy / 2.0
                z = alt - cz / 2.0
                
                obj3d_name = f"{obj.Name}_3D"
                old = doc.getObject(obj3d_name)
                if old:
                    doc.removeObject(obj3d_name)
                
                box = Part.makeBox(cx, cy, cz, App.Vector(x, y, z))
                feat = doc.addObject("Part::Feature", obj3d_name)
                feat.Shape = box
                
                tipo = obj.Proxy.Type
                if tipo == "Switch":
                    feat.Label = f"Caixa Interruptor ({obj.Label})"
                    feat.ViewObject.ShapeColor = (0.9, 0.85, 0.7)  # Bege
                elif tipo == "Outlet":
                    feat.Label = f"Caixa Tomada ({obj.Label})"
                    feat.ViewObject.ShapeColor = (0.7, 0.85, 0.95)  # Azul claro
                else:
                    feat.Label = f"Caixa Iluminação ({obj.Label})"
                    feat.ViewObject.ShapeColor = (1.0, 0.95, 0.6)  # Amarelo claro
                
                feat.ViewObject.Transparency = 30
                count += 1
                
            except Exception as e:
                App.Console.PrintError(f"Erro ao gerar 3D para {obj.Label}: {e}\n")
        
        # --- Processa tomadas Sketch (Tugs / ComponentEletric) ---
        for obj in sketch_tomadas:
            try:
                # Lê dimensões da caixa (se disponíveis, senão usa padrão)
                cx = float(getattr(obj, "CaixaLargura", 60.0))
                cy = float(getattr(obj, "CaixaProfundidade", 40.0))
                cz = float(getattr(obj, "CaixaAltura", 100.0))
                alt = float(getattr(obj, "altura_piso", 30.0))
                
                if cx <= 0 or cy <= 0 or cz <= 0:
                    App.Console.PrintWarning(f"Dimensões inválidas para {obj.Label}, ignorando.\n")
                    continue
                
                pos = obj.Placement.Base
                x = pos.x - cx / 2.0
                y = pos.y - cy / 2.0
                z = alt - cz / 2.0
                
                obj3d_name = f"{obj.Name}_3D"
                old = doc.getObject(obj3d_name)
                if old:
                    doc.removeObject(obj3d_name)
                
                box = Part.makeBox(cx, cy, cz, App.Vector(x, y, z))
                feat = doc.addObject("Part::Feature", obj3d_name)
                feat.Shape = box
                feat.Label = f"Caixa Tomada ({obj.Label})"
                feat.ViewObject.ShapeColor = (0.7, 0.85, 0.95)  # Azul claro
                feat.ViewObject.Transparency = 30
                count += 1
                
            except Exception as e:
                App.Console.PrintError(f"Erro ao gerar 3D para {obj.Label}: {e}\n")
        
        doc.recompute()
        App.Console.PrintMessage(f"{count} caixa(s) 3D gerada(s) com sucesso.\n")
    
    def IsActive(self):
        return True
    
    def GetResources(self):
        return {
            'Pixmap': os.path.join(WB.ICON_PATH, 'gerar3d_switch.svg'),
            'MenuText': 'Gerar Caixas 3D (Interruptores/Tomadas/Iluminação)',
            'ToolTip': 'Gera caixas 3D a partir das medidas dos interruptores, tomadas e pontos de iluminação'
        }


Gui.addCommand("Generate3DSwitches", Generate3DSwitches())
