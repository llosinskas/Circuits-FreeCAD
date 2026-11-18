"""Componentes de um quadro de distribuição, a partir dos dados e dos circuitos dele.

Sem FreeCAD. Monta a lista do que vai dentro do quadro: disjuntor geral, DPS,
disjuntores e DR dos circuitos, barramentos de fases, neutro e terra, e o
tamanho da caixa em módulos DIN.

Regras usadas (confira com o fabricante e com o projeto):

- reserva de circuitos conforme a NBR 5410, item 6.5.4.7: até 6 circuitos, 2 de
  reserva; de 7 a 12, 3; de 13 a 30, 4; acima de 30, 15 %;
- DR bipolar para circuitos com uma ou duas fases e tetrapolar para trifásicos,
  com corrente nominal igual ou acima da do disjuntor do circuito;
- DPS: um por fase, mais um para o neutro quando o quadro tem neutro;
- barramento de fases com corrente nominal igual ou acima da do disjuntor geral.

Unidades: correntes em A, tensões em V.
"""
import math

from freecad.Circuits.core import circuitos as calculo
from freecad.Circuits.core import nbr5410
from freecad.Circuits.core.simbolos import ILUM, TUG

CORRENTES_DR = [25, 40, 63, 80, 100, 125]
CORRENTES_BARRAMENTO = [50, 63, 80, 100, 125, 150, 200, 225, 250, 400, 630]
MODULOS_QUADRO = [6, 8, 12, 16, 18, 24, 28, 34, 36, 44, 48, 56, 70, 96]
SENSIBILIDADE_DR = "30mA"


def numero(texto, padrao=0.0):
    """Converte o texto de uma célula em número; vazio ou inválido devolve ``padrao``."""
    try:
        return float(str(texto).strip().replace(",", "."))
    except ValueError:
        return padrao


def verdadeiro(texto):
    return str(texto).strip().lower() in ("true", "1", "sim", "1.0")


def _formatar(valor):
    return f"{valor:.2f}".rstrip("0").rstrip(".")


def _comercial(valor, escala, nome):
    for item in escala:
        if item >= valor:
            return item
    raise ValueError(f"{nome} de {valor:g} acima do maior valor da tabela ({escala[-1]}).")


def dr_comercial(corrente):
    """Corrente nominal do DR para proteger um circuito com disjuntor de ``corrente`` [A]."""
    return _comercial(corrente, CORRENTES_DR, "DR")


def barramento_comercial(corrente):
    """Corrente nominal do barramento de fases para um disjuntor geral de ``corrente`` [A]."""
    return _comercial(corrente, CORRENTES_BARRAMENTO, "Barramento")


def reserva_de_circuitos(circuitos):
    """Circuitos de reserva exigidos pela NBR 5410, item 6.5.4.7."""
    if circuitos <= 0:
        return 0
    if circuitos <= 6:
        return 2
    if circuitos <= 12:
        return 3
    if circuitos <= 30:
        return 4
    return math.ceil(circuitos * 0.15)


def fases_do_circuito(circuito):
    """Número de fases marcadas no circuito (colunas Fase R, S e T). No mínimo 1."""
    marcadas = sum(verdadeiro(circuito.get(chave, "")) for chave in ("Fase_R", "Fase_S", "Fase_T"))
    return max(1, marcadas)


def completar(circuito, parametros=None):
    """Preenche corrente, cabo, disjuntor e curva que ficaram em branco na planilha.

    O cálculo é o de ``core.nbr5410.dimensionar_circuito``, com a potência em W
    tratada como VA, os ``parametros`` do projeto (isolação, temperatura, material,
    queda máxima; sem eles, PVC a 30 °C) e o ``Comprimento`` da linha, se houver,
    para a queda de tensão. Circuitos cuja descrição começa com "Ilum" usam a
    seção mínima de iluminação; os demais, a de tomadas. Sem potência ou tensão,
    ou com corrente acima das tabelas, o circuito volta como está. Com o disjuntor
    digitado e o cabo em branco, o cabo é escolhido para suportar esse disjuntor.
    """
    p = parametros or {}
    completo = dict(circuito)
    if not str(completo.get("Curva", "")).strip():
        completo["Curva"] = "C"
    potencia, tensao = numero(completo.get("Potencia")), numero(completo.get("Tensao"))
    em_branco = [chave for chave in ("Corrente", "Cabo", "Disjuntor") if not str(completo.get(chave, "")).strip()]
    if not em_branco or potencia <= 0 or tensao <= 0:
        return completo
    tipo = ILUM if str(completo.get("Destino", "")).strip().lower().startswith("ilum") else TUG
    n_fases = fases_do_circuito(completo)
    isolacao, temperatura = p.get("isolacao", "PVC"), p.get("temperatura_ambiente", 30.0)
    try:
        corrente = calculo.corrente_projeto(potencia, tensao, n_fases)
        calculado = nbr5410.dimensionar_circuito(
            corrente, tipo, numero(completo.get("Comprimento")), tensao, n_fases, temperatura=temperatura,
            isolacao=isolacao, queda_max=p.get("queda_terminal", 4.0), material=p.get("material", "cobre"))
    except ValueError:
        return completo
    valores = {"Corrente": corrente, "Cabo": calculado["secao"], "Disjuntor": calculado["disjuntor"]}
    digitado = numero(completo.get("Disjuntor"))
    if "Cabo" in em_branco and digitado > 0:
        # O cabo precisa suportar o disjuntor que o usuário escolheu, não o calculado.
        carregados, fator = 3 if n_fases == 3 else 2, nbr5410.fct(temperatura, isolacao)
        minima = calculo.SECAO_MINIMA.get(tipo, 2.5)
        comprimento, queda_max = numero(completo.get("Comprimento")), p.get("queda_terminal", 4.0)
        cabo = next((s for s in nbr5410.SECOES if s >= minima
                     and nbr5410.capacidade(s, "B1", carregados, isolacao) * fator >= digitado
                     and nbr5410.queda_tensao(corrente, comprimento, s, tensao, n_fases,
                                              material=p.get("material", "cobre")) <= queda_max), None)
        if cabo is None:
            em_branco.remove("Cabo")  # acima da tabela: fica em branco para o usuário decidir
        else:
            valores["Cabo"] = cabo
    for chave in em_branco:
        completo[chave] = _formatar(valores[chave])
    return completo


def _item(item, especificacao, quantidade, unidade="un"):
    return {"item": item, "especificacao": especificacao, "quantidade": quantidade, "unidade": unidade}


def _agrupar(nome, especificacoes):
    """Um item por especificação diferente, com a quantidade de vezes que ela aparece."""
    contagem = {}
    for especificacao in especificacoes:
        contagem[especificacao] = contagem.get(especificacao, 0) + 1
    return [_item(nome, especificacao, quantidade) for especificacao, quantidade in contagem.items()]


def componentes(quadro, circuitos):
    """Lista de componentes do quadro.

    Args:
        quadro: dados da linha 3 da planilha, pelas chaves de
            ``core.planilha.CABECALHO_QUADRO`` (valores em texto ou número).
        circuitos: linhas de circuito, pelas chaves de ``core.planilha.COLUNAS_CIRCUITO``.
    Returns:
        Lista de dicionários com ``item``, ``especificacao``, ``quantidade`` e ``unidade``,
        na ordem de montagem do quadro.
    """
    fases = max(1, min(3, int(numero(quadro.get("numero_fases"), 1))))
    tem_neutro = verdadeiro(quadro.get("neutro", ""))
    tem_terra = verdadeiro(quadro.get("terra", ""))
    geral = numero(quadro.get("corrente_nominal_disjuntor"))
    reserva = reserva_de_circuitos(len(circuitos))
    itens = []
    modulos = 0

    # Disjuntor geral
    if geral > 0:
        curva = str(quadro.get("curva_disjuntor", "")).strip()
        interrupcao = numero(quadro.get("corrente_curto_circuito"))
        especificacao = f"{fases}P {_formatar(geral)} A curva {curva}"
        if interrupcao > 0:
            especificacao += f", {_formatar(interrupcao)} kA"
        itens.append(_item("Disjuntor geral", especificacao, 1))
        modulos += fases

    # DPS
    if verdadeiro(quadro.get("DPS", "")):
        quantidade = fases + (1 if tem_neutro else 0)
        especificacao = (
            f"Classe {str(quadro.get('classe_DPS', '')).strip()}, "
            f"{_formatar(numero(quadro.get('tensao_DPS')))} V, {_formatar(numero(quadro.get('corrente_DPS')))} kA"
        )
        itens.append(_item("DPS", especificacao, quantidade))
        modulos += quantidade

    # DR e disjuntores dos circuitos
    drs, disjuntores = [], []
    for circuito in circuitos:
        polos = fases_do_circuito(circuito)
        corrente = numero(circuito.get("Disjuntor"))
        if corrente > 0:
            disjuntores.append(f"{polos}P {_formatar(corrente)} A curva {str(circuito.get('Curva', '')).strip()}")
            modulos += polos
        if verdadeiro(circuito.get("DR", "")):
            polos_dr = 4 if polos == 3 else 2
            sensibilidade = str(circuito.get("Corrente_DR", "")).strip() or SENSIBILIDADE_DR
            drs.append(f"{polos_dr}P {dr_comercial(max(corrente, CORRENTES_DR[0]))} A, {sensibilidade}")
            modulos += polos_dr
    itens += _agrupar("Interruptor DR", drs)
    itens += _agrupar("Disjuntor de circuito", disjuntores)

    # Barramentos
    if geral > 0:
        tipo = {1: "monofásico", 2: "bifásico", 3: "trifásico"}[fases]
        itens.append(_item("Barramento de fases", f"{tipo}, {barramento_comercial(geral)} A", 1))
    if tem_neutro:
        terminais = sum(verdadeiro(c.get("Neutro", "")) for c in circuitos) + reserva + 1
        itens.append(_item("Barramento de neutro", f"{terminais} terminais", 1))
    if tem_terra:
        terminais = sum(verdadeiro(c.get("Terra", "")) for c in circuitos) + reserva + 1
        itens.append(_item("Barramento de terra (PE)", f"{terminais} terminais", 1))

    # Caixa do quadro: os módulos ocupados mais um módulo por circuito de reserva.
    necessarios = modulos + reserva
    if necessarios > 0:
        material = str(quadro.get("material_quadro", "")).strip()
        especificacao = f"{_comercial(necessarios, MODULOS_QUADRO, 'Quadro')} módulos DIN"
        especificacao += f" ({modulos} ocupados + {reserva} de reserva)"
        if material:
            especificacao += f", {material}"
        itens.insert(0, _item("Quadro de distribuição", especificacao, 1))
    return itens


def corrente_do_barramento(quadro):
    """Corrente nominal do barramento de fases, ou None se o quadro não tem disjuntor geral."""
    geral = numero(quadro.get("corrente_nominal_disjuntor"))
    return barramento_comercial(geral) if geral > 0 else None
