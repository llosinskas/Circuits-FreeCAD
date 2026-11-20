"""Luminotécnico pelo método dos lúmens: quantas luminárias e onde colocá-las em um ambiente retangular.

Passos:

- índice do local: K = (C x L) / (Hu x (C + L)), com Hu = pé-direito - altura do
  plano de trabalho - suspensão da luminária; num ambiente que não é retângulo,
  a forma geral K = 2 x A / (Hu x P) (área e perímetro), que dá o mesmo valor
  no retângulo;
- fator de utilização U estimado a partir de K;
- número de luminárias: N = E x A / (fluxo x U x Fm), com E a iluminância
  **mantida** (o Fm já desconta sujeira e envelhecimento);
- malha de nx por ny luminárias, com o mesmo espaçamento em cada direção e meio
  espaçamento até as paredes, e o espaçamento limitado a
  ``ESPACAMENTO_MAXIMO_FATOR`` x Hu para a iluminação ficar uniforme (sem isso,
  um ambiente comprido podia ficar com uma luminária só no meio).

Iluminâncias: a NBR ISO/CIE 8995-1:2013 (que substituiu a NBR 5413) dá os
valores para locais de trabalho: escritório 500 lx, sala de aula 300 lx, área de
vendas 300 lx, sanitários 200 lx, corredores 100 lx, escadas 150 lx e
estacionamento interno 75 lx (no piso). Ela não trata de residências; para salas,
quartos e cozinhas valem os da antiga NBR 5413 (iluminação geral de 100 a
200 lx, com 300 lx localizados na bancada e na leitura).

ATENÇÃO: é um pré-dimensionamento. O fator de utilização vem de uma curva
genérica (luminária direta, teto e paredes claros), não do catálogo da
luminária. Confira com os dados do fabricante, ou informe o fator de
utilização do catálogo.

Unidades: comprimentos em m, iluminância em lux, fluxo em lúmens, potência em VA.
"""
import math

# Iluminância média usual por ambiente [lux]. "Personalizado" usa o valor informado.
PERSONALIZADO = "Personalizado"
ILUMINANCIAS = {
    "Sala e quarto (150 lx)": 150,
    "Cozinha e banheiro (200 lx)": 200,
    "Circulação e corredor (100 lx)": 100,
    "Escada (150 lx)": 150,
    "Garagem (75 lx)": 75,
    "Escritório (500 lx)": 500,
    "Sala de aula (300 lx)": 300,
    "Loja (300 lx)": 300,
    PERSONALIZADO: None,
}

# Fator de utilização estimado pelo índice do local: (K, U).
FATORES_UTILIZACAO = [
    (0.6, 0.32), (0.8, 0.39), (1.0, 0.45), (1.25, 0.51), (1.5, 0.55),
    (2.0, 0.61), (2.5, 0.65), (3.0, 0.68), (4.0, 0.72), (5.0, 0.75),
]
FATOR_MANUTENCAO = 0.8
PLANO_DE_TRABALHO = 0.75  # m
# Ambientes em que a NBR ISO/CIE 8995-1 dá a iluminância no piso (plano de trabalho = 0).
NO_PISO = ("Circulação e corredor (100 lx)", "Escada (150 lx)", "Garagem (75 lx)")
# Espaçamento máximo entre luminárias (e o dobro até a parede), em múltiplos da altura útil.
# Valor usual para luminárias de distribuição larga; o catálogo pode dar outro.
ESPACAMENTO_MAXIMO_FATOR = 1.5


def indice_do_local(comprimento, largura, altura_util):
    """Índice do local K para luminárias diretas."""
    if comprimento <= 0 or largura <= 0:
        raise ValueError("O comprimento e a largura do ambiente precisam ser maiores que zero.")
    if altura_util <= 0:
        raise ValueError("A luminária precisa ficar acima do plano de trabalho.")
    return (comprimento * largura) / (altura_util * (comprimento + largura))


def indice_pela_area(area, perimetro, altura_util):
    """Índice do local de um ambiente qualquer: K = 2 x A / (Hu x P) [m², m, m]."""
    if area <= 0 or perimetro <= 0:
        raise ValueError("A área e o perímetro do ambiente precisam ser maiores que zero.")
    if altura_util <= 0:
        raise ValueError("A luminária precisa ficar acima do plano de trabalho.")
    return 2.0 * area / (altura_util * perimetro)


def fator_utilizacao(indice):
    """Fator de utilização estimado, interpolado na curva genérica e limitado às pontas dela."""
    pontos = FATORES_UTILIZACAO
    if indice <= pontos[0][0]:
        return pontos[0][1]
    for (k1, u1), (k2, u2) in zip(pontos, pontos[1:]):
        if indice <= k2:
            return u1 + (u2 - u1) * (indice - k1) / (k2 - k1)
    return pontos[-1][1]


def malha(quantidade, comprimento, largura):
    """Malha (nx, ny) com pelo menos ``quantidade`` luminárias e espaçamentos parecidos nas duas direções.

    ``nx`` é o número de luminárias ao longo do comprimento. Para a malha ficar
    regular, aceita até 25 % de luminárias a mais que o calculado (7 viram 4 x 2,
    e não uma fileira de 7).
    """
    quantidade = max(1, int(quantidade))
    limite = max(quantidade, int(quantidade * 1.25))
    melhor = None
    for nx in range(1, limite + 1):
        ny = math.ceil(quantidade / nx)
        if nx * ny > limite:
            continue
        # Espaçamentos mais próximos de um quadrado primeiro; no empate, menos luminárias.
        desproporcao = round(abs(math.log((comprimento / nx) / (largura / ny))), 9)
        chave = (desproporcao, nx * ny)
        if melhor is None or chave < melhor[0]:
            melhor = (chave, nx, ny)
    return melhor[1], melhor[2]


def espacamento_maximo(altura_util):
    """Maior distância entre luminárias [m] para a iluminação ficar uniforme."""
    return ESPACAMENTO_MAXIMO_FATOR * altura_util


def ajustar_espacamento(nx, ny, comprimento, largura, altura_util):
    """Acrescenta colunas ou fileiras até o espaçamento não passar do máximo."""
    maximo = espacamento_maximo(altura_util)
    while comprimento / nx > maximo + 1e-9:
        nx += 1
    while largura / ny > maximo + 1e-9:
        ny += 1
    return nx, ny


def calcular(area, perimetro, iluminancia, fluxo_luminaria, pe_direito=2.7, plano_trabalho=PLANO_DE_TRABALHO,
             suspensao=0.0, fator_manutencao=FATOR_MANUTENCAO, fator_utilizacao_informado=0.0):
    """Altura útil, índice do local, fatores e a quantidade calculada (sem arredondar) de um ambiente.

    Returns:
        dict com ``area``, ``altura_util``, ``indice_local``, ``fator_utilizacao``,
        ``fator_manutencao``, ``iluminancia``, ``fluxo_luminaria`` e ``quantidade_calculada``.
    """
    if iluminancia <= 0 or fluxo_luminaria <= 0:
        raise ValueError("A iluminância e o fluxo da luminária precisam ser maiores que zero.")
    if not 0 < fator_manutencao <= 1:
        raise ValueError("O fator de manutenção precisa estar entre 0 e 1.")
    altura_util = pe_direito - plano_trabalho - suspensao
    indice = indice_pela_area(area, perimetro, altura_util)
    utilizacao = fator_utilizacao_informado if fator_utilizacao_informado > 0 else fator_utilizacao(indice)
    return {
        "area": area, "altura_util": altura_util, "indice_local": indice, "fator_utilizacao": utilizacao,
        "fator_manutencao": fator_manutencao, "iluminancia": iluminancia, "fluxo_luminaria": fluxo_luminaria,
        "quantidade_calculada": iluminancia * area / (fluxo_luminaria * utilizacao * fator_manutencao),
    }


def iluminancia_com(quantidade, base):
    """Iluminância média mantida [lux] com ``quantidade`` luminárias, nos fatores de ``calcular``."""
    return quantidade * base["fluxo_luminaria"] * base["fator_utilizacao"] * base["fator_manutencao"] / base["area"]


def posicoes(nx, ny, comprimento, largura):
    """Centro de cada luminária, a partir do canto do ambiente: lista de (x, y)."""
    passo_x, passo_y = comprimento / nx, largura / ny
    return [
        (passo_x * (coluna + 0.5), passo_y * (linha + 0.5))
        for linha in range(ny) for coluna in range(nx)
    ]


def dimensionar(
    comprimento,
    largura,
    iluminancia,
    fluxo_luminaria,
    pe_direito=2.7,
    plano_trabalho=PLANO_DE_TRABALHO,
    suspensao=0.0,
    fator_manutencao=FATOR_MANUTENCAO,
    fator_utilizacao_informado=0.0,
):
    """Calcula a quantidade e a posição das luminárias de um ambiente retangular.

    Args:
        comprimento, largura: dimensões do ambiente [m].
        iluminancia: iluminância média desejada no plano de trabalho [lux].
        fluxo_luminaria: fluxo luminoso de cada luminária [lm].
        pe_direito: altura do piso ao teto [m].
        plano_trabalho: altura do plano de trabalho [m].
        suspensao: distância do teto à luminária [m].
        fator_manutencao: perdas por sujeira e envelhecimento (0 a 1).
        fator_utilizacao_informado: fator do catálogo; zero usa a curva genérica.
    Returns:
        dict com área, índice do local, fatores, quantidade calculada, malha,
        quantidade final, iluminância resultante, espaçamentos e ``posicoes``.
    """
    if comprimento <= 0 or largura <= 0:
        raise ValueError("O comprimento e a largura do ambiente precisam ser maiores que zero.")
    base = calcular(comprimento * largura, 2 * (comprimento + largura), iluminancia, fluxo_luminaria, pe_direito,
                    plano_trabalho, suspensao, fator_manutencao, fator_utilizacao_informado)
    nx, ny = malha(math.ceil(base["quantidade_calculada"] - 1e-9), comprimento, largura)
    regular = (nx, ny)
    nx, ny = ajustar_espacamento(nx, ny, comprimento, largura, base["altura_util"])
    avisos = []
    if (nx, ny) != regular:
        avisos.append(
            f"malha aumentada de {regular[0]} x {regular[1]} para {nx} x {ny} para o espaçamento não passar de "
            f"{espacamento_maximo(base['altura_util']):.2f} m ({ESPACAMENTO_MAXIMO_FATOR:g} x altura útil)")
    final = nx * ny
    return dict(base, **{
        "comprimento": comprimento,
        "largura": largura,
        "nx": nx,
        "ny": ny,
        "quantidade": final,
        "iluminancia_resultante": iluminancia_com(final, base),
        "espacamento_x": comprimento / nx,
        "espacamento_y": largura / ny,
        "espacamento_maximo": espacamento_maximo(base["altura_util"]),
        "posicoes": posicoes(nx, ny, comprimento, largura),
        "avisos": avisos,
    })


def relatorio(resultado):
    """Texto do cálculo, para mostrar ao usuário."""
    r = resultado
    return "\n".join([
        f"Ambiente: {r['comprimento']:.2f} m x {r['largura']:.2f} m = {r['area']:.2f} m²",
        f"Altura útil: {r['altura_util']:.2f} m   Índice do local: {r['indice_local']:.2f}",
        f"Fator de utilização: {r['fator_utilizacao']:.2f}   Fator de manutenção: {r['fator_manutencao']:.2f}",
        "",
        f"Luminárias calculadas: {r['quantidade_calculada']:.1f}",
        f"Malha: {r['nx']} x {r['ny']} = {r['quantidade']} luminárias",
        f"Espaçamento: {r['espacamento_x']:.2f} m x {r['espacamento_y']:.2f} m (metade até as paredes;"
        f" máximo {r['espacamento_maximo']:.2f} m)",
        f"Iluminância mantida resultante: {r['iluminancia_resultante']:.0f} lux (desejada: {r['iluminancia']:.0f} lux)",
        *[f"Aviso: {a}" for a in r.get("avisos", [])],
        "",
        "Pré-dimensionamento com fator de utilização genérico. Confira com o",
        "catálogo da luminária (iluminâncias: NBR ISO/CIE 8995-1 e antiga NBR 5413).",
    ])
