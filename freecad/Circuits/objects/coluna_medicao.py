"""Objeto FeaturePython paramétrico do centro de medição convencional (padrão Enel SP).

Mudar ``Medidores``, ``MedidoresPorColuna``, ``DemandaPorMedidor``, ``Fases``,
``Modelo`` ou ``CDPM`` refaz o dimensionamento (``core.centro_medicao.dimensionar_colunas``:
caixa P em agrupamento modular, caixas E com CDPM, caixas metálicas K a O ou medição indireta
(policarbonato até 300 A, caixa M até 600 A), disjuntor geral, barramento,
ramal de distribuição) e o 3D detalhado de todos os conjuntos, lado a lado. Os
resultados ficam nas propriedades só de leitura do grupo "Dimensionamento".

O nome deste módulo e das classes ficam gravados nos .FCStd: não mude.
"""
import FreeCAD as App
import Part

from freecad.Circuits.core import centro_medicao as regras

AUTOMATICO = "Automático"
RESULTADOS = ("Solucao", "Conjuntos", "DisjuntorUnidade", "CorrenteTotal", "Avisos", "coluna_medicao", "CDPMs",
              "CaixasMetalicas", "MedicoesMetalicas", "CaixasE", "CDPMsE", "Indiretas",
              "LarguraTotal", "ProfundidadeTotal", "AlturaTotal")
SOLUCOES = {"P": "Caixas P em agrupamento modular", "E": "Caixas E com CDPM",
            "metalica": "Caixas coletivas metálicas", "indireta": "Medição indireta (TCs)"}


def _solido(peca):
    if peca["forma"] == "caixa":
        (x, y, z), (dx, dy, dz) = peca["origem"], peca["dims"]
        return Part.makeBox(dx, dy, dz, App.Vector(x, y, z))
    x, y, z = peca["origem"]
    return Part.makeCylinder(peca["raio"], peca["comprimento"], App.Vector(x, y, z), App.Vector(*peca["eixo"]))


def _descricao(conjunto):
    if conjunto.get("modelo") in regras.INDIRETAS:
        return (f"{conjunto['cdpm']}: {conjunto['corrente']:.0f} A, chave seccionadora {conjunto['chave']} A, "
                f"TC {conjunto['tc']}, proteção geral {conjunto['disjuntor_geral']} A, ramal "
                f"{conjunto.get('paralelos', 1)} × {conjunto['ramal']} mm²").replace(".", ",")
    if conjunto.get("modelo", "P") == "P":
        caixa = f"{conjunto['caixas']} caixas P, {conjunto['cdpm']}"
    elif conjunto["modelo"] == "E":
        caixa = f"{conjunto['medicoes']} caixa(s) E" + (" com CDPM" if conjunto["medicoes"] > 1 else "")
    else:
        caixa = f"{conjunto['cdpm']}, {conjunto['medicoes']} medições"
    return (f"{caixa}: {conjunto['corrente']:.0f} A, disjuntor geral {conjunto['disjuntor_geral']} A, "
            f"barramento {conjunto['barramento']}, ramal {conjunto['ramal']} mm²").replace(".", ",")


class ColunaMedicao:
    """Colunas de medição paramétricas: dimensiona e desenha a cada mudança das entradas."""

    Type = "ColunaMedicao"

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

        entrada = "Medição"
        propriedade("App::PropertyInteger", "Medidores", entrada, "Medições diretas (unidades consumidoras)", 12)
        propriedade("App::PropertyIntegerConstraint", "MedidoresPorColuna", entrada,
                    "Caixas P sobrepostas em cada coluna (1 a 3, Tabela 29)", (3, 1, 3, 1))
        propriedade("App::PropertyFloat", "DemandaPorMedidor", entrada, "Corrente de demanda de cada unidade [A]",
                    63.0)
        propriedade("App::PropertyFloat", "DemandaTotal", entrada,
                    "Demanda do conjunto [A] pelo cálculo de demanda; 0 soma as unidades", 0.0)
        propriedade("App::PropertyIntegerConstraint", "Fases", entrada, "Fases de cada unidade (1, 2 ou 3)",
                    (2, 1, 3, 1))
        if not hasattr(obj, "Modelo"):
            obj.addProperty("App::PropertyEnumeration", "Modelo", entrada,
                            "Caixa: automática (P mono e bifásicas; E até 4 trifásicas; metálicas K a O; indireta acima "
                            "de 100 A) ou forçada")
            obj.Modelo = list(regras.MODELOS)
            obj.Modelo = AUTOMATICO
        if not hasattr(obj, "CDPM"):
            obj.addProperty("App::PropertyEnumeration", "CDPM", entrada, "Tipo da CDPM das caixas P (Tabela 28)")
            obj.CDPM = [AUTOMATICO] + list(regras.CDPM)
            obj.CDPM = AUTOMATICO
        propriedade("App::PropertyFloat", "Tensao", entrada, "Tensão entre fases [V]", 220.0)
        propriedade("App::PropertyFloat", "ComprimentoRamal", entrada,
                    "Do QDC ao conjunto de medição [m], para o ramal de distribuição", 10.0)

        layout = "Layout"
        if not hasattr(obj, "PosicaoCDPM"):
            obj.addProperty("App::PropertyEnumeration", "PosicaoCDPM", layout, "Posição da CDPM no conjunto")
            obj.PosicaoCDPM = list(regras.POSICOES_CDPM)
            obj.PosicaoCDPM = "Centro"
        propriedade("App::PropertyFloat", "AlturaBase", layout,
                    "Altura da base em relação ao piso [mm]; 0 usa a norma Enel", 0.0)
        if not hasattr(obj, "SaidaEletroduto"):
            obj.addProperty("App::PropertyEnumeration", "SaidaEletroduto", layout,
                            "Direção da saída dos eletrodutos das unidades")
            obj.SaidaEletroduto = list(regras.SAIDAS_ELETRODUTO)
            obj.SaidaEletroduto = "Fundo"
        propriedade("App::PropertyFloat", "LarguraCaixaP", layout,
                    "Largura da caixa P [mm]; 0 usa 260 mm (Enel)", 0.0)
        propriedade("App::PropertyFloat", "ProfundidadeCaixaP", layout,
                    "Profundidade da caixa P [mm]; 0 usa 190 mm (Enel)", 0.0)
        propriedade("App::PropertyFloat", "AlturaCaixaP", layout,
                    "Altura da caixa P [mm]; 0 usa 520 mm (Enel)", 0.0)
        propriedade("App::PropertyFloat", "FolgaConjuntos", layout,
                    "Espaço entre agrupamentos [mm]; 0 usa 100 mm", 0.0)
        propriedade("App::PropertyBool", "ComSuporte", layout,
                    "Desenha estrutura metálica de sustentação/pedestal até o piso", True)
        if not hasattr(obj, "Representacao"):
            obj.addProperty("App::PropertyEnumeration", "Representacao", layout,
                            "Sólida: caixas fechadas, tampa opaca e medidor, disjuntor e barramentos em relevo na "
                            "frente. Interna: caixas ocas com a tampa transparente")
            obj.Representacao = list(regras.REPRESENTACOES)
            obj.Representacao = regras.REPRESENTACOES[0]

        saida = "Dimensionamento"
        propriedade("App::PropertyString", "Solucao", saida, "Caixas escolhidas", "", True)
        propriedade("App::PropertyStringList", "Conjuntos", saida, "Cada agrupamento ou caixa coletiva", None, True)
        propriedade("App::PropertyInteger", "DisjuntorUnidade", saida, "Disjuntor de cada unidade [A]", 0, True)
        propriedade("App::PropertyFloat", "CorrenteTotal", saida, "Corrente de demanda do conjunto [A]", 0.0, True)
        propriedade("App::PropertyStringList", "Avisos", saida, "Avisos do dimensionamento", None, True)
        propriedade("App::PropertyInteger", "coluna_medicao", saida, "Caixas tipo P", 0, True)
        propriedade("App::PropertyStringList", "CDPMs", saida, "CDPM de cada agrupamento de caixas P", None, True)
        propriedade("App::PropertyStringList", "CaixasMetalicas", saida, "Caixas coletivas metálicas", None, True)
        propriedade("App::PropertyInteger", "MedicoesMetalicas", saida, "Medições nas caixas metálicas", 0, True)
        propriedade("App::PropertyInteger", "CaixasE", saida, "Caixas de medição tipo E", 0, True)
        propriedade("App::PropertyInteger", "CDPMsE", saida, "CDPMs das caixas E", 0, True)
        propriedade("App::PropertyStringList", "Indiretas", saida, "Conjuntos de medição indireta", None, True)
        propriedade("App::PropertyFloat", "LarguraTotal", saida, "Largura total do conjunto [mm]", 0.0, True)
        propriedade("App::PropertyFloat", "ProfundidadeTotal", saida, "Profundidade total do conjunto [mm]", 0.0, True)
        propriedade("App::PropertyFloat", "AlturaTotal", saida, "Altura total do conjunto [mm]", 0.0, True)
        propriedade("App::PropertyStringList", "TiposDasPecas", saida, "Tipo de cada sólido, para as cores")
        obj.setEditorMode("TiposDasPecas", 2)

    def dimensionar(self, obj):
        cdpm = None if str(obj.CDPM) == AUTOMATICO else str(obj.CDPM)
        return regras.dimensionar_colunas(
            int(obj.Medidores), float(obj.DemandaPorMedidor), int(obj.Fases), int(obj.MedidoresPorColuna),
            str(obj.Modelo), cdpm, float(obj.DemandaTotal), float(obj.Tensao), float(obj.ComprimentoRamal))

    def execute(self, obj):
        caixa_p = (
            float(getattr(obj, "LarguraCaixaP", 0.0) or 0.0),
            float(getattr(obj, "ProfundidadeCaixaP", 0.0) or 0.0),
            float(getattr(obj, "AlturaCaixaP", 0.0) or 0.0),
        )
        posicao_cdpm = str(getattr(obj, "PosicaoCDPM", "Centro") or "Centro")
        altura_base = float(getattr(obj, "AlturaBase", 0.0) or 0.0)
        com_suporte = bool(getattr(obj, "ComSuporte", True))
        try:
            dados = self.dimensionar(obj)
            pecas = regras.pecas_do_centro(
                dados,
                posicao_cdpm=posicao_cdpm,
                altura_base_mm=altura_base,
                caixa_p_mm=caixa_p if any(v > 0 for v in caixa_p) else None,
                saida_eletroduto=str(getattr(obj, "SaidaEletroduto", "Fundo") or "Fundo"),
                folga_conjuntos_mm=float(getattr(obj, "FolgaConjuntos", 0.0) or 0.0),
                com_suporte=com_suporte,
                representacao=str(getattr(obj, "Representacao", "") or regras.REPRESENTACOES[0]),
            )
            avisos_layout = regras.avisos_layout_enel(dados, pecas, posicao_cdpm=posicao_cdpm,
                                                      altura_base_mm=altura_base)
        except ValueError as erro:
            dados, pecas, avisos_layout = {
                "modelo": None, "conjuntos": [], "corrente": 0.0, "disjuntor_unidade": None, "avisos": [str(erro)],
            }, [], []
        dims = regras.dimensoes_das_pecas(pecas)
        conjuntos = dados["conjuntos"]
        p = [c for c in conjuntos if c.get("modelo", "P") == "P"]
        e = [c for c in conjuntos if c.get("modelo") == "E"]
        indiretas = [c for c in conjuntos if c.get("modelo") in regras.INDIRETAS]
        metalicas = [c for c in conjuntos if c.get("modelo") in regras.CAIXAS_METALICAS]
        obj.Solucao = SOLUCOES.get(dados["modelo"], "Sem conjunto: veja os avisos")
        obj.Conjuntos = [_descricao(c) for c in conjuntos]
        obj.DisjuntorUnidade = int(dados["disjuntor_unidade"] or 0)
        obj.CorrenteTotal = round(float(dados["corrente"]), 1)
        obj.Avisos = list(dados["avisos"]) + avisos_layout
        obj.coluna_medicao = sum(c["caixas"] for c in p)
        obj.CDPMs = [c["cdpm"] for c in p]
        obj.CaixasMetalicas = [c["modelo"] for c in metalicas]
        obj.MedicoesMetalicas = sum(c["medicoes"] for c in metalicas)
        obj.CaixasE = sum(c["medicoes"] for c in e)
        obj.CDPMsE = sum(1 for c in e if c["medicoes"] > 1)
        obj.Indiretas = [c["modelo"] for c in indiretas]
        obj.LarguraTotal = dims["largura_mm"]
        obj.ProfundidadeTotal = dims["profundidade_mm"]
        obj.AlturaTotal = dims["altura_mm"]
        obj.TiposDasPecas = [peca.get("cor_tipo", peca["tipo"]) for peca in pecas]
        posicao = obj.Placement
        obj.Shape = Part.makeCompound([_solido(peca) for peca in pecas]) if pecas else Part.Shape()
        obj.Placement = posicao

    def onDocumentRestored(self, obj):
        self._add_properties(obj)

    def dumps(self):
        return {"Type": self.Type}

    def loads(self, state):
        if state:
            self.Type = state.get("Type", "ColunaMedicao")


def cores_das_faces(forma, tipos):
    """Cor (r, g, b, transparência 0 a 1) de cada face, pelo tipo de cada sólido (``CORES_DAS_PECAS``)."""
    cores = []
    for solido, tipo in zip(forma.Solids, tipos):
        cor, transparencia = regras.CORES_DAS_PECAS.get(tipo, ((0.8, 0.8, 0.8), 0))
        cores += [(cor[0], cor[1], cor[2], transparencia / 100.0)] * len(solido.Faces)
    return cores


def _fosco(vobj):
    """Material sem brilho: com o especular padrão, a face de frente para a câmera (vista frontal)
    sai branca e as cores das peças somem."""
    materiais = list(getattr(vobj, "ShapeAppearance", ()) or ())
    if not materiais:
        return
    for material in materiais:
        material.SpecularColor = (0.0, 0.0, 0.0)
        material.Shininess = 0.0
    vobj.ShapeAppearance = materiais


class ViewProviderColunaMedicao:
    """Pinta cada peça com a cor do tipo dela (tampas transparentes, barramentos de cobre...)."""

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        import os
        from freecad.Circuits import ICON_PATH
        return os.path.join(ICON_PATH, "coluna_medicao.svg")

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def updateData(self, fp, prop):
        if prop in ("Shape", "TiposDasPecas"):
            try:
                cores = cores_das_faces(fp.Shape, list(fp.TiposDasPecas))
                if cores and len(cores) == len(fp.Shape.Faces):
                    fp.ViewObject.DiffuseColor = cores
                    _fosco(fp.ViewObject)
            except Exception:
                pass

    def onChanged(self, vp, prop):
        pass

    def getDefaultDisplayMode(self):
        return "Shaded"  # sólidos coloridos, sem as arestas pretas de cada peça

    def dumps(self):
        return None

    def loads(self, state):
        return None


def create_coluna_medicao(doc=None, nome="Colunas_medicao", **valores):
    """Cria as colunas de medição paramétricas no documento, com os valores dados (nomes das propriedades)."""
    doc = doc or App.activeDocument()
    obj = doc.addObject("Part::FeaturePython", nome)
    ColunaMedicao(obj)
    try:
        ViewProviderColunaMedicao(obj.ViewObject)
        obj.ViewObject.DisplayMode = "Shaded"
    except Exception:
        pass
    for chave, valor in valores.items():
        setattr(obj, chave, valor)
    obj.Label = "Colunas de medição"
    doc.recompute()
    return obj
