import pandas as pd 

METODOS = pd.DataFrame({
    "metodo": ["A1", "A2", "B1", "B2", "C", "D", "E", "F", "G"], 
    "Descrição": [
        "Condutores isolados em eletrodutos de seção circular embuitdo em parede termicamente isolante", 
        "Cabo multipolar em eletroduto de seção circular embutido em parede termicamente isolante", 
        "Condutores isolados em eletroduto de seção circular sobre a parede de madeira ", 
        "Cabo multipolar em eletroduto de seção circular sobre parede de madeira ", 
        "Cabos unipolares ou cabo multipolar sobre parede de madeira", 
        "Cabo multipolar em eletroduto enterrado no solo", 
        "Cabo multipolar ao ar livre", 
        "Cabos unipolares (na horizontal, vertical ou em trifólio) ao ar livre", 
        "Cabos unipolares espaçados ao ar livre "
    ] })