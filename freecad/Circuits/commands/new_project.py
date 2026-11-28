"""Comandos para iniciar projetos, planilhas e modelos da biblioteca."""
import os

import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits import ELECTRIC_LIBRARY_PATH
from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import biblioteca, novo_projeto, parametros, planilhas
from freecad.Circuits.UI.dialogs.novo_projeto_dialog import NovoProjetoDialog
from freecad.Circuits.UI.insert_circuit import InsertCircuit


class newProjetctEletrical:
    """Abre o diálogo do projeto: identificação, pavimentos, fornecimento, condutores e proteção.

    Num documento que já é um projeto da bancada, o diálogo vem preenchido e edita o projeto."""

    def Activated(self):
        doc = App.activeDocument()
        editando = doc is not None and parametros.planilha(doc) is not None
        dialogo = NovoProjetoDialog(novo_projeto.dados_iniciais(doc), novo_projeto.bim_disponivel(), editando)
        if not dialogo.exec_():
            return
        dados = dialogo.get_dados()
        if doc is None:
            doc = App.newDocument(_nome_do_documento(dados.get("projeto")))
        doc.openTransaction("Projeto elétrico")
        try:
            feito = novo_projeto.aplicar(doc, dados)
            doc.commitTransaction()
        except ValueError as erro:
            doc.abortTransaction()
            QtWidgets.QMessageBox.warning(None, "Projeto", str(erro))
            return
        except Exception:
            doc.abortTransaction()
            raise
        App.Console.PrintMessage(
            f"Projeto: {len(feito['criados'])} pavimento(s) criado(s), {len(feito['atualizados'])} atualizado(s); "
            f"ativo: {feito['ativo']}; parâmetros alterados: {', '.join(feito['parametros']) or 'nenhum'}.\n")
        if feito.get("convertidos"):
            QtWidgets.QMessageBox.information(
                None, "Projeto", "Pavimentos convertidos em níveis do BIM, com tudo o que estava dentro deles:\n\n"
                + "\n".join(feito["convertidos"]))

    def GetResources(self):
        return recursos(
            "newProject.svg",
            "Novo projeto",
            "Abre o formulário do projeto elétrico: identificação (carimbo), tipo de edificação, pavimentos "
            "(subsolos, andares, cobertura, piso a piso), fornecimento (concessionária, tensões, fases, curto, "
            "aterramento), condutores e proteção. Cria os grupos, os pavimentos e os parâmetros; num projeto "
            "existente, abre preenchido para editar.",
        )


def _nome_do_documento(projeto):
    """Nome interno válido para o documento novo."""
    import re
    nome = re.sub(r"\W+", "_", str(projeto or "").strip(), flags=re.ASCII).strip("_")
    return nome or "Projeto_eletrico"


class ParametrosProjeto:
    """Abre a planilha de parâmetros do projeto, criando-a com os padrões se ainda não existe."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        folha = parametros.planilha(doc, criar=True)
        try:
            folha.ViewObject.doubleClicked()
        except Exception:
            pass
        App.Console.PrintMessage(
            "Parâmetros do projeto: edite a coluna Valor. Montar circuitos usa estes valores na próxima vez.\n"
        )

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "parametros.svg",
            "Parâmetros",
            "Parâmetros do projeto: tensões, curto na entrada, esquema de aterramento, isolação, temperatura, "
            "limites de queda, curvas dos disjuntores e DR, usados no dimensionamento pela NBR 5410",
        )


class CreateModel:
    def Activated(self):
        os.makedirs(ELECTRIC_LIBRARY_PATH, exist_ok=True)
        nome, ok = QtWidgets.QInputDialog.getText(None, "Salvar desenho", "Digite o nome do arquivo:")
        if ok and nome.strip():
            biblioteca.criar_modelo(nome.strip())

    def GetResources(self):
        return recursos(
            "add_model.svg",
            "Criar modelo",
            "Cria um novo modelo de componente (.FCStd) na biblioteca",
        )


class newSpreadsheet:
    def Activated(self):
        doc = documento_ou_aviso()
        if doc:
            planilhas.criar_planilha_circuitos(doc)

    def GetResources(self):
        return recursos(
            "planilha.svg",
            "Planilha de circuitos",
            "Cria a planilha geral de circuitos do projeto",
        )


class addCircuit:
    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        quadros = [q.Label for q in planilhas.listar_quadros(doc)]
        dialogo = InsertCircuit(quadros=quadros)
        if not dialogo.exec_():
            return
        doc.openTransaction("Inserir circuito")
        try:
            folha, linha = planilhas.adicionar_circuito_geral(doc, dialogo.get_dados())
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        App.Console.PrintMessage(f"Circuito gravado na linha {linha} de '{folha.Label}'.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "record-svgrepo-com.svg",
            "Formulário de circuito",
            "Adiciona um circuito preenchido à planilha geral de circuitos do projeto",
        )


class listElements:
    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        os.makedirs(ELECTRIC_LIBRARY_PATH, exist_ok=True)

        arquivos = biblioteca.listar_modelos()
        if not arquivos:
            QtWidgets.QMessageBox.information(None, "Importar modelo", "Não há modelos (.FCStd) na biblioteca.")
            return

        item, ok = QtWidgets.QInputDialog.getItem(None, "Importar modelo", "Escolha o modelo:", arquivos, 0, False)
        if not ok:
            return
        biblioteca.importar_modelo(doc, item)

    def GetResources(self):
        return recursos(
            "listElements.svg",
            "Importar modelo",
            "Escolhe um modelo da biblioteca e o importa para o documento",
        )


Gui.addCommand("newProjetctEletrical", newProjetctEletrical())
Gui.addCommand("newSpreadsheet", newSpreadsheet())
Gui.addCommand("AddSpreadsheet", addCircuit())
Gui.addCommand("ListElements", listElements())
Gui.addCommand("CreateModel", CreateModel())
Gui.addCommand("ParametrosProjeto", ParametrosProjeto())
