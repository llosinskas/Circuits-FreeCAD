"""Botões com lista suspensa, que reúnem vários comandos em um só lugar da barra.

Os grupos são definidos em ``init_gui.GROUPS`` e registrados em ``Initialize``,
depois dos comandos que eles reúnem.
"""
import FreeCADGui as Gui


class GrupoDeComandos:
    """Comando de grupo do FreeCAD: um botão cuja seta abre os comandos do grupo.

    O FreeCAD mostra no botão o ícone do último comando usado e, ao clicar,
    executa esse comando.
    """

    def __init__(self, legenda, dica, comandos):
        self.legenda = legenda
        self.dica = dica
        self.comandos = tuple(comandos)

    def GetCommands(self):
        return self.comandos

    def GetDefaultCommand(self):
        return 0

    def GetResources(self):
        return {"MenuText": self.legenda, "ToolTip": self.dica, "DropDownMenu": True, "Exclusive": True}

    def IsActive(self):
        return True


def registrar(grupos):
    """Registra os grupos de ``{id: (legenda, dica, comandos)}``."""
    for identificador, (legenda, dica, comandos) in grupos.items():
        Gui.addCommand(identificador, GrupoDeComandos(legenda, dica, comandos))
