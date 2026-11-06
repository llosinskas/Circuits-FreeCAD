"""Leitura de condutores de arquivos do QElectroTech (.qet), sem FreeCAD."""

CABECALHO = ["Wire ID", "From Ref", "From Pin", "To Ref", "To Pin", "Area", "Color", "Wire Length", "Unique Code", "Cable"]

_SETAS = ("Going arrow", "Coming arrow")


def _origem_destino(conductor, numero):
    """Referência do elemento: prefere o elemento vinculado, se houver."""
    vinculado = conductor.get(f"element{numero}_linked", "")
    return vinculado or conductor.get(f"element{numero}_label", "")


def extrair_linhas(root):
    """Converte a árvore XML de um .qet nas linhas da planilha de fios.

    Condutores ligados diretamente viram uma linha cada. Condutores que passam
    por setas ("Going arrow"/"Coming arrow") são unidos pelo número do fio e só
    entram na planilha quando as duas pontas foram encontradas.

    Returns:
        Lista de listas: [fio, origem, pino, destino, pino, seção, cor].
    """
    conexoes = {}
    diretos = []

    for conductor in root.findall(".//conductor"):
        fio = conductor.get("num", "")
        elemento1 = conductor.get("element1_name", "")
        elemento2 = conductor.get("element2_name", "")
        cor = conductor.get("conductor_color", "")
        secao = conductor.get("conductor_section", "")

        if fio not in conexoes:
            conexoes[fio] = {"color": cor, "section": secao, "from_ref": None, "from_pin": None, "to_ref": None, "to_pin": None}
        conexao = conexoes[fio]

        if elemento1 == "Going arrow":
            conexao["from_ref"] = conductor.get("element2_label", "")
            conexao["from_pin"] = conductor.get("terminalname2", "")
        elif elemento2 == "Going arrow":
            conexao["from_ref"] = conductor.get("element1_label", "")
            conexao["from_pin"] = conductor.get("terminalname1", "")
        if elemento1 == "Coming arrow":
            conexao["to_ref"] = conductor.get("element2_label", "")
            conexao["to_pin"] = conductor.get("terminalname2", "")
        elif elemento2 == "Coming arrow":
            conexao["to_ref"] = conductor.get("element1_label", "")
            conexao["to_pin"] = conductor.get("terminalname1", "")

        if elemento1 not in _SETAS and elemento2 not in _SETAS:
            diretos.append([
                fio,
                _origem_destino(conductor, 1),
                conductor.get("terminalname1", ""),
                _origem_destino(conductor, 2),
                conductor.get("terminalname2", ""),
                secao,
                cor,
            ])

    unidos = [
        [fio, c["from_ref"], c["from_pin"], c["to_ref"], c["to_pin"], c["section"], c["color"]]
        for fio, c in conexoes.items()
        if c["from_ref"] and c["to_ref"]
    ]
    return diretos + unidos
