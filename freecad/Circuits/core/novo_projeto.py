"""Novo projeto elétrico: dados pedidos no diálogo, pavimentos gerados e parâmetros do projeto.

O diálogo do botão *Novo projeto* pede a identificação (carimbo), o tipo de edificação, os pavimentos
(subsolos, andares acima do térreo, cobertura, piso a piso), o fornecimento de energia (concessionária,
sistema de tensões, fases, curto na entrada, esquema de aterramento) e os condutores e a proteção.
Aqui ficam só as regras: as sugestões por tipo de edificação, a lista de pavimentos com cota e altura,
a validação e a conversão para as chaves de ``core.parametros.CAMPOS``.
Cotas e alturas em mm.
"""
from freecad.Circuits.core import parametros

TIPOS_EDIFICACAO = ("Residencial unifamiliar", "Residencial multifamiliar", "Comercial", "Industrial")
FORNECIMENTOS = ("Monofásico", "Bifásico", "Trifásico")
# Sistema de tensões (fase-neutro / fase-fase), em V.
SISTEMAS = {
    "127/220 V": (127.0, 220.0),
    "220/380 V": (220.0, 380.0),
    "115/230 V": (115.0, 230.0),
    "254/440 V": (254.0, 440.0),
}
MAXIMO_ANDARES = 80
MAXIMO_SUBSOLOS = 6
TERREO = "Térreo"
COBERTURA = "Cobertura"

# Sugestões ao escolher o tipo de edificação (o usuário pode mudar tudo depois).
SUGESTOES = {
    "Residencial unifamiliar": {"subsolos": 0, "andares": 0, "cobertura": False, "piso_a_piso": 3000.0,
                                "altura_terreo": 3000.0, "sistema": "127/220 V", "fornecimento": "Bifásico",
                                "esquema": "TN-S", "icc_entrada_ka": 5.0},
    "Residencial multifamiliar": {"subsolos": 1, "andares": 4, "cobertura": True, "piso_a_piso": 2880.0,
                                  "altura_terreo": 3500.0, "sistema": "127/220 V", "fornecimento": "Trifásico",
                                  "esquema": "TN-S", "icc_entrada_ka": 10.0},
    "Comercial": {"subsolos": 0, "andares": 1, "cobertura": False, "piso_a_piso": 3500.0,
                  "altura_terreo": 4000.0, "sistema": "127/220 V", "fornecimento": "Trifásico",
                  "esquema": "TN-S", "icc_entrada_ka": 10.0},
    "Industrial": {"subsolos": 0, "andares": 0, "cobertura": False, "piso_a_piso": 6000.0,
                   "altura_terreo": 8000.0, "sistema": "220/380 V", "fornecimento": "Trifásico",
                   "esquema": "TN-S", "icc_entrada_ka": 20.0},
}

# Campo do diálogo -> chave de core.parametros.CAMPOS (gravados na planilha de parâmetros).
PARAMETROS_DO_DIALOGO = ("projeto", "obra", "cliente", "responsavel", "registro", "desenhista", "concessionaria",
                         "icc_entrada_ka", "esquema", "resistencia_terra", "material", "isolacao",
                         "temperatura_ambiente", "sensibilidade_dr", "curva_iluminacao", "curva_tomadas",
                         "tipo_edificacao", "fornecimento")


def nome_do_andar(numero):
    """1 -> '1º Pavimento'."""
    return f"{int(numero)}º Pavimento"


def pavimentos(subsolos=0, andares=0, cobertura=False, piso_a_piso=3000.0, altura_terreo=None,
               cota_terreo=0.0, piso_a_piso_subsolo=None):
    """Lista dos pavimentos, do mais baixo ao mais alto.

    Args:
        subsolos: quantidade de subsolos (Subsolo 1 logo abaixo do térreo).
        andares: andares acima do térreo (1º Pavimento, 2º...).
        cobertura: acrescenta a Cobertura (casa de máquinas, barrilete) acima do último andar.
        piso_a_piso: altura de piso a piso dos andares [mm].
        altura_terreo: piso a piso do térreo [mm]; sem ele, ``piso_a_piso``.
        cota_terreo: cota do piso do térreo [mm].
        piso_a_piso_subsolo: dos subsolos [mm]; sem ele, ``piso_a_piso``.

    Returns:
        [{'nome', 'cota', 'altura'}] em mm.
    """
    subsolos = max(0, min(MAXIMO_SUBSOLOS, int(subsolos)))
    andares = max(0, min(MAXIMO_ANDARES, int(andares)))
    piso_a_piso = float(piso_a_piso)
    altura_terreo = float(altura_terreo or piso_a_piso)
    subsolo = float(piso_a_piso_subsolo or piso_a_piso)
    cota_terreo = float(cota_terreo)
    lista = [{"nome": f"Subsolo {i}", "cota": cota_terreo - i * subsolo, "altura": subsolo}
             for i in range(subsolos, 0, -1)]
    lista.append({"nome": TERREO, "cota": cota_terreo, "altura": altura_terreo})
    cota = cota_terreo + altura_terreo
    for i in range(1, andares + 1):
        lista.append({"nome": nome_do_andar(i), "cota": cota, "altura": piso_a_piso})
        cota += piso_a_piso
    if cobertura:
        lista.append({"nome": COBERTURA, "cota": cota, "altura": piso_a_piso})
    return lista


def pavimento_inicial(lista):
    """Nome do pavimento que fica ativo: o Térreo, senão o de cota mais perto de zero."""
    if not lista:
        return None
    terreo = next((p for p in lista if p["nome"] == TERREO), None)
    return (terreo or min(lista, key=lambda p: abs(float(p["cota"]))))["nome"]


def validar(dados):
    """Erros que impedem criar o projeto (lista vazia = pode criar)."""
    erros = []
    lista = dados.get("pavimentos") or []
    if not lista:
        erros.append("Informe pelo menos um pavimento.")
    nomes = [str(p.get("nome", "")).strip() for p in lista]
    if any(not n for n in nomes):
        erros.append("Todo pavimento precisa de nome.")
    repetidos = sorted({n for n in nomes if n and nomes.count(n) > 1})
    if repetidos:
        erros.append("Pavimentos com o mesmo nome: " + ", ".join(repetidos) + ".")
    cotas = [float(p.get("cota", 0.0)) for p in lista]
    if any(b <= a for a, b in zip(cotas, cotas[1:])):
        erros.append("As cotas dos pavimentos precisam crescer de cima para baixo da lista (do mais baixo ao mais alto).")
    if any(float(p.get("altura", 0.0)) <= 0 for p in lista):
        erros.append("O piso a piso de cada pavimento precisa ser maior que zero.")
    if dados.get("sistema") and dados["sistema"] not in SISTEMAS:
        erros.append(f"Sistema de tensões desconhecido: {dados['sistema']}.")
    return erros


def _texto(valor):
    if isinstance(valor, float):
        return f"{valor:g}".replace(".", ",")
    return str(valor if valor is not None else "").strip()


def valores_dos_parametros(dados):
    """{chave de core.parametros.CAMPOS: texto} para ``services.parametros.gravar``.

    As tensões vêm do sistema escolhido (``SISTEMAS``); os outros campos vão como estão.
    """
    valores = {chave: _texto(dados[chave]) for chave in PARAMETROS_DO_DIALOGO
               if chave in dados and chave in parametros.CAMPOS and dados[chave] is not None}
    if dados.get("sistema") in SISTEMAS:
        fn, ff = SISTEMAS[dados["sistema"]]
        valores["tensao_fn"], valores["tensao_ff"] = _texto(fn), _texto(ff)
    return valores


def sistema_das_tensoes(tensao_fn, tensao_ff):
    """Nome do sistema com estas tensões, ou o primeiro de ``SISTEMAS``."""
    for nome, (fn, ff) in SISTEMAS.items():
        if abs(fn - float(tensao_fn)) < 0.5 and abs(ff - float(tensao_ff)) < 0.5:
            return nome
    return next(iter(SISTEMAS))


def dados_iniciais(textos=None, existentes=None, tipo=None):
    """Valores para abrir o diálogo: os do projeto (planilha de parâmetros e pavimentos já criados)
    ou, num projeto novo, as sugestões do tipo de edificação.

    Args:
        textos: {chave: texto} da planilha de parâmetros (``services.parametros.textos``).
        existentes: pavimentos do documento [{'nome', 'cota', 'altura'}].
        tipo: tipo de edificação, quando o projeto não tem um gravado.
    """
    textos = dict(textos or {})
    valores = parametros.ler(textos)
    tipo = textos.get("tipo_edificacao") or tipo or TIPOS_EDIFICACAO[0]
    if tipo not in SUGESTOES:
        tipo = TIPOS_EDIFICACAO[0]
    sugestao = SUGESTOES[tipo]
    novo = not any(str(v).strip() for v in textos.values())
    dados = {chave: (valores[chave] if chave in valores else "") for chave in PARAMETROS_DO_DIALOGO}
    dados["tipo_edificacao"] = tipo
    dados["fornecimento"] = textos.get("fornecimento") or sugestao["fornecimento"]
    if novo:
        dados["sistema"] = sugestao["sistema"]
        dados["esquema"] = sugestao["esquema"]
        dados["icc_entrada_ka"] = sugestao["icc_entrada_ka"]
    else:
        dados["sistema"] = sistema_das_tensoes(valores["tensao_fn"], valores["tensao_ff"])
    if existentes:
        dados["pavimentos"] = [{"nome": p["nome"], "cota": float(p["cota"]), "altura": float(p["altura"]),
                                "bim": bool(p.get("bim"))} for p in existentes]
        dados["niveis_bim"] = any(p.get("bim") for p in existentes)
    else:
        dados["pavimentos"] = pavimentos(sugestao["subsolos"], sugestao["andares"], sugestao["cobertura"],
                                         sugestao["piso_a_piso"], sugestao["altura_terreo"])
    dados["novo"] = novo
    return dados


def resumo(dados):
    """Texto curto do que será criado, para o rodapé do diálogo."""
    lista = dados.get("pavimentos") or []
    fn, ff = SISTEMAS.get(dados.get("sistema"), (None, None))
    partes = [f"{len(lista)} pavimento(s)"]
    if lista:
        partes.append(f"de {lista[0]['nome']} ({lista[0]['cota'] / 1000:.2f} m) a {lista[-1]['nome']} "
                      f"({lista[-1]['cota'] / 1000:.2f} m)".replace(".", ","))
    if fn:
        partes.append(f"{dados.get('fornecimento', '').lower()} {fn:g}/{ff:g} V")
    if dados.get("esquema"):
        partes.append(f"esquema {dados['esquema']}")
    return ", ".join(partes)
