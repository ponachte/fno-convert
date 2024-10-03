from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QSizePolicy
from PyQt6.QtCore import QPoint, QPointF

from pyqtgraph import GraphicsView, ViewBox
from pyqtgraph.dockarea import DockArea, Dock
from rdflib import URIRef

from ..execute.flow import Flow
from ..execute.process import Process
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
        self.internal_flows = {}
        self.flow_items = {}
        self.terminals = {}
        self.variables = {}
        self.compositions = {}
        self.mappings = set()

        self.addFlow(flow)

        for int_flow in self.internal_flows.values():
            int_flow.close()
        
        self.autoArrange()
    
    def addFlow(self, flow: Flow, internal=None):
        function_items = set()

        # add input and output
        function_items.add(self.addFunction(flow.input))
        function_items.add(self.addFunction(flow.output))

        # add all used functions
        for fun in flow.functions.values():
            function_items.add(self.addFunction(fun))
            if fun in flow.internal_flows:
                function_items.update(self.addFlow(flow.internal_flows[fun], fun))

        # add all mappings
        for comp in flow.compositions.values():
            self.addComposition(comp)
            for mapping in comp.mappings:
                self.addMapping(mapping.source, mapping.target)
        
        if internal is not None:
            self.internal_flows[internal] = flow
            self.flow_items[flow] = function_items
        
        return function_items
    
    def addFunction(self, fun: Process):
        item = ProcessGraphicsItem(fun)
        item.setZValue(self.nextZVal*2)
        self.nextZVal += 1
        self.viewBox().addItem(item)
        self.functions[fun] = item
        self.terminals.update(item.terminals)

        item.visibleChanged.connect(self.autoArrange)

        return item
    
    def addComposition(self, comp: Composition):
        function_items = set()
        for fun in comp.functions:
            function_items.add(self.functions[fun])
            if fun in self.internal_flows:
                flow = self.internal_flows[fun]
                function_items.update(self.flow_items[flow])

        item = CompositionGraphicsItem(comp, function_items)
        self.viewBox().addItem(item)
        self.compositions[comp] = item

        return item
    
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

        return item
    
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
        edges = [(mapping.source.parentItem(), mapping.target.parentItem()) for mapping in self.mappings if mapping.isVisible()]

        if len(edges) > 0:
            positions = sugiyama_algorithm(edges, list(self.functions.values()))

            for process in positions:
                process.setPos(*positions[process])
        
        self.viewBox().autoRange()
            
