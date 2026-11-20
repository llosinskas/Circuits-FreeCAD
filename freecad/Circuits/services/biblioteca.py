"""Biblioteca de componentes: modelos .FCStd de ``Componentes/`` e os exemplos paramétricos.

Todo componente inserido vira uma pasta própria (``App::Part``, que move tudo
junto) dentro de *<pavimento> > Equipamentos*, no piso do pavimento de inserção,
com a propriedade ``componente_biblioteca`` (o arquivo ou ``exemplo:<chave>``).
O arquivo entra como link (referência que acompanha a biblioteca; exige o
projeto salvo) ou como cópia; o exemplo é desenhado com primitivas
(``core.biblioteca.EXEMPLOS``).
"""
import os
import re
import zipfile

import FreeCAD as App
import Part

from freecad.Circuits import ELECTRIC_LIBRARY_PATH
from freecad.Circuits.core import biblioteca as regras
from freecad.Circuits.services import pavimentos
from freecad.Circuits.services.documento import GRUPOS_MODELO

LINK, COPIA = "link", "copia"


def listar_modelos():
    """Nomes dos arquivos .FCStd da biblioteca elétrica."""
    return [f for f in os.listdir(ELECTRIC_LIBRARY_PATH) if f.endswith(".FCStd")]


def listar_itens(pasta, com_exemplos=True):
    """Itens da biblioteca (``core.biblioteca``): os exemplos e os .FCStd da pasta e das subpastas."""
    itens = regras.itens_dos_exemplos() if com_exemplos else []
    for raiz, _, arquivos in os.walk(pasta):
        for arquivo in sorted(arquivos):
            if arquivo.lower().endswith(".fcstd"):
                itens.append(regras.item_do_arquivo(os.path.join(raiz, arquivo), arquivo))
    return itens


def miniatura(caminho):
    """Bytes do PNG da miniatura gravada no .FCStd, ou None."""
    try:
        with zipfile.ZipFile(caminho) as arquivo:
            nome = next((n for n in arquivo.namelist() if n.lower() == "thumbnails/thumbnail.png"), None)
            return arquivo.read(nome) if nome else None
    except (OSError, zipfile.BadZipFile):
        return None


def criar_modelo(nome):
    """Cria e salva um documento novo de modelo na biblioteca."""
    caminho = os.path.join(ELECTRIC_LIBRARY_PATH, nome + ".FCStd")
    doc = App.newDocument(nome)
    for grupo in GRUPOS_MODELO:
        doc.addObject("App::DocumentObjectGroup", grupo)
    App.ActiveDocument.saveAs(caminho)
    doc.recompute()
    return doc


def _renomear_se_existir(doc, objeto):
    for obj in doc.Objects:
        if obj.Label == objeto.Label:
            obj.Label = f"_{objeto.Label}"
            return True
    return False


def importar_modelo(doc, arquivo):
    """Copia os objetos de um modelo da biblioteca para um grupo do documento."""
    nome = arquivo.split(".")[0]
    pasta = doc.addObject("App::DocumentObjectGroup", nome)
    origem = App.open(os.path.join(ELECTRIC_LIBRARY_PATH, arquivo))

    for obj in origem.Objects:
        if not _renomear_se_existir(doc, obj):
            pasta.addObject(doc.copyObject(obj))

    App.closeDocument(origem.Name)
    doc.recompute()


# --- inserção ---------------------------------------------------------------------

def _nome_interno(texto):
    nome = re.sub(r"[^A-Za-z0-9_]", "_", str(texto)) or "Componente"
    return f"_{nome}" if nome[0].isdigit() else nome


def _pasta_do_componente(doc, rotulo, origem, pavimento):
    """``App::Part`` do componente, dentro de *<pavimento> > Equipamentos*, no piso do pavimento."""
    parte = doc.addObject("App::Part", _nome_interno(rotulo))
    parte.Label = rotulo
    parte.addProperty("App::PropertyString", "componente_biblioteca", "Biblioteca",
                      "Arquivo da biblioteca ou exemplo que gerou o componente")
    parte.componente_biblioteca = str(origem)
    if pavimento is not None:
        pavimentos.pasta(doc, pavimento, "equipamentos").addObject(parte)
        posicao = parte.Placement
        posicao.Base = App.Vector(0, 0, pavimentos.elevacao(pavimento))
        parte.Placement = posicao
    return parte


def _forma_do_exemplo(dados):
    """Sólido do exemplo, com as primitivas subidas da altura de montagem."""
    altura = float(dados.get("altura_mm", 0.0))
    solidos = []
    for primitiva in dados["primitivas"]:
        if primitiva[0] == "caixa":
            (x, y, z), (dx, dy, dz) = primitiva[1], primitiva[2]
            solidos.append(Part.makeBox(dx, dy, dz, App.Vector(x, y, z + altura)))
        else:
            (x, y, z), raio, comprimento, eixo = primitiva[1], primitiva[2], primitiva[3], primitiva[4]
            solidos.append(Part.makeCylinder(raio, comprimento, App.Vector(x, y, z + altura), App.Vector(*eixo)))
    return Part.makeCompound(solidos)


def inserir_exemplo(doc, chave, pavimento=None):
    """Desenha o exemplo ``chave`` de ``core.biblioteca.EXEMPLOS`` na pasta Equipamentos do pavimento.

    Returns:
        A pasta (``App::Part``) do componente.
    """
    dados = regras.EXEMPLOS[chave]
    parte = _pasta_do_componente(doc, dados["nome"], regras.caminho_do_exemplo(chave), pavimento)
    corpo = doc.addObject("Part::Feature", _nome_interno(chave))
    corpo.Label = dados["nome"]
    corpo.Shape = _forma_do_exemplo(dados)
    for nome, tipo, valor, dica in (
            ("Descricao", "App::PropertyString", dados["descricao"], "Descrição do equipamento"),
            ("AlturaMontagem", "App::PropertyLength", float(dados.get("altura_mm", 0.0)), "Do piso à base [mm]"),
            ("Potencia", "App::PropertyFloat", float(dados.get("potencia_va", 0.0)), "Potência aparente [VA]")):
        corpo.addProperty(tipo, nome, "Equipamento", dica)
        setattr(corpo, nome, valor)
    try:
        corpo.ViewObject.ShapeColor = dados.get("cor", (0.8, 0.8, 0.8))
    except Exception:
        pass
    parte.addObject(corpo)
    doc.recompute()
    return parte


def _documento_aberto(caminho):
    alvo = os.path.normpath(caminho)
    return next((d for d in App.listDocuments().values() if os.path.normpath(d.FileName or "") == alvo), None)


def _raizes(objetos):
    """Objetos que não estão dentro de outro grupo do mesmo conjunto."""
    filhos = {f.Name for o in objetos for f in (getattr(o, "Group", None) or [])}
    return [o for o in objetos if o.Name not in filhos]


def inserir_arquivo(doc, caminho, modo=LINK, pavimento=None):
    """Insere um .FCStd da biblioteca como link (referência) ou cópia, na pasta Equipamentos do pavimento.

    Returns:
        A pasta (``App::Part``) do componente.
    Raises:
        RuntimeError: link com o projeto ainda não salvo, ou arquivo vazio.
    """
    rotulo = regras.nome_amigavel(os.path.basename(caminho))
    if modo == LINK and not doc.FileName:
        raise RuntimeError("Para inserir como link, salve o projeto antes (ou escolha Cópia).")
    if modo == COPIA:
        antes = {o.Name for o in doc.Objects}
        doc.mergeProject(caminho)
        novos = [o for o in doc.Objects if o.Name not in antes]
        if not novos:
            raise RuntimeError(f"Nenhum objeto em {os.path.basename(caminho)}.")
        parte = _pasta_do_componente(doc, rotulo, caminho, pavimento)
        for obj in _raizes(novos):
            parte.addObject(obj)
        doc.recompute()
        return parte

    origem = _documento_aberto(caminho) or App.openDocument(caminho, hidden=True)
    if not origem.Objects:
        raise RuntimeError(f"Nenhum objeto em {os.path.basename(caminho)}.")
    App.setActiveDocument(doc.Name)
    parte = _pasta_do_componente(doc, rotulo, caminho, pavimento)
    prefixo = _nome_interno(os.path.splitext(os.path.basename(caminho))[0])

    def ligar(obj, destino):
        if obj.TypeId == "App::DocumentObjectGroup":  # o grupo é recriado aqui, com links dentro
            grupo = doc.addObject("App::DocumentObjectGroup", _nome_interno(f"{prefixo}_{obj.Label}"))
            grupo.Label = obj.Label
            destino.addObject(grupo)
            for filho in obj.Group:
                ligar(filho, grupo)
            return
        link = doc.addObject("App::Link", _nome_interno(f"{prefixo}_{obj.Label}"))
        link.Label = obj.Label
        link.LinkedObject = obj
        destino.addObject(link)

    for obj in _raizes(list(origem.Objects)):
        ligar(obj, parte)
    doc.recompute()
    return parte


def inserir(doc, caminho, modo=LINK, pavimento=None):
    """Insere o item da biblioteca (exemplo ou arquivo) e devolve a pasta dele."""
    chave = regras.chave_do_exemplo(caminho)
    return inserir_exemplo(doc, chave, pavimento) if chave else inserir_arquivo(doc, caminho, modo, pavimento)
