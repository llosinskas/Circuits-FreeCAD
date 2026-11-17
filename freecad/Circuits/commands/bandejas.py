"""Comandos das bandejas: eletrocalhas e leitos com conexões, modelo 3D e suportes."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import bandejas
from freecad.Circuits.UI.dialogs.bandeja_dialog import BandejaDialog


def _valores(obj):
    if not bandejas.eh_bandeja(obj):
        return None
    return {"tipo": str(obj.TipoBandeja), "largura": bandejas._mm(obj.Largura), "aba": bandejas._mm(obj.Aba),
            "altura": bandejas._mm(obj.AlturaBandeja), "tampa": bool(obj.Tampa)}


class CableTray:
    """Transforma as linhas selecionadas em eletrocalha ou leito, com 3D e as conexões na planta."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        linhas = [obj for obj in Gui.Selection.getSelection() if hasattr(obj, "Points")]
        if not linhas:
            App.Console.PrintMessage(
                "Bandeja: desenhe o trajeto com a linha (Wire), selecione as linhas e clique de novo em Bandeja/leito.\n"
            )
            Gui.runCommand("Draft_Wire")
            return
        dialogo = BandejaDialog(len(linhas), _valores(linhas[0]))
        if not dialogo.exec_():
            return
        dados = dialogo.get_dados()
        doc.openTransaction("Bandejas e leitos")
        try:
            marcadas = bandejas.marcar(doc, linhas, **dados)
            bandejas.gerar_3d(doc, marcadas)
            conexoes = bandejas.anotar_conexoes(doc)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        App.Console.PrintMessage(
            f"{len(marcadas)} bandeja(s) marcada(s); {conexoes} conexão(ões) identificada(s) na planta.\n"
        )

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "eletrocalha.svg",
            "Bandeja/leito",
            "Eletrocalha ou leito: selecione as linhas do trajeto para definir tipo, largura, aba e altura; "
            "gera o 3D e identifica curvas, tês, cruzetas e terminais",
        )


class GerarSuportes:
    """Posiciona os suportes ao longo das bandejas de cada pavimento."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        if not bandejas.listar(doc):
            QtWidgets.QMessageBox.information(
                None, "Suportes", "Nenhuma bandeja no projeto: use o botão Bandeja/leito primeiro."
            )
            return
        doc.openTransaction("Suportes das bandejas")
        try:
            contagem = bandejas.gerar_suportes(doc)
            bandejas.anotar_conexoes(doc)
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        linhas = [f"{pav or 'Sem pavimento'}: {quantidade} suporte(s)" for pav, quantidade in contagem.items()]
        QtWidgets.QMessageBox.information(None, "Suportes", "\n".join(linhas) or "Nenhum suporte gerado.")

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "suportes.svg",
            "Suportes",
            "Suportes suspensos das bandejas: um perto de cada conexão e os intermediários pelo vão máximo, "
            "com o traço na planta e o modelo 3D até a laje",
        )


Gui.addCommand("InsertCableTray", CableTray())
Gui.addCommand("GerarSuportes", GerarSuportes())
