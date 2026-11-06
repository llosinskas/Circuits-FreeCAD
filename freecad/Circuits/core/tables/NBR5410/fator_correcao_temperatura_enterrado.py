import pandas as pd 

TEMPERATURA = [10, 15, 20, 25, 35, 40, 45, 50,55, 60, 65, 70, 75, 80]

FATOR_PVC = pd.DataFrame({
    "temperatura": TEMPERATURA,
    "fator":[1.10, 1.05, 0.95, 0.89, 0.89, 0.84, 0.77, 0.71, 0.63, 0.55, 0.45, 0,0,0,0]
    })

FATOR_EPR_XLPE = pd.DataFrame({
    "temperatura": TEMPERATURA,
    "fator":[1.07, 1.04, 0.96, 0.93, 0.89, 0.85, 0.80, 0.76, 0.71, 0.65, 0.60, 0.53, 0.46, 0.38]
})

FATOR_DIFERENTE_25KmW = pd.DataFrame({
    'resistividade':[1,1.5, 2, 3],  
    "fator":[1.18,1.1, 1.05, 0.96]})