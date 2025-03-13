from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QHeaderView, QTreeWidgetItem, QVBoxLayout, QLineEdit, QPushButton, QGridLayout
from PyQt6.QtGui import QIntValidator, QDoubleValidator
from rdflib import URIRef
from pyqtgraph import TreeWidget

from ..executors import Function
from ..executors.store import Terminal
from ..graph import ExecutableGraph
from .flowview import ExeViewWidget

class ExeCtrlWidget(QWidget):

    def __init__(self) -> None:
        QWidget.__init__(self)

        self.grid = QGridLayout(self)

        self.inputWidget = InputWidget()
        self.grid.addWidget(self.inputWidget, 0, 0)
        self.viewWidget = ExeViewWidget(self)
        self.grid.addWidget(self.viewWidget, 0, 1, 2, 1)
        self.functionList = FunctionList(self.viewWidget)
        self.grid.addWidget(self.functionList, 1, 0)

        self.grid.setRowStretch(0, 1)
        self.grid.setRowStretch(1, 2)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 3)

        # Make the widgets fill available space
        self.inputWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.viewWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def setExe(self, g: ExecutableGraph, uri: URIRef):
        self.exe = Function(g, uri)
        self.viewWidget.setExe(self.exe)
        self.inputWidget.setExe(self.exe)
        self.functionList.setExe(self.exe)

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
    
    def setExe(self, exe: Function):
        self.inputList.clear()
        self.exe = exe
        inputs = exe.inputs()
        for inp in inputs:
            inp_type = getattr(inp.type, '__name__', str(inp.type))
            item = QTreeWidgetItem([inp.name, inp_type, ''])
            self.inputList.addTopLevelItem(item)
            convertItem = ConvertWidget(inp)
            self.inputList.setItemWidget(item, 2, convertItem)
            self.items[inp] = convertItem
    
    # TODO Use correct executor
    def execute(self):
        for inp, item in self.items.items():
            inp.set(item.getInput())
        self.exe.execute()


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

class FunctionList(QWidget):

    def __init__(self, view) -> None:
        super().__init__()
        self.view = view

        self.list = TreeWidget(self)
        self.list.setColumnCount(2)
        self.list.setHeaderLabels(["Functions", ""])
        self.list.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.list.setUniformRowHeights(True)

        layout = QVBoxLayout()
        layout.addWidget(self.list)
        self.setLayout(layout)
    
    def setExe(self, exe: Function):
        self.list.clear()
        self.exe = exe
        
        self.add_function_item(exe)

    def add_function_item(self, fun: Function, parent=None):
        item = QTreeWidgetItem([fun.name, ""])
        
        if parent:
            parent.addChild(item)
        else:
            self.list.addTopLevelItem(item)

        if fun.comp_uri:
            fun.setInternal(False)
            expandButton = QPushButton('Expand')
            expandButton.setFixedWidth(50)
            expandButton.fun = fun
            expandButton.item = item
            expandButton.clicked.connect(self.toggleChildren)
            self.list.setItemWidget(item, 1, expandButton)
    
    def toggleChildren(self):
        btn = QObject.sender(self)
        
        if btn.text() == "Expand":
            btn.fun.setInternal(True)
            for call in btn.fun.comp.functions.values():
                self.add_function_item(call, btn.item)
            btn.item.setExpanded(True)
            btn.setText("Hide")
        else:
            btn.fun.setInternal(False)
            btn.item.takeChildren()
            btn.setText("Expand")
        
        self.view.draw()