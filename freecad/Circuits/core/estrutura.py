"""Estrutura de pastas do projeto: poucas pastas na raiz, criadas só quando há algo para elas.

::

    <Projeto>
    ├── Pavimentos      um grupo por pavimento, com as pastas por tipo (Tomadas, Iluminação, Quadros...)
    ├── Planilhas       parâmetros, notas, centro de medição, curto, gerador, listas, quadros sem símbolo
    ├── Diagramas       unifilares, multifilares e transferência dos quadros sem símbolo na planta
    ├── Documentos      legenda, notas, detalhes das verticais, identificação fora dos pavimentos
    └── Folhas          pranchas do TechDraw

Com níveis da bancada BIM, os pavimentos ficam no edifício do BIM (com o nome do projeto), e a pasta
Pavimentos não é criada. Cada pasta é marcada pela propriedade ``pasta_projeto`` (a chave).
Aqui ficam só as regras: as pastas, para qual delas vai cada objeto e as pastas antigas.
"""
MARCA = "pasta_projeto"

# chave: (nome interno, rótulo, descrição). O nome interno de Pavimentos é o antigo "Pontos_eletricos",
# que ``services.pavimentos.GRUPO_MAE`` procura.
PASTAS = {
    "pavimentos": ("Pontos_eletricos", "Pavimentos", "Um grupo por pavimento, com as pastas de cada tipo"),
    "planilhas": ("Planilhas", "Planilhas", "Parâmetros, notas, centro de medição, curto, gerador e listas"),
    "diagramas": ("Diagramas", "Diagramas", "Unifilares, multifilares e transferência dos quadros sem símbolo"),
    "documentos": ("Documentos", "Documentos", "Legenda, notas e detalhes"),
    "folhas": ("Folhas", "Folhas", "Pranchas do TechDraw"),
}

# Pastas que versões anteriores criavam no Novo projeto; saem quando estão vazias.
PASTAS_ANTIGAS = ("Arquitetura_referencia", "Niveis", "Quadros", "Tomadas", "Iluminacao", "Equipamentos",
                  "Eletrodutos", "Eletrocalha", "Cabos", "Aterramento", "Tabelas_e_planilhas", "Detalhes",
                  "Diagramas", "Projetos_2D")

# Marca (propriedade) -> pasta, para os objetos que ficam na raiz do documento.
PLANILHAS = ("parametros_do_projeto", "notas_do_projeto", "centro_medicao", "estudo_de_curto", "cargas_do_gerador",
             "lista_de_verticais", "ocupacao_eletrodutos", "calculo_aterramento", "quadro", "circuitos_de",
             "componentes_de", "quadro_cargas_de")
DIAGRAMAS = ("quadro_origem", "multifilar_de", "diagrama_gerador")
DOCUMENTOS_POR_NOME = ("Legenda_simbolos", "Notas_projeto", "Detalhes_verticais", "Identificacao_pontos")
DOCUMENTOS_POR_MARCA = ("esquema_grupo_de",)
TIPOS_DE_FOLHA = ("TechDraw::DrawPage",)


def pasta_de(propriedades, tipo, nome):
    """Chave da pasta de um objeto da raiz, ou None se ele fica onde está.

    Args:
        propriedades: nomes das propriedades do objeto.
        tipo: ``TypeId``.
        nome: ``Name``.
    """
    propriedades = set(propriedades)
    if MARCA in propriedades:
        return None
    if tipo in TIPOS_DE_FOLHA:
        return "folhas"
    if tipo == "Spreadsheet::Sheet" and propriedades.intersection(PLANILHAS):
        return "planilhas"
    if propriedades.intersection(DIAGRAMAS):
        return "diagramas"
    if nome in DOCUMENTOS_POR_NOME or propriedades.intersection(DOCUMENTOS_POR_MARCA):
        return "documentos"
    return None


def pastas_iniciais(niveis_bim=False):
    """Pastas que o Novo projeto cria já de saída: Pavimentos (sem níveis do BIM) e Planilhas."""
    return (["planilhas"] if niveis_bim else ["pavimentos", "planilhas"])
