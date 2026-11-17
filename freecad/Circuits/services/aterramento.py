"""Condutores de aterramento desenhados na planta."""
from freecad.Circuits.services import pavimentos
from freecad.Circuits.services.estilo import pintar_linha

SECOES = ["16", "25", "35", "50", "70"]  # mm², cobre nu
SECAO_PADRAO = "50"
COR_ATERRAMENTO = (0.0, 0.55, 0.0)


def eh_condutor(obj):
    return hasattr(obj, "Points") and hasattr(obj, "SecaoAterramento")


def listar_condutores(doc):
    return [obj for obj in doc.Objects if eh_condutor(obj)]


def marcar_condutores(doc, objetos, secao=SECAO_PADRAO):
    """Marca as linhas como condutores de aterramento de cobre nu, na seção dada.

    As linhas vão para a pasta Aterramento do pavimento ativo (se ainda não estão
    num pavimento) e ficam verdes.

    Returns:
        Quantidade de linhas marcadas; objetos que não são linhas são ignorados.
    """
    linhas = [obj for obj in objetos if hasattr(obj, "Points")]
    destino = pavimentos.pavimento_para_insercao(doc) if linhas else None
    doc.openTransaction("Condutor de aterramento")
    try:
        for obj in linhas:
            if not hasattr(obj, "SecaoAterramento"):
                obj.addProperty("App::PropertyEnumeration", "SecaoAterramento", "Aterramento",
                                "Seção do condutor de cobre nu [mm²]")
                obj.SecaoAterramento = SECOES
            obj.SecaoAterramento = str(secao)
            if pavimentos.pavimento_do_objeto(doc, obj) is None:
                pavimentos.arquivar(doc, obj, destino)  # mesmo pavimento em que os símbolos entram
            pintar_linha(obj, COR_ATERRAMENTO)
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    doc.recompute()
    return len(linhas)
