"""Quadro de cargas do quadro: carga por fase, desequilíbrio, sugestão de fases, reservas e DR por grupo.

Os circuitos são as linhas da planilha de circuitos, no formato de
``services.planilhas.ler_circuitos_completos``: ``N_circuito``, ``Destino``, ``Potencia``
(VA, aceita vírgula decimal), ``Fase_R``/``Fase_S``/``Fase_T``, ``DR`` e ``Grupo_DR`` (sim/não
como "True"/"False" ou S/N), ``Corrente``, ``Disjuntor`` e ``Cabo``.

Nada aqui grava na planilha: ``sugerir_fases`` só sugere (o usuário aceita ou não).
"""
from freecad.Circuits.core import balanceamento
from freecad.Circuits.core.quadro import reserva_de_circuitos

FASES = "RST"
RESERVA = "Reserva"
VERDADEIRO = {"true", "s", "sim", "1", "x", "yes"}


def numero(valor):
    """'1500,5' -> 1500.5; vazio ou inválido -> 0."""
    try:
        return float(str(valor).strip().replace(",", ".")) if str(valor).strip() else 0.0
    except ValueError:
        return 0.0


def sim(valor):
    return str(valor).strip().lower() in VERDADEIRO


def fases_do_circuito(circuito):
    """'R', 'RS', 'RST' pelas colunas Fase_R, Fase_S e Fase_T."""
    return "".join(f for f in FASES if sim(circuito.get(f"Fase_{f}", "")))


def eh_reserva(circuito):
    return str(circuito.get("Destino", "")).strip().lower() == RESERVA.lower()


def carga_por_fase(circuitos):
    """{'R', 'S', 'T': VA}: cada circuito divide a potência igualmente entre as fases dele."""
    carga = {f: 0.0 for f in FASES}
    for c in circuitos:
        fases = fases_do_circuito(c)
        if not fases:
            continue
        for f in fases:
            carga[f] += numero(c.get("Potencia")) / len(fases)
    return carga


def sem_fase(circuitos):
    """Números dos circuitos com potência e sem fase marcada (ficam fora da carga por fase)."""
    return [str(c["N_circuito"]) for c in circuitos
            if not eh_reserva(c) and not fases_do_circuito(c) and numero(c.get("Potencia")) > 0]


def desequilibrio(carga):
    """(maior − menor) / maior × 100 [%]; 0 sem carga."""
    return balanceamento.desequilibrio(carga)


def sugerir_fases(circuitos, fases_quadro=3):
    """Fases sugeridas {número: 'R'} que equilibram o quadro, sem mudar a quantidade de fases de
    cada circuito (bifásico continua bifásico) e sem alterar a entrada.

    Args:
        fases_quadro: 1 (tudo em R), 2 (R e S) ou 3.
    """
    fases = balanceamento.disponiveis(fases_quadro)
    entrada = [{"numero": str(c["N_circuito"]), "potencia": numero(c.get("Potencia")),
                "fases": fases_do_circuito(c)} for c in circuitos if not eh_reserva(c)]
    if not entrada:
        return {}
    return dict(balanceamento.balancear(entrada, fases)["fases"])


def _numero_do_circuito(circuito):
    try:
        return int(str(circuito["N_circuito"]).strip())
    except (KeyError, ValueError):
        return 0


def com_reservas(circuitos):
    """Os circuitos e as reservas da NBR 5410 (6.5.4.7) numeradas em seguida, sem potência nem fase."""
    linhas = [dict(c) for c in circuitos]
    ativos = [c for c in circuitos if not eh_reserva(c)]
    faltam = reserva_de_circuitos(len(ativos)) - (len(circuitos) - len(ativos))
    proximo = max((_numero_do_circuito(c) for c in circuitos), default=0) + 1
    modelo = {chave: "" for chave in (circuitos[0] if circuitos else {"N_circuito": ""})}
    for indice in range(max(faltam, 0)):
        reserva = dict(modelo, N_circuito=str(proximo + indice), Destino=RESERVA, Potencia="")
        reserva.update({f"Fase_{f}": "False" for f in FASES}, DR="False", Grupo_DR="")
        linhas.append(reserva)
    return linhas


def quadro_de_cargas(circuitos):
    """Linhas do quadro de cargas: uma por circuito e a de total.

    Returns:
        [{'circuito', 'descricao', 'potencia' (VA), 'R', 'S', 'T' (VA), 'corrente',
        'disjuntor', 'cabo'}], a última com ``circuito`` = 'Total'.
    """
    linhas = []
    total = {f: 0.0 for f in FASES}
    for c in circuitos:
        carga = carga_por_fase([c])
        for f in FASES:
            total[f] += carga[f]
        linhas.append({"circuito": str(c["N_circuito"]), "descricao": str(c.get("Destino", "")),
                       "potencia": numero(c.get("Potencia")), "R": carga["R"], "S": carga["S"], "T": carga["T"],
                       "corrente": str(c.get("Corrente", "")), "disjuntor": str(c.get("Disjuntor", "")),
                       "cabo": str(c.get("Cabo", ""))})
    linhas.append({"circuito": "Total", "descricao": f"Desequilíbrio {desequilibrio(total):.1f} %".replace(".", ","),
                   "potencia": sum(total.values()), "R": total["R"], "S": total["S"], "T": total["T"],
                   "corrente": "", "disjuntor": "", "cabo": ""})
    return linhas


def grupos_dr(circuitos):
    """DRs do quadro: [(nome, [números])].

    Circuitos com o mesmo ``Grupo_DR`` ficam sob um DR com esse nome (mesmo sem ``DR``
    marcado); com ``DR`` e sem grupo, um DR só do circuito, chamado ``C<n>``.
    """
    grupos, ordem = {}, []
    for c in circuitos:
        if eh_reserva(c):
            continue
        nome = str(c.get("Grupo_DR", "")).strip()
        if not nome and sim(c.get("DR", "")):
            nome = f"C{c['N_circuito']}"
        if not nome:
            continue
        if nome not in grupos:
            grupos[nome] = []
            ordem.append(nome)
        grupos[nome].append(str(c["N_circuito"]))
    return [(nome, grupos[nome]) for nome in ordem]


CABECALHO = ("Circuito", "Descrição", "Potência [VA]", "R [VA]", "S [VA]", "T [VA]", "Corrente [A]",
             "Disjuntor [A]", "Cabo [mm²]")


def tabela(circuitos):
    """Linhas para a planilha do quadro de cargas (cabeçalho e valores)."""
    return [CABECALHO] + [(l["circuito"], l["descricao"], l["potencia"], l["R"], l["S"], l["T"], l["corrente"],
                           l["disjuntor"], l["cabo"]) for l in quadro_de_cargas(circuitos)]
