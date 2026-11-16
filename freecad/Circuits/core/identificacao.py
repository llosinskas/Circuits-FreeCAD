"""Identificação dos pontos da planta: circuito, comando de interruptor e texto de anotação.

Sem FreeCAD. O *comando* é a letra minúscula que liga um interruptor aos
pontos de luz que ele aciona (a, b, c...), como nas plantas elétricas usuais.
"""
import re
import string


def _letras():
    """a, b, ..., z, aa, ab, ..."""
    for letra in string.ascii_lowercase:
        yield letra
    for primeira in string.ascii_lowercase:
        for segunda in string.ascii_lowercase:
            yield primeira + segunda


def proximo_comando(usados):
    """Primeira letra de comando que ainda não está em uso."""
    ocupados = {str(comando).strip().lower() for comando in usados if str(comando).strip()}
    return next(letra for letra in _letras() if letra not in ocupados)


def escolher_comando(dos_interruptores, usados_fora):
    """Letra para ligar interruptores a pontos de luz.

    Mantém a letra que um dos interruptores selecionados já tem, desde que
    nenhum ponto fora da seleção a use; senão, pega a próxima letra livre.

    Args:
        dos_interruptores: letras atuais dos interruptores selecionados.
        usados_fora: letras dos interruptores e pontos de luz fora da seleção.
    """
    ocupados = {str(comando).strip().lower() for comando in usados_fora if str(comando).strip()}
    for comando in dos_interruptores:
        comando = str(comando).strip().lower()
        if comando and comando not in ocupados:
            return comando
    return proximo_comando(ocupados)


def ordenar_circuitos(circuitos):
    """Circuitos sem repetição, com '2' antes de '10' e textos depois dos números."""
    def chave(numero):
        achado = re.match(r"\d+", numero)
        return (0, int(achado.group()), numero) if achado else (1, 0, numero)
    return sorted({str(c).strip() for c in circuitos if str(c).strip()}, key=chave)


def proximo_circuito(circuitos):
    """Número do próximo circuito: o maior número em uso mais um."""
    numeros = [int(c) for c in ordenar_circuitos(circuitos) if c.isdigit()]
    return str(max(numeros) + 1) if numeros else "1"


def texto_ponto(circuito="", comando="", potencia_va=None):
    """Texto de identificação de um ponto na planta.

    Exemplos: 'C1 · a · 100 VA' (luz), 'C2 · 600 VA' (tomada), 'C1 · a' (interruptor).
    Devolve '' quando não há nada a mostrar.
    """
    partes = []
    if str(circuito).strip():
        partes.append(f"C{str(circuito).strip()}")
    if str(comando).strip():
        partes.append(str(comando).strip().lower())
    if potencia_va:
        partes.append(f"{potencia_va:.0f} VA")
    return " · ".join(partes)
