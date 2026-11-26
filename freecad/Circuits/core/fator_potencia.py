"""Correção do fator de potência: banco de capacitores em estágios.

- Q = P·(tg φ1 − tg φ2), com o FP de referência 0,92 (o mínimo da regulação brasileira).
- Banco: estágios comerciais (``ESTAGIOS_KVAR``), os maiores enquanto couberem e o menor
  que completa a potência; o menor estágio dá o passo da regulação automática.
- Cabo e proteção do banco pela corrente nominal × 1,35 (``FATOR_PROJETO``: tolerância da
  capacitância e harmônicas).
- Ressonância paralela com a rede: fr = 60·√(Scc/Q); risco se fr fica a até
  ``TOLERANCIA_RESSONANCIA`` da 5ª ou da 7ª harmônica (aí o banco pede reator de dessintonia).

Potências em kW, kvar e kVA; tensão de linha em V; correntes em A.
"""
import math

FP_REFERENCIA = 0.92
FATOR_PROJETO = 1.35
FREQUENCIA = 60.0
ESTAGIOS_KVAR = [2.5, 5, 7.5, 10, 12.5, 15, 20, 25, 30, 40, 50]
HARMONICAS_RISCO = (5, 7)
TOLERANCIA_RESSONANCIA = 0.10


def _validar(fp):
    if not 0 < float(fp) <= 1:
        raise ValueError(f"fator de potência fora de 0 a 1: {fp}")


def potencia_reativa(potencia_kw, fp_atual, fp_desejado=FP_REFERENCIA):
    """kvar para levar o FP de ``fp_atual`` a ``fp_desejado``; 0 se já está corrigido."""
    _validar(fp_atual)
    _validar(fp_desejado)
    q = float(potencia_kw) * (math.tan(math.acos(fp_atual)) - math.tan(math.acos(fp_desejado)))
    return max(q, 0.0)


def banco(potencia_kvar):
    """Estágios do banco que cobrem a potência.

    Returns:
        {'estagios': [kvar], 'total', 'menor_estagio', 'pedida'}.
    """
    falta = float(potencia_kvar)
    maior = max(ESTAGIOS_KVAR)
    estagios = []
    while falta > maior:
        estagios.append(maior)
        falta -= maior
    if falta > 1e-9:
        estagios.append(next(e for e in ESTAGIOS_KVAR if e >= falta - 1e-9))
    return {"estagios": estagios, "total": float(sum(estagios)),
            "menor_estagio": min(estagios) if estagios else 0.0, "pedida": float(potencia_kvar)}


def corrente_capacitor(potencia_kvar, tensao):
    """Corrente nominal [A] de um banco trifásico."""
    return float(potencia_kvar) * 1e3 / (math.sqrt(3) * float(tensao))


def corrente_de_projeto(potencia_kvar, tensao):
    """Corrente para o cabo e a proteção do banco [A]: nominal × ``FATOR_PROJETO``."""
    return FATOR_PROJETO * corrente_capacitor(potencia_kvar, tensao)


def frequencia_ressonancia(potencia_curto_kva, potencia_kvar):
    """fr = 60·√(Scc/Q) [Hz]."""
    return FREQUENCIA * math.sqrt(float(potencia_curto_kva) / float(potencia_kvar))


def risco_ressonancia(potencia_curto_kva, potencia_kvar):
    """True se a ressonância cai perto da 5ª ou da 7ª harmônica."""
    if potencia_kvar <= 0:
        return False
    fr = frequencia_ressonancia(potencia_curto_kva, potencia_kvar)
    return any(abs(fr - h * FREQUENCIA) <= TOLERANCIA_RESSONANCIA * h * FREQUENCIA for h in HARMONICAS_RISCO)


def dimensionar(potencia_kw, fp_atual, fp_desejado=FP_REFERENCIA, tensao=380.0, potencia_curto_kva=0.0):
    """Banco para corrigir a instalação (argumentos do formulário ``core.formularios.FATOR_POTENCIA``)."""
    q = potencia_reativa(potencia_kw, fp_atual, fp_desejado)
    resultado = {"potencia_kw": float(potencia_kw), "fp_atual": float(fp_atual), "fp_desejado": float(fp_desejado),
                 "tensao": float(tensao), "potencia_reativa": q, "banco": banco(q) if q > 0 else None}
    total = resultado["banco"]["total"] if resultado["banco"] else 0.0
    resultado["corrente_nominal"] = corrente_capacitor(total, tensao) if total else 0.0
    resultado["corrente_projeto"] = corrente_de_projeto(total, tensao) if total else 0.0
    resultado["ressonancia"] = (frequencia_ressonancia(potencia_curto_kva, total)
                                if total and potencia_curto_kva > 0 else None)
    resultado["risco_ressonancia"] = bool(total and potencia_curto_kva > 0
                                          and risco_ressonancia(potencia_curto_kva, total))
    return resultado


def _br(valor, casas=1):
    return f"{valor:.{casas}f}".replace(".", ",")


def relatorio(r):
    """Texto do resultado para o formulário."""
    if not r["banco"]:
        return (f"O fator de potência {_br(r['fp_atual'], 2)} já atende {_br(r['fp_desejado'], 2)}: "
                "não precisa de banco de capacitores.")
    b = r["banco"]
    linhas = [
        f"Potência reativa: {_br(r['potencia_reativa'])} kvar ({_br(r['fp_atual'], 2)} → {_br(r['fp_desejado'], 2)})",
        f"Banco: {_br(b['total'])} kvar em {len(b['estagios'])} estágios: "
        + " + ".join(_br(e) for e in b["estagios"]) + " kvar",
        f"Menor estágio (passo da regulação): {_br(b['menor_estagio'])} kvar",
        f"Corrente nominal: {_br(r['corrente_nominal'])} A; de projeto (× {_br(FATOR_PROJETO, 2)}): "
        f"{_br(r['corrente_projeto'])} A — cabo e proteção do banco por ela",
    ]
    if r["ressonancia"]:
        linhas.append(f"Ressonância com a rede: {_br(r['ressonancia'], 0)} Hz"
                      + (" — perto da 5ª ou 7ª harmônica: use reator de dessintonia" if r["risco_ressonancia"]
                         else ""))
    return "\n".join(linhas)
