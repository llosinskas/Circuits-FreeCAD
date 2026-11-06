"""Ponto único de importação do Qt.

Todo o código da bancada deve fazer ``from freecad.Circuits.qt import QtWidgets``.
A escolha do binding (PySide2, PySide6 ou o shim PySide do FreeCAD) fica só aqui.
"""
try:
    from PySide2 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError:
        from PySide import QtCore, QtGui

        QtWidgets = QtGui

Qt = QtCore.Qt
Signal = QtCore.Signal
Slot = QtCore.Slot
