"""Teste de regressão com o FreeCAD real (sem janela).

Executa os comandos da bancada num documento novo e grava um retrato JSON de
tudo o que foi criado. Dois retratos (antes/depois de uma mudança) podem ser
comparados com ``diff`` para provar que o comportamento não mudou.

Uso (Git Bash, a partir da raiz do repositório)::

    QT_QPA_PLATFORM=offscreen CIRCUITS_SMOKE_OUT=/tmp/retrato.json \
      "/c/Program Files/FreeCAD 1.1/bin/freecad.exe" \
      --user-cfg /tmp/u.cfg --system-cfg /tmp/s.cfg tests/gui/smoke_gui.py

Encerra o FreeCAD ao terminar. Não salva nada na bancada nem na biblioteca.
"""
import importlib
import json
import os
import re
import tempfile
import traceback

import FreeCAD as App
import FreeCADGui as Gui

try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets

OUT = os.environ.get("CIRCUITS_SMOKE_OUT") or os.path.join(tempfile.gettempdir(), "circuits_smoke.json")
WORKBENCH = "CircuitsWorkbench"
result = {"errors": [], "steps": {}}

QET_SAMPLE = """<project><diagram>
<conductor num="W1" element1_name="Bobina" element2_name="Rele" element1_label="K1" element2_label="K2"
  terminalname1="A1" terminalname2="A2" conductor_color="azul" conductor_section="1.5"/>
<conductor num="W2" element1_name="Bobina" element2_name="Rele" element1_label="K3" element1_linked="K9"
  element2_label="K4" element2_linked="" terminalname1="13" terminalname2="14" conductor_color="preto" conductor_section="2.5"/>
<conductor num="W3" element1_name="Going arrow" element2_name="Rele" element2_label="K5" terminalname2="11"
  conductor_color="vermelho" conductor_section="4"/>
<conductor num="W3" element1_name="Rele" element2_name="Coming arrow" element1_label="K6" terminalname1="12"
  conductor_color="vermelho" conductor_section="4"/>
</diagram></project>"""

DADOS_QUADRO = {
    "indentificacao": "QD01", "bitola_entrada": "16", "origem": "QGBT", "curto_circuito": "5",
    "descricao": "Quadro teste", "tensao": "220", "n_fases": "3", "terra": True, "neutro": True,
    "curva_disjuntor": "C", "corrente_nominal_disjuntor": "40", "corrente_cc_disjuntor": "6",
    "pot_quadro": "10", "demanda": "8", "material": "Aco", "dps": True, "classe_DPS": "II",
    "tensao_DPS": "275", "corrente_DPS": "20",
}
DADOS_CIRCUITO = {
    "N_circuito": "1", "Destino": "Tomadas", "Potencia": "1500", "Tensao": "220", "Corrente": "8.5",
    "Cabo": "2.5", "Disjuntor": "16", "Curva": "C", "Fase_R": "True", "Fase_S": "False",
    "Fase_T": "False", "Neutro": "True", "Terra": "True", "DR": "True", "Corrente_DR": "30mA",
}
IGNORED_PROPS = {
    "Shape", "Label", "Label2", "Proxy", "ExpressionEngine", "Visibility", "Geometry", "Constraints",
    "ExternalGeo", "cells", "column_widths", "row_heights", "AddSubShape", "SuppressedShape",
    "Support", "AttachmentSupport",
}


def locate(*candidates):
    """Devolve o primeiro atributo encontrado entre 'modulo:atributo'."""
    for candidate in candidates:
        module_name, attr = candidate.split(":")
        try:
            return getattr(importlib.import_module(module_name), attr)
        except (ImportError, AttributeError):
            continue
    raise LookupError(candidates)


def clean(value):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, (int, str, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if hasattr(value, "UserString"):
        return value.UserString
    return re.sub(r" at (0x)?[0-9A-Fa-f]{8,}", "", str(value))  # endereços de memória mudam a cada execução


def snapshot(doc):
    data = []
    for obj in sorted(doc.Objects, key=lambda o: o.Name):
        item = {"name": obj.Name, "label": obj.Label, "type": obj.TypeId}
        props = {}
        for prop in obj.PropertiesList:
            if prop in IGNORED_PROPS:
                continue
            try:
                props[prop] = clean(getattr(obj, prop))
            except Exception as exc:  # propriedade ilegível também é informação
                props[prop] = "<erro %s>" % type(exc).__name__
        item["props"] = props
        proxy = getattr(obj, "Proxy", None)
        if proxy is not None:
            item["proxy"] = "%s.%s" % (type(proxy).__module__, type(proxy).__name__)
        if hasattr(obj, "Group"):
            item["group"] = [o.Name for o in obj.Group]
        if hasattr(obj, "Geometry"):
            item["geometry"] = [str(g) for g in obj.Geometry]
        shape = getattr(obj, "Shape", None)
        if shape is not None and not shape.isNull():
            item["shape"] = {
                "type": shape.ShapeType, "edges": len(shape.Edges), "length": round(shape.Length, 3),
                "volume": round(shape.Volume, 3), "bbox": str(shape.BoundBox),
            }
        view = getattr(obj, "ViewObject", None)
        if view is not None and hasattr(view, "ShapeColor"):
            item["color"] = clean(tuple(round(c, 4) for c in view.ShapeColor))
        if obj.TypeId == "Spreadsheet::Sheet":
            item["cells"] = {c: clean(obj.getContents(c)) for c in sorted(obj.getUsedCells())}
        data.append(item)
    return data


def run(name):
    """Executa um comando registrado no FreeCAD."""
    Gui.runCommand(name, 0)
    Gui.updateGui()


def stop_insertion_mode():
    mode_cls = locate("freecad.Circuits.UI.dialogs.ComponentInserter:ComponentInsertionMode")
    active = mode_cls._active_instance
    if active is not None:
        active.stop()


def scenario(doc):
    App.ParamGet("User parameter:BaseApp/Preferences/Document").SetBool("DuplicateLabels", True)

    # Diálogos substituídos: o teste não pode ficar parado esperando clique.
    criar = locate("freecad.Circuits.UI.dialogs.quadro_dialogs:CriarQuadro",
                   "freecad.Circuits.commands.gerar_unifilar:CriarQuadro")
    criar.exec_ = lambda self: 1
    criar.get_dados = lambda self: dict(DADOS_QUADRO)
    add = locate("freecad.Circuits.UI.dialogs.quadro_dialogs:Add_circuito",
                 "freecad.Circuits.commands.gerar_unifilar:Add_circuito")
    add.exec_ = lambda self: 1
    add.get_dados = lambda self: dict(DADOS_CIRCUITO)

    qet_path = os.path.join(tempfile.gettempdir(), "circuits_smoke_sample.qet")
    with open(qet_path, "w", encoding="utf-8") as handle:
        handle.write(QET_SAMPLE)
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (qet_path, ""))

    for name in ("newProjetctEletrical", "NewQuadro", "newSpreadsheet", "ComponentEletric"):
        run(name)
    for name in ("InsertTugs", "InsertSwitch", "InsertLighting", "InsertOutlet"):
        run(name)
        stop_insertion_mode()
    doc.recompute()
    result["steps"]["inseridos"] = snapshot(doc)

    run("Cabo")
    run("Gerar3D")
    run("Generate3DSwitches")
    result["steps"]["3d_caixas"] = snapshot(doc)

    run("GerarPlanilha")
    run("AddCircuito")
    run("GerarUnifilar")
    result["steps"]["unifilar"] = snapshot(doc)
    run("GerarUnifilar")  # segunda execução: precisa substituir, não duplicar
    result["steps"]["unifilar_repetido"] = [o["name"] for o in snapshot(doc)]

    import Draft
    wire = Draft.make_wire([App.Vector(0, 0, 0), App.Vector(1000, 0, 0), App.Vector(1000, 1000, 0)])
    doc.recompute()
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(wire)
    run("Generate3DConduits")
    Gui.Selection.clearSelection()
    result["steps"]["eletrodutos"] = [o for o in snapshot(doc) if o["name"].startswith("Wire")]

    run("ImportQET")
    result["steps"]["qet"] = [o for o in snapshot(doc) if "circuits_smoke_sample" in o["name"]]

    pdf_cls = locate("freecad.Circuits.services.pdf_generator:PDFGenerator",
                     "freecad.Circuits.core.pdf_generator:PDFGenerator")
    pdf_path = os.path.join(tempfile.gettempdir(), "circuits_smoke.pdf")
    generator = pdf_cls(doc, pdf_path, {"materiais": True, "calculos": True, "projeto": "T", "autor": "A"})
    result["steps"]["pdf_materiais"] = clean(generator._get_materiais_table())
    result["steps"]["pdf_calculos"] = clean(generator._get_calculos_table())
    generator.generate()
    result["steps"]["pdf_gerado"] = os.path.getsize(pdf_path) > 0

    run("Add_Node")  # sem seleção: não pode quebrar
    run("GetSpaces")


def attempt(name, action):
    """Executa uma verificação extra e registra 'ok' ou o traceback completo."""
    try:
        result["extras"][name] = action() or "ok"
    except Exception:
        result["extras"][name] = traceback.format_exc()


def scenario_extras(doc):
    """Caminhos que dependem de diálogo ou da biblioteca, chamados diretamente."""
    import shutil

    result["extras"] = {}
    package = "freecad.Circuits"
    module = lambda name: importlib.import_module(f"{package}.{name}")

    attempt("dialogo_quadro", lambda: module("UI.dialogs.quadro_dialogs").CriarQuadro().close() and None)
    attempt("dialogo_add_circuito", lambda: module("UI.dialogs.quadro_dialogs").Add_circuito().close() and None)
    attempt("dialogo_relatorio", lambda: sorted(module("UI.dialogs.report_dialog").ReportDialog().get_opcoes()))
    attempt("dialogo_circuito", lambda: module("UI.insert_circuit").InsertCircuit().close())
    attempt("seletor_componentes", lambda: module("UI.dialogs").ComponentSelectorDialog(
        module("services.biblioteca").ELECTRIC_LIBRARY_PATH).close())

    # A biblioteca é trocada por uma cópia temporária: nada é gravado em Componentes/.
    biblioteca = module("services.biblioteca")
    commands = module("commands.new_project")
    original = biblioteca.ELECTRIC_LIBRARY_PATH
    temp_library = tempfile.mkdtemp(prefix="circuits_smoke_")
    shutil.copy(os.path.join(original, "Lampada.FCStd"), temp_library)
    biblioteca.ELECTRIC_LIBRARY_PATH = commands.ELECTRIC_LIBRARY_PATH = temp_library
    QtWidgets.QInputDialog.getText = staticmethod(lambda *a, **k: ("ModeloTeste", True))
    QtWidgets.QInputDialog.getItem = staticmethod(lambda *a, **k: ("Lampada.FCStd", True))
    try:
        attempt("criar_modelo", lambda: commands.CreateModel().Activated())
        attempt("modelo_salvo", lambda: str(os.path.exists(os.path.join(temp_library, "ModeloTeste.FCStd"))))
        App.setActiveDocument(doc.Name)
        App.ActiveDocument = doc
        attempt("listar_elementos", lambda: commands.listElements().Activated())
    finally:
        biblioteca.ELECTRIC_LIBRARY_PATH = commands.ELECTRIC_LIBRARY_PATH = original
    App.closeDocument("ModeloTeste")
    App.setActiveDocument(doc.Name)
    App.ActiveDocument = doc

    insert = module("commands.insert_component")
    messages = []
    QtWidgets.QMessageBox.information = staticmethod(lambda *a, **k: messages.append(a[2]))
    attempt("avisos_em_breve", lambda: (insert.Wire().Activated(), insert.CableTray().Activated()) and None)
    result["extras"]["mensagens"] = messages

    attempt("reiniciar_bancada", lambda: module("commands.tools").ReiniciarBancada().Activated())
    result["extras"]["apos_reiniciar"] = {
        "ativa": type(Gui.activeWorkbench()).__name__,
        "modulo": type(Gui.activeWorkbench()).__module__,
        "comando": bool(Gui.Command.get("GerarUnifilar")),
        "barras": "Diagrama Unifilar" in Gui.activeWorkbench().listToolbars(),
    }
    before = len(doc.Objects)
    run("newSpreadsheet")
    result["extras"]["comando_apos_reiniciar"] = len(doc.Objects) == before + 1
    result["loaded_from_services"] = "freecad.Circuits.services.unifilar" in __import__("sys").modules


try:
    workbenches = Gui.listWorkbenches()
    result["workbench_menu"] = workbenches[WORKBENCH].MenuText
    Gui.activateWorkbench(WORKBENCH)
    Gui.updateGui()
    workbench = Gui.activeWorkbench()
    own_toolbars = ["Snap", "Desenho", "Modificador", "BIM", "Anotações", "Inserir Componentes", "Novo Projeto",
                    "Componentes", "Relatórios", "Ferramentas", "Diagrama Unifilar", "QEletrotech", "Quadro Elétrico"]
    items = workbench.getToolbarItems()
    result["toolbars"] = {t: items.get(t) for t in own_toolbars}
    commands = {}
    for names in result["toolbars"].values():
        for name in names or []:
            command = Gui.Command.get(name)
            if command is None:
                commands[name] = None
                continue
            info = command.getInfo()
            commands[name] = {"menu": info.get("menuText"), "tooltip": info.get("toolTip"),
                              "icon": os.path.basename(info.get("pixmap") or "")}
    result["commands"] = dict(sorted(commands.items()))
    document = App.newDocument("Smoke")
    scenario(document)
    scenario_extras(document)
except Exception:
    result["errors"].append(traceback.format_exc())

with open(OUT, "w", encoding="utf-8") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=1, sort_keys=True)
os._exit(0)
