"""Garante as regras de camadas descritas no AGENTS.md, lendo só o código-fonte."""
import ast
import os
import unittest

from tests import PACKAGE_ROOT

PACKAGE = os.path.join(PACKAGE_ROOT, "Circuits")
FREECAD_MODULES = {"FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet", "Arch"}
QT_MODULES = {"PySide", "PySide2", "PySide6"}
OWN_PREFIX = "freecad.Circuits."


def python_files(*layer):
    base = os.path.join(PACKAGE, *layer)
    if base.endswith(".py"):
        return [base]
    return [
        os.path.join(folder, name)
        for folder, _, names in os.walk(base)
        for name in names
        if name.endswith(".py")
    ]


def imports_of(path):
    """Nomes completos importados por um arquivo, com imports relativos resolvidos."""
    with open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), path)
    relative = os.path.relpath(path, PACKAGE_ROOT).replace(os.sep, ".")[: -len(".py")]
    package_parts = ["freecad", *relative.split(".")[:-1]]
    if relative.endswith("__init__"):
        package_parts = ["freecad", *relative.split(".")[:-1]]
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parent = package_parts[: len(package_parts) - node.level + 1]
                module = ".".join(parent + ([node.module] if node.module else []))
            else:
                module = node.module or ""
            found.add(module)
            found.update(f"{module}.{alias.name}" for alias in node.names)
    return found


def violations(files, forbidden_roots=(), forbidden_prefixes=()):
    problems = []
    for path in files:
        for name in imports_of(path):
            root = name.split(".")[0]
            if root in forbidden_roots or any(name.startswith(prefix) for prefix in forbidden_prefixes):
                problems.append(f"{os.path.relpath(path, PACKAGE)} importa {name}")
    return sorted(set(problems))


class TestLayers(unittest.TestCase):
    def test_core_is_pure_python(self):
        layers = [OWN_PREFIX + name for name in ("services", "commands", "objects", "UI", "qt", "init_gui")]
        self.assertEqual(violations(python_files("core"), FREECAD_MODULES | QT_MODULES, layers), [])

    def test_package_metadata_loads_without_freecad(self):
        self.assertEqual(violations(python_files("__init__.py"), FREECAD_MODULES | QT_MODULES), [])

    def test_services_have_no_dialogs(self):
        layers = [OWN_PREFIX + name for name in ("commands", "UI", "qt", "init_gui")]
        self.assertEqual(violations(python_files("services"), QT_MODULES, layers), [])

    def test_objects_have_no_dialogs(self):
        layers = [OWN_PREFIX + name for name in ("commands", "UI", "qt", "init_gui")]
        self.assertEqual(violations(python_files("objects"), QT_MODULES, layers), [])

    def test_ui_does_not_import_commands(self):
        self.assertEqual(violations(python_files("UI"), (), [OWN_PREFIX + "commands"]), [])

    def test_qt_is_imported_only_through_qt_module(self):
        others = [path for path in python_files() if os.path.basename(path) != "qt.py"]
        self.assertEqual(violations(others, QT_MODULES), [])

    def test_no_imports_outside_the_namespace(self):
        """Nomes genéricos colidem com outras bancadas no sys.path do FreeCAD."""
        generic = {"WorkbenchBase", "InitGui", "UI", "core", "commands", "utils", "Tools"}
        self.assertEqual(violations(python_files(), generic), [])


class TestCommands(unittest.TestCase):
    def test_commands_are_registered_only_in_commands_package(self):
        problems = []
        commands_dir = os.path.join(PACKAGE, "commands")
        for path in python_files():
            with open(path, encoding="utf-8") as handle:
                if "addCommand(" in handle.read() and not path.startswith(commands_dir):
                    problems.append(os.path.relpath(path, PACKAGE))
        self.assertEqual(problems, [])


class TestPersistedPaths(unittest.TestCase):
    """Estes caminhos ficam gravados nos .FCStd dos usuários: não podem mudar."""

    def test_feature_python_modules_stay_in_place(self):
        for module, classes in {
            "switch": ("Switch", "ViewProviderSwitch"),
            "lighting": ("Lighting", "ViewProviderLighting"),
            "outlet": ("Outlet", "ViewProviderOutlet"),
            "conduit_path": ("ConduitPath", "ViewProviderConduitPath"),
        }.items():
            path = os.path.join(PACKAGE, "objects", module + ".py")
            with open(path, encoding="utf-8") as handle:
                defined = {n.name for n in ast.walk(ast.parse(handle.read())) if isinstance(n, ast.ClassDef)}
            self.assertTrue(set(classes) <= defined, module)

    def test_library_folder_stays_in_place(self):
        self.assertTrue(os.path.isdir(os.path.join(PACKAGE, "Componentes", "Eletrica")))


if __name__ == "__main__":
    unittest.main()
