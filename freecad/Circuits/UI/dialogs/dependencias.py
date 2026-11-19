"""Pergunta ao usuário se pode instalar as bibliotecas que faltam (``services.dependencias``)."""
from freecad.Circuits.qt import QtCore, QtWidgets
from freecad.Circuits.services import dependencias

TITULO = "Bibliotecas da bancada Engenharia"
_perguntado = False  # uma vez por sessão, na ativação da bancada


def perguntar_e_instalar(motivo="", forcar=False):
    """Oferece instalar o que falta; devolve True se, no fim, nada falta.

    Args:
        motivo: frase que explica para que a biblioteca é usada agora.
        forcar: pergunta mesmo que o usuário tenha pedido para não perguntar
            (quando ele clicou num botão que precisa da biblioteca).
    """
    global _perguntado
    pacotes = dependencias.faltando()
    if not pacotes:
        return True
    if not forcar and (_perguntado or not dependencias.perguntar()):
        return False
    _perguntado = True

    caixa = QtWidgets.QMessageBox()
    caixa.setWindowTitle(TITULO)
    caixa.setIcon(QtWidgets.QMessageBox.Question)
    caixa.setText(
        f"A bancada usa {', '.join(pacotes)}, que não está instalado no Python do FreeCAD.\n"
        f"{motivo or 'Ele gera o relatório e os quantitativos em PDF.'}\n\nInstalar agora?"
    )
    caixa.setInformativeText(f"Será instalado com o pip em:\n{dependencias.pasta_de_pacotes()}")
    instalar = caixa.addButton("Instalar", QtWidgets.QMessageBox.AcceptRole)
    caixa.addButton("Agora não", QtWidgets.QMessageBox.RejectRole)
    nunca = None if forcar else caixa.addButton("Não perguntar de novo", QtWidgets.QMessageBox.DestructiveRole)
    caixa.exec_()
    if nunca is not None and caixa.clickedButton() is nunca:
        dependencias.nunca_mais_perguntar()
        return False
    if caixa.clickedButton() is not instalar:
        return False

    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
    try:
        ok, saida = dependencias.instalar(pacotes)
    finally:
        QtWidgets.QApplication.restoreOverrideCursor()
    if ok:
        QtWidgets.QMessageBox.information(None, TITULO, f"{', '.join(pacotes)} instalado.")
        return True
    comando = " ".join(dependencias.comando_de_instalacao(pacotes))
    QtWidgets.QMessageBox.warning(
        None, TITULO,
        "Não foi possível instalar. Rode no terminal:\n\n" + comando + "\n\nSaída do pip:\n" + saida[-1500:],
    )
    return False
