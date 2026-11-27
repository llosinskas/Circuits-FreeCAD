"""Novo projeto elétrico no documento: grupos, pavimentos e parâmetros (``core.novo_projeto``)."""
import FreeCAD as App

from freecad.Circuits.core import novo_projeto as regras
from freecad.Circuits.services import estrutura, parametros, pavimentos

PROPRIEDADE_UNIDADES = "Unidades"


def bim_disponivel():
    try:
        import Arch  # noqa: F401
        return True
    except Exception:
        return False


def existentes(doc):
    """Pavimentos do documento como no diálogo: [{'nome', 'cota', 'altura', 'bim', 'unidades'}]."""
    if doc is None:
        return []
    return [{"nome": pav.Label, "cota": pavimentos.elevacao(pav), "altura": pavimentos.altura(pav),
             "bim": pavimentos.eh_nivel_bim(pav), "unidades": unidades(pav)}
            for pav in pavimentos.listar(doc)]


def unidades(pavimento):
    """Unidades (apartamentos, salas) do pavimento, gravadas pelo Novo projeto; None se não foram informadas."""
    valor = getattr(pavimento, PROPRIEDADE_UNIDADES, None)
    return int(valor) if valor is not None else None


def gravar_unidades(pavimento, quantidade):
    if not hasattr(pavimento, PROPRIEDADE_UNIDADES):
        pavimento.addProperty("App::PropertyInteger", PROPRIEDADE_UNIDADES, "Pavimento",
                              "Unidades (apartamentos ou salas) do pavimento: prumadas e centro de medição")
    if getattr(pavimento, PROPRIEDADE_UNIDADES) != int(quantidade):
        setattr(pavimento, PROPRIEDADE_UNIDADES, int(quantidade))


def dados_iniciais(doc):
    """Valores do diálogo para este documento (ou para um projeto novo, sem documento)."""
    textos = parametros.textos(doc) if doc is not None else {}
    dados = regras.dados_iniciais(textos, existentes(doc))
    if doc is not None and not dados.get("projeto"):
        dados["projeto"] = doc.Label
    return dados


def aplicar(doc, dados):
    """Cria ou atualiza o projeto com os dados do diálogo.

    - estrutura de pastas (``services.estrutura.criar``: Pavimentos e Planilhas, o edifício do BIM com
      níveis, sem as pastas antigas vazias, com o que estava na raiz arrumado);
    - um pavimento por linha, com as unidades (propriedade ``Unidades``): nível da bancada BIM
      (``dados['niveis_bim']``, dentro do edifício) ou pasta da bancada; os níveis do BIM que já existem ficam
      com a cota e a altura deles;
    - o pavimento inicial (Térreo) fica ativo;
    - planilha de parâmetros com a identificação, o fornecimento, os condutores e a proteção, na pasta
      Planilhas, e o carimbo das folhas que já existem.

    Returns:
        {'criados': [nomes], 'atualizados': [nomes], 'ativo': nome, 'parametros': [chaves que mudaram],
         'estrutura': {...}}.

    Raises:
        ValueError: com as mensagens de ``core.novo_projeto.validar``.
    """
    erros = regras.validar(dados)
    if erros:
        raise ValueError("\n".join(erros))
    criados, atualizados = [], []
    usar_bim = bool(dados.get("niveis_bim")) and bim_disponivel()
    feito_estrutura = estrutura.criar(doc, usar_bim, str(dados.get("projeto") or "").strip())
    for linha in dados["pavimentos"]:
        nome, cota, altura = str(linha["nome"]).strip(), float(linha["cota"]), float(linha["altura"])
        ja_existia = pavimentos.por_nome(doc, nome) is not None
        if usar_bim and not ja_existia:
            pav = pavimentos.criar_nivel_bim(doc, nome, cota, altura)
        else:
            pav = pavimentos.definir(doc, nome, cota, altura)
        if pav is not None and linha.get("unidades") is not None:
            gravar_unidades(pav, int(linha["unidades"] or 0))
        (atualizados if ja_existia else criados).append(nome)
    inicial = pavimentos.por_nome(doc, regras.pavimento_inicial(dados["pavimentos"]))
    if inicial is not None:
        pavimentos.ativar(doc, inicial)
    parametros.planilha(doc, criar=True)
    mudaram = parametros.gravar(doc, regras.valores_dos_parametros(dados))
    if dados.get("projeto"):
        doc.Label = str(dados["projeto"]).strip() or doc.Label
    estrutura.organizar(doc)  # a planilha de parâmetros vai para Planilhas
    try:
        from freecad.Circuits.services import folhas
        if folhas.listar_folhas(doc):
            folhas.atualizar_carimbos(doc)
    except Exception as erro:
        App.Console.PrintWarning(f"Projeto: carimbo das folhas não atualizado: {erro}\n")
    doc.recompute()
    return {"criados": criados, "atualizados": atualizados, "ativo": inicial.Label if inicial is not None else "",
            "parametros": mudaram, "estrutura": feito_estrutura}
