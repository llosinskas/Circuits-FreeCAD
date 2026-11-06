"""
Gerenciador de inserção de componentes FreeCAD.
Controla o fluxo de seleção e posicionamento de componentes no documento.
"""

import os
import re
import traceback
from typing import Optional, Callable, Any

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.qt import QtCore, QtGui, QtWidgets

from .ComponentSelectorDialog import ComponentSelectorDialog


class ComponentInserter:
    """Gerenciador de inserção de componentes no documento FreeCAD."""
    
    def __init__(
        self, 
        components_folder: str,
        on_component_loaded: Optional[Callable[[str, Any], None]] = None,
        parent: Optional[QtWidgets.QWidget] = None
    ):
        """Inicializa o gerenciador."""
        self.components_folder = components_folder
        self.on_component_loaded = on_component_loaded
        self.parent = parent
        self.loaded_component = None
        
    def insert_component(self) -> bool:
        """Abre o diálogo de seleção e insere o componente."""
        # Valida documento ativo
        if not App.activeDocument():
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Erro",
                "Nenhum documento FreeCAD aberto.\nCrie ou abra um projeto primeiro."
            )
            return False
        
        # Abre diálogo de seleção
        dialog = ComponentSelectorDialog(
            self.components_folder,
            title="Selecionar Componente",
            parent=self.parent
        )
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected = dialog.get_selected_component()
            if selected:
                return self.load_and_insert_component(selected)
        
        return False
    
    def load_and_insert_component(self, filepath: str) -> bool:
        """Carrega e insere um componente específico (cópia via mergeProject)."""
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
            
            doc = App.activeDocument()
            
            # Abre o componente em um documento temporário
            component_doc = App.open(filepath)
            
            if not component_doc:
                raise RuntimeError(f"Falha ao abrir: {filepath}")
            
            if not component_doc.Objects:
                App.closeDocument(component_doc.Name)
                raise RuntimeError("Nenhum objeto encontrado no componente")
            
            # Usa mergeProject para importar TODOS os objetos com estrutura completa
            App.setActiveDocument(doc.Name)
            doc.mergeProject(filepath)
            
            # Salva label do primeiro objeto para referência
            component_label = component_doc.Objects[0].Label if component_doc.Objects else "Componente"
            self.loaded_component = component_label
            
            # Fecha documento temporário
            App.closeDocument(component_doc.Name)
            
            # Recomputa
            doc.recompute()
            
            # Callback - passa o último objeto adicionado ao doc
            if self.on_component_loaded:
                last_obj = doc.Objects[-1] if doc.Objects else None
                self.on_component_loaded(filepath, last_obj)
            
            return True
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.parent,
                "Erro ao Inserir Componente",
                f"Falha ao inserir componente:\n\n{str(e)}"
            )
            return False

    def _sanitize_fc_name(self, name: str) -> str:
        """Sanitiza um nome para uso como nome interno no FreeCAD.
        
        FreeCAD exige nomes internos alfanuméricos com underscores,
        sem começar com dígito.
        """
        safe = re.sub(r'[^A-Za-z0-9_]', '_', name)
        if safe and safe[0].isdigit():
            safe = '_' + safe
        if not safe:
            safe = 'Component'
        return safe

    def _find_open_document(self, filepath: str):
        """Verifica se um documento já está aberto pelo filepath."""
        # Normaliza o caminho para comparação
        norm_path = os.path.normpath(filepath)
        for doc in App.listDocuments().values():
            if os.path.normpath(doc.FileName) == norm_path:
                return doc
        return None

    def load_and_insert_as_link(self, filepath: str) -> bool:
        """Insere componente como App::Link (referência) dentro de uma pasta.
        
        Ao invés de copiar os objetos com mergeProject, abre o documento
        fonte e cria Links para cada objeto raiz, organizando tudo dentro
        de um App::DocumentObjectGroup.
        """
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
            
            doc = App.activeDocument()
            doc_name = doc.Name
            
            # App::Link para documento externo exige que o documento atual esteja salvo
            if not doc.FileName:
                QtWidgets.QMessageBox.warning(
                    self.parent,
                    "Documento não salvo",
                    "Para inserir um componente como Link (referência), o projeto atual precisa ser salvo primeiro.\n\nPor favor, salve seu documento e tente novamente."
                )
                return False
            
            # Nome base do componente (sem extensão)
            component_basename = os.path.splitext(os.path.basename(filepath))[0]
            safe_name = self._sanitize_fc_name(component_basename)
            
            # Verifica se o documento já está aberto; se não, abre
            component_doc = self._find_open_document(filepath)
            if component_doc is None:
                component_doc = App.open(filepath)
            
            if not component_doc:
                raise RuntimeError(f"Falha ao abrir: {filepath}")
            
            if not component_doc.Objects:
                raise RuntimeError("Nenhum objeto encontrado no componente")
            
            # Volta o foco para o documento ativo
            App.setActiveDocument(doc_name)
            Gui.setActiveDocument(doc_name)
            
            # Cria container principal como App::Part para podermos mover tudo junto
            folder = doc.addObject("App::Part", safe_name)
            folder.Label = component_basename
            
            # Identifica objetos raiz (que não são filhos de nenhum outro)
            child_set = set()
            for obj in component_doc.Objects:
                if hasattr(obj, 'Group'):
                    for child in obj.Group:
                        child_set.add(child.Name)
            
            root_objects = [
                obj for obj in component_doc.Objects
                if obj.Name not in child_set
            ]
            
            # Se não encontrou raízes, linka todos os objetos
            if not root_objects:
                root_objects = component_doc.Objects
            
            App.Console.PrintMessage(
                f"Inserindo {len(root_objects)} objeto(s) raiz como link de '{component_basename}'...\n"
            )
            
            # Função recursiva para processar grupos
            def _process_object(obj_to_link, parent_group, prefix):
                if obj_to_link.TypeId == 'App::DocumentObjectGroup':
                    # Recria o grupo localmente
                    local_group_name = self._sanitize_fc_name(f"{prefix}_{obj_to_link.Label}")
                    local_group = doc.addObject("App::DocumentObjectGroup", local_group_name)
                    local_group.Label = obj_to_link.Label
                    parent_group.addObject(local_group)
                    
                    # Processa recursivamente os filhos
                    if hasattr(obj_to_link, 'Group'):
                        for child in obj_to_link.Group:
                            _process_object(child, local_group, prefix)
                else:
                    # Cria link real para peças/features
                    link_internal = self._sanitize_fc_name(f"{prefix}_{obj_to_link.Label}")
                    link = doc.addObject("App::Link", link_internal)
                    link.Label = obj_to_link.Label
                    link.LinkedObject = obj_to_link
                    parent_group.addObject(link)

            for obj in root_objects:
                _process_object(obj, folder, safe_name)
            
            self.loaded_component = component_basename
            
            # Recomputa
            doc.recompute()
            
            App.Console.PrintMessage(
                f"Componente '{component_basename}' inserido como link com sucesso.\n"
            )
            
            # Retornamos a pasta/part criada para ser manipulada
            if self.on_component_loaded:
                self.on_component_loaded(filepath, folder)
            
            # IMPORTANTE: retorna o objeto root para possibilitar o posicionamento interativo
            return folder
            
        except Exception as e:
            App.Console.PrintError(f"Erro ao inserir link: {str(e)}\n")
            App.Console.PrintError(traceback.format_exc() + "\n")
            QtWidgets.QMessageBox.critical(
                self.parent,
                "Erro ao Inserir Componente (Link)",
                f"Falha ao inserir componente como link:\n\n{str(e)}"
            )
            return None

    def insert_component_as_link(self) -> bool:
        """Abre o diálogo de seleção e insere o componente como link."""
        if not App.activeDocument():
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Erro",
                "Nenhum documento FreeCAD aberto.\nCrie ou abra um projeto primeiro."
            )
            return False
        
        dialog = ComponentSelectorDialog(
            self.components_folder,
            title="Selecionar Componente (Link)",
            parent=self.parent
        )
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected = dialog.get_selected_component()
            if selected:
                return self.load_and_insert_as_link(selected) is not None
        
        return False

    def insert_component_as_link_with_placement(self) -> bool:
        """Insere como link e aguarda o clique do usuário para definir a posição."""
        if not App.activeDocument():
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Erro",
                "Nenhum documento FreeCAD aberto.\nCrie ou abra um projeto primeiro."
            )
            return False
            
        dialog = ComponentSelectorDialog(
            self.components_folder,
            title="Selecionar Componente e Posicionar",
            parent=self.parent
        )
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected = dialog.get_selected_component()
            if selected:
                obj = self.load_and_insert_as_link(selected)
                if obj:
                    # Inicia modo de posicionamento interativo
                    mode = ComponentInsertionMode(obj)
                    mode.start()
                    return True
                    
        return False
    
    def _get_main_component_object(self, doc):
        """Identifica o objeto principal do componente."""
        for obj in doc.Objects:
            if obj.TypeId == 'App::DocumentObjectGroup':
                if obj.Group: 
                    return obj
        
        for obj in doc.Objects:
            if hasattr(obj, 'Shape') or obj.TypeId in [
                'App::DocumentObjectGroup',
                'Part::FeaturePython',
                'Part::Feature'
            ]:
                return obj
        
        return doc.Objects[0] if doc.Objects else None
    
    def insert_component_with_placement(self, filepath: str) -> bool:
        """Insere componente (cópia) permitindo ajustar a posição com o mouse."""
        if not self.load_and_insert_component(filepath):
            return False
        return True
    
    def insert_multiple_components(self, filepaths: list) -> int:
        """Insere múltiplos componentes."""
        count = 0
        for filepath in filepaths:
            if self.load_and_insert_component(filepath):
                count += 1
        return count


class ComponentInsertionMode:
    """Modo interativo para inserção de componentes com o cursor do mouse."""
    
    _active_instance = None  # Mantém a referência viva contra o Garbage Collector do Python
    
    def __init__(self, obj):
        self.obj = obj
        self.is_active = False
        self.view = Gui.ActiveDocument.ActiveView
        self.cb_mouse = None
        self.cb_move = None
        self.cb_key = None
        
    def start(self):
        if not self.view:
            return
        
        # Previne que o Python destrua esta classe enquanto os callbacks rodam
        ComponentInsertionMode._active_instance = self
        
        self.is_active = True
        
        # Callbacks para capturar eventos 3D
        self.cb_mouse = self.view.addEventCallback("SoMouseButtonEvent", self.on_mouse)
        self.cb_move = self.view.addEventCallback("SoLocation2Event", self.on_move)
        self.cb_key = self.view.addEventCallback("SoKeyboardEvent", self.on_key)
        
        # Feedback no console
        App.Console.PrintMessage("Modo de Inserção Ativo: Mova o cursor para posicionar e CLIQUE para fixar. ESC para cancelar.\n")
        
    def stop(self):
        self.is_active = False
        if self.view:
            if self.cb_mouse: self.view.removeEventCallback("SoMouseButtonEvent", self.cb_mouse)
            if self.cb_move: self.view.removeEventCallback("SoLocation2Event", self.cb_move)
            if self.cb_key: self.view.removeEventCallback("SoKeyboardEvent", self.cb_key)
            
        ComponentInsertionMode._active_instance = None
            
    def on_move(self, info):
        """Atualiza a posição do objeto baseado no mouse."""
        if not self.is_active or not self.obj or not hasattr(self.obj, 'Placement'):
            return
            
        x, y = info["Position"]
        pnt = self.view.getPoint(x, y)
        if pnt:
            # No FreeCAD, precisamos ler, alterar e reatribuir o Placement
            pl = self.obj.Placement
            pl.Base = pnt
            self.obj.Placement = pl
            
            # Força a atualização da interface visual sem recomputar todo o documento
            self.obj.touch()
            self.view.redraw()
            
    def on_mouse(self, info):
        """Fixa o objeto ao clicar com o botão esquerdo."""
        if info["State"] == "DOWN" and info["Button"] == "BUTTON1":
            App.Console.PrintMessage("Posição fixada.\n")
            self.stop()
            # Registra no undo/redo após a colocação final
            App.ActiveDocument.recompute()
            
    def on_key(self, info):
        """Cancela a inserção e deleta o objeto se pressionar ESC."""
        if info["State"] == "DOWN" and info["Key"] == "ESCAPE":
            App.Console.PrintMessage("Inserção cancelada.\n")
            self.stop()
            if self.obj:
                App.ActiveDocument.removeObject(self.obj.Name)
                App.ActiveDocument.recompute()
