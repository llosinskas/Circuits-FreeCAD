import pandas as pd 

TEMPERATURA = [10, 15, 20, 25, 35, 40, 45, 50,55, 60, 65, 70, 75, 80]

FATOR_EPR_XLPE = pd.DataFrame({
    "temperatura": TEMPERATURA,
    "fator":[1.15, 1.12, 1.08, 1.04, 0.96, 0.96, 0.87,0.82,0.76, 0.71, 0.65, 0.58, 0.50, 0.41]
    })

FATOR_PVC = pd.DataFrame({
    "temperatura": TEMPERATURA,
    "fator":[1.22, 1.17, 1.12, 1.06, 0.94, 0.87, 0.79, 0.71, 0.61, 0.50, 0, 0, 0, 0]
})