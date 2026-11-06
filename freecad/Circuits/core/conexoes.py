# Author: Lucas Losinskas 
# data: 04/2024
# Classe para definir os tipos de dados de conexão: Elétrica, Eletroduto, Eletrocalha, Conduite, duto.
from enum import Enum 
class typeConection(Enum):
    eletrica    = 0
    eletroduto  = 1
    eletrocalha = 2
    conduite    = 3
    duto        = 4
