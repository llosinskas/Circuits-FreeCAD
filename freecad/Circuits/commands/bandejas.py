"""Comandos das bandejas: eletrocalhas e leitos com conexões, modelo 3D e suportes."""
import FreeCAD as App
import FreeCADGui as Gui

from freecad.Circuits.commands._base import documento_ou_aviso, recursos
from freecad.Circuits.core import bandejas as regras
from freecad.Circuits.qt import QtWidgets
from freecad.Circuits.services import bandejas, eletrodutos, eletrodutos_planta, rede
from freecad.Circuits.UI.dialogs.bandeja_dialog import BandejaDialog, SuportesDialog


def _valores(obj):
    if not bandejas.eh_bandeja(obj):
        return None
    return {"tipo": str(obj.TipoBandeja), "largura": bandejas._mm(obj.Largura), "aba": bandejas._mm(obj.Aba),
            "altura": bandejas._mm(obj.AlturaBandeja), "tampa": bool(obj.Tampa)}


def _valores_suporte(obj):
    if obj is None or not bandejas.eh_bandeja(obj):
        return {}
    tipo_b = str(getattr(obj, "TipoBandeja", regras.TIPO_PADRAO))
    vao_padrao = regras.VAO_SUPORTE.get(tipo_b, regras.VAO_SUPORTE[regras.TIPO_PADRAO])
    return {
        "tipo_suporte": str(getattr(obj, "TipoSuporte", regras.TIPO_SUPORTE_PADRAO) or regras.TIPO_SUPORTE_PADRAO),
        "vao_suporte": bandejas._mm(obj.VaoSuporte) if hasattr(obj, "VaoSuporte") and obj.VaoSuporte is not None else vao_padrao,
        "distancia_no": bandejas._mm(obj.DistanciaConexao) if hasattr(obj, "DistanciaConexao") and obj.DistanciaConexao is not None else regras.DISTANCIA_SUPORTE_CONEXAO,
        "pendente": bandejas._mm(obj.ComprimentoPendente) if hasattr(obj, "ComprimentoPendente") and obj.ComprimentoPendente is not None else 0.0,
        "folga_perfilado": bandejas._mm(obj.FolgaPerfilado) if hasattr(obj, "FolgaPerfilado") and obj.FolgaPerfilado is not None else regras.FOLGA_PERFILADO_MM,
    }


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
            juncoes = bandejas.encaixar(doc, marcadas)
            bandejas.gerar_3d(doc)  # todas: uma junção nova muda o recorte das vizinhas
            bandejas.desenhar_contorno(doc)
            conexoes = bandejas.anotar_conexoes(doc)
            saidas = 0
            if rede.listar_eletrodutos(doc):  # eletrodutos que chegam às bandejas: saídas
                eletrodutos_planta.encaixar_nas_bandejas(doc)
                resultados = eletrodutos_planta.analisar(doc)
                saidas = sum(len(r.get("saidas", [])) for r in resultados.values())
                eletrodutos_planta.anotar(doc, resultados)
                if saidas:
                    eletrodutos.gerar_saidas_3d(doc, resultados)  # flange e luva no 3D da eletrocalha
            doc.commitTransaction()
        except Exception:
            doc.abortTransaction()
            raise
        App.Console.PrintMessage(
            f"{len(marcadas)} bandeja(s) marcada(s), {juncoes} junção(ões) feita(s); "
            f"{conexoes} ponto(s) com peça identificada na planta; {saidas} saída(s) de eletroduto.\n"
        )

    def IsActive(self):
        return True

    def GetResources(self):
        return recursos(
            "eletrocalha.svg",
            "Bandeja/leito",
            "Eletrocalha ou leito: selecione as linhas do trajeto para definir tipo, largura, aba e altura. "
            "Junta as pontas a até 30 cm de outra bandeja, cruza as da mesma altura e monta curvas, tês e "
            "cruzetas no 3D e no contorno da planta",
        )


class GerarSuportes:
    """Configura (vão, comprimento dos pendentes, distância às conexões, tipo) e posiciona os suportes."""

    def Activated(self):
        doc = documento_ou_aviso()
        if not doc:
            return
        todas = bandejas.listar(doc)
        if not todas:
            QtWidgets.QMessageBox.information(
                None, "Suportes", "Nenhuma bandeja no projeto: use o botão Bandeja/leito primeiro."
            )
            return
        selecionadas = [obj for obj in Gui.Selection.getSelection() if bandejas.eh_bandeja(obj)]
        alvos = selecionadas or todas
        dialogo = SuportesDialog(len(selecionadas), _valores_suporte(alvos[0]))
        if not dialogo.exec_():
            return
        ajustes = dialogo.get_dados()
        doc.openTransaction("Suportes das bandejas")
        try:
            bandejas.configurar_suportes(alvos, **ajustes)
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
            "Suportes das bandejas: ajusta espaçamento máximo (vão), comprimento dos pendentes/tirantes, "
            "distância às conexões, folga do perfilado e tipo de suporte, gerando o traço 2D e o modelo 3D",
        )


Gui.addCommand("InsertCableTray", CableTray())
Gui.addCommand("GerarSuportes", GerarSuportes())
