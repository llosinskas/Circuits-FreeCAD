"""Comandos de geração de modelos 3D: eletrodutos e caixas."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import caixas_3d, eletrodutos, modelo_3d, quadro_3d, rede


class Quadro3D:
    """Quadro de distribuição em 3D com os componentes da planilha nos trilhos DIN."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        selecionados = Gui.Selection.getSelection()
        simbolos = [o for o in selecionados if quadro_3d.eh_quadro_com_planilha(doc, o)]
        simbolos += [o for o in doc.Objects if getattr(o, "Planilha", None) in {s.Name for s in selecionados}
                     and quadro_3d.eh_quadro_com_planilha(doc, o) and o not in simbolos]
        if not simbolos:
            simbolos = [o for o in doc.Objects if quadro_3d.eh_quadro_com_planilha(doc, o)]
        if not simbolos:
            QtWidgets.QMessageBox.information(
                None, "Quadro 3D",
                "Nenhum símbolo de quadro ligado a uma planilha. Selecione o símbolo do quadro na planta e use "
                "Dados do quadro > Quadro (planilha) para ligá-lo, depois clique aqui de novo.")
            return
        doc.openTransaction("Quadro 3D")
        try:
            feitos = [quadro_3d.gerar(doc, s) for s in simbolos]
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        doc.recompute()
        feitos = [f for f in feitos if f is not None]
        App.Console.PrintMessage("Quadro 3D: " + "; ".join(f"{f.Label}: {f.Resumo}" for f in feitos) + "\n")

    def IsActive(self):
        return App.activeDocument() is not None

    def GetResources(self):
        return recursos(
            "quadro3d.svg",
            "Quadro 3D",
            "Desenha o quadro de distribuição em 3D com os componentes da planilha: disjuntor geral, DPS, IDR, "
            "DRs e disjuntores dos circuitos nos trilhos DIN, barramentos de fases, neutro e terra e a porta. "
            "Com o símbolo (ou a planilha) do quadro selecionado, só ele; sem seleção, todos os quadros ligados "
            "a uma planilha. O Modelo 3D completo também desenha assim os quadros ligados.",
        )


class Modelo3DCompleto:
    """Gera ou refaz todo o modelo 3D: caixas, eletrodutos, eletrocalhas e suportes."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        doc.openTransaction("Modelo 3D completo")
        try:
            feito = modelo_3d.gerar_tudo(doc)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        if not any(feito.values()):
            QtWidgets.QMessageBox.information(
                None, "Modelo 3D", "Nada para modelar: insira pontos, eletrodutos ou eletrocalhas na planta.")
            return
        App.Console.PrintMessage(
            f"Modelo 3D: {feito['caixas']} caixa(s), {feito['eletrodutos']} eletroduto(s), "
            f"{feito['bandejas']} eletrocalha(s) e {feito['suportes']} suporte(s).\n"
        )

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "modelo3d.svg",
            "Modelo 3D completo",
            "Gera ou refaz todo o 3D de uma vez: caixas (tomadas dentro da parede), eletrodutos, eletrocalhas com "
            "curvas, tês e reduções, e suportes",
        )


class Generate3DConduits:
    """Gera os tubos 3D a partir da seleção ou de todos os ConduitPath do documento."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return

        caminhos = Gui.Selection.getSelection() or rede.listar_eletrodutos(doc)  # inclui as linhas marcadas
        if not caminhos:
            QtWidgets.QMessageBox.information(None, "Aviso", "Selecione uma linha (Wire) para gerar o eletroduto 3D.")
            return

        criados = eletrodutos.gerar_tubos(doc, caminhos)
        App.Console.PrintMessage(f"{criados} eletrodutos 3D gerados com sucesso.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "eletroduto3d.svg",
            "Eletrodutos 3D",
            "Gera os tubos 3D dos caminhos selecionados, ou de todos se nada estiver selecionado",
        )


class Generate3DSwitches:
    """Gera as caixas 3D de interruptores, pontos de iluminação e tomadas."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return

        objetos, tomadas = caixas_3d.listar_alvos(doc)
        if not objetos and not tomadas:
            QtWidgets.QMessageBox.information(
                None,
                "Aviso",
                "Nenhum interruptor, ponto de iluminação ou tomada encontrado no documento.\n"
                "Insira componentes primeiro usando os botões correspondentes.",
            )
            return

        criadas = caixas_3d.gerar_caixas(doc, objetos, tomadas)
        App.Console.PrintMessage(f"{criadas} caixa(s) 3D gerada(s) com sucesso.\n")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "gerar3d_switch.svg",
            "Caixas 3D",
            "Gera as caixas 3D de interruptores, tomadas e pontos de iluminação",
        )


Gui.addCommand("Quadro3D", Quadro3D())
Gui.addCommand("Gerar3DCompleto", Modelo3DCompleto())
Gui.addCommand("Generate3DConduits", Generate3DConduits())
Gui.addCommand("Generate3DSwitches", Generate3DSwitches())
