"""Torna ``freecad.Circuits`` importável fora do FreeCAD.

O Python do FreeCAD já traz um pacote ``freecad`` próprio; por isso a pasta do
repositório é acrescentada ao ``__path__`` em vez de depender só do ``sys.path``.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_ROOT = os.path.join(ROOT, "freecad")
sys.path.insert(0, ROOT)

import freecad  # noqa: E402

if PACKAGE_ROOT not in list(freecad.__path__):
    freecad.__path__ = [*freecad.__path__, PACKAGE_ROOT]
