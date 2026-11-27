"""Prumadas verticais paramétricas: energia, dados e telefonia, interfone e iluminação de emergência.

``Part::FeaturePython`` no ponto do shaft, no piso do pavimento mais baixo. As entradas (andares,
sistemas, cabos por unidade, eletrodutos) refazem no ``execute`` o ``core.prumadas.dimensionar`` e o 3D
(``pecas_3d``: eletrodutos ou eletrocalha de cada trecho e a caixa de passagem de cada andar).
Os símbolos em planta e o esquema vertical são desenhados pelo serviço (``services.prumadas``).
"""
import FreeCAD as App
import Part

from freecad.Circuits.core import ocupacao
from freecad.Circuits.core import prumadas as regras
from freecad.Circuits.objects.coluna_medicao import quarto_e_opacidade

SEPARADOR = "|"
PROPRIEDADE_DO_SISTEMA = {"energia": "Energia", "dados": "Dados", "interfone": "Interfone",
                          "emergencia": "IluminacaoEmergencia"}
NOMINAIS = list(ocupacao.DIAMETROS_INTERNOS)


def andares_em_texto(andares):
    """['nome|cota [mm]|unidades'] para a propriedade ``Andares``."""
    return [f"{a['nome']}{SEPARADOR}{float(a['cota']):g}{SEPARADOR}{int(a['unidades'])}" for a in andares]


def andares_do_texto(linhas):
    andares = []
    for linha in linhas or []:
        partes = str(linha).split(SEPARADOR)
        if len(partes) != 3:
            continue
        try:
            andares.append(regras.andar(partes[0], float(partes[1]), int(float(partes[2]))))
        except ValueError:
            continue
    return andares


def _solido(peca):
    if peca["forma"] == "caixa":
        (x, y, z), (dx, dy, dz) = peca["origem"], peca["dims"]
        return Part.makeBox(dx, dy, dz, App.Vector(x, y, z))
    x, y, z = peca["origem"]
    return Part.makeCylinder(peca["raio"], peca["comprimento"], App.Vector(x, y, z), App.Vector(*peca["eixo"]))


class Prumada:
    """Prumadas verticais do edifício, recalculadas a cada mudança das entradas."""

    Type = "Prumada"

    def __init__(self, obj):
        obj.Proxy = self
        self._add_properties(obj)

    @staticmethod
    def _add_properties(obj):
        def propriedade(tipo, nome, grupo, dica, valor=None, somente_leitura=False):
            if hasattr(obj, nome):
                return
            obj.addProperty(tipo, nome, grupo, dica)
            if valor is not None:
                setattr(obj, nome, valor)
            if somente_leitura:
                obj.setEditorMode(nome, 1)

        def lista(nome, grupo, dica, opcoes, valor):
            if hasattr(obj, nome):
                return
            obj.addProperty("App::PropertyEnumeration", nome, grupo, dica)
            setattr(obj, nome, list(opcoes))
            setattr(obj, nome, valor)

        p = regras.PADROES
        sistemas = "Sistemas"
        for chave, nome in PROPRIEDADE_DO_SISTEMA.items():
            propriedade("App::PropertyBool", nome, sistemas, f"Desenha a prumada de {regras.SISTEMAS[chave][0].lower()}",
                        True)
        propriedade("App::PropertyStringList", "Andares", "Edifício",
                    "Um andar por linha: nome|cota do piso [mm]|unidades; o mais baixo é a origem")
        energia = "Energia"
        propriedade("App::PropertyFloat", "SecaoAlimentador", energia, "Seção do alimentador de cada unidade [mm²]",
                    float(p["secao_alimentador"]))
        propriedade("App::PropertyInteger", "CondutoresPorUnidade", energia,
                    "Condutores do alimentador de cada unidade (2 fases, neutro e PE = 4)", int(p["condutores_por_unidade"]))
        lista("FormaEnergia", energia, "Um eletroduto por unidade ou eletrocalha vertical", regras.FORMAS_ENERGIA,
              p["forma_energia"])
        fracos = "Dados, interfone e emergência"
        propriedade("App::PropertyInteger", "PontosDados", fracos, "Cabos UTP por unidade", int(p["pontos_dados"]))
        lista("EletrodutoDados", fracos, "Eletroduto da prumada de dados", NOMINAIS, p["eletroduto_dados"])
        propriedade("App::PropertyInteger", "CabosInterfone", fracos, "Cabos CCI por unidade", int(p["cabos_interfone"]))
        lista("EletrodutoInterfone", fracos, "Eletroduto da prumada de interfone", NOMINAIS, p["eletroduto_interfone"])
        propriedade("App::PropertyInteger", "CircuitosEmergencia", fracos, "Circuitos da iluminação de emergência",
                    int(p["circuitos_emergencia"]))
        propriedade("App::PropertyFloat", "SecaoEmergencia", fracos, "Seção do circuito de emergência [mm²]",
                    float(p["secao_emergencia"]))
        lista("TipoEletroduto", "Eletrodutos", "Tipo dos eletrodutos (diâmetros internos)", ("Rígido", "Flexível"),
              p["tipo_eletroduto"])
        saida = "Dimensionamento"
        propriedade("App::PropertyStringList", "Resumo", saida, "Trechos de cada sistema", None, True)
        propriedade("App::PropertyStringList", "Avisos", saida, "Avisos do dimensionamento", None, True)
        propriedade("App::PropertyStringList", "TiposDasPecas", saida, "Sistema de cada sólido, para as cores")
        obj.setEditorMode("TiposDasPecas", 2)

    @staticmethod
    def parametros(obj):
        return {
            "sistemas": [chave for chave, nome in PROPRIEDADE_DO_SISTEMA.items() if bool(getattr(obj, nome, True))],
            "secao_alimentador": float(obj.SecaoAlimentador),
            "condutores_por_unidade": int(obj.CondutoresPorUnidade),
            "forma_energia": str(obj.FormaEnergia),
            "pontos_dados": int(obj.PontosDados),
            "eletroduto_dados": str(obj.EletrodutoDados),
            "cabos_interfone": int(obj.CabosInterfone),
            "eletroduto_interfone": str(obj.EletrodutoInterfone),
            "circuitos_emergencia": int(obj.CircuitosEmergencia),
            "secao_emergencia": float(obj.SecaoEmergencia),
            "tipo_eletroduto": str(obj.TipoEletroduto),
        }

    def resultado(self, obj):
        return regras.dimensionar(andares_do_texto(obj.Andares), self.parametros(obj))

    def execute(self, obj):
        resultado = self.resultado(obj)
        resumo = []
        for s in resultado["sistemas"].values():
            for t in s["trechos"]:
                resumo.append(f"{s['sigla']} {t['de']} → {t['ate']}: {regras.descricao_trecho(t)}")
        obj.Resumo = resumo
        obj.Avisos = list(resultado["avisos"]) + [a for s in resultado["sistemas"].values() for a in s["avisos"]]
        pecas = regras.pecas_3d(resultado)
        obj.TiposDasPecas = [peca["cor_tipo"] for peca in pecas]
        posicao = obj.Placement
        obj.Shape = Part.makeCompound([_solido(peca) for peca in pecas]) if pecas else Part.Shape()
        obj.Placement = posicao

    def onDocumentRestored(self, obj):
        self._add_properties(obj)
        pintar(obj)

    def dumps(self):
        return {"Type": self.Type}

    def loads(self, state):
        if state:
            self.Type = state.get("Type", "Prumada")


def cores_das_faces(forma, tipos, opacidade=None):
    """Cor de cada face pelo sistema do sólido (``core.prumadas.CORES``), opaca nas duas versões do FreeCAD."""
    if opacidade is None:
        opacidade = quarto_e_opacidade()
    cores = []
    for solido, tipo in zip(forma.Solids, tipos):
        r, g, b = regras.CORES.get(tipo, (0.7, 0.7, 0.7))
        cores += [(r, g, b, 1.0 if opacidade else 0.0)] * len(solido.Faces)
    return cores


def pintar(fp):
    vobj = getattr(fp, "ViewObject", None)
    if vobj is None:
        return
    try:
        cores = cores_das_faces(fp.Shape, list(fp.TiposDasPecas))
        if cores and len(cores) == len(fp.Shape.Faces):
            vobj.DiffuseColor = cores
    except Exception as erro:
        App.Console.PrintWarning(f"Prumadas: cores não aplicadas ({erro}).\n")


class ViewProviderPrumada:
    """Pinta os eletrodutos e as caixas com a cor de cada sistema."""

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        import os
        from freecad.Circuits import ICON_PATH
        return os.path.join(ICON_PATH, "prumadas.svg")

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def updateData(self, fp, prop):
        if prop in ("Shape", "TiposDasPecas"):
            pintar(fp)

    def onChanged(self, vp, prop):
        pass

    def getDefaultDisplayMode(self):
        return "Shaded"

    def dumps(self):
        return None

    def loads(self, state):
        return None


def create_prumada(doc=None, nome="Prumadas", **valores):
    """Cria as prumadas no documento com os valores dados (nomes das propriedades)."""
    doc = doc or App.activeDocument()
    obj = doc.addObject("Part::FeaturePython", nome)
    Prumada(obj)
    try:
        ViewProviderPrumada(obj.ViewObject)
        obj.ViewObject.DisplayMode = "Shaded"
    except Exception:
        pass
    for chave, valor in valores.items():
        setattr(obj, chave, valor)
    obj.Label = "Prumadas verticais"
    doc.recompute()
    return obj
