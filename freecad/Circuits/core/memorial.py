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
from freecad.Circuits.core import curto as regras_curto
from freecad.Circuits.core.functions.Predial import demanda as regras_demanda
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


def _secao_centro(dados):
    c = dados.get("centro_medicao")
    if not c or not c.get("resumo"):
        return None
    blocos = [("paragrafo", "Comparação entre a medição agrupada no térreo, a descentralizada por grupos de andares e "
                            "o barramento blindado (busway), pela especificação Enel 0018: queda de tensão, caixas, "
                            "alimentadores e orçamento de referência.")]
    if c.get("andares"):
        blocos.append(("tabela", ["Pavimento", "Cota [m]", "Unidades", "Demanda/un. [A]", "Fases"],
                       [[a.get("nome", ""), br(a.get("cota", 0.0)), str(a.get("unidades", 0)),
                         br_g(a.get("demanda_a", 0.0)), str(a.get("fases", ""))] for a in c["andares"]],
                       [2, 1, 1, 1.4, 0.8]))
    blocos.append(("tabela", ["Resultado", "Valor"], [[k, v] for k, v in c["resumo"].items()], [3, 3]))
    return "Centro de medição", blocos


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
            ``rotulos_parametros``, ``ambientes``, ``quadros``, ``curto``, ``gerador``,
            ``centro_medicao``, ``ocupacao``, ``avisos``.
    """
    parametros = dados.get("parametros", {})
    secoes = [_secao_identificacao(dados), _secao_normas(dados), _secao_parametros(dados)]
    avisos = list(dados.get("avisos", []))
    ambientes = _secao_ambientes(dados)
    if ambientes:
        secoes.append(ambientes)
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
    for funcao in (_secao_gerador, _secao_centro, _secao_ocupacao):
        secao = funcao(dados)
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
