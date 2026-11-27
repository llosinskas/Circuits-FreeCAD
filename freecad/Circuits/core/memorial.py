"""Memorial descritivo e de cálculo do projeto, sem FreeCAD.

``montar(dados)`` recebe o que ``services.memorial.coletar`` leu do documento e devolve as
seções do relatório como blocos simples, que o PDF (``services.pdf_generator``) só desenha:

- ``("paragrafo", texto)``, ``("formula", texto)``, ``("lista", [textos])``, ``("aviso", texto)``,
- ``("tabela", cabeçalho, linhas, larguras relativas ou None)``,
- ``("subtitulo", texto)``.

Cada cálculo aparece com a fórmula, os valores substituídos e a conclusão (atende ou não),
como num memorial de cálculo. Os circuitos são **verificados** com o cabo e o disjuntor
adotados na planilha de circuitos (``verificar_circuito``), não redimensionados.

Unidades: potências em VA ou W, tensões em V, correntes em A, seções em mm², comprimentos em m.
"""
import math

from freecad.Circuits.core import nbr5410, quadro as regras_quadro, quadro_cargas
from freecad.Circuits.core import centro_medicao as regras_centro
from freecad.Circuits.core import curto as regras_curto
from freecad.Circuits.core.functions.Predial import aterramento as regras_aterramento
from freecad.Circuits.core.functions.Predial import demanda as regras_demanda
from freecad.Circuits.core.functions.Predial import luminotecnico as regras_luminotecnico
from freecad.Circuits.core.simbolos import ILUM, TUE, TUG

NORMAS = [
    "ABNT NBR 5410:2004 — Instalações elétricas de baixa tensão",
    "ABNT NBR 5419 — Proteção contra descargas atmosféricas (DPS e equipotencialização)",
    "IEC 60364-5-52, anexo G — Queda de tensão",
    "IEC 60909-0 — Correntes de curto-circuito em sistemas trifásicos",
    "ABNT NBR ISO/CIE 8995-1 — Iluminação de ambientes de trabalho (e a antiga NBR 5413 nas residências)",
    "ABNT NBR 10068 e NBR 10582 — Folhas de desenho e carimbo",
]
NORMA_ENEL = "Enel SP — Especificação técnica 0018 (fornecimento em tensão secundária, conexão coletiva)"

ROTULOS_CRITERIO = {"secao_minima": "seção mínima", "capacidade": "capacidade de condução",
                    "queda_tensao": "queda de tensão", "curto_circuito": "curto-circuito"}
PALAVRAS_TUE = ("chuveiro", "ar ", "ar-cond", "ar cond", "split", "torneira", "forno", "motor", "bomba",
                "aquecedor", "secadora", "lava", "cooktop", "micro", "elevador", "portão", "força")

LIMITACOES = [
    "Tabelas da NBR 5410:2004 transcritas na bancada; confira com o texto da norma.",
    "Método de instalação B1 (eletroduto embutido) em todos os circuitos; cos φ = 1 na queda de tensão "
    "(caso mais desfavorável nos cabos finos).",
    "Fatores de demanda de guias de instalações residenciais: confira com a norma da concessionária.",
    "Curto-circuito sem contribuição de motores; a fase-terra mínima usa o condutor de proteção igual à fase.",
    "Luminotécnico pelo método dos lúmens, com fator de utilização de uma curva genérica (luminária direta, "
    "refletâncias claras) quando o do catálogo não foi informado; não verifica uniformidade nem ofuscamento.",
    "Aterramento por hastes em linha (fórmula de Dwight e fator λ da IEEE 142); a resistividade do solo deve "
    "ser medida (método de Wenner) e a resistência máxima conferida com a NBR 5410 e a NBR 5419.",
    "Valores de catálogo genéricos (disjuntores, DR, contatores, eletrodutos e cabos): confira com o fabricante.",
]


# --- números -------------------------------------------------------------------------------------

def numero(valor, padrao=0.0):
    try:
        texto = str(valor).strip().replace(",", ".")
        return float(texto) if texto else padrao
    except (TypeError, ValueError):
        return padrao


def br(valor, casas=2):
    """Número com vírgula decimal: br(3.14159) -> '3,14'."""
    return f"{float(valor):.{casas}f}".replace(".", ",")


def br_g(valor):
    """Número sem zeros à direita: 2.5 -> '2,5'; 16.0 -> '16'."""
    return f"{float(valor):g}".replace(".", ",")


def _ok(condicao):
    return "atende" if condicao else "NÃO ATENDE"


# --- circuitos -------------------------------------------------------------------------------------

def tipo_do_circuito(circuito):
    """ILUM, TUE ou TUG pela descrição e pelas fases (para a seção mínima e a demanda): bifásico ou
    trifásico, ou com palavra de equipamento (chuveiro, ar-condicionado, forno...), é uso específico."""
    descricao = str(circuito.get("Destino", "")).strip().lower()
    if descricao.startswith("ilum") or "luz" in descricao or "lumin" in descricao:
        return ILUM
    fases = len(quadro_cargas.fases_do_circuito(circuito)) or 1
    if fases > 1 or any(p in descricao + " " for p in PALAVRAS_TUE):
        return TUE
    return TUG


def verificar_circuito(circuito, parametros, rede=None, icc_ka=None):
    """Verificação de um circuito pela NBR 5410, com o cabo e o disjuntor da planilha.

    Args:
        circuito: linha de ``planilhas.ler_circuitos_completos``.
        parametros: de ``core.parametros.ler``.
        rede: {'comprimento' [m], 'agrupados'} da rede de eletrodutos, ou None (usa a coluna
            ``Comprimento`` e 1 circuito no trecho).
        icc_ka: curto no quadro [kA] para a verificação de S ≥ I·√t/k (só com ``tempo_curto`` > 0).
    Returns:
        dict com ``linha`` (para a tabela resumo), ``blocos`` (o cálculo passo a passo),
        ``ok`` e ``avisos``.
    """
    rede = rede or {}
    nome = f"C{str(circuito.get('N_circuito', '')).strip()}"
    descricao = str(circuito.get("Destino", "")).strip()
    potencia, tensao = numero(circuito.get("Potencia")), numero(circuito.get("Tensao"))
    fases = quadro_cargas.fases_do_circuito(circuito)
    n = len(fases) or 1
    disjuntor, secao = numero(circuito.get("Disjuntor")), numero(circuito.get("Cabo"))
    curva = str(circuito.get("Curva", "")).strip().upper() or "C"
    if quadro_cargas.eh_reserva(circuito) or potencia <= 0 or tensao <= 0 or disjuntor <= 0 or secao <= 0:
        return {"linha": [nome, descricao or "Reserva", br_g(potencia) if potencia else "-", "-", "-", "-", "-", "-",
                          "-", "-", "reserva / sem dados"],
                "blocos": [], "ok": True, "avisos": []}

    tipo = tipo_do_circuito(circuito)
    isolacao, material = parametros.get("isolacao", "PVC"), parametros.get("material", "cobre")
    temperatura = float(parametros.get("temperatura_ambiente", 30.0))
    agrupados = int(rede.get("agrupados") or 1)
    comprimento = float(rede.get("comprimento") or numero(circuito.get("Comprimento")))
    queda_max = float(parametros.get("queda_terminal", 4.0))
    carregados = 3 if n == 3 else 2
    avisos, blocos, verificacoes = [], [], []

    # 1. corrente de projeto
    if n == 3:
        ib = potencia / (math.sqrt(3) * tensao)
        blocos.append(("formula", f"Ib = S / (√3 · V) = {br_g(potencia)} / (1,732 × {br_g(tensao)}) = {br(ib)} A"))
    else:
        ib = potencia / tensao
        blocos.append(("formula", f"Ib = S / V = {br_g(potencia)} / {br_g(tensao)} = {br(ib)} A"))

    # 2. proteção: Ib ≤ In
    ok_in = ib <= disjuntor + 1e-9
    verificacoes.append(ok_in)
    blocos.append(("formula", f"Disjuntor curva {curva}, In = {br_g(disjuntor)} A: Ib ≤ In → {br(ib)} ≤ "
                              f"{br_g(disjuntor)} → {_ok(ok_in)}"))

    # 3. capacidade de condução: In ≤ Iz = Iz0 · FCT · FCA
    try:
        iz0 = nbr5410.capacidade(secao, "B1", carregados, isolacao)
        f_t, f_a = nbr5410.fct(temperatura, isolacao), nbr5410.fca(agrupados)
        iz = iz0 * f_t * f_a
        ok_iz = disjuntor <= iz + 1e-9
        verificacoes.append(ok_iz)
        blocos.append(("formula", f"Iz = Iz0 · FCT · FCA = {br_g(iz0)} × {br(f_t)} × {br(f_a)} = {br(iz)} A "
                                  f"(#{br_g(secao)} mm² {isolacao}, B1, {carregados} carregados, {br_g(temperatura)} °C, "
                                  f"{agrupados} circuito(s) no trecho)"))
        blocos.append(("formula", f"In ≤ Iz → {br_g(disjuntor)} ≤ {br(iz)} → {_ok(ok_iz)} "
                                  f"(sobrecarga: I2 = 1,45·In ≤ 1,45·Iz, atendida com disjuntor NBR NM 60898)"))
    except ValueError as erro:
        iz, ok_iz = None, False
        verificacoes.append(False)
        avisos.append(f"{nome}: {erro}")
        blocos.append(("aviso", f"Capacidade de condução não verificada: {erro}"))

    # 4. queda de tensão (anexo G da IEC 60364-5-52, cos φ = 1)
    rho = nbr5410.RESISTIVIDADE_QUEDA.get(material, nbr5410.RESISTIVIDADE_QUEDA["cobre"])
    b, b_texto = (math.sqrt(3), "√3") if n == 3 else (2.0, "2")
    if comprimento > 0:
        u = b * rho * comprimento / secao * ib
        queda = u / tensao * 100
        ok_queda = queda <= queda_max + 1e-9
        verificacoes.append(ok_queda)
        blocos.append(("formula", f"ΔV = b · ρ · L / S · Ib = {b_texto} × {br(rho, 4)} × {br(comprimento, 1)} / "
                                  f"{br_g(secao)} × {br(ib)} = {br(u)} V"))
        blocos.append(("formula", f"ΔV% = ΔV / V × 100 = {br(u)} / {br_g(tensao)} × 100 = {br(queda)} % ≤ "
                                  f"{br_g(queda_max)} % → {_ok(ok_queda)}"))
    else:
        queda = None
        blocos.append(("paragrafo", "Queda de tensão não verificada: comprimento desconhecido (ligue o circuito "
                                    "à rede de eletrodutos ou preencha a coluna Comprimento)."))

    # 5. seção mínima (tabela 47)
    minima = nbr5410.SECAO_MINIMA.get(tipo, nbr5410.SECAO_MINIMA_PADRAO)
    ok_min = secao >= minima - 1e-9
    verificacoes.append(ok_min)
    rotulo_tipo = {ILUM: "iluminação", TUG: "tomadas", TUE: "uso específico"}[tipo]
    blocos.append(("formula", f"Seção mínima ({rotulo_tipo}, tabela 47): {br_g(secao)} ≥ {br_g(minima)} mm² → "
                              f"{_ok(ok_min)}"))

    # 6. curto-circuito: S ≥ I·√t / k
    tempo = float(parametros.get("tempo_curto", 0.0) or 0.0)
    if tempo > 0:
        icc = float(icc_ka if icc_ka else parametros.get("icc_entrada_ka", 5.0))
        k = nbr5410.K_CURTO.get((material, "EPR" if isolacao in ("EPR", "XLPE") else "PVC"), 115)
        s_curto = icc * 1000 * math.sqrt(tempo) / k
        ok_curto = secao >= s_curto - 1e-9
        verificacoes.append(ok_curto)
        blocos.append(("formula", f"Curto: S ≥ I·√t / k = {br_g(icc * 1000)} × √{br_g(tempo)} / {k} = "
                                  f"{br(s_curto)} mm² → {_ok(ok_curto)}"))

    # 7. condutor de proteção (tabela 58)
    pe = nbr5410.secao_protecao(secao)
    blocos.append(("formula", f"Condutor de proteção (tabela 58): S ≤ 16 mm² → SPE = S = {br_g(pe)} mm²"
                   if secao <= 16 else f"Condutor de proteção (tabela 58): SPE = {br_g(pe)} mm²"))

    # 8. proteção contra choque (contatos indiretos)
    esquema = parametros.get("esquema", "TN-S")
    com_dr = regras_quadro.verdadeiro(circuito.get("DR", "")) or bool(regras_quadro.grupo_dr(circuito))
    if com_dr:
        sensibilidade = regras_quadro.sensibilidade_texto(circuito.get("Corrente_DR"))
        grupo = regras_quadro.grupo_dr(circuito)
        blocos.append(("formula", f"Contatos indiretos: DR {sensibilidade}" + (f" (grupo {grupo})" if grupo else "")
                                  + " → seccionamento automático garantido (5.1.3.2.2)"))
    elif esquema == "TT":
        verificacoes.append(False)
        avisos.append(f"{nome}: esquema TT sem DR")
        blocos.append(("aviso", "Esquema TT sem DR: a NBR 5410 exige DR para o seccionamento automático."))
    elif comprimento > 0:
        tensao_fn = float(parametros.get("tensao_fn", 127.0))
        lmax = nbr5410.comprimento_maximo_tn(tensao_fn, secao, pe, disjuntor, curva)
        ok_tn = comprimento <= lmax + 1e-9
        verificacoes.append(ok_tn)
        ia = nbr5410.MULTIPLO_DISPARO.get(curva, 10) * disjuntor
        blocos.append(("formula", f"Contatos indiretos ({esquema}): Lmáx = 0,8·U0·S / (ρ·(1+m)·Ia) = 0,8 × "
                                  f"{br_g(tensao_fn)} × {br_g(secao)} / ({br(nbr5410.RESISTIVIDADE_COBRE_CURTO, 4)} × "
                                  f"(1 + {br_g(secao / pe)}) × {br_g(ia)}) = {br(lmax, 1)} m ≥ L = "
                                  f"{br(comprimento, 1)} m → {_ok(ok_tn)}"))

    ok = all(verificacoes)
    if not ok:
        avisos.append(f"{nome} ({descricao}): verificação não atendida — revise cabo, disjuntor ou trajeto.")
    criterio = ROTULOS_CRITERIO.get(str(circuito.get("Criterio", "")).strip(), str(circuito.get("Criterio", "")))
    linha = [nome, descricao, br_g(potencia), br_g(tensao), br(ib), br_g(disjuntor), br_g(secao),
             br(iz, 1) if iz is not None else "-", br(queda) if queda is not None else "-",
             br(comprimento, 1) if comprimento > 0 else "-", "atende" if ok else "NÃO ATENDE"]
    blocos.insert(0, ("subtitulo", f"{nome} — {descricao} ({fases or 'R'}, {br_g(potencia)} VA)"
                                   + (f"; critério determinante: {criterio}" if criterio else "")))
    return {"linha": linha, "blocos": blocos, "ok": ok, "avisos": avisos}


CABECALHO_CIRCUITOS = ["Circ.", "Descrição", "S [VA]", "V", "Ib [A]", "In [A]", "S [mm²]", "Iz [A]", "ΔV [%]",
                       "L [m]", "Situação"]
LARGURAS_CIRCUITOS = [1.0, 3.6, 1.3, 0.9, 1.2, 1.1, 1.3, 1.2, 1.2, 1.1, 1.8]


# --- demanda -------------------------------------------------------------------------------------

def demanda_dos_circuitos(circuitos):
    """Demanda (``demanda.demanda_residencial``) a partir das linhas da planilha de circuitos."""
    ilum_tug, tue = 0.0, []
    for c in circuitos:
        if quadro_cargas.eh_reserva(c):
            continue
        potencia = numero(c.get("Potencia"))
        if potencia <= 0:
            continue
        if tipo_do_circuito(c) == TUE:
            tue.append(potencia)
        else:
            ilum_tug += potencia
    return regras_demanda.demanda_residencial(ilum_tug, tue)


def blocos_da_demanda(demanda, dados_quadro, parametros):
    r = demanda
    blocos = [
        ("paragrafo", "Demanda pelos fatores de guias de instalações residenciais: um fator para iluminação e "
                      "tomadas de uso geral pela faixa da potência somada, e um fator para as tomadas de uso "
                      "específico pelo número de circuitos."),
        ("formula", f"D(ilum + TUG) = {br_g(r['instalada_ilum_tug_w'])} × {br(r['fator_ilum_tug'])} = "
                    f"{br(r['demanda_ilum_tug_w'], 0)} W"),
        ("formula", f"D(TUE) = {br_g(r['instalada_tue_w'])} × {br(r['fator_tue'])} ({r['circuitos_tue']} circuito(s)) "
                    f"= {br(r['demanda_tue_w'], 0)} W"),
        ("formula", f"D = {br(r['demanda_ilum_tug_w'], 0)} + {br(r['demanda_tue_w'], 0)} = {br(r['demanda_w'], 0)} W"
                    f" ({br(r['demanda_w'] / 1000)} kW; instalada {br(r['instalada_w'] / 1000)} kW; fator global "
                    f"{br(r['fator_global'])})"),
    ]
    fases = max(1, min(3, int(numero(dados_quadro.get("numero_fases"), 1))))
    vff, vfn = float(parametros.get("tensao_ff", 220.0)), float(parametros.get("tensao_fn", 127.0))
    if fases == 3:
        corrente = r["demanda_w"] / (math.sqrt(3) * vff)
        blocos.append(("formula", f"Id = D / (√3 · Vff) = {br(r['demanda_w'], 0)} / (1,732 × {br_g(vff)}) = "
                                  f"{br(corrente)} A"))
    elif fases == 2:
        corrente = r["demanda_w"] / (2 * vfn)
        blocos.append(("formula", f"Id = D / (2 · Vfn) = {br(r['demanda_w'], 0)} / (2 × {br_g(vfn)}) = "
                                  f"{br(corrente)} A (por fase)"))
    else:
        corrente = r["demanda_w"] / vfn
        blocos.append(("formula", f"Id = D / Vfn = {br(r['demanda_w'], 0)} / {br_g(vfn)} = {br(corrente)} A"))
    geral = numero(dados_quadro.get("corrente_nominal_disjuntor"))
    if geral > 0:
        blocos.append(("formula", f"Disjuntor geral: Id ≤ In → {br(corrente)} ≤ {br_g(geral)} A → "
                                  f"{_ok(corrente <= geral + 1e-9)}"))
    blocos.append(("aviso", "Cada concessionária tem a sua tabela de demanda: confira com a norma de fornecimento."))
    return blocos


# --- seções ----------------------------------------------------------------------------------------

def _secao_identificacao(dados):
    p = dados.get("projeto", {})
    linhas = [[rotulo, p.get(chave) or "-"] for chave, rotulo in (
        ("projeto", "Projeto"), ("obra", "Obra / endereço"), ("cliente", "Cliente"),
        ("responsavel", "Responsável técnico"), ("registro", "CREA / CFT"), ("desenhista", "Desenho"),
        ("data", "Data"), ("documento", "Arquivo"))]
    blocos = [("tabela", ["Item", "Valor"], linhas, [1, 3])]
    contagem = dados.get("contagem", {})
    if contagem:
        blocos.append(("subtitulo", "Elementos do projeto"))
        blocos.append(("tabela", ["Elemento", "Quantidade"], [[k, str(v)] for k, v in contagem.items()], [3, 1]))
    return "Identificação do projeto", blocos


def _secao_normas(dados):
    normas = list(NORMAS) + ([NORMA_ENEL] if dados.get("centro_medicao") else [])
    return "Objetivo e normas", [
        ("paragrafo", "Este memorial descreve as instalações elétricas do projeto e apresenta os cálculos de "
                      "dimensionamento dos circuitos, dos quadros e das proteções, com as fórmulas, os valores "
                      "adotados e a verificação de cada critério."),
        ("lista", normas),
    ]


def _secao_parametros(dados):
    rotulos = dados.get("rotulos_parametros", {})
    p = dados.get("parametros", {})
    linhas = [[rotulos.get(chave, chave), br_g(valor) if isinstance(valor, float) else str(valor)]
              for chave, valor in p.items() if chave in rotulos and not rotulos[chave].startswith("Carimbo")]
    return "Parâmetros e premissas de cálculo", [
        ("paragrafo", "Valores da planilha Parâmetros do projeto (em branco vale o padrão da bancada)."),
        ("tabela", ["Parâmetro", "Valor"], linhas, [3, 1]),
        ("lista", [
            "Método de referência B1: condutores isolados em eletroduto embutido (tabela 33 da NBR 5410).",
            "Capacidade de condução: tabelas 36 e 37, corrigida pela temperatura (tabela 40) e pelo "
            "agrupamento no trecho mais cheio do trajeto (tabela 42).",
            f"Queda de tensão: ρ = {br(nbr5410.RESISTIVIDADE_QUEDA.get(p.get('material', 'cobre'), 0.0225), 4)} "
            "Ω·mm²/m (condutor em serviço), b = 2 nos circuitos monofásicos e bifásicos e √3 nos trifásicos.",
        ]),
    ]


def _secao_ambientes(dados):
    ambientes = dados.get("ambientes") or []
    if not ambientes:
        return None
    linhas, blocos_lum = [], []
    for a in ambientes:
        prev = a["previsao"]
        linhas.append([a["nome"], a["tipo"], br(a["area"]), br(a["perimetro"]), str(prev["tugs"]),
                       br_g(prev["total_tug_va"]), br_g(prev["iluminacao_va"])])
        lum = a.get("luminotecnico")
        if lum:
            blocos_lum.append(("subtitulo", f"{a['nome']} ({a['tipo']})"))
            blocos_lum.append(("formula", f"Hu = pé-direito − plano − suspensão = {br(lum['altura_util'])} m; "
                                          f"K = 2A / (Hu · P) = 2 × {br(a['area'])} / ({br(lum['altura_util'])} × "
                                          f"{br(a['perimetro'])}) = {br(lum['indice_local'])}"))
            blocos_lum.append(("formula", f"N = E · A / (Φ · Fu · Fm) = {br_g(lum['iluminancia'])} × {br(a['area'])} / "
                                          f"({br_g(lum['fluxo_luminaria'])} × {br(lum['fator_utilizacao'])} × "
                                          f"{br(lum['fator_manutencao'])}) = {br(lum['quantidade_calculada'])} → "
                                          f"{lum['quantidade']} luminária(s); Em = "
                                          f"{br(lum.get('iluminancia_resultante', 0.0), 0)} lx"))
    blocos = [
        ("paragrafo", "Previsão mínima de cargas pela NBR 5410, 9.5.2: iluminação de 100 VA nos primeiros 6 m² e "
                      "mais 60 VA a cada 4 m² inteiros; tomadas de uso geral por perímetro (uma a cada 5 m nas "
                      "salas e dormitórios, a cada 3,5 m nas cozinhas e áreas de serviço) ou por área, com 600 VA "
                      "nas três primeiras das áreas molhadas e 100 VA nas demais."),
        ("tabela", ["Ambiente", "Tipo", "Área [m²]", "Perímetro [m]", "TUG", "TUG [VA]", "Ilum. [VA]"], linhas,
         [2.4, 1.6, 1.1, 1.3, 0.7, 1.1, 1.1]),
    ]
    if blocos_lum:
        blocos += [("subtitulo", "Luminotécnico (método dos lúmens)")] + blocos_lum
    return "Previsão de cargas e iluminação por ambiente", blocos


# --- luminotécnico (Distribuir luminárias) -------------------------------------------------------------

ENTRADAS_LUMINOTECNICO = ("comprimento", "largura", "iluminancia", "fluxo_luminaria", "pe_direito",
                          "plano_trabalho", "suspensao", "fator_utilizacao_informado")


def _blocos_luminotecnico(a):
    """Blocos e linha da tabela de um ambiente do luminotécnico (``services.luminotecnico.calculos``)."""
    calculo = a.get("calculo")
    if not calculo:
        linha = [a["nome"], "-", "-", "-", str(a["luminarias"]), "-", "-"]
        return [("paragrafo", f"{a['nome']}: {a['luminarias']} luminária(s), {br_g(a['potencia_va'])} VA, "
                              "distribuídas sem o cálculo gravado (versão anterior): refaça com Luminotécnico.")], \
            linha, []
    entradas = {k: float(calculo[k]) for k in ENTRADAS_LUMINOTECNICO if k in calculo}
    r = regras_luminotecnico.dimensionar(**entradas)
    c, l, hu = r["comprimento"], r["largura"], r["altura_util"]
    area = c * l
    potencia = numero(calculo.get("potencia"))
    titulo = a["nome"] + (f" ({calculo['ambiente']})" if calculo.get("ambiente") else "")
    fu = ("do catálogo" if entradas.get("fator_utilizacao_informado", 0) > 0
          else "pela curva genérica, com o K")
    blocos = [
        ("subtitulo", titulo),
        ("paragrafo", f"Ambiente de {br(c)} × {br(l)} m (A = {br(area)} m²); "
                      + (f"{calculo['lampada']}, " if calculo.get("lampada") else "")
                      + f"{br_g(r['fluxo_luminaria'])} lm e {br_g(potencia)} W por luminária."),
        ("formula", f"Hu = H − hp − hs = {br(entradas.get('pe_direito', 2.7))} − "
                    f"{br(entradas.get('plano_trabalho', regras_luminotecnico.PLANO_DE_TRABALHO))} − "
                    f"{br(entradas.get('suspensao', 0.0))} = {br(hu)} m"),
        ("formula", f"K = C · L / (Hu · (C + L)) = {br(c)} × {br(l)} / ({br(hu)} × ({br(c)} + {br(l)})) = "
                    f"{br(r['indice_local'])}; Fu = {br(r['fator_utilizacao'])} ({fu}); "
                    f"Fm = {br(r['fator_manutencao'])}"),
        ("formula", f"N = E · A / (Φ · Fu · Fm) = {br_g(r['iluminancia'])} × {br(area)} / "
                    f"({br_g(r['fluxo_luminaria'])} × {br(r['fator_utilizacao'])} × {br(r['fator_manutencao'])}) "
                    f"= {br(r['quantidade_calculada'])} → {r['quantidade']} luminária(s), malha "
                    f"{r['nx']} × {r['ny']}"),
        ("formula", f"Espaçamento {br(r['espacamento_x'])} × {br(r['espacamento_y'])} m ≤ 1,5 · Hu = "
                    f"{br(r['espacamento_maximo'])} m → "
                    f"{_ok(max(r['espacamento_x'], r['espacamento_y']) <= r['espacamento_maximo'] + 1e-9)}"),
        ("formula", f"Em = N · Φ · Fu · Fm / A = {r['quantidade']} × {br_g(r['fluxo_luminaria'])} × "
                    f"{br(r['fator_utilizacao'])} × {br(r['fator_manutencao'])} / {br(area)} = "
                    f"{br(r['iluminancia_resultante'], 0)} lx ≥ {br_g(r['iluminancia'])} lx → "
                    f"{_ok(r['iluminancia_resultante'] >= r['iluminancia'] - 1e-6)}"),
    ]
    densidade = r["quantidade"] * potencia / area if area else 0.0
    if potencia:
        blocos.append(("formula", f"Densidade de potência = N · P / A = {r['quantidade']} × {br_g(potencia)} / "
                                  f"{br(area)} = {br(densidade, 1)} W/m²"))
    avisos = []
    if a["luminarias"] != r["quantidade"]:
        avisos.append(f"Luminotécnico de {a['nome']}: a planta tem {a['luminarias']} luminária(s) e o cálculo "
                      f"pede {r['quantidade']}")
        blocos.append(("aviso", avisos[-1] + "."))
    blocos += [("aviso", aviso) for aviso in r.get("avisos", [])]
    linha = [a["nome"], f"{br(c)} × {br(l)}", br_g(r["iluminancia"]), br(r["quantidade_calculada"]),
             str(r["quantidade"]), br(r["iluminancia_resultante"], 0), br(densidade, 1) if potencia else "-"]
    return blocos, linha, avisos


def _secao_luminotecnico(dados):
    """Ambientes calculados com Luminotécnico (Distribuir luminárias). Returns: (título, blocos, avisos)."""
    ambientes = dados.get("luminotecnico") or []
    if not ambientes:
        return None, [], []
    blocos, linhas, avisos = [], [], []
    for a in ambientes:
        try:
            mais, linha, av = _blocos_luminotecnico(a)
        except (ValueError, KeyError, TypeError) as erro:
            avisos.append(f"Luminotécnico de {a.get('nome', '?')}: {erro}")
            continue
        blocos += mais
        linhas.append(linha)
        avisos += av
    inicio = [
        ("paragrafo", "Método dos lúmens: quantidade de luminárias para a iluminância média mantida E do "
                      "ambiente (NBR ISO/CIE 8995-1; nas residências, a antiga NBR 5413), com o índice do local K, "
                      "o fator de utilização Fu e o fator de manutenção Fm. As luminárias ficam numa malha "
                      "regular, com espaçamento até 1,5 vez a altura útil."),
        ("tabela", ["Ambiente", "C × L [m]", "E [lx]", "N calc.", "N", "Em [lx]", "W/m²"], linhas,
         [2.4, 1.5, 0.9, 1.0, 0.7, 1.0, 0.9]),
    ]
    return "Luminotécnico", inicio + blocos, avisos


# --- aterramento --------------------------------------------------------------------------------------

RESISTIVIDADE_ADOTADA = 100.0  # Ω·m, quando o cálculo não foi gravado


def _secao_aterramento(dados, parametros):
    """Elementos de aterramento da planta e a resistência das hastes. Returns: (título, blocos, avisos)."""
    info = dados.get("aterramento") or {}
    planta = info.get("levantamento") or {}
    entradas = info.get("calculo")
    hastes_planta = int(planta.get("hastes", 0))
    condutores = planta.get("condutores") or {}
    if not entradas and not hastes_planta and not condutores and not planta.get("bep"):
        return None, [], []
    blocos = [("paragrafo", f"Esquema de aterramento: {parametros.get('esquema', '-')}. Eletrodo de aterramento "
                            "por hastes verticais interligadas por cabo de cobre nu, ligado ao barramento de "
                            "equipotencialização principal (BEP), ao qual chegam os condutores de proteção dos "
                            "quadros (NBR 5410, 6.4).")]
    linhas = [["Hastes de aterramento", str(hastes_planta)],
              ["Caixas de inspeção", str(planta.get("caixas_inspecao", 0))],
              ["BEP", str(planta.get("bep", 0))]]
    linhas += [[f"Cabo de cobre nu {secao} mm² [m]", br(metros, 1)]
               for secao, metros in sorted(condutores.items(), key=lambda item: numero(item[0]))]
    blocos += [("subtitulo", "Elementos na planta"), ("tabela", ["Item", "Quantidade"], linhas, [3, 1.2])]
    avisos = []
    padrao = not entradas
    if padrao:
        entradas = {"resistividade": RESISTIVIDADE_ADOTADA, "hastes": hastes_planta}
    e = {"resistividade": float(entradas.get("resistividade") or RESISTIVIDADE_ADOTADA),
         "resistencia_alvo": float(entradas.get("resistencia_alvo") or regras_aterramento.ALVO_PADRAO),
         "hastes": int(entradas.get("hastes") or 0),
         "espacamento": float(entradas.get("espacamento") or regras_aterramento.ESPACAMENTO_PADRAO),
         "comprimento_haste": float(entradas.get("comprimento_haste") or regras_aterramento.HASTE_COMPRIMENTO),
         "diametro_haste": float(entradas.get("diametro_haste") or regras_aterramento.HASTE_DIAMETRO_MM)}
    try:
        r = regras_aterramento.dimensionar(**e)
    except ValueError as erro:
        avisos.append(f"Aterramento: {erro}")
        return "Aterramento", blocos + [("aviso", str(erro))], avisos
    rho, comp, n, s = e["resistividade"], e["comprimento_haste"], r["hastes"], e["espacamento"]
    raio = e["diametro_haste"] / 2000.0
    blocos.append(("subtitulo", "Resistência de aterramento das hastes em linha"))
    if padrao:
        blocos.append(("aviso", f"Cálculo não gravado no projeto: resistividade adotada de {br_g(rho)} Ω·m e as "
                                f"{hastes_planta} haste(s) da planta. Meça o solo e grave com Resistência de terra."))
        avisos.append("Aterramento calculado com a resistividade adotada de "
                      f"{br_g(rho)} Ω·m: meça o solo (Wenner) e grave o cálculo")
    blocos += [
        ("paragrafo", f"Solo de {br_g(rho)} Ω·m; hastes de {br(comp)} m e {br(e['diametro_haste'], 1)} mm "
                      f"(a = {br(raio, 5)} m), a cada {br(s, 1)} m."),
        ("formula", f"R1 = ρ / (2π·L) · [ln(4L/a) − 1] = {br_g(rho)} / (2π × {br(comp)}) × [ln(4 × {br(comp)} / "
                    f"{br(raio, 5)}) − 1] = {br(r['resistencia_uma_haste'])} Ω"),
    ]
    if n > 1:
        alfa = rho / (2 * math.pi * r["resistencia_uma_haste"] * s)
        lam = regras_aterramento.fator_lambda(n)
        blocos += [
            ("formula", f"α = ρ / (2π · R1 · s) = {br_g(rho)} / (2π × {br(r['resistencia_uma_haste'])} × {br(s, 1)}) "
                        f"= {br(alfa, 3)}; λ = 2 · (1/2 + … + 1/n) = {br(lam, 3)}"),
            ("formula", f"Rn = R1 · (1 + λ · α) / n = {br(r['resistencia_uma_haste'])} × (1 + {br(lam, 3)} × "
                        f"{br(alfa, 3)}) / {n} = {br(r['resistencia'])} Ω"),
        ]
    blocos.append(("formula", f"R = {br(r['resistencia'])} Ω ≤ {br_g(r['resistencia_alvo'])} Ω → {_ok(r['atende'])}"
                              + ("" if r["atende"] or not r["hastes_necessarias"]
                                 else f" (seriam necessárias {r['hastes_necessarias']} hastes)")))
    if not r["atende"]:
        avisos.append(f"Aterramento: {br(r['resistencia'])} Ω com {n} haste(s), acima de "
                      f"{br_g(r['resistencia_alvo'])} Ω")
    if n > 1:
        texto = f"Cabo entre as hastes: (n − 1) · s = ({n} − 1) × {br(s, 1)} = {br(r['cabo_entre_hastes'], 1)} m"
        if condutores:
            texto += f"; desenhado na planta: {br(sum(condutores.values()), 1)} m"
        blocos.append(("paragrafo", texto + "."))
    if not padrao and hastes_planta and hastes_planta < n:
        avisos.append(f"Aterramento: a planta tem {hastes_planta} haste(s) e o cálculo usa {n}")
        blocos.append(("aviso", avisos[-1] + "."))
    return "Aterramento", blocos, avisos


def _secao_quadro(q, parametros, icc_quadro):
    """Blocos de um quadro: dados, quadro de cargas, demanda, circuitos, DR, componentes."""
    dados, circuitos = q["dados"], q["circuitos"]
    blocos, avisos = [], []
    identificacao = dados.get("indentificacao_painel") or q["nome"]
    linhas_dados = [[rotulo, str(dados.get(chave, "") or "-")] for chave, rotulo in (
        ("descricao", "Descrição"), ("origem", "Alimentado por"), ("tensao", "Tensão [V]"),
        ("numero_fases", "Fases"), ("bitola", "Cabo de entrada [mm²]"),
        ("curva_disjuntor", "Curva do disjuntor geral"), ("corrente_nominal_disjuntor", "Disjuntor geral [A]"),
        ("corrente_curto_circuito", "Capacidade de interrupção [kA]"), ("curto_circuito", "Curto no ponto [kA]"),
        ("material_quadro", "Material"))]
    blocos += [("subtitulo", "Dados do quadro"), ("tabela", ["Dado", "Valor"], linhas_dados, [2, 2])]

    ativos = [c for c in circuitos if not quadro_cargas.eh_reserva(c)]
    if ativos:
        tabela = quadro_cargas.tabela(circuitos)
        corpo = [[str(v) if not isinstance(v, float) else br(v, 0) for v in linha] for linha in tabela[1:]]
        carga = quadro_cargas.carga_por_fase(ativos)
        maior, menor = max(carga.values()), min(carga.values())
        blocos += [
            ("subtitulo", "Quadro de cargas e equilíbrio de fases"),
            ("tabela", list(tabela[0]), corpo, [1.15, 2.8, 1.2, 1.0, 1.0, 1.0, 1.1, 1.1, 1.0]),
            ("formula", f"Desequilíbrio = (Fmáx − Fmín) / Fmáx × 100 = ({br(maior, 0)} − {br(menor, 0)}) / "
                        f"{br(maior, 0)} × 100 = {br(quadro_cargas.desequilibrio(carga), 1)} %"
                        + (" (acima dos 10 % usuais: use Balancear fases)"
                           if quadro_cargas.desequilibrio(carga) > 10 else "")),
        ]
        sem = quadro_cargas.sem_fase(circuitos)
        if sem:
            avisos.append(f"{identificacao}: circuitos sem fase definida: {', '.join('C' + s for s in sem)}.")

        demanda = demanda_dos_circuitos(circuitos)  # as mesmas linhas da tabela dos circuitos
        blocos += [("subtitulo", "Demanda")] + blocos_da_demanda(demanda, dados, parametros)

        resultados = [verificar_circuito(c, parametros, q.get("rede", {}).get(str(c.get("N_circuito", "")).strip()),
                                         icc_quadro) for c in circuitos]
        blocos += [("subtitulo", "Dimensionamento dos circuitos (resumo)"),
                   ("tabela", CABECALHO_CIRCUITOS, [r["linha"] for r in resultados], LARGURAS_CIRCUITOS),
                   ("subtitulo", "Memória de cálculo dos circuitos")]
        for r in resultados:
            blocos += r["blocos"]
            avisos += r["avisos"]

        drs = quadro_cargas.grupos_dr(circuitos)
        idr = regras_quadro.idr_geral(dados)
        if drs or idr:
            linhas = []
            if idr:
                linhas.append(["IDR geral", "todos", idr["especificacao"]])
            for nome, numeros in drs:
                membros = [c for c in circuitos if str(c.get("N_circuito", "")).strip() in numeros]
                proprio = len(membros) == 1 and not regras_quadro.grupo_dr(membros[0])
                espec = (regras_quadro.dr_do_circuito(membros[0]) if proprio
                         else regras_quadro.dr_do_grupo(membros))["especificacao"]
                linhas.append([nome, ", ".join("C" + n for n in numeros), espec])
            blocos += [("subtitulo", "Proteção diferencial-residual (DR)"),
                       ("paragrafo", "DR de alta sensibilidade (≤ 30 mA) nos circuitos de áreas molhadas, tomadas "
                                     "externas e de uso geral (NBR 5410, 5.1.3.2.2). Corrente nominal igual ou acima "
                                     "da soma das correntes na fase mais carregada e do maior disjuntor protegido."),
                       ("tabela", ["DR", "Circuitos", "Especificação"], linhas, [1.2, 2.4, 2.4])]

        componentes = regras_quadro.componentes(dados, circuitos)
        if componentes:
            blocos += [("subtitulo", "Componentes do quadro"),
                       ("tabela", ["Item", "Especificação", "Qtd.", "Un."],
                        [[i["item"], i["especificacao"], str(i["quantidade"]), i["unidade"]] for i in componentes],
                        [2.2, 3.6, 0.8, 0.7])]
    else:
        blocos.append(("paragrafo", "Quadro sem circuitos na planilha de circuitos."))
    return f"Quadro {identificacao}", blocos, avisos


def _secao_curto(dados):
    c = dados.get("curto")
    if not c or not c.get("resultado"):
        return None, [], []
    tensao, resultado = c["tensao"], c["resultado"]
    blocos = [
        ("paragrafo", f"Estudo pela IEC 60909 com a tensão de linha U = {br_g(tensao)} V, somando as impedâncias "
                      "da rede, do transformador e dos cabos da entrada até cada barra."),
        ("formula", "Rede: ZQ = c · U² / S″kQ; transformador: ZT = uk · U² / ST · KT, RT = PkrT · U² / ST²; "
                    "cabo: R = ρ · L / S, X = 0,08 mΩ/m · L"),
        ("formula", "I″k3 = cmáx · U / (√3 · |Z|), cmáx = 1,05; ip = κ · √2 · I″k3, κ = 1,02 + 0,98 · e^(−3R/X)"),
        ("formula", "I″k1 mín = cmín · U0 / |Zfase + ZPE| (cabos a 80 °C, cmín = 0,95, PE igual à fase)"),
    ]
    linhas, avisos = [], []
    for nome, d in resultado.items():
        z = math.hypot(d["r"], d["x"])
        kappa = regras_curto.fator_pico(d["r"], d["x"]) if d["x"] > 0 else 1.02
        linhas.append([nome, d.get("origem") or "-", br(d["r"]), br(d["x"]), br(z), br(d["ik3"]), br(kappa),
                       br(d["ip"]), br(d["ik1_min"]), br_g(d["icu_minimo"])])
        icu_quadro = _icu_dos_quadros(dados).get(nome)
        if icu_quadro and icu_quadro < d["ik3"]:
            avisos.append(f"Quadro {nome}: capacidade de interrupção de {br_g(icu_quadro)} kA menor que o curto de "
                          f"{br(d['ik3'])} kA.")
    blocos.append(("tabela", ["Barra", "Origem", "R [mΩ]", "X [mΩ]", "|Z| [mΩ]", "I″k3 [kA]", "κ", "ip [kA]",
                              "I″k1 mín [kA]", "Icu mín [kA]"], linhas,
                   [1.6, 1.4, 1.0, 1.0, 1.0, 1.1, 0.8, 1.0, 1.2, 1.1]))
    for nome, d in list(resultado.items())[:1]:
        z = math.hypot(d["r"], d["x"])
        blocos.append(("formula", f"Exemplo ({nome}): I″k3 = 1,05 × {br_g(tensao)} / (1,732 × {br(z)} mΩ) = "
                                  f"{br(d['ik3'])} kA"))
    return "Curto-circuito", blocos + [("aviso", a) for a in avisos], avisos


def _icu_dos_quadros(dados):
    """{identificação: capacidade de interrupção do disjuntor geral [kA]} dos quadros com ela preenchida."""
    icu = {}
    for q in dados.get("quadros", []):
        valor = numero(q["dados"].get("corrente_curto_circuito"))
        if valor > 0:
            icu[q["dados"].get("indentificacao_painel") or q["nome"]] = valor
    return icu


def _secao_gerador(dados):
    g = dados.get("gerador")
    if not g or not g.get("resumo"):
        return None
    linhas = [[c.get("descricao", ""), str(c.get("tipo", "")), br_g(c.get("quantidade", 1)),
               br(c.get("kw", 0.0)), br(c.get("kva", 0.0)), br(c.get("fator_potencia", 0.0) or 0.0),
               br(c.get("fator_demanda", 1.0) or 1.0), str(c.get("partida", "") or "-"),
               "S" if c.get("no_gerador") else "N"]
              for c in g.get("cargas", [])]
    blocos = [
        ("paragrafo", "Gerador escolhido pelo maior de três critérios: a demanda em kVA (cargas não lineares × 1,5) "
                      "sobre o carregamento máximo do regime, a demanda em kW sobre 0,8 × carregamento, e a partida "
                      "do maior motor pelo afundamento de tensão admissível; todos corrigidos pela altitude e pela "
                      "temperatura."),
        ("formula", "Sg ≥ x″d · Sp · (1 − ΔV) / ΔV (partida do maior motor)"),
    ]
    if linhas:
        blocos.append(("tabela", ["Carga", "Tipo", "Qtd.", "kW", "kVA", "FP", "FD", "Partida", "Ger."], linhas,
                       [2.6, 1.4, 0.6, 0.8, 0.8, 0.6, 0.6, 1.4, 0.6]))
    blocos.append(("tabela", ["Resultado", "Valor"], [[k, v] for k, v in g["resumo"].items()], [3, 2]))
    return "Grupo gerador", blocos


ARGUMENTOS_CENTRO = ("tensao", "uso", "distancia_horizontal", "comprimento_ramal", "demanda_total_a",
                     "altura_ultimo_pavimento", "andares_por_centro")


def _comparacao_do_centro(c):
    """Refaz a comparação de ``core.centro_medicao`` com os parâmetros gravados na planilha."""
    parametros = c.get("parametros") or {}
    argumentos = {k: parametros[k] for k in ARGUMENTOS_CENTRO if k in parametros}
    if "andares_por_centro" in argumentos:
        argumentos["andares_por_centro"] = int(argumentos["andares_por_centro"])
    andares = [regras_centro.andar(a["nome"], a["cota"], a["unidades"], a.get("demanda_a", regras_centro.DEMANDA_PADRAO),
                                   a.get("fases", regras_centro.FASES_PADRAO)) for a in c.get("andares", [])]
    return regras_centro.comparar(andares, precos=c.get("precos"), **argumentos), argumentos, andares


def _adotada(c, comparacao):
    """Solução do projeto: a do busway desenhado, a gerada no desenho ou a recomendada pelo custo."""
    desenho = c.get("desenho") or {}
    if desenho.get("busways") and comparacao.get("busway"):
        return "busway", "desenhada no projeto"
    for solucao in ("descentralizado", "convencional"):
        if solucao in desenho.get("solucoes", []) and comparacao.get(solucao):
            return solucao, "gerada no projeto"
    return comparacao["recomendada"], "a de menor custo; nenhuma foi desenhada ainda"


def _tabela_conjuntos(conjuntos):
    linhas = []
    for g in conjuntos:
        cdpm = g.get("cdpm") or "-"
        if g.get("chave"):
            cdpm += f"; chave {g['chave']} A, TC {g.get('tc', '-')}"
        linhas.append([str(g.get("modelo", "-")), str(g.get("medicoes", g.get("caixas", 0))), br(g.get("corrente", 0.0), 1),
                       cdpm, str(g.get("disjuntor_geral", "-")), str(g.get("barramento") or "-"),
                       f"{g.get('ramal', '-')}" + (f" × {g['paralelos']}" if g.get("paralelos", 1) > 1 else "")])
    return ("tabela", ["Caixa", "Medições", "Corrente [A]", "CDPM / proteção", "Disj. geral [A]", "Barramento",
                       "Ramal [mm²]"], linhas, [0.9, 0.9, 1.0, 2.8, 1.0, 1.0, 1.0])


def _tabela_alimentadores(alimentadores):
    limite = regras_centro.QUEDA_ALIMENTADOR_UNIDADE
    linhas = [[a["andar"], str(a["unidades"]), f"{a['condutores']} × {br_g(a['secao'])} + PE {br_g(a['pe'])}",
               br(a["comprimento"], 1), str(a["disjuntor"]), br(a["queda"]), _ok(a["queda"] <= limite + 1e-9)]
              for a in alimentadores]
    return ("tabela", ["Andar", "Unidades", "Cabo de cada unidade [mm²]", "L [m]", "Disjuntor [A]", "ΔV [%]",
                       f"≤ {br_g(limite)} %"], linhas, [1.4, 0.9, 2.2, 0.8, 1.0, 0.8, 1.1])


def _abrigo(abrigo):
    return (f"Abrigo do centro: {br(abrigo['comprimento'], 1)} × {br(abrigo['profundidade'], 1)} m = "
            f"{br(abrigo['area'], 1)} m² (frente das caixas, circulação e porta aberta).")


def _orcamento(custo, titulo):
    linhas = [[i["descricao"], br_g(round(i["quantidade"], 2)), i["unidade"], br(i["unitario"]), br(i["total"])]
              for i in custo["itens"]]
    linhas += [["Mão de obra", "", "", "", br(custo["mao_de_obra"])], ["Total", "", "", "", br(custo["total"])]]
    return [("subtitulo", titulo),
            ("tabela", ["Item", "Qtd.", "Un.", "Unitário [R$]", "Total [R$]"], linhas, [3.6, 0.8, 0.6, 1.2, 1.2])]


def _secao_centro(dados):
    """Centro de medição (Enel SP): andares, comparação das soluções e a solução do projeto.

    Returns: (título, blocos, avisos); título None se o projeto não tem a planilha do centro.
    """
    c = dados.get("centro_medicao")
    if not c or not c.get("andares"):
        return None, [], []
    try:
        comparacao, argumentos, andares = _comparacao_do_centro(c)
    except ValueError as erro:
        return "Centro de medição", [("aviso", str(erro))], [f"Centro de medição: {erro}"]
    adotada, motivo = _adotada(c, comparacao)
    avisos = []
    outras = [regras_centro.NOMES[x] for x in (c.get("desenho") or {}).get("solucoes", [])
              if x != adotada and x in regras_centro.NOMES]
    if outras:
        avisos.append(f"o projeto também tem desenhada a {' e a '.join(outras).lower()}: apague a que não vale "
                      f"(vale no memorial a {regras_centro.NOMES[adotada].lower()})")
    tensao = argumentos.get("tensao", 220.0)
    demanda_total = argumentos.get("demanda_total_a", 0.0)
    com_unidades = [a for a in andares if a["unidades"] > 0]
    correntes = dict(zip((a["nome"] for a in com_unidades),
                         regras_centro.corrente_dos_andares(com_unidades, demanda_total)))
    soma = sum(a["unidades"] * a["demanda_a"] for a in com_unidades)
    blocos = [
        ("paragrafo", "Centro de medição pela especificação Enel SP 0018 (fornecimento em tensão secundária, "
                      f"conexão coletiva), em {br_g(tensao)} V. Foram comparadas a medição agrupada no térreo, a "
                      "descentralizada por grupos de andares e o barramento blindado (busway) com medição "
                      "centralizada nos andares."),
        ("tabela", ["Pavimento", "Cota [m]", "Unidades", "Demanda/un. [A]", "Fases", "Corrente do andar [A]"],
         [[a["nome"], br(a["cota"]), str(a["unidades"]), br_g(a["demanda_a"]), str(a["fases"]),
           br(correntes.get(a["nome"], 0.0), 1) if a["unidades"] else "-"] for a in andares],
         [1.8, 0.9, 0.9, 1.2, 0.7, 1.4]),
    ]
    if demanda_total:
        blocos.append(("formula", f"I andar = Id edifício × (n · Iun) do andar / Σ (n · Iun) = {br_g(demanda_total)} × "
                                  f"(n · Iun) / {br_g(soma)}"))
    else:
        blocos.append(("formula", f"I total = Σ (n · Iun) = {br_g(soma)} A (sem a demanda do edifício: soma sem "
                                  "diversidade)"))
    conv = comparacao["convencional"]
    blocos.append(("paragrafo", f"Entrada: {conv['qdc']} com {conv['ramal']} circuito(s) de 4 × "
                                f"{br_g(regras_centro.SECAO_RAMAL)} mm² para {br(conv['corrente'], 1)} A."))
    custos = comparacao["custos"]
    linhas = [[regras_centro.NOMES[s], br(custos[s]["material"]), br(custos[s]["mao_de_obra"]), br(custos[s]["total"]),
               ("recomendada" if s == comparacao["recomendada"] else "") + (" · adotada" if s == adotada else "")]
              for s in ("convencional", "descentralizado", "busway") if s in custos]
    blocos += [("subtitulo", "Comparação das soluções (orçamento de referência)"),
               ("tabela", ["Solução", "Material [R$]", "Mão de obra [R$]", "Total [R$]", ""], linhas,
                [3.2, 1.2, 1.2, 1.2, 1.4])]
    if comparacao.get("erro_busway"):
        blocos.append(("aviso", f"Busway: {comparacao['erro_busway']}"))
    blocos.append(("paragrafo", f"Solução adotada: {regras_centro.NOMES[adotada]} ({motivo}). Preços de referência "
                                "da planilha do centro de medição: troque pelas cotações."))
    if adotada == "convencional":
        blocos += [("subtitulo", "Medição agrupada no térreo"), _tabela_conjuntos(conv["agrupamentos"]),
                   ("paragrafo", f"Disjuntor de cada unidade: {conv['disjuntor_unidade']} A. " + _abrigo(conv["abrigo"])),
                   ("subtitulo", "Alimentadores das unidades (do centro ao quadro da unidade)"),
                   _tabela_alimentadores(conv["alimentadores"])]
        avisos += conv.get("avisos", [])
    elif adotada == "descentralizado":
        desc = comparacao["descentralizado"]
        blocos.append(("subtitulo", "Medição descentralizada"))
        for centro in desc["centros"]:
            ramal = centro["ramal"]
            texto = (f"Centro {centro['numero']} no {centro['andar']}: atende {', '.join(centro['andares'])} "
                     f"({centro['unidades']} unidades, {br(centro['corrente'], 1)} A). Ramal de distribuição do QDC: "
                     f"{ramal['paralelos']} × 4 × {br_g(ramal['secao'])} mm², {br(ramal['comprimento'], 1)} m")
            texto += f", chave vertical de {centro['chave']} A no QDC" if centro.get("chave") else ""
            texto += f"; {centro['qdc_local']} no centro (7.18.2)" if centro.get("qdc_local") else ""
            blocos += [("paragrafo", texto + ". " + _abrigo(centro["abrigo"])), _tabela_conjuntos(centro["conjuntos"]),
                       _tabela_alimentadores(centro["alimentadores"])]
        avisos += desc.get("avisos", [])
    desenho = c.get("desenho") or {}
    if desenho.get("colunas"):
        blocos += [("subtitulo", "Colunas de medição desenhadas no projeto"),
                   ("tabela", ["Objeto", "Pavimento", "Medições", "Corrente [A]", "Disj. unidade", "Conjuntos"],
                    [[col["nome"], col["pavimento"], str(col["medidores"]), br(col["corrente"], 1), col["disjuntor"],
                      "; ".join(col["conjuntos"]) or "-"] for col in desenho["colunas"]],
                    [1.8, 1.2, 0.9, 1.0, 1.0, 3.0])]
    if adotada != "busway":
        blocos += _orcamento(custos[adotada], f"Orçamento: {regras_centro.NOMES[adotada]}")
    else:
        blocos.append(("paragrafo", "O dimensionamento do busway, das caixas MEC e o orçamento estão na seção Busway."))
    blocos += [("aviso", a) for a in avisos]
    return "Centro de medição", blocos, [f"Centro de medição: {a}" for a in avisos]


def _secao_busway(dados):
    """Busway: queda trecho a trecho, caixas MEC por andar, shaft e materiais. Returns: (título, blocos, avisos)."""
    c = dados.get("centro_medicao")
    if not c or not c.get("andares"):
        return None, [], []
    try:
        comparacao, argumentos, _ = _comparacao_do_centro(c)
    except ValueError:
        return None, [], []
    bus = comparacao.get("busway")
    if not bus:
        return None, [], []
    adotada, _ = _adotada(c, comparacao)
    tensao = argumentos.get("tensao", 220.0)
    uso = argumentos.get("uso", 2.0)
    ramal_m = argumentos.get("comprimento_ramal", 0.0)
    _, circuitos, k_ramal = regras_centro.entrada(bus["corrente"])
    volts_ramal = regras_centro.queda(k_ramal, ramal_m, bus["corrente"], tensao)[0]
    papel = "solução adotada no projeto" if adotada == "busway" else "alternativa comparada; não adotada"
    blocos = [("paragrafo", f"Barramento blindado (busway) do QDC até a prumada e subindo pelo shaft, com uma caixa MEC "
                            f"por andar ({papel}). Queda de tensão pela Tabela 42 da Enel: ΔV = k · L · I / 100, com a "
                            f"carga concentrada em cada derivação, limitada a {br_g(uso)} % (Tabela 41).")]
    avisos = []
    if ramal_m:
        blocos.append(("formula", f"Ramal de entrada ({circuitos} × 4 × {br_g(regras_centro.SECAO_RAMAL)} mm²): ΔV = k · L · I / "
                                  f"100 = {br(k_ramal, 4)} × {br(ramal_m, 1)} × {br(bus['corrente'], 1)} / 100 = "
                                  f"{br(volts_ramal)} V"))
    for n, linha in enumerate(bus["linhas"], start=1):
        titulo = f"Linha {n}: busway {linha['nominal']} A" if len(bus["linhas"]) > 1 else f"Busway {linha['nominal']} A"
        corpo = []
        for comprimento, corrente, andar in linha["trechos"]:
            volts = regras_centro.queda(linha["k"], comprimento, corrente, tensao)[0]
            corpo.append([f"até {andar}", br(comprimento, 2), br(corrente, 1), br(volts, 3)])
        ok = linha["queda"] <= uso + 1e-9
        blocos += [
            ("subtitulo", titulo),
            ("paragrafo", f"Atende {', '.join(linha['andares'])}; corrente no início {br(linha['corrente'], 1)} A ≤ "
                          f"{linha['nominal']} A; k = {br_g(linha['k'])} V/(100 m·A); {br(linha['comprimento'], 1)} m "
                          "de busway (horizontal e prumada)."),
            ("tabela", ["Trecho", "L [m]", "I [A]", "ΔV [V]"], corpo, [2, 1, 1, 1]),
            ("formula", ("ΔV = ΔV ramal + Σ k · L · I / 100 = " + f"{br(volts_ramal)} + " if ramal_m
                         else "ΔV = Σ k · L · I / 100 = ")
                        + f"{br(linha['queda_v'] - volts_ramal, 3)} = {br(linha['queda_v'])} V = "
                        f"{br(linha['queda'])} % ≤ {br_g(uso)} % → {_ok(ok)}"),
        ]
        if not ok:
            avisos.append(f"Busway {linha['nominal']} A: queda de {br(linha['queda'])} % acima de {br_g(uso)} %")
    blocos += [("subtitulo", "Caixas MEC por andar (Tabela 30)"),
               ("tabela", ["Andar", "Cota [m]", "Unidades", "Corrente [A]", "Caixas"],
                [[a["andar"], br(a["cota"]), str(a["unidades"]), br(a["corrente"], 1),
                  "; ".join(f"{cx['tipo']} ({cx['medicoes']} med., {cx['disjuntor']} A"
                            + (", indireta" if cx.get("indireta") else "") + ")" for cx in a["caixas"])]
                 for a in bus["andares"]], [1.4, 0.8, 0.9, 1.0, 3.4])]
    m = bus["materiais"]
    metros = "; ".join(f"{br(v, 1)} m de {k} A" for k, v in sorted(m["metros"].items()))
    blocos += [
        ("paragrafo", f"Shaft (Desenho 75): {br_g(bus['shaft']['largura'])} × {br_g(bus['shaft']['profundidade'])} mm. "
                      f"Topo da prumada a {br(bus['topo'], 1)} m."),
        ("lista", [f"Busway: {metros}", f"Cotovelos {m['cotovelos']}, flanges {m['flanges']}, tampas finais {m['tampas']}",
                   f"Emendas {m['emendas']} (a cada 3 m), suportes {m['suportes']} (a cada 1,5 m)",
                   f"Barreiras corta-fogo {m['corta_fogo']} (uma por laje), plug-ins {m['plugins']}",
                   "Caixas MEC: " + ", ".join(f"{q} × {t}" for t, q in sorted(m.get("mec", {}).items())),
                   f"Cabo de comunicação {br(m.get('comunicacao_m', 0.0), 1)} m"]),
    ]
    desenho = (c.get("desenho") or {}).get("busways") or []
    if desenho:
        blocos += [("subtitulo", "Busway desenhado no projeto"),
                   ("tabela", ["Objeto", "Pavimento", "Trecho", "Corrente [A]", "Comprimento [m]"],
                    [[b["nome"], b["pavimento"], b["trecho"], str(b["corrente"]), br(b["metros"], 1)] for b in desenho],
                    [2, 1.4, 1, 1, 1.2])]
        calculadas = sorted(linha["nominal"] for linha in bus["linhas"])
        desenhadas = sorted(b["corrente"] for b in desenho if b["trecho"] == "horizontal")
        if desenhadas and desenhadas != calculadas:
            avisos.append(f"Busway: desenhado {' + '.join(map(str, desenhadas))} A e o cálculo atual pede "
                          f"{' + '.join(map(str, calculadas))} A (refaça o Busway)")
            blocos.append(("aviso", avisos[-1] + "."))
    if adotada == "busway":
        blocos += _orcamento(comparacao["custos"]["busway"], "Orçamento: busway")
    blocos += [("aviso", a) for a in bus.get("avisos", [])]
    avisos += [f"Busway: {a}" for a in bus.get("avisos", [])] if adotada == "busway" else []
    return "Busway", blocos, avisos


def _secao_murais(dados):
    """Mural de cada objeto de colunas de medição: o desenho cotado (bloco ``desenho``) e os avisos das colunas.

    Returns: (título, blocos, avisos); título None sem colunas no projeto."""
    murais = dados.get("murais") or []
    if not murais:
        return None, [], []
    blocos = [("paragrafo", "Elevação frontal das colunas de medição como montadas no projeto (ET 0018 Enel SP, "
                            "Desenhos 23, 55 e 8.24 a 8.33): caixas tipo P numeradas, CDPM com os barramentos, "
                            "disjuntor geral e DPS, eletroduto de entrada, altura ao piso e cotas em milímetros.")]
    avisos = []
    for mural in murais:
        blocos += [("subtitulo", mural["nome"]), ("desenho", mural["desenho"])]
        blocos += [("aviso", aviso) for aviso in mural.get("avisos", [])]
        avisos += [f"{mural['nome']}: {aviso}" for aviso in mural.get("avisos", [])]
    return "Mural de medição", blocos, avisos


def _secao_prumadas(dados):
    """Prumadas verticais: trechos de cada sistema (cabos, eletrodutos e taxa), materiais e o esquema vertical."""
    lista = dados.get("prumadas") or []
    if not lista:
        return None, [], []
    from freecad.Circuits.core import prumadas as regras_prumadas
    blocos = [("paragrafo", "Prumadas verticais pelo shaft, do pavimento mais baixo (origem de cada sistema) aos "
                            "andares, com uma caixa de passagem em cada andar atendido. Os eletrodutos de cada "
                            "trecho atendem à taxa máxima de ocupação da NBR 5410, 6.2.11.1.6 (53 % com um cabo, "
                            "31 % com dois, 40 % com três ou mais); a eletrocalha, a 40 % da seção útil."),
              ("formula", "Taxa = Σ (π · d²/4) dos cabos / (π · Di²/4) ≤ 40 %")]
    avisos = []
    for item in lista:
        resultado = item["resultado"]
        if len(lista) > 1:
            blocos.append(("subtitulo", item["nome"]))
        for s in resultado["sistemas"].values():
            linhas = [[f"{t['de']} → {t['ate']}", br(t["comprimento"]), str(t["cabos"]),
                       regras_prumadas.descricao_trecho(t).split(" (")[0], br(100.0 * t["taxa"], 1)]
                      for t in s["trechos"]]
            blocos += [("subtitulo", f"{s['sigla']} - {s['nome']} (origem: {s['origem']})"),
                       ("tabela", ["Trecho", "L [m]", "Cabos", "Eletroduto ou eletrocalha", "Taxa [%]"], linhas,
                        [2.6, 0.8, 0.8, 2.0, 0.9])]
            blocos += [("aviso", a) for a in s["avisos"]]
            avisos += [f"Prumada {s['sigla']}: {a}" for a in s["avisos"]]
        blocos += [("subtitulo", "Materiais das prumadas"),
                   ("tabela", ["Sistema", "Item", "Especificação", "Qtd.", "Un."],
                    [[m[0], m[1], m[2], br_g(m[3]), m[4]] for m in item["materiais"]], [2.2, 2.2, 2.0, 0.8, 0.5]),
                   ("subtitulo", "Esquema vertical"), ("desenho", item["esquema"])]
        avisos += list(resultado["avisos"])
    return "Prumadas verticais", blocos, avisos


def _secao_ocupacao(dados):
    o = dados.get("ocupacao")
    if not o or not o.get("tabela"):
        return None
    cabecalho, *linhas = o["tabela"]
    return "Ocupação dos eletrodutos e eletrocalhas", [
        ("paragrafo", "Taxa máxima de ocupação da seção interna do eletroduto (NBR 5410, 6.2.11.1.6): 53 % com um "
                      "condutor, 31 % com dois e 40 % com três ou mais; vale o trecho mais cheio de cada eletroduto."),
        ("formula", "Taxa = Σ (π · d²/4) dos condutores / (π · Di²/4) × 100"),
        ("tabela", list(cabecalho), [[str(v) for v in linha] for linha in linhas], None),
    ]


def montar(dados):
    """Seções do memorial: [(título, blocos)], na ordem do relatório.

    Args:
        dados: de ``services.memorial.coletar``: ``projeto``, ``contagem``, ``parametros``,
            ``rotulos_parametros``, ``ambientes``, ``luminotecnico``, ``quadros``, ``curto``,
            ``aterramento``, ``gerador``, ``centro_medicao``, ``murais``, ``ocupacao``, ``avisos``.
        Blocos: ``paragrafo``, ``formula``, ``lista``, ``aviso``, ``subtitulo``, ``tabela`` e ``desenho``
        (geometria em mm de ``core.centro_medicao.mural``: linhas, círculos, textos e limites).
    """
    parametros = dados.get("parametros", {})
    secoes = [_secao_identificacao(dados), _secao_normas(dados), _secao_parametros(dados)]
    avisos = list(dados.get("avisos", []))
    ambientes = _secao_ambientes(dados)
    if ambientes:
        secoes.append(ambientes)
    titulo, blocos, avisos_lum = _secao_luminotecnico(dados)
    if titulo:
        secoes.append((titulo, blocos))
        avisos += avisos_lum
    curto = dados.get("curto") or {}
    for q in dados.get("quadros", []):
        identificacao = q["dados"].get("indentificacao_painel") or q["nome"]
        icc = (curto.get("resultado") or {}).get(identificacao, {}).get("ik3") or numero(q["dados"].get("curto_circuito"))
        titulo, blocos, avisos_q = _secao_quadro(q, parametros, icc or None)
        secoes.append((titulo, blocos))
        avisos += avisos_q
    titulo, blocos, avisos_curto = _secao_curto(dados)
    if titulo:
        secoes.append((titulo, blocos))
        avisos += avisos_curto
    titulo, blocos, avisos_terra = _secao_aterramento(dados, parametros)
    if titulo:
        secoes.append((titulo, blocos))
        avisos += avisos_terra
    secao = _secao_gerador(dados)
    if secao:
        secoes.append(secao)
    for funcao in (_secao_centro, _secao_busway):
        titulo, blocos, mais = funcao(dados)
        if titulo:
            secoes.append((titulo, blocos))
            avisos += mais
    for funcao in (_secao_murais, _secao_prumadas):
        titulo, blocos, mais = funcao(dados)
        if titulo:
            secoes.append((titulo, blocos))
            avisos += mais
    secao = _secao_ocupacao(dados)
    if secao:
        secoes.append(secao)
    if dados.get("ocupacao"):
        avisos += dados["ocupacao"].get("avisos", [])
    secoes.append(("Avisos e limitações", [
        ("subtitulo", "Pontos a revisar"),
        ("lista", avisos or ["Nenhuma verificação deixou de ser atendida."]),
        ("subtitulo", "Limitações dos cálculos"),
        ("lista", LIMITACOES),
    ]))
    return secoes
