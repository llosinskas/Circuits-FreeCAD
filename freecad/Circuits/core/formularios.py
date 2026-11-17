"""Campos dos formulários de cálculo, sem FreeCAD nem Qt.

Cada formulário é uma lista de campos, na ordem em que aparecem. Um campo é um
dicionário com:

    chave      nome do dado devolvido pelo formulário
    rotulo     texto ao lado da entrada
    valor      valor inicial: inteiro, decimal ou lista de opções
    dica       explicação mostrada quando o mouse para sobre o campo
    avancado   True coloca o campo em "Opções avançadas", fechadas no início
    minimo, maximo, decimais, sufixo   limites e unidade dos campos numéricos
    preenche   só em listas: {opção: {chave de outro campo: valor}}; escolher
               a opção preenche esses outros campos

A ideia é o usuário responder poucas perguntas, com opções prontas, e só abrir
as opções avançadas quando tiver os dados do catálogo ou do projeto.
"""
from freecad.Circuits.core.functions.Predial import luminotecnico, pressurizacao, recalque
from freecad.Circuits.core.simbolos import CATALOGO, ILUMINACAO

# Rótulo da alimentação -> (tensão [V], fases)
ALIMENTACOES = {
    "Trifásico 380 V": (380, 3),
    "Trifásico 220 V": (220, 3),
    "Monofásico 220 V": (220, 2),
    "Monofásico 127 V": (127, 1),
}
TRIFASICAS = [rotulo for rotulo, (_, fases) in ALIMENTACOES.items() if fases == 3]

# Legenda do símbolo de iluminação -> chave do catálogo
SIMBOLOS_ILUMINACAO = {dados["legenda"]: chave for chave, dados in CATALOGO.items() if dados["categoria"] == ILUMINACAO}

OUTRA = "Outra (informar nas opções avançadas)"
# Lâmpadas e luminárias usuais: fluxo [lm] e potência [VA] aproximados.
LAMPADAS = {
    "Lâmpada LED 9 W (cerca de 800 lm)": {"fluxo_luminaria": 800.0, "potencia": 9.0, "simbolo": "Luz de teto"},
    "Lâmpada LED 12 W (cerca de 1000 lm)": {"fluxo_luminaria": 1000.0, "potencia": 12.0, "simbolo": "Luz de teto"},
    "Lâmpada LED 15 W (cerca de 1500 lm)": {"fluxo_luminaria": 1500.0, "potencia": 15.0, "simbolo": "Luz de teto"},
    "Spot LED 7 W (cerca de 500 lm)": {"fluxo_luminaria": 500.0, "potencia": 7.0, "simbolo": "Luz embutida"},
    "Painel LED 24 W (cerca de 1900 lm)": {"fluxo_luminaria": 1900.0, "potencia": 24.0, "simbolo": "Luz embutida"},
    "Painel LED 40 W (cerca de 3600 lm)": {"fluxo_luminaria": 3600.0, "potencia": 40.0, "simbolo": "Luz embutida"},
    "Tubular LED 18 W (cerca de 1850 lm)": {"fluxo_luminaria": 1850.0, "potencia": 18.0, "simbolo": "Luminária tubular"},
    "Luminária 2 x tubular LED 18 W (cerca de 3700 lm)": {
        "fluxo_luminaria": 3700.0, "potencia": 36.0, "simbolo": "Luminária tubular",
    },
    OUTRA: {},
}

LUMINOTECNICO = [
    {
        "chave": "ambiente", "rotulo": "Tipo de ambiente", "valor": list(luminotecnico.ILUMINANCIAS),
        "dica": "Define a iluminância desejada. Em Personalizado, informe o valor nas opções avançadas.",
    },
    {
        "chave": "lampada", "rotulo": "Lâmpada ou luminária", "valor": list(LAMPADAS), "preenche": LAMPADAS,
        "dica": "Preenche o fluxo luminoso, a potência e o símbolo. Os valores são aproximados.",
    },
    {
        "chave": "circuito", "rotulo": "Circuito das luminárias", "valor": 1, "minimo": 1, "maximo": 999,
        "dica": "Número do circuito que as luminárias criadas vão receber.",
    },
    {
        "chave": "pe_direito", "rotulo": "Pé-direito", "valor": 2.7, "minimo": 1.8, "maximo": 30.0, "sufixo": "m",
        "dica": "Altura do piso ao teto.",
    },
    {
        "chave": "iluminancia", "rotulo": "Iluminância (só para Personalizado)", "avancado": True,
        "valor": 300.0, "minimo": 10.0, "maximo": 5000.0, "decimais": 0, "sufixo": "lux",
        "dica": "Usada só quando o tipo de ambiente é Personalizado.",
    },
    {
        "chave": "fluxo_luminaria", "rotulo": "Fluxo luminoso de cada luminária", "avancado": True,
        "valor": 800.0, "minimo": 50.0, "maximo": 100000.0, "decimais": 0, "sufixo": "lm",
        "dica": "Está na embalagem ou no catálogo da lâmpada, em lúmens.",
    },
    {
        "chave": "potencia", "rotulo": "Potência de cada luminária", "avancado": True,
        "valor": 9.0, "minimo": 1.0, "maximo": 5000.0, "decimais": 0, "sufixo": "VA",
        "dica": "Potência que cada luminária soma ao circuito.",
    },
    {
        "chave": "simbolo", "rotulo": "Símbolo na planta", "avancado": True, "valor": list(SIMBOLOS_ILUMINACAO),
        "dica": "Símbolo desenhado para cada luminária.",
    },
    {
        "chave": "plano_trabalho", "rotulo": "Altura do plano de trabalho", "avancado": True,
        "valor": luminotecnico.PLANO_DE_TRABALHO, "minimo": 0.0, "maximo": 3.0, "sufixo": "m",
        "dica": "Altura de mesas e bancadas. Use 0 para iluminar o piso (garagem, circulação).",
    },
    {
        "chave": "suspensao", "rotulo": "Luminária abaixo do teto", "avancado": True,
        "valor": 0.0, "minimo": 0.0, "maximo": 20.0, "sufixo": "m",
        "dica": "Distância do teto à luminária, para pendentes.",
    },
    {
        "chave": "fator_utilizacao_informado", "rotulo": "Fator de utilização do catálogo (0 = estimar)",
        "avancado": True, "valor": 0.0, "minimo": 0.0, "maximo": 1.0,
        "dica": "Deixe 0 para o programa estimar pelo formato do ambiente.",
    },
]

PRESSURIZACAO = [
    {
        "chave": "numero_portas", "rotulo": "Portas da escada", "valor": 12, "minimo": 1, "maximo": 200,
        "dica": "Em geral uma porta por pavimento, mais a da descarga.",
    },
    {
        "chave": "portas_abertas", "rotulo": "Portas abertas ao mesmo tempo", "valor": 2, "minimo": 0, "maximo": 20,
        "dica": "Critério da norma e do Corpo de Bombeiros para o edifício.",
    },
    {"chave": "alimentacao", "rotulo": "Alimentação do motor", "valor": TRIFASICAS, "dica": "Tensão da rede do edifício."},
    {
        "chave": "tipo_porta", "rotulo": "Tipo de porta", "avancado": True, "valor": list(pressurizacao.AREA_FRESTA),
        "dica": "Define a área de fresta por onde o ar escapa com a porta fechada.",
    },
    {
        "chave": "largura_porta", "rotulo": "Largura da porta", "avancado": True,
        "valor": 0.9, "minimo": 0.5, "maximo": 3.0, "sufixo": "m", "dica": "Vão livre da porta.",
    },
    {
        "chave": "altura_porta", "rotulo": "Altura da porta", "avancado": True,
        "valor": 2.1, "minimo": 1.5, "maximo": 3.0, "sufixo": "m", "dica": "Vão livre da porta.",
    },
    {
        "chave": "duto", "rotulo": "Duto de insuflamento", "avancado": True, "valor": list(pressurizacao.ACRESCIMO_DUTO),
        "dica": "O duto de alvenaria vaza mais que o metálico.",
    },
    {
        "chave": "pressao_total_ventilador", "rotulo": "Pressão total do ventilador", "avancado": True,
        "valor": 500.0, "minimo": 50.0, "maximo": 3000.0, "decimais": 0, "sufixo": "Pa",
        "dica": "Os 50 Pa da escada mais as perdas em dutos, grelhas e veneziana.",
    },
]

RECALQUE = [
    {
        "chave": "populacao", "rotulo": "Pessoas atendidas", "valor": 80, "minimo": 1, "maximo": 100000,
        "dica": "Em apartamentos, conte duas pessoas por dormitório.",
    },
    {
        "chave": "altura_geometrica", "rotulo": "Desnível entre os reservatórios", "valor": 40.0,
        "minimo": 0.0, "maximo": 300.0, "sufixo": "m",
        "dica": "Do nível da água no reservatório inferior até a entrada do superior.",
    },
    {
        "chave": "comprimento_tubulacao", "rotulo": "Comprimento da tubulação", "valor": 60.0,
        "minimo": 0.0, "maximo": 2000.0, "sufixo": "m", "dica": "Sucção mais recalque, medido no trajeto do tubo.",
    },
    {"chave": "alimentacao", "rotulo": "Alimentação do motor", "valor": list(ALIMENTACOES), "dica": "Tensão da rede do edifício."},
    {
        "chave": "consumo_por_pessoa", "rotulo": "Consumo por pessoa", "avancado": True,
        "valor": recalque.CONSUMO_POR_PESSOA, "minimo": 1.0, "maximo": 1000.0, "decimais": 0, "sufixo": "L/dia",
        "dica": "200 L por dia é o usual em apartamentos.",
    },
    {
        "chave": "horas", "rotulo": "Funcionamento da bomba por dia", "avancado": True,
        "valor": recalque.HORAS_FUNCIONAMENTO, "minimo": 0.5, "maximo": 24.0, "decimais": 1, "sufixo": "h",
        "dica": "Tempo para a bomba repor o consumo do dia.",
    },
    {
        "chave": "material", "rotulo": "Material da tubulação", "avancado": True,
        "valor": list(recalque.COEFICIENTE_HAZEN_WILLIAMS), "dica": "Muda a perda de carga no tubo.",
    },
    {
        "chave": "rendimento", "rotulo": "Rendimento da bomba", "avancado": True,
        "valor": recalque.RENDIMENTO_BOMBA, "minimo": 0.1, "maximo": 1.0,
        "dica": "Do catálogo da bomba. Bombas pequenas ficam perto de 0,5.",
    },
]


def padroes(campos):
    """Valor inicial de cada campo: a primeira opção, nas listas, ou o próprio valor."""
    return {campo["chave"]: campo["valor"][0] if isinstance(campo["valor"], list) else campo["valor"] for campo in campos}


def valores_iniciais(campos):
    """Padrões já com os preenchimentos da primeira opção de cada lista de predefinições."""
    valores = padroes(campos)
    for campo in campos:
        if "preenche" in campo:
            valores.update(campo["preenche"].get(valores[campo["chave"]], {}))
    return valores


def converter(campo, texto):
    """Converte o texto guardado nas preferências no tipo do campo; inválido devolve None."""
    valor = campo["valor"]
    try:
        if isinstance(valor, list):
            return texto if texto in valor else None
        numero = int(float(texto)) if isinstance(valor, int) else float(texto)
    except (TypeError, ValueError):
        return None
    if numero < campo.get("minimo", 0) or numero > campo.get("maximo", 1000000):
        return None
    return numero
