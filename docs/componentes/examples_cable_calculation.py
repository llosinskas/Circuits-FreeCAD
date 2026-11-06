"""
EXEMPLO PRÁTICO: Integração com Cálculo de Cabos

Este arquivo demonstra como usar ComponentSelectorDialog e ComponentInserter
para criar um fluxo de trabalho: Selecionar Cabo → Calcular → Visualizar Resultado

Copie e adapte este padrão para suas funcionalidades (cálculo de barramento,
infraestrutura, aterramento, etc.).
"""

from pathlib import Path
from typing import Optional, Dict, Any

from PySide import QtGui, QtCore
from PySide.QtGui import (QMessageBox, QDialog, QFormLayout, QDoubleSpinBox, 
                           QDialogButtonBox, QWidget, QVBoxLayout)
import FreeCAD as App
import FreeCADGui as Gui

from UI.dialogs import ComponentSelectorDialog, ComponentInserter


# ============================================================================
# EXEMPLO 1: Simples - Apenas Seleção
# ============================================================================

class SimpleCableSelector:
    """Exemplo básico: seleciona um cabo e printa informações."""
    
    def __init__(self):
        self.selected_cable_path: Optional[str] = None
    
    def show_selector(self):
        """Abre o diálogo de seleção."""
        folder = self._get_cable_folder()
        dialog = ComponentSelectorDialog(
            components_path=folder,
            title="Selecionar Cabo para Análise",
        )
        
        if dialog.exec_() == QDialog.Accepted:
            self.selected_cable_path = dialog.get_selected_component()
            self._on_cable_selected(self.selected_cable_path)
    
    def _on_cable_selected(self, filepath: str):
        """Executa ação após seleção."""
        import os
        filename = os.path.splitext(os.path.basename(filepath))[0]
        print(f"✓ Cabo selecionado: {filename}")
        print(f"  Caminho: {filepath}")
    
    def _get_cable_folder(self) -> str:
        """Retorna caminho da pasta de cabos."""
        base = Path(__file__).parent.parent.parent
        return str(base / "Componentes" / "Eletrica")  # Usar Componentes/Cabos quando existir


# ============================================================================
# EXEMPLO 2: Integrado - Seleção + Cálculo
# ============================================================================

class CableCalculationWorkflow:
    """Exemplo intermediário: Seleciona → Calcula → Mostra Resultado."""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.selected_cable: Dict[str, Any] = {}
        self.calculation_result: Dict[str, Any] = {}
    
    def start_workflow(self):
        """Inicia o fluxo de trabalho."""
        self.step_1_select_cable()
    
    def step_1_select_cable(self):
        """Passo 1: Seleciona o cabo."""
        print("\n[PASSO 1] Selecionando cabo...")
        
        folder = self._get_cable_folder()
        dialog = ComponentSelectorDialog(
            components_path=folder,
            title="Passo 1: Selecionar Cabo",
            parent=self.parent
        )
        
        def on_selected(filepath: str):
            self.selected_cable = self._parse_cable_file(filepath)
            self.step_2_input_parameters()
        
        dialog.component_selected.connect(on_selected)
        dialog.exec_()
    
    def step_2_input_parameters(self):
        """Passo 2: Usuário insere parâmetros de cálculo."""
        print("\n[PASSO 2] Coletando parâmetros de cálculo...")
        
        # Cria diálogo customizado para parâmetros
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Passo 2: Parâmetros do Cálculo")
        layout = QFormLayout(dialog)
        
        # Campos de entrada
        input_comprimento = QDoubleSpinBox()
        input_comprimento.setValue(50.0)
        input_comprimento.setSuffix(" m")
        
        input_corrente = QDoubleSpinBox()
        input_corrente.setValue(30.0)
        input_corrente.setSuffix(" A")
        
        input_queda = QDoubleSpinBox()
        input_queda.setValue(3.0)
        input_queda.setSuffix(" %")
        
        layout.addRow("Comprimento da linha:", input_comprimento)
        layout.addRow("Corrente nominal:", input_corrente)
        layout.addRow("Queda de tensão máxima:", input_queda)
        
        # Botões
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            # Salva parâmetros
            params = {
                "comprimento": input_comprimento.value(),
                "corrente": input_corrente.value(),
                "queda_tensao": input_queda.value(),
            }
            self.step_3_calculate(params)
    
    def step_3_calculate(self, params: Dict[str, float]):
        """Passo 3: Executa os cálculos."""
        print("\n[PASSO 3] Calculando...")
        
        try:
            # Simula cálculo (substitua pela função real)
            from core.functions.Cabo.queda_tensao import calcular_secao_minima_queda
            
            secao = calcular_secao_minima_queda(
                comprimento_da_linha=params["comprimento"],
                corrente=params["corrente"],
                tensao=220,  # Padrão Brasil
                queda_percentual=params["queda_tensao"],
                resistividade=1.68e-8  # Cobre
            )
            
            self.calculation_result = {
                "secao_minima": secao,
                "corrente": params["corrente"],
                "comprimento": params["comprimento"],
                "queda": params["queda_tensao"]
            }
            
            self.step_4_show_results()
            
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Erro no Cálculo",
                f"Falha ao calcular: {str(e)}"
            )
    
    def step_4_show_results(self):
        """Passo 4: Mostra resultados."""
        print("\n[PASSO 4] Exibindo resultados...")
        
        result = self.calculation_result
        cable = self.selected_cable
        
        msg = f"""
        ╔════════════════════════════════════════╗
        ║      RESULTADO DO CÁLCULO              ║
        ╠════════════════════════════════════════╣
        ║ Cabo Selecionado: {cable.get('name', 'N/A'):<22} ║
        ║ Corrente Nominal: {result['corrente']:.2f} A{' '*22} ║
        ║ Comprimento: {result['comprimento']:.2f} m{' '*27} ║
        ║ Queda Máxima: {result['queda']:.2f} %{' '*27} ║
        ╠════════════════════════════════════════╣
        ║ SEÇÃO MÍNIMA: {result['secao_minima']:.2f} mm² {' '*22} ║
        ╚════════════════════════════════════════╝
        """
        
        QMessageBox.information(
            self.parent,
            "Resultado do Cálculo",
            msg.strip()
        )
    
    def _parse_cable_file(self, filepath: str) -> Dict[str, Any]:
        """Extrai informações do arquivo de cabo."""
        import os
        filename = os.path.splitext(os.path.basename(filepath))[0]
        return {
            "name": filename,
            "filepath": filepath,
            "material": "Cobre",  # Poderia ler de metadados
            "tipo": "PVC"
        }
    
    def _get_cable_folder(self) -> str:
        """Retorna caminho da pasta de cabos."""
        base = Path(__file__).parent.parent.parent
        return str(base / "Componentes" / "Eletrica")


# ============================================================================
# EXEMPLO 3: Avançado - Inserção no Projeto + Cálculo
# ============================================================================

class CableInsertionAndCalculation:
    """Exemplo avançado: Seleciona → Insere no Projeto → Calcula."""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.inserted_cable = None
        self.calculation = None
    
    def execute(self):
        """Executa o fluxo completo."""
        if not App.activeDocument():
            QMessageBox.warning(
                self.parent,
                "Erro",
                "Abra um documento FreeCAD primeiro."
            )
            return
        
        self._step_insert_cable()
    
    def _step_insert_cable(self):
        """Insere o cabo no projeto."""
        print("[1] Inserindo cabo no projeto...")
        
        folder = self._get_cable_folder()
        inserter = ComponentInserter(
            components_folder=folder,
            on_component_loaded=self._on_cable_inserted,
            parent=self.parent
        )
        
        inserter.insert_component()
    
    def _on_cable_inserted(self, filepath: str, freecad_obj):
        """Callback: Cabo foi inserido no documento."""
        self.inserted_cable = {
            "freecad_object": freecad_obj,
            "label": freecad_obj.Label,
            "filepath": filepath
        }
        
        print(f"✓ Cabo inserido no projeto: {freecad_obj.Label}")
        
        # Passa para próximo passo
        self._step_prompt_for_calculation()
    
    def _step_prompt_for_calculation(self):
        """Pergunta se usuário quer calcular o cabo."""
        reply = QMessageBox.question(
            self.parent,
            "Cálculo",
            f"Deseja calcular a seção mínima para '{self.inserted_cable['label']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._step_calculate()
    
    def _step_calculate(self):
        """Realiza o cálculo do cabo."""
        print("[2] Calculando seção mínima...")
        
        # Aqui você chamaria a função de cálculo real
        # Por enquanto, apenas um exemplo
        
        secao = 2.5  # mm² (exemplo)
        
        self.calculation = {
            "secao_minima": secao,
            "cable_label": self.inserted_cable["label"]
        }
        
        print(f"✓ Seção mínima calculada: {secao} mm²")
        
        self._step_show_final_result()
    
    def _step_show_final_result(self):
        """Mostra resultado final."""
        calc = self.calculation
        cable = self.inserted_cable
        
        msg = f"""
        Cabo: {cable['label']}
        Seção Mínima: {calc['secao_minima']} mm²
        
        O componente foi inserido no projeto e está pronto para uso.
        """
        
        QMessageBox.information(
            self.parent,
            "Concluído",
            msg.strip()
        )
    
    def _get_cable_folder(self) -> str:
        """Retorna caminho da pasta de cabos."""
        base = Path(__file__).parent.parent.parent
        return str(base / "Componentes" / "Eletrica")


# ============================================================================
# USO: Como executar os exemplos
# ============================================================================

def example_usage():
    """Demonstra como usar cada exemplo."""
    
    # Exemplo 1: Simples
    print("=" * 50)
    print("EXEMPLO 1: Seleção Simples")
    print("=" * 50)
    selector = SimpleCableSelector()
    selector.show_selector()
    
    # Exemplo 2: Cálculo
    print("\n" + "=" * 50)
    print("EXEMPLO 2: Seleção + Cálculo")
    print("=" * 50)
    workflow = CableCalculationWorkflow()
    workflow.start_workflow()
    
    # Exemplo 3: Inserção + Cálculo
    print("\n" + "=" * 50)
    print("EXEMPLO 3: Inserção + Cálculo")
    print("=" * 50)
    advanced = CableInsertionAndCalculation()
    advanced.execute()


# Para testar no FreeCAD console:
# from UI.dialogs.examples_cable_calculation import *
# example_usage()

if __name__ == "__main__":
    example_usage()
