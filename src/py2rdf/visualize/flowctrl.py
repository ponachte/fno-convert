from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QHeaderView, QTreeWidgetItem, QVBoxLayout, QLineEdit, QPushButton, QGridLayout
from PyQt6.QtGui import QIntValidator, QDoubleValidator
from rdflib import URIRef
from pyqtgraph import TreeWidget

from ..execute.flow import Flow
from ..execute.store import Terminal
from ..graph import PipelineGraph
from .flowview import FlowViewWidget

class FlowCtrlWidget(QWidget):

    def __init__(self) -> None:
        QWidget.__init__(self)

        self.grid = QGridLayout(self)

        self.inputWidget = InputWidget()
        self.grid.addWidget(self.inputWidget, 0, 0)
        self.viewWidget = FlowViewWidget(self)
        self.grid.addWidget(self.viewWidget, 0, 1)

        self.grid.setColumnStretch(0, 1)  # InputWidget takes 1/4 of the space
        self.grid.setColumnStretch(1, 3)  # FlowViewWidget takes 3/4 of the space

        # Make the widgets fill available space
        self.inputWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.viewWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def setFlow(self, g: PipelineGraph, uri: URIRef):
        self.flow = Flow(g, uri)
        self.viewWidget.setFlow(self.flow)
        self.inputWidget.setFlow(self.flow)

class InputWidget(QWidget):

    def __init__(self) -> None:
        QWidget.__init__(self)
        self.items = {}
        
        self.inputList = TreeWidget()
        self.inputList.headerItem().setText(0, 'Name')
        self.inputList.headerItem().setText(1, 'Type')
        self.inputList.headerItem().setText(2, 'Input')
        self.inputList.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        execute = QPushButton('Execute', self)
        execute.clicked.connect(self.execute)

        layout = QVBoxLayout()
        layout.addWidget(self.inputList)
        layout.addWidget(execute)
        self.setLayout(layout)
    
    def setFlow(self, flow: Flow):
        self.flow = flow
        inputs = { inp for inp in flow.input.outputs() }
        for inp in inputs:
            inp_type = getattr(inp.type, '__name__', str(inp.type))
            item = QTreeWidgetItem([inp.name, inp_type, ''])
            self.inputList.addTopLevelItem(item)
            convertItem = ConvertWidget(inp)
            self.inputList.setItemWidget(item, 2, convertItem)
            self.items[inp] = convertItem
    
    def execute(self):
        for inp, item in self.items.items():
            inp.setValue(item.getInput())
        self.flow.execute()


class ConvertWidget(QWidget):

    def __init__(self, inp: Terminal) -> None:
        super().__init__()
        self.inp = inp

        layout = QVBoxLayout(self)

        if self.inp.type in [str, int, float]:
            self.input_field = QLineEdit(self)
            if self.inp.type == int:
                self.input_field.setValidator(QIntValidator())
            elif self.inp.type == float:
                self.input_field.setValidator(QDoubleValidator())
            
            layout.addWidget(self.input_field)
        
        self.setLayout(layout)
    
    def getInput(self):
        if self.inp.type == int:
            return int(self.input_field.text())
        elif self.inp.type == float:
            return float(self.input_field.text())
        return self.input_field.text()