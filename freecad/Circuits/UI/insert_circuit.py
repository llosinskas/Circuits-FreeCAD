from freecad.Circuits.qt import QtCore, QtWidgets


global userCancelled, userOK
userCancelled = "Cancelled"
userOK = "OK"

class InsertCircuit(QtWidgets.QDialog):
        
    def __init__(self):
        super(InsertCircuit, self).__init__()
        self.initUI()
        

    def LabelCreate(self, labels):
        colum = 10
        self.labels_array =[]
        label_controle= ""
        for label in labels:
            label_controle = QtWidgets.QLabel(label, self)
            self.labels_array.append(label_controle)
            label_controle.move(10,colum)
            colum+=30
    def initUI(self):
        self.setGeometry(100, 100, 800, 800)
        self.setWindowTitle("Inserir o circuito")
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setMouseTracking(True)
        
        # Criar Label

        labels = [ 
            "Origem", 
            "Destino", 
            "Potencia [kW]", 
            "Tensão [kV]", 
            "Fator de potencia", 
            "Potencia aparente [kVA]", 
            "Corrente [A]", 
            "Comprimento [m]",
            "Método de instalacao", 
            "% de queda de tensao", 
            "Seccao do cabo [mm²]", 
            "Fator de agrupamento", 
            "Fator de temperatura", 
            "Disjuntor [A]", 
            "Curva do disjuntor", 
            "Fase R", 
            "Fase S", 
            "Fase T", 
            "Neutro", 
            "Terra"
        ]
        self.LabelCreate(labels)
        

        # Botão de visibilidade
        pushButton1 = QtWidgets.QPushButton("Toggle visibility", self)
        pushButton1.clicked.connect(self.onPushButton1)
        pushButton1.setMinimumWidth(150)
        pushButton1.move(210, 20)
		
        cancelButton = QtWidgets.QPushButton('Cancel', self)
        cancelButton.clicked.connect(self.onCancel)
        cancelButton.setAutoDefault(True)
		
        cancelButton.move(150, 110)
        okButton = QtWidgets.QPushButton('OK', self)
		
        okButton.clicked.connect(self.onOk)
		
        okButton.move(260, 110)
        self.show()
    
    def onPushButton1(self):
		
        if self.label1.isVisible():
            self.label1.hide()
        else:
            self.label1.show()
    def onCancel(self):
        self.result = userCancelled
        self.close()
    
    def onOk(self):
        self.result= userOK
        self.close()
    def mouseMoveEvent(self,event):
        self.label2.setText("X: "+str(event.x()) + " Y: "+str(event.y()))