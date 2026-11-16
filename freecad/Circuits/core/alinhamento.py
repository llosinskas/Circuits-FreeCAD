"""Alinhamento de símbolos em planta, sem FreeCAD.

Os pontos são pares (x, y) na unidade do desenho. Uma *trava* prende um dos
eixos em um valor: ("x", 1500.0) mantém o símbolo na vertical que passa por
x = 1500, e ("y", 800.0) na horizontal que passa por y = 800.
"""


def mais_proximo(ponto, referencias):
    """Referência mais próxima do ponto, ou None se não há referências."""
    if not referencias:
        return None
    return min(referencias, key=lambda r: (r[0] - ponto[0]) ** 2 + (r[1] - ponto[1]) ** 2)


def aplicar_trava(ponto, trava):
    """Ponto com o eixo travado no valor da trava. Sem trava, devolve o ponto."""
    if not trava:
        return tuple(ponto)
    eixo, valor = trava
    return (valor, ponto[1]) if eixo == "x" else (ponto[0], valor)


def travas_possiveis(ponto, referencias):
    """Travas oferecidas quando o usuário pede para alinhar com o símbolo vizinho.

    Returns:
        Lista com duas travas, do símbolo mais próximo do ponto: primeiro a do
        eixo em que o ponto já está mais perto dele, depois a do outro eixo.
        Lista vazia se não há símbolos na planta.
    """
    referencia = mais_proximo(ponto, referencias)
    if referencia is None:
        return []
    em_x, em_y = ("x", referencia[0]), ("y", referencia[1])
    perto_em_x = abs(referencia[0] - ponto[0]) <= abs(referencia[1] - ponto[1])
    return [em_x, em_y] if perto_em_x else [em_y, em_x]


def atrair(ponto, referencias, tolerancia):
    """Puxa o ponto para o X ou o Y de um símbolo vizinho, se estiver dentro da tolerância.

    Cada eixo é tratado separadamente, então o ponto pode alinhar com um
    símbolo na vertical e com outro na horizontal ao mesmo tempo.

    Returns:
        (x, y, alinhou_em_x, alinhou_em_y)
    """
    x, y = ponto
    alinhou_x = alinhou_y = False
    if referencias and tolerancia > 0:
        perto_x = min(referencias, key=lambda r: abs(r[0] - x))
        perto_y = min(referencias, key=lambda r: abs(r[1] - y))
        if abs(perto_x[0] - x) <= tolerancia:
            x, alinhou_x = perto_x[0], True
        if abs(perto_y[1] - y) <= tolerancia:
            y, alinhou_y = perto_y[1], True
    return x, y, alinhou_x, alinhou_y


def _em_linha_horizontal(pontos):
    """Os pontos se espalham mais em X do que em Y, isto é, formam uma fileira horizontal."""
    xs = [p[0] for p in pontos]
    ys = [p[1] for p in pontos]
    return (max(xs) - min(xs)) >= (max(ys) - min(ys))


def alinhar(pontos):
    """Coloca os pontos em uma linha reta, horizontal ou vertical.

    A direção é a do maior espalhamento, e a linha passa pelo primeiro ponto,
    que serve de referência e não se move.
    """
    if len(pontos) < 2:
        return [tuple(p) for p in pontos]
    referencia = pontos[0]
    if _em_linha_horizontal(pontos):
        return [(p[0], referencia[1]) for p in pontos]
    return [(referencia[0], p[1]) for p in pontos]


def distribuir(pontos):
    """Espaça os pontos igualmente entre os dois extremos, na direção do maior espalhamento.

    A ordem da lista é preservada: cada posição devolvida corresponde ao ponto
    de mesmo índice. A outra coordenada não muda.
    """
    if len(pontos) < 3:
        return [tuple(p) for p in pontos]
    eixo = 0 if _em_linha_horizontal(pontos) else 1
    ordem = sorted(range(len(pontos)), key=lambda i: pontos[i][eixo])
    inicio, fim = pontos[ordem[0]][eixo], pontos[ordem[-1]][eixo]
    passo = (fim - inicio) / (len(pontos) - 1)
    resultado = [tuple(p) for p in pontos]
    for posicao, indice in enumerate(ordem):
        novo = list(resultado[indice])
        novo[eixo] = inicio + posicao * passo
        resultado[indice] = tuple(novo)
    return resultado
