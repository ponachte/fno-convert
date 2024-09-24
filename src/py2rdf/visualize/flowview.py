from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QSizePolicy

from pyqtgraph import GraphicsView, ViewBox
from pyqtgraph.dockarea import DockArea, Dock
from rdflib import URIRef

from ..execute.flow_executer import Flow
from ..graph import PipelineGraph
from .function import FunctionGraphicsItem

class FlowGraphicsView(GraphicsView):

    def __init__(self, widget, *args):
        GraphicsView.__init__(self, *args, useOpenGL=False)

        # lockAspect ensures aspect ratio between X and Y axis is consistent during zooming
        self._viewbox = FlowViewBox(widget, lockAspect=True, invertY=True)
        self.setCentralItem(self._viewbox)
        # Enables smooth lines or edges
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    
    def viewBox(self):
        return self._viewbox

class FlowViewBox(ViewBox):

    def __init__(self, widget, *args, **kwargs):
        ViewBox.__init__(self, *args, **kwargs)
        self.widget = widget

        # Set the background of the viewbox
        self.setBackgroundColor('white')

class FlowCtrlWidget(QWidget):

    def __init__(self) -> None:
        QWidget.__init__(self)

        self.vlayout = QVBoxLayout(self)
        self.viewWidget = FlowViewWidget(self)
        self.vlayout.addWidget(self.viewWidget)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def setFlow(self, g: PipelineGraph, uri: URIRef):
        self.flow = Flow(g, uri)
        self.viewWidget.setFlow(self.flow)

class FlowViewWidget(DockArea):

    def __init__(self, ctrl):
        DockArea.__init__(self)

        self.ctrl = ctrl
        self.hoverItem = None
        self.nextZVal = 10

        # The graphics view
        self.view = FlowGraphicsView(ctrl)
        self.viewDock = Dock('view', size=(1000, 900))
        self.viewDock.addWidget(self.view)
        self.viewDock.hideTitleBar()
        self.addDock(self.viewDock)

        self.hoverText = QTextEdit()
        self.hoverText.setReadOnly(True)
        self.hoverDock = Dock('Hover Info', size=(1000, 5))
        self.hoverDock.addWidget(self.hoverText)
        self.addDock(self.hoverDock, 'bottom')

        # TODO add scrollable info
        self.selectText = QTextEdit()
        self.selectText.setReadOnly(True)
        self.selectDock = Dock('Selected Node', size=(1000, 500))
        self.selectDock.addWidget(self.selectText)
        self.addDock(self.selectDock, 'bottom')

        self._scene = self.view.scene()
        self._viewBox = self.view.viewBox()

        self._scene.selectionChanged.connect(self.selectionChanged)
        self._scene.sigMouseHover.connect(self.hoverOver)
    
    def scene(self):
        return self._scene
    
    def viewBox(self):
        return self._viewBox
    
    def setFlow(self, flow: Flow):
        self.flow = flow
        self.functions = {}
        for subject, fun in self.flow.functions.items():
            self.addFunction(subject, fun)
    
    def addFunction(self, subject, fun):
        item = FunctionGraphicsItem(fun)
        item.setZValue(self.nextZVal*2)
        self.nextZVal += 1
        self.viewBox().addItem(item)
        self.functions[subject] = fun
    
    def selectionChanged(self):
        items = self._scene.selectedItems()
        if len(items) > 0:
            item = items[0]
            self.selectText.setPlainText(f"Selected item: {item}")
    
    def hoverOver(self):
        pass