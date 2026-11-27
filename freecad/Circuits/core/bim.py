"""Classe IFC e propriedades BIM dos objetos da bancada, para a exportação IFC do FreeCAD.

O exportador da bancada BIM (``importers/exportIFC.py``) lê de cada objeto:

- ``IfcType`` (texto como ``Outlet`` ou ``Light Fixture``): vira ``IfcOutlet``, ``IfcLightFixture``...;
- as propriedades do grupo ``IFC Attributes`` (``PredefinedType``, ``ObjectType``, ``Tag``), copiadas
  para os atributos da entidade;
- ``IfcProperties`` (mapa ``"nome;;pset" -> "tipo;;valor"``), gravado em ``IfcPropertySet``.

Aqui ficam só as regras: ``classe(tipo, dados)`` devolve a classe IFC, o tipo predefinido e a lista
de propriedades ``(pset, nome, tipo IFC, valor)`` nos conjuntos padrão do IFC4
(``Pset_OutletTypeCommon``, ``Pset_ElectricalDeviceCommon``, ``Pset_LightFixtureTypeCommon``,
``Pset_SwitchingDeviceTypeCommon``, ``Pset_JunctionBoxTypeCommon``,
``Pset_CableCarrierSegmentTypeConduitSegment``, ``Pset_CableCarrierSegmentTypeCableTraySegment``,
``Pset_CableSegmentTypeBusBarSegment``, ``Pset_ElectricGeneratorTypeCommon``) e no conjunto próprio
``PSET_CIRCUITS`` (circuito, quadro, comando, pavimento, altura de montagem...). ``mapa_ifc`` monta o
valor de ``IfcProperties``.

Comprimentos chegam em mm e saem na unidade do arquivo IFC (``fator_comprimento``: 0,001 para metro,
o padrão do exportador); potência em W, tensão em V, corrente em A.
"""

PSET_CIRCUITS = "Circuits_Eletrica"
FREQUENCIA_HZ = 60.0
FATOR_METRO = 0.001

# Classe IFC (como no IfcType do FreeCAD) e tipo predefinido de cada símbolo do catálogo.
CLASSE_DO_SIMBOLO = {
    "tomada_baixa": ("Outlet", "POWEROUTLET"),
    "tomada_media": ("Outlet", "POWEROUTLET"),
    "tomada_alta": ("Outlet", "POWEROUTLET"),
    "tomada_piso": ("Outlet", "POWEROUTLET"),
    "chuveiro": ("Outlet", "POWEROUTLET"),
    "ar_condicionado": ("Outlet", "POWEROUTLET"),
    "ventilador": ("Outlet", "POWEROUTLET"),
    "ponto_forca": ("Outlet", "POWEROUTLET"),
    "luz_teto": ("Light Fixture", "POINTSOURCE"),
    "arandela": ("Light Fixture", "POINTSOURCE"),
    "fluorescente": ("Light Fixture", "DIRECTIONSOURCE"),
    "embutida": ("Light Fixture", "POINTSOURCE"),
    "emergencia": ("Light Fixture", "SECURITYLIGHTING"),
    "quadro_distribuicao": ("Electric Distribution Board", "DISTRIBUTIONBOARD"),
    "quadro_comando": ("Electric Distribution Board", "USERDEFINED"),
    "quadro_medicao": ("Electric Distribution Board", "USERDEFINED"),
    "medicao_agrupada": ("Electric Distribution Board", "USERDEFINED"),
    "gerador": ("Electric Generator", "ENGINEGENERATOR"),
    "qta": ("Electric Distribution Board", "SWITCHBOARD"),
    "campainha": ("Alarm", "BELL"),
    "botao_campainha": ("Switching Device", "MOMENTARYSWITCH"),
    "fotocelula": ("Sensor", "LIGHTSENSOR"),
    "caixa_passagem": ("Junction Box", "POWER"),
    "haste_aterramento": ("Discrete Accessory", "USERDEFINED"),
    "caixa_inspecao": ("Junction Box", "USERDEFINED"),
    "bep": ("Discrete Accessory", "USERDEFINED"),
}
CLASSE_PADRAO = ("Building Element Proxy", "USERDEFINED")

PONTOS_DE_LIGACAO = {"F+N": 2, "F+F": 2, "3F": 3}  # polos de cada ligação (fase e neutro = 2)
TIPO_DA_BANDEJA = {"leito": "CABLELADDERSEGMENT"}  # o resto é eletrocalha


def _numero(valor, padrao=None):
    try:
        return float(str(valor).replace(",", ".").strip().split()[0].rstrip("VvAaWw"))
    except (ValueError, IndexError, AttributeError):
        return padrao


def tensao_em_volts(texto):
    """``'220V'`` -> 220.0; ``None`` se não for número."""
    return _numero(texto)


def _comum(dados, fator):
    """Propriedades do conjunto próprio da bancada, só as que têm valor."""
    p = PSET_CIRCUITS
    props = [
        (p, "Descricao", "IfcLabel", dados.get("descricao")),
        (p, "Simbolo", "IfcIdentifier", dados.get("simbolo")),
        (p, "Circuito", "IfcIdentifier", dados.get("circuito")),
        (p, "Quadro", "IfcIdentifier", dados.get("quadro")),
        (p, "Comando", "IfcIdentifier", dados.get("comando")),
        (p, "Pavimento", "IfcLabel", dados.get("pavimento")),
        (p, "Ligacao", "IfcLabel", dados.get("ligacao")),
        (p, "Ambiente", "IfcLabel", dados.get("ambiente")),
    ]
    if dados.get("altura_mm") is not None:
        props.append((p, "AlturaMontagem", "IfcLengthMeasure", float(dados["altura_mm"]) * fator))
    if dados.get("potencia_va"):
        props.append((p, "PotenciaAparente_VA", "IfcReal", float(dados["potencia_va"])))
    return props


def _eletrica(dados, polos=None):
    """``Pset_ElectricalDeviceCommon``: tensão, potência ativa, fator de potência, polos e terra."""
    p = "Pset_ElectricalDeviceCommon"
    props = []
    tensao = tensao_em_volts(dados.get("tensao"))
    if tensao:
        props.append((p, "RatedVoltage", "IfcElectricVoltageMeasure", tensao))
        props.append((p, "NominalFrequencyRange", "IfcFrequencyMeasure", FREQUENCIA_HZ))
    if dados.get("corrente_a"):
        props.append((p, "RatedCurrent", "IfcElectricCurrentMeasure", float(dados["corrente_a"])))
    potencia, fp = dados.get("potencia_va"), dados.get("fator_potencia")
    if potencia:
        ativa = float(potencia) * (float(fp) if fp else 1.0)
        props.append((p, "Power", "IfcPowerMeasure", round(ativa, 3)))
        props.append((p, "NominalPowerConsumption", "IfcPowerMeasure", round(ativa, 3)))
    if fp:
        props.append((p, "PowerFactor", "IfcNormalisedRatioMeasure", float(fp)))
    polos = polos or PONTOS_DE_LIGACAO.get(dados.get("ligacao"))
    if polos:
        props.append((p, "NumberOfPoles", "IfcCountMeasure", int(polos)))
    props.append((p, "HasProtectiveEarth", "IfcBoolean", True))
    return props


def _resultado(ifc_type, predefinido, tipo_objeto, tag, propriedades):
    return {"IfcType": ifc_type, "PredefinedType": predefinido, "ObjectType": tipo_objeto or "",
            "Tag": tag or "", "propriedades": [x for x in propriedades if x[3] not in (None, "")]}


def tag_do_circuito(dados):
    """``QD1-C3``, ``C3`` ou a sigla do quadro."""
    circuito = str(dados.get("circuito") or "").strip()
    quadro = str(dados.get("quadro") or "").strip()
    if not circuito:
        return quadro
    rotulo = circuito if circuito.upper().startswith("C") else f"C{circuito}"
    return f"{quadro}-{rotulo}" if quadro else rotulo


def do_ponto(dados, fator=FATOR_METRO):
    """Ponto elétrico (``Ponto``, tomada em Sketch, ``Outlet``, ``Lighting``) ou a caixa 3D dele.

    ``dados``: simbolo, legenda, categoria, descricao, potencia_va, fator_potencia, tensao, ligacao,
    circuito, quadro, comando, pavimento, altura_mm, caixa_mm (largura, profundidade, altura) e,
    nos quadros, medidores.
    """
    simbolo = dados.get("simbolo") or ""
    ifc_type, predefinido = CLASSE_DO_SIMBOLO.get(simbolo, CLASSE_PADRAO)
    legenda = dados.get("legenda") or dados.get("descricao") or simbolo
    props = _comum(dados, fator)
    referencia = legenda
    if ifc_type == "Outlet":
        p = "Pset_OutletTypeCommon"
        props += [(p, "Reference", "IfcIdentifier", referencia), (p, "IsPluggableOutlet", "IfcLogical",
                                                                   simbolo.startswith("tomada")),
                  (p, "NumberOfSockets", "IfcCountMeasure", 1)]
        props += _eletrica(dados)
    elif ifc_type == "Light Fixture":
        p = "Pset_LightFixtureTypeCommon"
        props += [(p, "Reference", "IfcIdentifier", referencia), (p, "NumberOfSources", "IfcCountMeasure", 1)]
        if dados.get("potencia_va"):
            ativa = float(dados["potencia_va"]) * float(dados.get("fator_potencia") or 1.0)
            props.append((p, "TotalWattage", "IfcPowerMeasure", round(ativa, 3)))
        props += _eletrica(dados)
    elif ifc_type == "Switching Device":
        p = "Pset_SwitchingDeviceTypeCommon"
        props += [(p, "Reference", "IfcIdentifier", referencia), (p, "NumberOfGangs", "IfcCountMeasure", 1),
                  (p, "Legend", "IfcLabel", dados.get("comando"))]
    elif ifc_type == "Junction Box":
        p = "Pset_JunctionBoxTypeCommon"
        props += [(p, "Reference", "IfcIdentifier", referencia), (p, "NumberOfGangs", "IfcCountMeasure", 1)]
        caixa = dados.get("caixa_mm")
        if caixa:
            largura, profundidade, altura = caixa
            props += [(p, "NominalWidth", "IfcNonNegativeLengthMeasure", largura * fator),
                      (p, "NominalLength", "IfcNonNegativeLengthMeasure", altura * fator),
                      (p, "NominalHeight", "IfcNonNegativeLengthMeasure", profundidade * fator),
                      (p, "ClearDepth", "IfcPositiveLengthMeasure", profundidade * fator)]
    elif ifc_type == "Electric Distribution Board":
        p = "Pset_ElectricDistributionBoardTypeCommon"
        props += [(p, "Reference", "IfcIdentifier", dados.get("descricao") or referencia)]
        props += _eletrica(dados, polos=PONTOS_DE_LIGACAO.get(dados.get("ligacao")))
        if dados.get("medidores"):
            props.append((PSET_CIRCUITS, "Medidores", "IfcCountMeasure", int(dados["medidores"])))
    elif ifc_type == "Electric Generator":
        props += [("Pset_ElectricGeneratorTypeCommon", "Reference", "IfcIdentifier", dados.get("descricao"))]
    elif ifc_type == "Sensor":
        props += [("Pset_SensorTypeCommon", "Reference", "IfcIdentifier", referencia)]
    elif ifc_type == "Alarm":
        props += [("Pset_AlarmTypeCommon", "Reference", "IfcIdentifier", referencia)]
        props += _eletrica(dados)
    tag = dados.get("descricao") if ifc_type in ("Electric Distribution Board", "Electric Generator") \
        else tag_do_circuito(dados)
    return _resultado(ifc_type, predefinido, legenda, tag, props)


def do_interruptor(dados, fator=FATOR_METRO):
    """Interruptor (``Switch``): tipo Simples, Paralelo ou Intermediário."""
    tipo = dados.get("tipo") or "Simples"
    nomes = {"Simples": "Interruptor simples", "Paralelo": "Interruptor paralelo",
             "Intermediário": "Interruptor intermediário"}
    legenda = nomes.get(tipo, f"Interruptor {tipo.lower()}")
    funcao = {"Simples": "ONOFFSWITCH", "Paralelo": "TWOWAYSWITCH", "Intermediário": "INTERMEDIATESWITCH"}
    dados = dict(dados, simbolo=dados.get("simbolo") or "interruptor", descricao=dados.get("descricao") or legenda)
    props = _comum(dados, fator)
    p = "Pset_SwitchingDeviceTypeCommon"
    props += [(p, "Reference", "IfcIdentifier", legenda), (p, "NumberOfGangs", "IfcCountMeasure", 1),
              (p, "Legend", "IfcLabel", dados.get("comando")),
              ("Pset_SwitchingDeviceTypeToggleSwitch", "SwitchFunction", "IfcLabel", funcao.get(tipo, "OTHER"))]
    return _resultado("Switching Device", "TOGGLESWITCH", legenda, tag_do_circuito(dados), props)


def do_eletroduto(dados, fator=FATOR_METRO):
    """Eletroduto (linha marcada, ``ConduitPath`` ou o tubo 3D dele).

    ``dados``: diametro (nominal, texto como ``3/4"``), diametro_mm (externo, se conhecido), tipo
    (Rígido/Flexível), material, instalacao, altura_mm, comprimento_mm, pavimento.
    """
    nominal = str(dados.get("diametro") or "").strip()
    rigido = str(dados.get("tipo") or "").lower().startswith("r")
    material = dados.get("material") or "PVC"
    legenda = f"Eletroduto {'rígido' if rigido else 'flexível'} {material} {nominal}".strip()
    props = _comum(dict(dados, descricao=dados.get("descricao") or legenda), fator)
    p = "Pset_CableCarrierSegmentTypeConduitSegment"
    props += [("Pset_CableCarrierSegmentTypeCommon", "Reference", "IfcIdentifier", nominal and f"Ø{nominal}"),
              (p, "IsRigid", "IfcBoolean", rigido)]
    if dados.get("diametro_mm"):
        props.append((p, "NominalDiameter", "IfcPositiveLengthMeasure", float(dados["diametro_mm"]) * fator))
    props += [(PSET_CIRCUITS, "DiametroNominal", "IfcLabel", nominal), (PSET_CIRCUITS, "Material", "IfcLabel", material),
              (PSET_CIRCUITS, "Instalacao", "IfcLabel", dados.get("instalacao"))]
    if dados.get("comprimento_mm"):
        props.append((PSET_CIRCUITS, "Comprimento", "IfcLengthMeasure", float(dados["comprimento_mm"]) * fator))
    return _resultado("Cable Carrier Segment", "CONDUITSEGMENT", legenda, nominal and f"Ø{nominal}", props)


def da_bandeja(dados, fator=FATOR_METRO):
    """Eletrocalha ou leito: tipo_bandeja, largura_mm, aba_mm, altura_mm (do piso à base), tampa."""
    tipo = str(dados.get("tipo_bandeja") or "eletrocalha_perfurada")
    predefinido = TIPO_DA_BANDEJA.get(tipo, "CABLETRAYSEGMENT")
    legenda = tipo.replace("_", " ").capitalize()
    largura, aba = dados.get("largura_mm"), dados.get("aba_mm")
    if largura and aba:
        legenda += f" {float(largura):g} x {float(aba):g} mm"
    props = _comum(dict(dados, descricao=dados.get("descricao") or legenda), fator)
    p = "Pset_CableCarrierSegmentTypeCableTraySegment"
    if predefinido == "CABLELADDERSEGMENT":
        p = "Pset_CableCarrierSegmentTypeCableLadderSegment"
    props += [("Pset_CableCarrierSegmentTypeCommon", "Reference", "IfcIdentifier", legenda)]
    if largura:
        props.append((p, "NominalWidth", "IfcPositiveLengthMeasure", float(largura) * fator))
    if aba:
        props.append((p, "NominalHeight", "IfcPositiveLengthMeasure", float(aba) * fator))
    if predefinido == "CABLETRAYSEGMENT":
        props.append((p, "HasCover", "IfcBoolean", bool(dados.get("tampa"))))
    return _resultado("Cable Carrier Segment", predefinido, legenda, "", props)


def da_conexao(dados, fator=FATOR_METRO):
    """Peças de ligação: conexões das eletrocalhas, curvas das descidas e saídas de eletroduto.

    ``dados['peca']``: ``conexoes`` (curvas, tês e reduções de um pavimento), ``descida`` ou ``saida``.
    """
    peca = dados.get("peca") or "conexoes"
    predefinido, legenda = {"descida": ("BEND", "Curva vertical de eletroduto"),
                            "saida": ("USERDEFINED", "Saída de eletroduto na eletrocalha"),
                            "conexoes": ("USERDEFINED", "Conexões de eletrocalha")}.get(peca, ("NOTDEFINED", peca))
    props = _comum(dict(dados, descricao=dados.get("descricao") or legenda), fator)
    props.append(("Pset_CableCarrierFittingTypeCommon", "Reference", "IfcIdentifier", dados.get("referencia") or legenda))
    return _resultado("Cable Carrier Fitting", predefinido, legenda, "", props)


def do_suporte(dados, fator=FATOR_METRO):
    """Suportes das eletrocalhas de um pavimento (``quantidade``)."""
    legenda = "Suportes de eletrocalha"
    props = _comum(dict(dados, descricao=legenda), fator)
    if dados.get("quantidade"):
        props.append((PSET_CIRCUITS, "Quantidade", "IfcCountMeasure", int(dados["quantidade"])))
    return _resultado("Discrete Accessory", "BRACKET", legenda, "", props)


def da_coluna_medicao(dados, fator=FATOR_METRO):
    """Colunas de medição (``ColunaMedicao``): medidores, modelo, disjuntor e corrente."""
    legenda = f"Centro de medição - {dados.get('modelo') or 'caixas P'}"
    props = _comum(dict(dados, descricao=dados.get("descricao") or legenda), fator)
    p = "Pset_ElectricDistributionBoardTypeCommon"
    props += [(p, "Reference", "IfcIdentifier", dados.get("solucao") or legenda)]
    props += _eletrica(dados, polos=dados.get("fases"))
    c = PSET_CIRCUITS
    props += [(c, "Medidores", "IfcCountMeasure", int(dados.get("medidores") or 0) or None),
              (c, "MedidoresPorColuna", "IfcCountMeasure", int(dados.get("por_coluna") or 0) or None),
              (c, "DisjuntorUnidade", "IfcLabel", dados.get("disjuntor_unidade")),
              (c, "Conjuntos", "IfcLabel", dados.get("conjuntos"))]
    return _resultado("Electric Distribution Board", "USERDEFINED", legenda, dados.get("descricao") or "CM", props)


def da_prumada(dados, fator=FATOR_METRO):
    """Prumadas verticais (``Prumada``) ou a prumada de eletroduto/eletrocalha entre pavimentos."""
    eletrocalha = dados.get("eletrocalha")
    legenda = dados.get("descricao") or "Prumadas verticais"
    props = _comum(dict(dados, descricao=legenda), fator)
    props.append(("Pset_CableCarrierSegmentTypeCommon", "Reference", "IfcIdentifier", legenda))
    if dados.get("sistemas"):
        props.append((PSET_CIRCUITS, "Sistemas", "IfcLabel", ", ".join(dados["sistemas"])))
    if dados.get("andares"):
        props.append((PSET_CIRCUITS, "Andares", "IfcCountMeasure", int(dados["andares"])))
    predefinido = "CABLETRAYSEGMENT" if eletrocalha else ("CONDUITSEGMENT" if dados.get("simples") else "USERDEFINED")
    return _resultado("Cable Carrier Segment", predefinido, legenda, "", props)


def do_busway(dados, fator=FATOR_METRO):
    """Busway (barramento blindado) da prumada de medição: corrente nominal."""
    corrente = dados.get("corrente_a")
    legenda = f"Busway {float(corrente):g} A" if corrente else "Busway"
    props = _comum(dict(dados, descricao=legenda), fator)
    p = "Pset_CableSegmentTypeBusBarSegment"
    if corrente:
        props += [(p, "NominalCurrent", "IfcElectricCurrentMeasure", float(corrente)),
                  (p, "IsHorizontalBusbar", "IfcBoolean", False)]
    props.append(("Pset_CableSegmentTypeCommon", "Reference", "IfcIdentifier", legenda))
    return _resultado("Cable Segment", "BUSBARSEGMENT", legenda, "", props)


def do_equipamento(dados, fator=FATOR_METRO):
    """Equipamento da biblioteca: descricao, potencia_va, altura_mm."""
    legenda = dados.get("descricao") or "Equipamento"
    props = _comum(dados, fator) + (_eletrica(dados) if dados.get("potencia_va") else [])
    return _resultado("Building Element Proxy", "USERDEFINED", legenda, "", props)


CLASSIFICADORES = {
    "ponto": do_ponto, "interruptor": do_interruptor, "eletroduto": do_eletroduto, "bandeja": da_bandeja,
    "conexao": da_conexao, "suporte": do_suporte, "coluna_medicao": da_coluna_medicao, "prumada": da_prumada,
    "busway": do_busway, "equipamento": do_equipamento,
}


def classe(tipo, dados, fator=FATOR_METRO):
    """Classe IFC de um objeto da bancada.

    Args:
        tipo: chave de ``CLASSIFICADORES``.
        dados: dicionário do tipo (veja cada função).
        fator: unidade do arquivo IFC por mm (0,001 = metro).

    Returns:
        {'IfcType', 'PredefinedType', 'ObjectType', 'Tag', 'propriedades': [(pset, nome, tipo IFC, valor)]}.
    """
    return CLASSIFICADORES[tipo](dict(dados), fator)


def _texto(tipo_ifc, valor):
    if isinstance(valor, bool):
        return "True" if valor else "False"
    if tipo_ifc in ("IfcInteger", "IfcCountMeasure") and float(valor) == int(float(valor)):
        return str(int(float(valor)))
    if isinstance(valor, float):
        return repr(round(valor, 6))
    return str(valor).replace(";;", ";")


def mapa_ifc(propriedades):
    """Valor de ``IfcProperties`` (formato do FreeCAD 0.19 em diante): ``{"nome;;pset": "tipo;;valor"}``."""
    return {f"{nome};;{pset}": f"{tipo_ifc};;{_texto(tipo_ifc, valor)}"
            for pset, nome, tipo_ifc, valor in propriedades if valor not in (None, "")}


def ler_mapa(mapa):
    """Caminho de volta de ``mapa_ifc``: [(pset, nome, tipo IFC, texto do valor)]."""
    lista = []
    for chave, valor in (mapa or {}).items():
        nome, _, pset = chave.partition(";;")
        tipo_ifc, _, texto = str(valor).partition(";;")
        lista.append((pset, nome, tipo_ifc, texto))
    return lista


def fator_da_unidade(unidade_ifc):
    """Preferência ``ifcUnit`` da bancada BIM (0 metro, 1 pé) -> unidade do arquivo por mm."""
    return 0.00328084 if int(unidade_ifc or 0) == 1 else FATOR_METRO
