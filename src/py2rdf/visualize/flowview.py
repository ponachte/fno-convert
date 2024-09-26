from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QSizePolicy
from PyQt6.QtCore import QPoint, QPointF

from pyqtgraph import GraphicsView, ViewBox
from pyqtgraph.dockarea import DockArea, Dock
from rdflib import URIRef

from ..execute.flow_executer import Flow
from ..execute.processable import Processable
from ..execute.store import ValueStore, Terminal
from ..execute.composition import Composition
from ..graph import PipelineGraph
from .process import ProcessGraphicsItem
from .store import StoreGraphicsItem, VariableGraphicsItem
from .mapping import MappingGraphicsItem
from .composition import CompositionGraphicsItem
from .layout import sugiyama_algorithm

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
        self.terminals = {}
        self.variables = {}
        self.compositions = {}
        self.mappings = set()

        # add input and output
        self.addFunction(self.flow.input)
        self.addFunction(self.flow.output)

        # add all used functions
        for fun in self.flow.functions.values():
            self.addFunction(fun)

        # add all mappings
        for comp in self.flow.compositions.values():
            self.addComposition(comp)
            for mapping in comp.mappings:
                self.addMapping(mapping.source, mapping.target)
        
        self.autoArrange()
    
    def addFunction(self, fun: Processable):
        item = ProcessGraphicsItem(fun)
        item.setZValue(self.nextZVal*2)
        self.nextZVal += 1
        self.viewBox().addItem(item)
        self.functions[fun] = item
        self.terminals.update(item.terminals)
    
    def addComposition(self, comp: Composition):
        function_items = [ self.functions[fun] for fun in comp.functions ]
        item = CompositionGraphicsItem(comp, function_items)
        self.viewBox().addItem(item)
        self.compositions[comp] = item
    
    def addVariable(self, name, var):
        item = VariableGraphicsItem(var)
        item.setZValue(self.nextZVal*2)
        self.nextZVal += 1
        self.viewBox().addItem(item)
        if name not in self.variables:
            self.variables[name] = []
        self.variables[name].append((var, item))
    
    def addMapping(self, source: ValueStore, target: ValueStore):
        if isinstance(source, Terminal):
            source = self.terminals[source]
        if isinstance(target, Terminal):
            target = self.terminals[target]
        
        item = MappingGraphicsItem(source, target)
        self.viewBox().addItem(item)
        self.mappings.add(item)
    
    def selectionChanged(self):
        items = self._scene.selectedItems()
        if len(items) > 0:
            item = items[0]
            self.selectText.setPlainText(f"Selected item: {item}")
    
    def hoverOver(self, items):
        store = None
        for item in items:
            if item is self.hoverItem:
                return
            self.hoverItem = item
            if isinstance(item, StoreGraphicsItem):
                store = item.store
                break
        if store is None:
            self.hoverText.setPlainText("")
        else:
            value = str(store.value)
            if len(value) > 400:
                value = value[:400] + "..."
            self.hoverText.setPlainText("%s = %s" % (store.name, value))
    
    def autoArrange(self):
        edges = [(mapping.source.parentItem(), mapping.target.parentItem()) for mapping in self.mappings]

        if len(edges) > 0:
            positions = sugiyama_algorithm(edges, list(self.functions.values()))

            for process in positions:
                process.setPos(*positions[process])
        
        self.viewBox().autoRange()
            
