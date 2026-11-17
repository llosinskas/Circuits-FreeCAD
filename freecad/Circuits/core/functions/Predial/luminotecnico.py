"""Luminotécnico pelo método dos lúmens: quantas luminárias e onde colocá-las em um ambiente retangular.

Passos:

- índice do local: K = (C x L) / (Hu x (C + L)), com Hu = pé-direito - altura do
  plano de trabalho - suspensão da luminária;
- fator de utilização U estimado a partir de K;
- número de luminárias: N = E x A / (fluxo x U x Fm);
- malha de nx por ny luminárias, com o mesmo espaçamento em cada direção e meio
  espaçamento até as paredes.

ATENÇÃO: é um pré-dimensionamento. O fator de utilização vem de uma curva
genérica (luminária direta, teto e paredes claros), não do catálogo da
luminária, e as iluminâncias da lista são valores usuais. Confira com a
NBR ISO/CIE 8995-1 e com os dados do fabricante, ou informe o fator de
utilização do catálogo.

Unidades: comprimentos em m, iluminância em lux, fluxo em lúmens, potência em VA.
"""
import math

# Iluminância média usual por ambiente [lux]. "Personalizado" usa o valor informado.
PERSONALIZADO = "Personalizado"
ILUMINANCIAS = {
    "Sala e quarto (150 lx)": 150,
    "Cozinha e banheiro (200 lx)": 200,
    "Circulação e escada (100 lx)": 100,
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


def indice_do_local(comprimento, largura, altura_util):
    """Índice do local K para luminárias diretas."""
    if comprimento <= 0 or largura <= 0:
        raise ValueError("O comprimento e a largura do ambiente precisam ser maiores que zero.")
    if altura_util <= 0:
        raise ValueError("A luminária precisa ficar acima do plano de trabalho.")
    return (comprimento * largura) / (altura_util * (comprimento + largura))


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
    if iluminancia <= 0 or fluxo_luminaria <= 0:
        raise ValueError("A iluminância e o fluxo da luminária precisam ser maiores que zero.")
    if not 0 < fator_manutencao <= 1:
        raise ValueError("O fator de manutenção precisa estar entre 0 e 1.")
    altura_util = pe_direito - plano_trabalho - suspensao
    indice = indice_do_local(comprimento, largura, altura_util)
    utilizacao = fator_utilizacao_informado if fator_utilizacao_informado > 0 else fator_utilizacao(indice)
    area = comprimento * largura

    calculada = iluminancia * area / (fluxo_luminaria * utilizacao * fator_manutencao)
    nx, ny = malha(math.ceil(calculada - 1e-9), comprimento, largura)
    final = nx * ny
    return {
        "comprimento": comprimento,
        "largura": largura,
        "area": area,
        "altura_util": altura_util,
        "indice_local": indice,
        "fator_utilizacao": utilizacao,
        "fator_manutencao": fator_manutencao,
        "iluminancia": iluminancia,
        "quantidade_calculada": calculada,
        "nx": nx,
        "ny": ny,
        "quantidade": final,
        "iluminancia_resultante": final * fluxo_luminaria * utilizacao * fator_manutencao / area,
        "espacamento_x": comprimento / nx,
        "espacamento_y": largura / ny,
        "posicoes": posicoes(nx, ny, comprimento, largura),
    }


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
        f"Espaçamento: {r['espacamento_x']:.2f} m x {r['espacamento_y']:.2f} m (metade até as paredes)",
        f"Iluminância resultante: {r['iluminancia_resultante']:.0f} lux (desejada: {r['iluminancia']:.0f} lux)",
        "",
        "Pré-dimensionamento com fator de utilização genérico. Confira com a",
        "NBR ISO/CIE 8995-1 e com o catálogo da luminária.",
    ])
