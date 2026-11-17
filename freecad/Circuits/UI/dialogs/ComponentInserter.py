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

from freecad.Circuits.core import alinhamento
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


def _criar_filtro_de_teclas(modo):
    """Filtro do Qt que entrega R, Shift+R, Espaço, A, L e ESC ao modo de inserção.

    Sem ele, o Qt trata essas teclas como início de um atalho (o Draft usa
    "R, O" e "R, E", a bancada "A, L", o FreeCAD Espaço para mostrar/ocultar) e
    elas nunca chegam à vista 3D. Enquanto um campo de texto tem o foco, as
    teclas seguem para ele normalmente.
    """
    Qt, QEvent = QtCore.Qt, QtCore.QEvent
    teclas = {Qt.Key_R: "R", Qt.Key_A: "A", Qt.Key_L: "L", Qt.Key_Space: "SPACE", Qt.Key_Escape: "ESCAPE"}
    campos = tuple(getattr(QtWidgets, nome) for nome in ("QLineEdit", "QAbstractSpinBox", "QTextEdit", "QPlainTextEdit")
                   if hasattr(QtWidgets, nome))

    class FiltroDeTeclas(QtCore.QObject):
        def eventFilter(self, alvo, evento):
            try:
                tipo = evento.type()
                if tipo not in (QEvent.ShortcutOverride, QEvent.KeyPress) or not modo.is_active:
                    return False
                nome = teclas.get(evento.key())
                if nome is None or isinstance(QtWidgets.QApplication.focusWidget(), campos):
                    return False
                if tipo == QEvent.ShortcutOverride:
                    evento.accept()  # impede o atalho; o KeyPress vem em seguida
                    return True
                if not evento.isAutoRepeat():
                    modo.tratar_tecla(nome, bool(evento.modifiers() & Qt.ShiftModifier))
                return True
            except Exception:
                return False

    return FiltroDeTeclas()


class ComponentInsertionMode:
    """Modo interativo para posicionar um objeto com o cursor do mouse.

    Teclas durante a inserção:
        clique   fixa o objeto
        R        gira 90° em torno de Z (Shift+R gira 45°); a rotação vale
                 para os próximos objetos da mesma sequência
        Espaço   alinha com o símbolo mais próximo: trava em um eixo, depois no
                 outro, depois solta (a tecla A faz o mesmo)
        L        liga ou desliga o alinhamento automático com os símbolos vizinhos
        ESC      cancela e apaga o objeto
    """

    _active_instance = None  # Mantém a referência viva contra o Garbage Collector do Python
    _trava_da_sequencia = None  # trava herdada pelo próximo objeto de uma inserção em sequência
    _rotacao_da_sequencia = None  # rotação herdada pelo próximo objeto de uma inserção em sequência
    TOLERANCIA_PIXELS = 10  # alcance do alinhamento automático, em pixels da tela

    def __init__(self, obj, ao_fixar=None, plano_z0=False, referencias=None, cota=None):
        """
        Args:
            obj: objeto que acompanha o cursor.
            ao_fixar: função chamada depois do clique que fixa o objeto
                (usada para inserir vários pontos em sequência).
            plano_z0: mantém o objeto no plano Z=0, para desenho em planta.
            cota: mantém o objeto nesta cota Z [mm], a do pavimento; tem
                prioridade sobre ``plano_z0``.
            referencias: lista de (x, y) dos símbolos já colocados, usada para
                alinhar. None desliga o alinhamento.
        """
        self.obj = obj
        self.ao_fixar = ao_fixar
        self.plano_z0 = plano_z0
        self.cota = cota
        self.referencias = list(referencias) if referencias else []
        self.automatico = True
        self.trava = ComponentInsertionMode._trava_da_sequencia if ao_fixar else None
        self._travas = []
        self._ultimo_ponto = (0.0, 0.0)
        self.is_active = False
        self.view = Gui.ActiveDocument.ActiveView
        self.cb_mouse = None
        self.cb_move = None
        self.cb_key = None
        self._filtro = None
        rotacao = ComponentInsertionMode._rotacao_da_sequencia if ao_fixar else None
        if rotacao is not None and hasattr(obj, "Placement"):
            posicao = obj.Placement
            posicao.Rotation = rotacao
            obj.Placement = posicao

    def _instalar_filtro(self):
        try:
            self._filtro = _criar_filtro_de_teclas(self)
            QtWidgets.QApplication.instance().installEventFilter(self._filtro)
        except Exception:
            self._filtro = None  # sem Qt (testes): as teclas chegam pela vista 3D

    def _remover_filtro(self):
        if self._filtro is None:
            return
        try:
            QtWidgets.QApplication.instance().removeEventFilter(self._filtro)
        except Exception:
            pass
        self._filtro = None

    def start(self):
        if not self.view:
            return

        # Outro comando de inserção ainda ativo: encerra o anterior antes de começar.
        anterior = ComponentInsertionMode._active_instance
        if anterior is not None and anterior is not self:
            anterior.cancelar()

        # Previne que o Python destrua esta classe enquanto os callbacks rodam
        ComponentInsertionMode._active_instance = self
        self.is_active = True
        # Com algo selecionado, a tecla Espaço do FreeCAD alternaria a visibilidade.
        Gui.Selection.clearSelection()

        self.cb_mouse = self.view.addEventCallback("SoMouseButtonEvent", self.on_mouse)
        self.cb_move = self.view.addEventCallback("SoLocation2Event", self.on_move)
        self.cb_key = self.view.addEventCallback("SoKeyboardEvent", self.on_key)
        self._instalar_filtro()

        self._avisar(
            "Clique fixa | R gira 90° (Shift+R 45°) | Espaço alinha com o símbolo vizinho | "
            "L alinhamento automático | ESC encerra"
        )

    def stop(self):
        self.is_active = False
        self._remover_filtro()
        if self.view:
            if self.cb_mouse:
                self.view.removeEventCallback("SoMouseButtonEvent", self.cb_mouse)
            if self.cb_move:
                self.view.removeEventCallback("SoLocation2Event", self.cb_move)
            if self.cb_key:
                self.view.removeEventCallback("SoKeyboardEvent", self.cb_key)

        ComponentInsertionMode._active_instance = None

    @staticmethod
    def _avisar(texto):
        """Mostra a mensagem na barra de status e no painel de relatório."""
        App.Console.PrintMessage(texto + "\n")
        try:
            Gui.getMainWindow().statusBar().showMessage(texto, 8000)
        except Exception:
            pass  # sem janela principal (testes): o painel de relatório basta

    def _tolerancia(self, x, y):
        """Comprimento, no desenho, de ``TOLERANCIA_PIXELS`` pixels da tela."""
        try:
            a = self.view.getPoint(x, y)
            b = self.view.getPoint(x + self.TOLERANCIA_PIXELS, y)
            return (b - a).Length
        except Exception:
            return 0.0

    def _posicionar(self, x, y):
        """Leva o objeto ao ponto da tela, aplicando plano, trava e alinhamento."""
        pnt = self.view.getPoint(x, y)
        if not pnt:
            return
        if self.cota is not None:
            pnt.z = float(self.cota)
        elif self.plano_z0:
            pnt.z = 0.0
        self._ultimo_ponto = (pnt.x, pnt.y)
        self._ultima_tela = (x, y)

        if self.trava:
            pnt.x, pnt.y = alinhamento.aplicar_trava((pnt.x, pnt.y), self.trava)
        elif self.automatico and self.referencias:
            pnt.x, pnt.y, _, _ = alinhamento.atrair((pnt.x, pnt.y), self.referencias, self._tolerancia(x, y))

        # No FreeCAD, precisamos ler, alterar e reatribuir o Placement
        pl = self.obj.Placement
        pl.Base = pnt
        self.obj.Placement = pl
        # Força a atualização da interface visual sem recomputar todo o documento
        self.obj.touch()
        self.view.redraw()

    def on_move(self, info):
        """Atualiza a posição do objeto baseado no mouse."""
        if not self.is_active or not self.obj or not hasattr(self.obj, 'Placement'):
            return
        x, y = info["Position"]
        self._posicionar(x, y)

    def on_mouse(self, info):
        """Fixa o objeto ao clicar com o botão esquerdo."""
        if info["State"] == "DOWN" and info["Button"] == "BUTTON1":
            App.Console.PrintMessage("Posição fixada.\n")
            self.stop()
            # Registra no undo/redo após a colocação final
            App.ActiveDocument.recompute()
            if self.ao_fixar:
                ComponentInsertionMode._trava_da_sequencia = self.trava
                ComponentInsertionMode._rotacao_da_sequencia = getattr(self.obj.Placement, "Rotation", None)
                self.ao_fixar()

    def _alternar_trava(self):
        """Espaço: trava no eixo mais próximo do vizinho, depois no outro, depois solta."""
        if not self.referencias:
            self._avisar("Não há outro símbolo na planta para alinhar.")
            return
        if self.trava is None:
            self._travas = alinhamento.travas_possiveis(self._ultimo_ponto, self.referencias)
            self.trava = self._travas[0]
        elif self._travas and self.trava == self._travas[0]:
            self.trava = self._travas[1]
        else:
            self.trava = None
        if self.trava is None:
            self._avisar("Alinhamento solto.")
        else:
            direcao = "vertical" if self.trava[0] == "x" else "horizontal"
            self._avisar(f"Alinhado na {direcao} com o símbolo vizinho. Espaço troca o eixo ou solta.")
        if hasattr(self, "_ultima_tela"):
            self._posicionar(*self._ultima_tela)

    def on_key(self, info):
        """Teclas pela vista 3D (quando o filtro do Qt não as pegou antes)."""
        if info["State"] != "DOWN":
            return
        self.tratar_tecla(str(info["Key"]).upper(), bool(info.get("ShiftDown", False)))

    def girar(self, graus=90.0):
        """Gira o objeto em torno de Z, no ponto de inserção."""
        if not self.obj or not hasattr(self.obj, "Placement"):
            return
        pl = self.obj.Placement
        pl.Rotation = App.Rotation(App.Vector(0, 0, 1), graus).multiply(pl.Rotation)
        self.obj.Placement = pl
        self.view.redraw()
        self._avisar(f"Girado {graus:g}°.")

    def tratar_tecla(self, tecla, shift=False):
        """R gira 90° (Shift+R, 45°), Espaço/A alinha, L alterna o automático, ESC cancela."""
        if not self.is_active:
            return
        if tecla == "R":
            self.girar(45.0 if shift else 90.0)
        elif tecla in ("SPACE", " ", "A"):
            self._alternar_trava()
        elif tecla == "L":
            self.automatico = not self.automatico
            self._avisar("Alinhamento automático " + ("ligado." if self.automatico else "desligado."))
        elif tecla == "ESCAPE":
            App.Console.PrintMessage("Inserção encerrada.\n")
            self.cancelar()

    def cancelar(self):
        """Encerra a inserção e apaga o objeto que ainda não foi fixado."""
        ComponentInsertionMode._trava_da_sequencia = None
        ComponentInsertionMode._rotacao_da_sequencia = None
        self.stop()
        try:
            if self.obj and self.obj.Document:
                documento = self.obj.Document
                documento.removeObject(self.obj.Name)
                documento.recompute()
        except Exception:
            pass  # o objeto já foi apagado pelo usuário
        self.obj = None
