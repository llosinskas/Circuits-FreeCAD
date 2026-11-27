"""Novo projeto elétrico no documento: grupos, pavimentos e parâmetros (``core.novo_projeto``)."""
from freecad.Circuits.core import novo_projeto as regras
from freecad.Circuits.services import parametros, pavimentos
from freecad.Circuits.services.documento import GRUPOS_PROJETO, criar_grupos


def bim_disponivel():
    try:
        import Arch  # noqa: F401
        return True
    except Exception:
        return False


def existentes(doc):
    """Pavimentos do documento como no diálogo: [{'nome', 'cota', 'altura', 'bim'}]."""
    if doc is None:
        return []
    return [{"nome": p["nome"], "cota": p["elevacao_mm"], "altura": p["altura_mm"], "bim": p["bim"]}
            for p in pavimentos.resumo(doc)]


def dados_iniciais(doc):
    """Valores do diálogo para este documento (ou para um projeto novo, sem documento)."""
    textos = parametros.textos(doc) if doc is not None else {}
    dados = regras.dados_iniciais(textos, existentes(doc))
    if doc is not None and not dados.get("projeto"):
        dados["projeto"] = doc.Label
    return dados


def aplicar(doc, dados):
    """Cria ou atualiza o projeto com os dados do diálogo.

    - grupos do projeto (``GRUPOS_PROJETO``);
    - um pavimento por linha: nível da bancada BIM (``dados['niveis_bim']``) ou pasta da bancada; os níveis
      do BIM que já existem ficam com a cota e a altura deles;
    - o pavimento inicial (Térreo) fica ativo;
    - planilha de parâmetros com a identificação, o fornecimento, os condutores e a proteção.

    Returns:
        {'criados': [nomes], 'atualizados': [nomes], 'ativo': nome, 'parametros': [chaves que mudaram]}.

    Raises:
        ValueError: com as mensagens de ``core.novo_projeto.validar``.
    """
    erros = regras.validar(dados)
    if erros:
        raise ValueError("\n".join(erros))
    criar_grupos(doc, GRUPOS_PROJETO)
    criados, atualizados = [], []
    usar_bim = bool(dados.get("niveis_bim")) and bim_disponivel()
    for pav in dados["pavimentos"]:
        nome, cota, altura = str(pav["nome"]).strip(), float(pav["cota"]), float(pav["altura"])
        ja_existia = pavimentos.por_nome(doc, nome) is not None
        if usar_bim and not ja_existia:
            pavimentos.criar_nivel_bim(doc, nome, cota, altura)
        else:
            pavimentos.definir(doc, nome, cota, altura)
        (atualizados if ja_existia else criados).append(nome)
    inicial = pavimentos.por_nome(doc, regras.pavimento_inicial(dados["pavimentos"]))
    if inicial is not None:
        pavimentos.ativar(doc, inicial)
    parametros.planilha(doc, criar=True)
    mudaram = parametros.gravar(doc, regras.valores_dos_parametros(dados))
    if dados.get("projeto"):
        doc.Label = str(dados["projeto"]).strip() or doc.Label
    doc.recompute()
    return {"criados": criados, "atualizados": atualizados, "ativo": inicial.Label if inicial is not None else "",
            "parametros": mudaram}
