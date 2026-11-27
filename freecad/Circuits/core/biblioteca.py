"""Biblioteca de componentes: nomes, categorias, busca e os exemplos paramétricos, sem FreeCAD.

Os arquivos .FCStd de ``Componentes/`` ganham um nome legível
(``Tomada_Alta_1modulo_110v`` → "Tomada alta 1 módulo 110 V") e uma categoria
pelas palavras do nome. Os **exemplos** são equipamentos desenhados pela própria
bancada, sem arquivo: cada um é uma lista de primitivas em mm, com a origem no
ponto de inserção, no piso (Z = 0) ou na altura de montagem (``altura_mm``):

    ("caixa", (x, y, z) do canto, (dx, dy, dz))
    ("cilindro", (x, y, z) do centro da base, raio, altura, eixo (x, y, z))

Medidas típicas de catálogo, para representar o equipamento na planta e no 3D.
"""
import re

EXEMPLO = "exemplo:"  # prefixo do caminho de um exemplo na biblioteca

CATEGORIAS = ["Tomadas", "Interruptores", "Iluminação", "Quadros e proteção", "Caixas", "Equipamentos", "Outros"]
# palavras no nome do arquivo -> categoria (a primeira que aparecer)
_PALAVRAS = [
    (("interruptor",), "Interruptores"),
    (("tomada",), "Tomadas"),
    (("lampada", "lâmpada", "iluminacao", "iluminação", "luminaria", "luminária", "spot", "bocal", "plafon"),
     "Iluminação"),
    (("disjuntor", "quadro", "distribuicao", "distribuição", "dr", "dps"), "Quadros e proteção"),
    (("caixa",), "Caixas"),
    (("motor", "bomba", "gerador", "chuveiro", "ar_condicionado", "ar-condicionado", "split", "transformador"),
     "Equipamentos"),
]
_TROCAS = [
    (r"(\d+)\s*modulos?", r"\1 módulo"), (r"(\d+)\s*botoes", r"\1 botões"), (r"(\d+)\s*v\b", r"\1 V"),
    (r"\biluminacao\b", "iluminação"), (r"\bdistribuicao\b", "distribuição"), (r"\blampada\b", "lâmpada"),
    (r"\bbifasio\b", "bifásico"), (r"\bmonofasio\b", "monofásico"), (r"\btrifasio\b", "trifásico"),
    (r"\bconj\b", "conjunto"), (r"\bpassagem\b", "passagem"),
]


def nome_amigavel(arquivo):
    """'Tomada_Alta_1modulo_110v_com_simbologia.FCStd' → 'Tomada alta 1 módulo 110 V com simbologia'."""
    texto = re.sub(r"\.fcstd$", "", str(arquivo), flags=re.IGNORECASE)
    texto = texto.replace("_", " ").replace("-", " ")
    texto = re.sub(r"\s+", " ", texto).strip().lower()
    for padrao, troca in _TROCAS:
        texto = re.sub(padrao, troca, texto)
    return texto[:1].upper() + texto[1:]


def categoria(nome):
    """Categoria pelo nome do arquivo ou do exemplo; 'Outros' se nenhuma palavra bater."""
    texto = str(nome).lower()
    palavras = set(re.split(r"[^a-zà-ú0-9]+", texto))
    for chaves, nome_categoria in _PALAVRAS:
        if any((c in palavras) if len(c) <= 3 else (c in texto) for c in chaves):
            return nome_categoria
    return "Outros"


def filtrar(itens, texto="", categoria_escolhida=None, origem=None, recentes=None):
    """Itens ({'nome', 'categoria', ...}) filtrados por texto, categoria, origem e recentes."""
    palavras = [p for p in str(texto).lower().split() if p]
    recentes_lista = list(recentes or [])
    recentes_pos = {c: idx for idx, c in enumerate(recentes_lista)}
    resultado = []
    for item in itens:
        if categoria_escolhida and item["categoria"] != categoria_escolhida:
            continue
        if origem == "exemplos" and not item.get("exemplo"):
            continue
        if origem == "arquivos" and item.get("exemplo"):
            continue
        if origem == "recentes" and item.get("caminho") not in recentes_pos:
            continue
        nome = f"{item['nome']} {item.get('descricao', '')}".lower()
        if all(p in nome for p in palavras):
            resultado.append(item)
    if origem == "recentes":
        resultado.sort(key=lambda it: recentes_pos.get(it.get("caminho"), len(recentes_pos)))
    return resultado


# --- exemplos paramétricos -------------------------------------------------------

def _caixa(largura, profundidade, altura, z=0.0, cx=0.0, cy=0.0):
    """Caixa centrada em (cx, cy) em planta, com a base em z."""
    return ("caixa", (cx - largura / 2.0, cy - profundidade / 2.0, z), (largura, profundidade, altura))


def _cilindro(raio, altura, z=0.0, cx=0.0, cy=0.0, eixo=(0.0, 0.0, 1.0)):
    return ("cilindro", (cx, cy, z), raio, altura, eixo)


EXEMPLOS = {
    "quadro_embutir_24": {
        "nome": "Quadro de distribuição de embutir 24 módulos", "categoria": "Quadros e proteção",
        "descricao": "Caixa de embutir para 24 disjuntores DIN, 360 × 90 × 420 mm.", "altura_mm": 1500.0,
        "cor": (0.85, 0.85, 0.85), "primitivas": [_caixa(360, 90, 420), _caixa(330, 10, 390, z=15, cy=-50)],
    },
    "quadro_sobrepor_48": {
        "nome": "Quadro de sobrepor 48 módulos", "categoria": "Quadros e proteção",
        "descricao": "Quadro metálico de sobrepor, 500 × 160 × 700 mm.", "altura_mm": 1300.0,
        "cor": (0.75, 0.78, 0.8), "primitivas": [_caixa(500, 160, 700), _caixa(470, 15, 670, z=15, cy=-87)],
    },
    "caixa_4x2": {
        "nome": "Caixa 4×2 de embutir", "categoria": "Caixas",
        "descricao": "Caixa de luz 4×2 (101 × 50 × 50 mm) para tomada ou interruptor.", "altura_mm": 300.0,
        "cor": (1.0, 0.75, 0.2), "primitivas": [_caixa(50, 50, 101)],
    },
    "caixa_4x4": {
        "nome": "Caixa 4×4 de embutir", "categoria": "Caixas",
        "descricao": "Caixa 4×4 (101 × 101 × 50 mm).", "altura_mm": 300.0,
        "cor": (1.0, 0.75, 0.2), "primitivas": [_caixa(50, 101, 101)],
    },
    "caixa_octogonal": {
        "nome": "Caixa octogonal de laje 4×4", "categoria": "Caixas",
        "descricao": "Caixa de teto para ponto de luz, 101 mm e 50 mm de altura.", "altura_mm": 2750.0,
        "cor": (1.0, 0.75, 0.2), "primitivas": [_cilindro(50.5, 50)],
    },
    "plafon_led": {
        "nome": "Luminária plafon LED redonda", "categoria": "Iluminação",
        "descricao": "Plafon de sobrepor Ø300 mm, 24 W.", "altura_mm": 2750.0, "potencia_va": 24.0,
        "cor": (0.97, 0.97, 0.92), "primitivas": [_cilindro(150, 40, z=-40)],
    },
    "luminaria_tubular": {
        "nome": "Luminária tubular LED 2 × 18 W", "categoria": "Iluminação",
        "descricao": "Calha de sobrepor 1240 × 150 × 60 mm.", "altura_mm": 2750.0, "potencia_va": 36.0,
        "cor": (0.95, 0.95, 0.95), "primitivas": [_caixa(1240, 150, 60, z=-60)],
    },
    "arandela": {
        "nome": "Arandela de parede", "categoria": "Iluminação",
        "descricao": "Arandela 250 × 100 × 150 mm.", "altura_mm": 2000.0, "potencia_va": 15.0,
        "cor": (0.9, 0.85, 0.7), "primitivas": [_caixa(250, 100, 150, cy=50)],
    },
    "ar_split_12000": {
        "nome": "Ar-condicionado split 12.000 BTU (evaporadora)", "categoria": "Equipamentos",
        "descricao": "Evaporadora de parede 800 × 200 × 280 mm, cerca de 1.100 W.", "altura_mm": 2100.0,
        "potencia_va": 1250.0, "cor": (0.96, 0.96, 0.96), "primitivas": [_caixa(800, 200, 280, cy=100)],
    },
    "chuveiro": {
        "nome": "Chuveiro elétrico 5.500 W", "categoria": "Equipamentos",
        "descricao": "Chuveiro Ø160 mm com cano de 300 mm a 2,20 m do piso.", "altura_mm": 2200.0,
        "potencia_va": 5500.0, "cor": (0.95, 0.95, 0.98),
        "primitivas": [_cilindro(12, 300, eixo=(0.0, 1.0, 0.0)), _cilindro(80, 60, z=-60, cy=300)],
    },
    "motor_3cv": {
        "nome": "Motor de indução trifásico 3 cv", "categoria": "Equipamentos",
        "descricao": "Carcaça 90L: Ø180 × 300 mm sobre base de 220 × 250 mm, cerca de 2,6 kVA.",
        "altura_mm": 0.0, "potencia_va": 2600.0, "cor": (0.2, 0.35, 0.6),
        "primitivas": [_caixa(220, 250, 20), _cilindro(90, 300, z=110, cx=-150, eixo=(1.0, 0.0, 0.0)),
                       _cilindro(14, 60, z=110, cx=150, eixo=(1.0, 0.0, 0.0)), _caixa(110, 110, 80, z=200)],
    },
    "bomba_recalque": {
        "nome": "Conjunto motobomba de recalque 1 cv", "categoria": "Equipamentos",
        "descricao": "Motobomba centrífuga 400 × 200 × 250 mm, cerca de 1 kVA.", "altura_mm": 0.0,
        "potencia_va": 1000.0, "cor": (0.1, 0.45, 0.25),
        "primitivas": [_caixa(400, 200, 20), _cilindro(80, 220, z=100, cx=-160, eixo=(1.0, 0.0, 0.0)),
                       _cilindro(100, 60, z=100, cx=60, eixo=(1.0, 0.0, 0.0))],
    },
    "gerador_diesel": {
        "nome": "Grupo gerador diesel carenado 180 kVA", "categoria": "Equipamentos",
        "descricao": "Gerador com carenagem 3200 × 1100 × 1800 mm sobre base.", "altura_mm": 0.0,
        "cor": (0.85, 0.65, 0.1),
        "primitivas": [_caixa(3200, 1100, 150), _caixa(3100, 1050, 1650, z=150),
                       _cilindro(60, 300, z=1800, cx=1200)],
    },
    "transformador": {
        "nome": "Transformador a seco 225 kVA", "categoria": "Equipamentos",
        "descricao": "Transformador 1400 × 800 × 1600 mm com três bobinas.", "altura_mm": 0.0,
        "cor": (0.55, 0.55, 0.6),
        "primitivas": [_caixa(1400, 800, 200)]
        + [_cilindro(180, 1100, z=250, cx=x) for x in (-450, 0, 450)] + [_caixa(1400, 300, 150, z=1400)],
    },
}


def caminho_do_exemplo(chave):
    return f"{EXEMPLO}{chave}"


def chave_do_exemplo(caminho):
    """Chave do exemplo pelo caminho ``exemplo:<chave>``, ou None se é um arquivo."""
    texto = str(caminho)
    return texto[len(EXEMPLO):] if texto.startswith(EXEMPLO) and texto[len(EXEMPLO):] in EXEMPLOS else None


def itens_dos_exemplos():
    """Itens da biblioteca para os exemplos, no formato de ``filtrar``."""
    return [{"nome": dados["nome"], "categoria": dados["categoria"], "descricao": dados["descricao"],
             "caminho": caminho_do_exemplo(chave), "exemplo": True} for chave, dados in EXEMPLOS.items()]


def item_do_arquivo(caminho, nome_arquivo):
    """Item da biblioteca para um arquivo .FCStd."""
    return {"nome": nome_amigavel(nome_arquivo), "categoria": categoria(nome_arquivo), "descricao": nome_arquivo,
            "caminho": caminho, "exemplo": False}


def dimensoes_do_exemplo(chave):
    """Dimensões aproximadas (largura, profundidade, altura) [mm] das primitivas do exemplo."""
    dados = EXEMPLOS.get(chave)
    if not dados or not dados.get("primitivas"):
        return (0.0, 0.0, 0.0)
    xs, ys, zs = [], [], []
    for primitiva in dados["primitivas"]:
        if primitiva[0] == "caixa":
            (x, y, z), (dx, dy, dz) = primitiva[1], primitiva[2]
            xs.extend((x, x + dx))
            ys.extend((y, y + dy))
            zs.extend((z, z + dz))
        elif primitiva[0] == "cilindro":
            (cx, cy, cz), raio, comp, eixo = primitiva[1], primitiva[2], primitiva[3], primitiva[4]
            ex, ey, ez = (abs(v) for v in eixo)
            if ex >= ey and ex >= ez:
                sinal = 1.0 if eixo[0] >= 0 else -1.0
                xs.extend((cx, cx + sinal * comp))
                ys.extend((cy - raio, cy + raio))
                zs.extend((cz - raio, cz + raio))
            elif ey >= ex and ey >= ez:
                sinal = 1.0 if eixo[1] >= 0 else -1.0
                xs.extend((cx - raio, cx + raio))
                ys.extend((cy, cy + sinal * comp))
                zs.extend((cz - raio, cz + raio))
            else:
                sinal = 1.0 if eixo[2] >= 0 else -1.0
                xs.extend((cx - raio, cx + raio))
                ys.extend((cy - raio, cy + raio))
                zs.extend((cz, cz + sinal * comp))
    if not xs:
        return (0.0, 0.0, 0.0)
    return (round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1), round(max(zs) - min(zs), 1))
