import pandas as pd 

FATOR_AGRUPAMENTO = pd.DataFrame({
    # Númerio dee circuitos ou de cabos multipolares agrupados
    "agrupamento": [1, 2, 3, 4, 5,6,7, 8, 9,12, 16, 20], 
    # Em feixe ao ar livre ou sobre superfície; embutidos em condutos fechados: Métodos A a F
    "1":[1, 0.80, 0.70, 0.65, 0.6, 0.57, 0.54, 0.52, 0.50, 0.45, 0.41, 0.38], 
    # Camada única sobre a parede, piso, ou em bandeja não perfurada ou prateleira: Método C
    "2":[1, 0.85, 0.79, 0.75, 0.73, 0.72, 0.72, 0.71, 0.70, 0.70,0.70,0.70], 
    # Camada única no teto: Método C
    "3":[0.95, 0.81, 0.72, 0.68, 0.66, 0.64, 0.63, 0.62, 0.61, 0.61, 0.61, 0.61], 
    # Camada única em bandeja perfurada: Método E e F
    "4":[1, 0.88, 0.82, 0.77, 0.75, 0.73, 0.73, 0.72, 0.72, 0.72, 0.72, 0.72],
    # Camada única em leito suporte etc.: Método E e F
    "5":[1, 0.87, 0.82, 0.80, 0.80, 0.79, 0.79, 0.78, 0.78, 0.78, 0.78, 0.78],
})