"""Bibliotecas Python que a bancada usa e que podem faltar no FreeCAD: conferência e instalação.

A instalação usa o pip do Python do FreeCAD e grava na mesma pasta que o
Addon Manager usa (``<dados do usuário>/AdditionalPythonPackages/py3XX``), que
o FreeCAD põe no ``sys.path``. Sem Qt: quem pergunta ao usuário é o diálogo.
"""
import importlib
import importlib.util
import os
import subprocess
import sys

import FreeCAD as App

# módulo importado -> pacote do pip
PACOTES = {"reportlab": "reportlab"}
PREFERENCIAS = "User parameter:BaseApp/Preferences/Mod/Circuits"
NAO_PERGUNTAR = "NaoPerguntarDependencias"


def faltando():
    """Pacotes do pip que ainda não estão instalados."""
    return [pacote for modulo, pacote in PACOTES.items() if importlib.util.find_spec(modulo) is None]


def perguntar():
    """O usuário ainda não pediu para não perguntar de novo."""
    try:
        return not App.ParamGet(PREFERENCIAS).GetBool(NAO_PERGUNTAR, False)
    except Exception:
        return True


def nunca_mais_perguntar():
    App.ParamGet(PREFERENCIAS).SetBool(NAO_PERGUNTAR, True)


def pasta_de_pacotes():
    """Pasta de pacotes extras do FreeCAD, a mesma do Addon Manager."""
    versao = f"py{sys.version_info.major}{sys.version_info.minor}"
    return os.path.join(App.getUserAppDataDir(), "AdditionalPythonPackages", versao)


def python_do_freecad():
    """Executável do Python que roda dentro do FreeCAD (``sys.executable`` é o próprio FreeCAD)."""
    if os.path.basename(sys.executable).lower().startswith("python"):
        return sys.executable
    pasta = os.path.join(App.getHomePath(), "bin")
    for nome in ("python.exe", "python3", "python"):
        caminho = os.path.join(pasta, nome)
        if os.path.exists(caminho):
            return caminho
    return "python3"


def comando_de_instalacao(pacotes):
    """Linha de comando do pip para instalar os pacotes na pasta de pacotes extras."""
    return [python_do_freecad(), "-m", "pip", "install", "--disable-pip-version-check", "--upgrade",
            "--target", pasta_de_pacotes(), *pacotes]


def instalar(pacotes):
    """Instala os pacotes com o pip e os deixa disponíveis nesta sessão.

    Returns:
        (deu certo, texto da saída do pip).
    """
    os.makedirs(pasta_de_pacotes(), exist_ok=True)
    try:
        processo = subprocess.run(comando_de_instalacao(pacotes), capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.SubprocessError) as erro:
        return False, str(erro)
    if pasta_de_pacotes() not in sys.path:
        sys.path.append(pasta_de_pacotes())
    importlib.invalidate_caches()
    return processo.returncode == 0 and not faltando(), (processo.stdout or "") + (processo.stderr or "")
