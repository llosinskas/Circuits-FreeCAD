"""Quadro de distribuição em 3D com os componentes montados nos trilhos DIN.

A partir dos dados do quadro (linha 3 da planilha) e dos circuitos (``core.quadro``), monta a lista dos
dispositivos na ordem de montagem (disjuntor geral, DPS, IDR, cada DR com os circuitos dele, os
disjuntores dos circuitos), distribui os módulos nas fileiras e devolve as peças em caixas (blocos):
caixa de embutir, placa de fundo, trilhos, dispositivos com a alavanca, barramentos de fases, neutro e
terra com os isoladores, porta e a identificação de cada fileira.

Sistema local, em mm: x na largura (0 no centro), y na profundidade (porta em −P/2, virada para a vista de
frente do FreeCAD, e fundo em +P/2) e z na altura (0 no centro do quadro). O serviço põe o centro na altura de montagem do símbolo.
"""
import math

from freecad.Circuits.core import quadro as regras

MODULO_MM = 18.0          # largura de um módulo DIN (17,5 a 18 mm)
PASSO_FILEIRA_MM = 125.0  # distância entre trilhos
MARGEM_LATERAL_MM = 55.0
MARGEM_TOPO_MM = 110.0    # barramento de fases
MARGEM_BASE_MM = 110.0    # barramentos de neutro e terra
PROFUNDIDADE_MM = 110.0
PAREDE_MM = 2.0
TRILHO_MM = (35.0, 7.5)   # largura (z) e altura (y) do trilho TS35
CORPO_MM = (90.0, 68.0)   # altura (z) e profundidade (y) do dispositivo
ALAVANCA_MM = (10.0, 14.0, 12.0)  # largura (x), saliência (y), altura (z)
FOLGA_PORTA_MM = 8.0

CORES = {
    "caixa": (0.82, 0.83, 0.85), "fundo": (0.92, 0.92, 0.90), "trilho": (0.70, 0.71, 0.74),
    "geral": (0.97, 0.97, 0.97), "disjuntor": (0.97, 0.97, 0.97), "dr": (0.90, 0.94, 1.00),
    "idr": (0.90, 0.94, 1.00), "dps": (0.55, 0.60, 0.66), "alavanca": (0.12, 0.12, 0.12),
    "fases": (0.80, 0.45, 0.20), "neutro": (0.15, 0.35, 0.85), "terra": (0.15, 0.60, 0.20),
    "isolador": (0.85, 0.20, 0.15), "porta": (0.55, 0.60, 0.65),
}
NOMES = {"geral": "Disjuntor geral", "dps": "DPS", "idr": "Interruptor DR geral (IDR)", "dr": "Interruptor DR",
         "disjuntor": "Disjuntor"}


def _formatar(valor):
    return f"{valor:g}".replace(".", ",")


def dispositivos(quadro, circuitos):
    """Dispositivos na ordem de montagem.

    Returns:
        [{'tipo', 'polos', 'especificacao', 'circuitos' (lista de rótulos C<n>), 'rotulo'}] e a quantidade de
        módulos de reserva.
    """
    fases = max(1, min(3, int(regras.numero(quadro.get("numero_fases"), 1))))
    tem_neutro = regras.verdadeiro(quadro.get("neutro", ""))
    lista = []
    geral = regras.numero(quadro.get("corrente_nominal_disjuntor"))
    if geral > 0:
        curva = str(quadro.get("curva_disjuntor", "")).strip()
        lista.append({"tipo": "geral", "polos": fases, "circuitos": [],
                      "especificacao": f"{fases}P {_formatar(geral)} A {curva}".strip()})
    if regras.verdadeiro(quadro.get("DPS", "")):
        for i in range(fases + (1 if tem_neutro else 0)):
            condutor = "N" if i == fases else "RST"[i] if fases > 1 else "F"
            lista.append({"tipo": "dps", "polos": 1, "circuitos": [], "especificacao": f"DPS {condutor}"})
    idr = regras.idr_geral(quadro)
    if idr:
        lista.append({"tipo": "idr", "polos": idr["polos"], "circuitos": [], "especificacao": idr["especificacao"]})

    def rotulo(c):
        texto = str(c.get("N_circuito", c.get("Circuito", ""))).strip()
        return texto if texto.upper().startswith("C") else f"C{texto}"

    def disjuntor(c):
        corrente = regras.numero(c.get("Disjuntor"))
        if corrente <= 0:
            return None
        polos = regras.fases_do_circuito(c)
        return {"tipo": "disjuntor", "polos": polos, "circuitos": [rotulo(c)],
                "especificacao": f"{polos}P {_formatar(corrente)} A {str(c.get('Curva', '')).strip()}".strip()}

    grupos, feitos = {}, set()
    for c in circuitos:
        if regras.grupo_dr(c):
            grupos.setdefault(regras.grupo_dr(c), []).append(c)
    for c in circuitos:  # na ordem dos circuitos, cada DR antes dos disjuntores dele
        grupo = regras.grupo_dr(c)
        if grupo:
            if grupo in feitos:
                continue
            feitos.add(grupo)
            membros = grupos[grupo]
            dr = regras.dr_do_grupo(membros)
            lista.append({"tipo": "dr", "polos": dr["polos"], "circuitos": [rotulo(m) for m in membros],
                          "especificacao": f"DR {grupo} {dr['especificacao']}"})
            lista += [d for d in (disjuntor(m) for m in membros) if d]
            continue
        if regras.verdadeiro(c.get("DR", "")):
            dr = regras.dr_do_circuito(c)
            lista.append({"tipo": "dr", "polos": dr["polos"], "circuitos": [rotulo(c)],
                          "especificacao": f"DR {dr['especificacao']}"})
        d = disjuntor(c)
        if d:
            lista.append(d)
    for d in lista:
        d["rotulo"] = " ".join(d["circuitos"] + [NOMES[d["tipo"]], d["especificacao"]]) if d["circuitos"] \
            else f"{NOMES[d['tipo']]} {d['especificacao']}"
    return lista, regras.reserva_de_circuitos(len(circuitos))


def fileiras(modulos):
    """(módulos por fileira, fileiras) da caixa comercial que cabe ``modulos``."""
    total = regras._comercial(max(1, modulos), regras.MODULOS_QUADRO, "Quadro") \
        if modulos <= regras.MODULOS_QUADRO[-1] else modulos
    por_fileira = 12 if total <= 48 else 18 if total <= 72 else 24
    return por_fileira, max(1, math.ceil(total / por_fileira))


def distribuir(lista, por_fileira):
    """Posição (fileira, módulo inicial) de cada dispositivo; quem não cabe no fim da fileira vai à próxima."""
    fileira, modulo, posicoes = 0, 0, []
    for d in lista:
        if modulo + d["polos"] > por_fileira and modulo > 0:
            fileira, modulo = fileira + 1, 0
        posicoes.append((fileira, modulo))
        modulo += d["polos"]
    return posicoes, fileira + 1


def _bloco(x0, y0, z0, dx, dy, dz):
    return {"origem": (x0, y0, z0), "dims": (dx, dy, dz)}


def montar(quadro, circuitos):
    """Peças 3D do quadro.

    Returns:
        {'dimensoes': (largura, profundidade, altura), 'por_fileira', 'fileiras', 'modulos_ocupados',
         'reserva', 'pecas': [{'tipo', 'rotulo', 'especificacao', 'circuitos', 'cor', 'blocos'}]}.
    """
    lista, reserva = dispositivos(quadro, circuitos)
    ocupados = sum(d["polos"] for d in lista)
    por_fileira, n_fileiras = fileiras(ocupados + reserva)
    posicoes, usadas = distribuir(lista, por_fileira)
    n_fileiras = max(n_fileiras, usadas)
    largura = por_fileira * MODULO_MM + 2 * MARGEM_LATERAL_MM
    altura = n_fileiras * PASSO_FILEIRA_MM + MARGEM_TOPO_MM + MARGEM_BASE_MM
    prof = PROFUNDIDADE_MM
    x0, z_topo, y_fundo = -largura / 2, altura / 2, -prof / 2
    t = PAREDE_MM
    pecas = []

    def peca(tipo, rotulo, blocos, especificacao="", circuitos_=()):
        pecas.append({"tipo": tipo, "rotulo": rotulo, "especificacao": especificacao, "circuitos": list(circuitos_),
                      "cor": CORES.get(tipo, (0.7, 0.7, 0.7)), "blocos": blocos})

    peca("caixa", "Caixa do quadro", [
        _bloco(x0, y_fundo, -altura / 2, largura, t, altura),                      # fundo
        _bloco(x0, y_fundo, -altura / 2, t, prof, altura),                         # lateral esquerda
        _bloco(-x0 - t, y_fundo, -altura / 2, t, prof, altura),                    # lateral direita
        _bloco(x0, y_fundo, z_topo - t, largura, prof, t),                         # topo
        _bloco(x0, y_fundo, -altura / 2, largura, prof, t),                        # base
    ], f"{por_fileira * n_fileiras} módulos DIN, {largura:.0f} x {altura:.0f} x {prof:.0f} mm")
    y_placa = y_fundo + t
    peca("fundo", "Placa de montagem", [_bloco(x0 + 15, y_placa, -altura / 2 + 15, largura - 30, 2.0, altura - 30)])
    y_trilho = y_placa + 2.0 + 8.0  # espaçadores do trilho
    largura_trilho = por_fileira * MODULO_MM + 20.0
    centros = [z_topo - MARGEM_TOPO_MM - PASSO_FILEIRA_MM * (i + 0.5) for i in range(n_fileiras)]
    peca("trilho", "Trilhos DIN TS35", [_bloco(-largura_trilho / 2, y_trilho, zc - TRILHO_MM[0] / 2, largura_trilho,
                                              TRILHO_MM[1], TRILHO_MM[0]) for zc in centros])
    y_corpo = y_trilho + TRILHO_MM[1]
    alto, fundo_corpo = CORPO_MM
    alavancas = []
    x_inicio = -por_fileira * MODULO_MM / 2
    for d, (fileira, modulo) in zip(lista, posicoes):
        zc = centros[fileira]
        xd = x_inicio + modulo * MODULO_MM
        largura_d = d["polos"] * MODULO_MM - 0.6
        blocos = [_bloco(xd + 0.3, y_corpo, zc - alto / 2, largura_d, fundo_corpo * 0.55, alto),       # base larga
                  _bloco(xd + 0.3, y_corpo, zc - alto * 0.25, largura_d, fundo_corpo, alto * 0.5)]    # frente
        if d["tipo"] in ("dr", "idr"):  # botão de teste
            blocos.append(_bloco(xd + largura_d - 7, y_corpo + fundo_corpo, zc + alto * 0.12, 5, 3, 5))
        peca(d["tipo"], d["rotulo"], blocos, d["especificacao"], d["circuitos"])
        if d["tipo"] != "dps":
            ax, ay, az = ALAVANCA_MM
            largura_alavanca = min(largura_d - 4, ax + (d["polos"] - 1) * MODULO_MM)
            alavancas.append(_bloco(xd + 0.3 + (largura_d - largura_alavanca) / 2, y_corpo + fundo_corpo,
                                    zc - az / 2, largura_alavanca, ay, az))
    if alavancas:
        peca("alavanca", "Alavancas", alavancas)
    # Barramento de fases no alto, neutro e terra embaixo, sobre isoladores.
    fases = max(1, min(3, int(regras.numero(quadro.get("numero_fases"), 1))))
    comprimento_barra = largura - 2 * MARGEM_LATERAL_MM + 30
    isoladores = []

    def barra(z, comprimento, espessura=5.0, altura_barra=20.0):
        isoladores.extend(_bloco(sx - 9, y_placa + 2, z - 9, 18, 20, 18)
                          for sx in (-comprimento / 2 + 15, comprimento / 2 - 15))
        return _bloco(-comprimento / 2, y_placa + 22, z - altura_barra / 2, comprimento, espessura, altura_barra)

    z_fases = z_topo - MARGEM_TOPO_MM / 2
    barras = [barra(z_fases + (i - (fases - 1) / 2) * 26.0, comprimento_barra) for i in range(fases)]
    especificacao_fases = f"{fases} barra(s)"
    corrente = regras.corrente_do_barramento(quadro)
    if corrente:
        especificacao_fases += f", {corrente} A"
    peca("fases", "Barramento de fases", barras, especificacao_fases)
    z_base = -altura / 2 + MARGEM_BASE_MM / 2
    if regras.verdadeiro(quadro.get("neutro", "")):
        peca("neutro", "Barramento de neutro", [barra(z_base + 16, comprimento_barra * 0.45)])
    if regras.verdadeiro(quadro.get("terra", "")):
        peca("terra", "Barramento de terra (PE)", [barra(z_base - 16, comprimento_barra * 0.45)])
    if isoladores:
        peca("isolador", "Isoladores", isoladores)
    peca("porta", "Porta", [_bloco(x0, -y_fundo, -altura / 2, largura, 2.0, altura)])
    for p in pecas:  # monta com a porta em +y e espelha: a frente fica em −y
        for b in p["blocos"]:
            (x, y, z), (dx, dy, dz) = b["origem"], b["dims"]
            b["origem"] = (x, -(y + dy), z)
    return {"dimensoes": (largura, prof, altura), "por_fileira": por_fileira, "fileiras": n_fileiras,
            "modulos_ocupados": ocupados, "reserva": reserva, "pecas": pecas}
