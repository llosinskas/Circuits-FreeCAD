import pandas as pd 

TEMPERATURA = [10, 15, 20, 25, 35, 40, 45, 50,55, 60, 65, 70, 75, 80]

FATOR_EPR_XLPE = pd.DataFrame({
    "temperatura": TEMPERATURA,
    "fator":[1.06, 1.03, 0.97, 0.94, 0.91, 0.87, 0.84, 0.80, 0.76, 0.72, 0.68, 0.64, 0.59, 0.54]
    })

FATOR_PVC = pd.DataFrame({
    "temperatura": TEMPERATURA,
    "fator":[1.07, 1.04, 0.96, 0.93, 0.89, 0.85, 0.80, 0.76, 0.71, 0.65, 0.60, 0.53, 0.46, 0.38]
})