"""Pavimentos e pastas dos símbolos: regras puras e organização do documento com o FreeCAD simulado."""
import importlib
import sys
import types
import unittest
from unittest import mock

from tests import ROOT  # noqa: F401  (configura o caminho do pacote)
from freecad.Circuits.core import pavimentos as regras
from freecad.Circuits.core import simbolos

MODULOS_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Sketcher", "Spreadsheet")
RECARREGAR = ("freecad.Circuits.services.pavimentos",)


class TestRegras(unittest.TestCase):
    def test_todo_simbolo_do_catalogo_tem_pasta(self):
        for chave in simbolos.CATALOGO:
            with self.subTest(chave):
                self.assertIn(regras.pasta_do_objeto("Ponto", chave), regras.PASTAS)

    def test_pasta_pelo_tipo_do_objeto(self):
        self.assertEqual(regras.pasta_do_objeto("Ponto", "tomada_alta"), "tomadas")
        self.assertEqual(regras.pasta_do_objeto("Ponto", "chuveiro"), "energia")
        self.assertEqual(regras.pasta_do_objeto("Ponto", "luz_teto"), "iluminacao")
        self.assertEqual(regras.pasta_do_objeto("Ponto", "medicao_agrupada"), "quadros")
        self.assertEqual(regras.pasta_do_objeto("Switch"), "interruptores")
        self.assertEqual(regras.pasta_do_objeto("Outlet"), "tomadas")
        self.assertEqual(regras.pasta_do_objeto("Lighting"), "iluminacao")
        self.assertEqual(regras.pasta_do_objeto("tomada"), "tomadas")
        self.assertIsNone(regras.pasta_do_objeto("ConduitPath"))
        self.assertIsNone(regras.pasta_do_objeto("Ponto", "nao_existe"))

    def test_nome_do_pavimento(self):
        self.assertEqual(regras.nome_do_pavimento("  2º   Pavimento "), "2º Pavimento")
        self.assertEqual(regras.nome_do_pavimento("   "), "Térreo")

    def test_sugestao_do_proximo_pavimento(self):
        self.assertEqual(regras.sugerir_novo([]), ("Térreo", 0.0, 3000.0))
        self.assertEqual(regras.sugerir_novo([("Térreo", 0.0, 3000.0)]), ("1º Pavimento", 3000.0, 3000.0))
        existentes = [("Térreo", 0.0, 3200.0), ("1º Pavimento", 3200.0, 2900.0)]
        self.assertEqual(regras.sugerir_novo(existentes), ("2º Pavimento", 6100.0, 2900.0))
        # nome que o usuário já usou não é repetido, e a cota segue o pavimento mais alto
        self.assertEqual(regras.sugerir_novo([("1º Pavimento", 3000.0, 3000.0), ("Cobertura", 6000.0, 2500.0)]),
                         ("2º Pavimento", 8500.0, 2500.0))


class Objeto:
    """Objeto do documento: aceita propriedades novas e sabe em que pasta está."""

    def __init__(self, nome, **propriedades):
        self.Name = self.Label = nome
        self.Group = []
        self._pai = None
        self.__dict__.update(propriedades)

    def addProperty(self, tipo, nome, grupo="", dica=""):
        setattr(self, nome, None)

    def addObject(self, obj):
        self.Group.append(obj)
        obj._pai = self

    def removeObject(self, obj):
        self.Group.remove(obj)
        obj._pai = None

    def getParentGroup(self):
        return self._pai


class Documento:
    def __init__(self):
        self.Objects = []
        self.transacoes = []

    def addObject(self, tipo, nome):
        obj = Objeto(f"{nome}{len(self.Objects):03d}")
        self.Objects.append(obj)
        return obj

    def getObject(self, nome):
        return next((obj for obj in self.Objects if obj.Name == nome), None)

    def openTransaction(self, nome):
        self.transacoes.append(("abre", nome))

    def commitTransaction(self):
        self.transacoes.append(("fecha",))

    def abortTransaction(self):
        self.transacoes.append(("desfaz",))

    def recompute(self):
        pass


def ponto(nome, simbolo):
    obj = Objeto(nome, Simbolo=simbolo)
    obj.Proxy = types.SimpleNamespace(Type="Ponto")
    return obj


def interruptor(nome):
    obj = Objeto(nome)
    obj.Proxy = types.SimpleNamespace(Type="Switch")
    return obj


class TestServico(unittest.TestCase):
    def setUp(self):
        falsos = {nome: mock.MagicMock(name=nome) for nome in MODULOS_FREECAD}
        self.patch = mock.patch.dict(sys.modules, falsos)
        self.patch.start()
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.servico = importlib.import_module("freecad.Circuits.services.pavimentos")
        self.doc = Documento()

    def tearDown(self):
        for nome in RECARREGAR:
            sys.modules.pop(nome, None)
        self.patch.stop()

    def adicionar(self, obj):
        self.doc.Objects.append(obj)
        return obj

    def pastas(self, pav):
        return {filho.pasta: [obj.Name for obj in filho.Group] for filho in pav.Group}

    def test_sem_pavimento_cria_o_terreo_ativo(self):
        pav = self.servico.garantir_ativo(self.doc)
        self.assertEqual((pav.Label, pav.Elevacao, pav.AlturaPavimento, pav.Ativo), ("Térreo", 0.0, 3000.0, True))
        self.assertIs(self.servico.garantir_ativo(self.doc), pav)  # não cria outro
        self.assertEqual(len(self.servico.listar(self.doc)), 1)

    def test_pavimento_novo_entra_no_grupo_dos_pontos_eletricos(self):
        mae = Objeto("Pontos_eletricos")
        self.adicionar(mae)
        pav = self.servico.definir(self.doc, "Térreo")
        self.assertEqual(mae.Group, [pav])

    def test_definir_atualiza_o_existente_e_troca_o_ativo(self):
        terreo = self.servico.definir(self.doc, "Térreo", 0, 3000)
        primeiro = self.servico.definir(self.doc, "1º Pavimento", 3000, 2800)
        self.assertEqual((terreo.Ativo, primeiro.Ativo), (False, True))
        self.servico.definir(self.doc, "Térreo", 100, 3100)
        self.assertEqual((terreo.Elevacao, terreo.AlturaPavimento, terreo.Ativo, primeiro.Ativo), (100.0, 3100.0, True, False))
        self.assertEqual(len(self.servico.listar(self.doc)), 2)
        self.assertEqual(self.doc.transacoes.count(("fecha",)), 3)

    def test_resumo_e_sugestao_acompanham_os_pavimentos(self):
        self.servico.definir(self.doc, "Térreo", 0, 3000)
        self.servico.definir(self.doc, "1º Pavimento", 3000, 2800)
        self.assertEqual([(r["nome"], r["elevacao_mm"], r["ativo"]) for r in self.servico.resumo(self.doc)],
                         [("Térreo", 0.0, False), ("1º Pavimento", 3000.0, True)])
        self.assertEqual(self.servico.sugestao_novo(self.doc), ("2º Pavimento", 5800.0, 2800.0))

    def test_simbolos_vao_para_a_pasta_do_tipo_no_pavimento_ativo(self):
        tomada, luz, chave = ponto("T1", "tomada_baixa"), ponto("L1", "luz_teto"), interruptor("S1")
        for obj in (tomada, luz, chave):
            self.adicionar(obj)
            self.servico.arquivar(self.doc, obj)
        pav = self.servico.ativo(self.doc)
        self.assertEqual(self.pastas(pav), {"tomadas": ["T1"], "iluminacao": ["L1"], "interruptores": ["S1"]})
        self.assertEqual([obj.Pavimento for obj in (tomada, luz, chave)], ["Térreo"] * 3)

    def test_segundo_simbolo_do_mesmo_tipo_usa_a_mesma_pasta(self):
        a, b = self.adicionar(ponto("T1", "tomada_baixa")), self.adicionar(ponto("T2", "tomada_alta"))
        self.servico.arquivar(self.doc, a)
        self.servico.arquivar(self.doc, b)
        self.assertEqual(self.pastas(self.servico.ativo(self.doc)), {"tomadas": ["T1", "T2"]})

    def test_arquivar_de_novo_nao_duplica(self):
        a = self.adicionar(ponto("T1", "tomada_baixa"))
        self.servico.arquivar(self.doc, a)
        self.servico.arquivar(self.doc, a)
        self.assertEqual(self.pastas(self.servico.ativo(self.doc)), {"tomadas": ["T1"]})

    def test_objeto_que_nao_e_simbolo_nao_e_arquivado(self):
        outro = self.adicionar(Objeto("Linha"))
        self.assertIsNone(self.servico.arquivar(self.doc, outro))
        self.assertEqual(self.servico.listar(self.doc), [])  # nem criou o Térreo à toa

    def test_trocar_o_pavimento_ativo_muda_o_destino(self):
        a = self.adicionar(ponto("T1", "tomada_baixa"))
        self.servico.arquivar(self.doc, a)
        primeiro = self.servico.definir(self.doc, "1º Pavimento", 3000, 3000)
        b = self.adicionar(ponto("T2", "tomada_baixa"))
        self.servico.arquivar(self.doc, b)
        self.assertEqual(self.pastas(primeiro), {"tomadas": ["T2"]})
        self.assertEqual((a.Pavimento, b.Pavimento), ("Térreo", "1º Pavimento"))

    def test_mover_tira_da_pasta_antiga(self):
        a, luz = self.adicionar(ponto("T1", "tomada_baixa")), self.adicionar(ponto("L1", "luz_teto"))
        terreo = self.servico.definir(self.doc, "Térreo")
        for obj in (a, luz):
            self.servico.arquivar(self.doc, obj)
        primeiro = self.servico.definir(self.doc, "1º Pavimento", 3000, 3000)
        linha = self.adicionar(Objeto("Linha"))
        self.assertEqual(self.servico.mover(self.doc, [a, luz, linha], primeiro), 2)  # a linha é ignorada
        self.assertEqual(self.pastas(primeiro), {"tomadas": ["T1"], "iluminacao": ["L1"]})
        self.assertEqual(self.pastas(terreo), {"tomadas": [], "iluminacao": []})
        self.assertEqual((a.Pavimento, luz.Pavimento), ("1º Pavimento", "1º Pavimento"))

    def test_elevacao_vem_da_pasta_e_nao_do_nome_guardado(self):
        self.servico.definir(self.doc, "Térreo", 0, 3000)
        primeiro = self.servico.definir(self.doc, "1º Pavimento", 3000, 3000)
        a = self.adicionar(ponto("T1", "tomada_baixa"))
        self.servico.arquivar(self.doc, a)
        self.assertEqual(self.servico.elevacao_do_objeto(self.doc, a), 3000.0)
        self.assertIs(self.servico.pavimento_do_objeto(self.doc, a), primeiro)
        a.Pavimento = "Térreo"  # nome guardado desatualizado: vale a pasta
        self.assertEqual(self.servico.elevacao_do_objeto(self.doc, a), 3000.0)

    def test_elevacao_cai_no_nome_guardado_e_depois_em_zero(self):
        self.servico.definir(self.doc, "Térreo", 0, 3000)
        self.servico.definir(self.doc, "1º Pavimento", 3000, 3000)
        solto = self.adicionar(ponto("T9", "tomada_baixa"))
        self.assertEqual(self.servico.elevacao_do_objeto(self.doc, solto), 0.0)
        solto.Pavimento = "1º Pavimento"
        self.assertEqual(self.servico.elevacao_do_objeto(self.doc, solto), 3000.0)

    def test_rotulo_repetido_cai_no_nome_com_o_pavimento(self):
        class GrupoUnico(Objeto):
            """Imita o FreeCAD sem DuplicateLabels: recusa um Label que já existe."""
            usados = {"Tomadas"}

            def __setattr__(self, nome, valor):
                if nome == "Label" and valor in self.usados:
                    valor = valor + "001"
                super().__setattr__(nome, valor)

        class DocUnico(Documento):
            def addObject(self, tipo, nome):
                obj = GrupoUnico(f"{nome}{len(self.Objects):03d}") if nome.startswith("Pasta") else super().addObject(tipo, nome)
                if nome.startswith("Pasta"):
                    self.Objects.append(obj)
                return obj

        doc = DocUnico()
        a = ponto("T1", "tomada_baixa")
        doc.Objects.append(a)
        self.servico.arquivar(doc, a)
        pasta = self.servico.ativo(doc).Group[0]
        self.assertEqual(pasta.Label, "Térreo - Tomadas")


if __name__ == "__main__":
    unittest.main(verbosity=2)
