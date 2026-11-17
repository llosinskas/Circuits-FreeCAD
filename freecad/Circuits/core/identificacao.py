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


def texto_quadro(sigla, medidores=None, circuito=""):
    """Texto de identificação de um quadro ou medição na planta.

    Exemplos: 'QD1', 'CM · 12 medidores', 'QC · C8' (quadro alimentado pelo circuito 8).
    """
    partes = [str(sigla).strip()] if str(sigla).strip() else []
    if medidores and medidores > 1:
        partes.append(f"{medidores} medidores")
    if str(circuito).strip():
        partes.append(f"C{str(circuito).strip()}")
    return " · ".join(partes)


_FASES = {"F+N": 1, "F+F": 2, "3F": 3}
_CONDUTORES_INTERRUPTOR = {
    "Simples": "F+R",
    "Paralelo": "F+2R",
    "Intermediário": "4R",
    "Botão de campainha": "F+R",
    "Fotocélula": "F+N+R",  # o relé precisa de neutro para funcionar
}


def condutores_no_ponto(tipo, ligacao="F+N", comando="", tipo_interruptor="Simples"):
    """Condutores que chegam à caixa, para a identificação dos cabos na planta.

    F = fase, N = neutro, T = terra, R = retorno. Exemplos: tomada 'F+N+T';
    chuveiro em duas fases '2F+T'; luminária comandada por interruptor 'R+N+T';
    interruptor simples 'F+R', paralelo 'F+2R' (fase ou retorno e os dois
    condutores entre os paralelos), intermediário '4R'; botão de campainha
    'F+R'; fotocélula 'F+N+R'.

    Args:
        tipo: 'ponto' ou 'interruptor'.
        ligacao: 'F+N', 'F+F' ou '3F' (pontos).
        comando: letra do interruptor que comanda o ponto; vazia se não houver.
        tipo_interruptor: Simples, Paralelo, Intermediário, Botão de campainha ou Fotocélula.
    """
    if tipo == "interruptor":
        return _CONDUTORES_INTERRUPTOR.get(tipo_interruptor, "F+R")
    fases = _FASES.get(str(ligacao).strip(), 1)
    if str(comando).strip():  # a fase vai ao interruptor e volta como retorno
        partes = ["R"] + (["N"] if fases == 1 else ["F"] * (fases - 1))
    else:
        partes = (["F"] if fases == 1 else [f"{fases}F"]) + (["N"] if fases == 1 else [])
    return "+".join(partes + ["T"])


def texto_cabos(secao, condutores):
    """Identificação dos cabos: seção e condutores, como '#2,5 F+N+T'."""
    return f"#{float(secao):g} {condutores}".replace(".", ",")


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
