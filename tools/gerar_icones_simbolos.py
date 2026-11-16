"""Gera os ícones SVG dos pontos elétricos a partir de ``core.simbolos``.

Assim o ícone do botão é sempre igual ao símbolo desenhado na planta.
Execute a partir da raiz do repositório, depois de mudar o catálogo::

    python tools/gerar_icones_simbolos.py
"""
import math
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from tests import ROOT  # noqa: E402,F401  (configura o caminho do pacote)
from freecad.Circuits.core import simbolos  # noqa: E402

DESTINO = os.path.join(RAIZ, "freecad", "Circuits", "Resources", "Icons", "simbologia")
LADO = 64
MARGEM = 7
COR = {simbolos.TOMADA: "#1a73e8", simbolos.ENERGIA: "#d93025", simbolos.ILUMINACAO: "#b06000"}


def _caminho(primitivas, escala, dx, dy):
    """Atributo ``d`` de um <path> com todas as primitivas (Y do SVG é para baixo)."""
    def ponto(x, y):
        return f"{x * escala + dx:.2f} {dy - y * escala:.2f}"

    partes = []
    for primitiva in primitivas:
        if primitiva[0] == "linha":
            partes.append(f"M{ponto(primitiva[1], primitiva[2])}L{ponto(primitiva[3], primitiva[4])}")
            continue
        _, cx, cy, raio = primitiva[:4]
        inicio, fim = (primitiva[4], primitiva[5]) if primitiva[0] == "arco" else (0, 360)
        passos = max(2, int(abs(fim - inicio) / 6))
        pontos = [
            ponto(cx + raio * math.cos(math.radians(inicio + (fim - inicio) * i / passos)),
                  cy + raio * math.sin(math.radians(inicio + (fim - inicio) * i / passos)))
            for i in range(passos + 1)
        ]
        partes.append("M" + "L".join(pontos))
    return "".join(partes)


def svg(chave):
    xmin, ymin, xmax, ymax = simbolos.limites(chave)
    escala = (LADO - 2 * MARGEM) / max(xmax - xmin, ymax - ymin)
    dx = LADO / 2 - (xmin + xmax) / 2 * escala
    dy = LADO / 2 + (ymin + ymax) / 2 * escala
    caminho = _caminho(simbolos.geometria(chave), escala, dx, dy)
    cor = COR[simbolos.CATALOGO[chave]["categoria"]]
    traco = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {LADO} {LADO}" width="{LADO}" height="{LADO}">\n'
        f'  <!-- {simbolos.CATALOGO[chave]["legenda"]}: gerado por tools/gerar_icones_simbolos.py -->\n'
        f'  <path d="{caminho}" {traco} stroke="#ffffff" stroke-width="7" stroke-opacity="0.85"/>\n'
        f'  <path d="{caminho}" {traco} stroke="{cor}" stroke-width="3"/>\n'
        "</svg>\n"
    )


def main():
    os.makedirs(DESTINO, exist_ok=True)
    for chave in simbolos.CATALOGO:
        with open(os.path.join(DESTINO, f"{chave}.svg"), "w", encoding="utf-8") as arquivo:
            arquivo.write(svg(chave))
    print(f"{len(simbolos.CATALOGO)} ícones gravados em {DESTINO}")


if __name__ == "__main__":
    main()
