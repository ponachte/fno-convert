from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import QTextEdit, QGraphicsRectItem
from PyQt6.QtCore import QRectF

from pyqtgraph import GraphicsView, ViewBox, mkBrush, mkPen
from pyqtgraph.dockarea import DockArea, Dock
from rdflib import URIRef
import numpy as np

from ..execute.flow import Flow
from ..execute.process import Process
from ..execute.store import ValueStore, Terminal, Variable
from ..execute.composition import Composition
from ..graph import PipelineGraph
from .process import ProcessGraphicsItem
from .store import StoreGraphicsItem, VariableGraphicsItem
from .mapping import MappingGraphicsItem, ControlFlowGraphicsItem
from .composition import CompositionGraphicsItem
from .layout import sugiyama_algorithm
from .new_layout import layout_flow

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
        super().__init__(*args, **kwargs)
        self.widget = widget

        # Set the background of the viewbox
        self.setBackgroundColor('white')

    def items(self):
        return self.addedItems

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
        self.process = {}
        self.internal_flows = {}
        self.flow_items = {}
        self.terminals = {}
        self.variables = {}
        self.compositions = {}
        self.mappings = set()
        self.control_flows = set()
        self.viewBox().clear()

        self.addFlow(flow)

        for int_flow in self.internal_flows.values():
            int_flow.close()
        
        self.autoArrange()
    
    def addFlow(self, flow: Flow, internal=None):
        process_items = set()

        # add input and output
        process_items.add(self.addProcess(flow.input))
        process_items.add(self.addProcess(flow.output))

        # add all used functions
        for fun in flow.functions.values():
            process_items.add(self.addProcess(fun))
            if fun in flow.internal_flows:
                process_items.update(self.addFlow(flow.internal_flows[fun], fun))
        
        # add all constants
        for const in flow.constants:
            process_items.add(self.addProcess(const))

        # add all mappings
        for comp in flow.compositions.values():
            self.addComposition(comp)
            for mapping in comp.mappings:
                self.addMapping(mapping.source, mapping.target)
        
        # add all control flow mappings
        for comp in self.compositions:
            for (next, label) in comp.control_flows():
                if next is not None:
                    self.addControlFlow(comp, next, label)
        
        if internal is not None:
            self.internal_flows[internal] = flow
            self.flow_items[flow] = process_items
        
        return process_items
    
    def addProcess(self, fun: Process):
        item = ProcessGraphicsItem(fun, self)
        item.setZValue(self.nextZVal*2)
        self.nextZVal += 1
        self.viewBox().addItem(item)
        self.process[fun] = item
        self.terminals.update(item.terminals)

        item.visibleChanged.connect(self.autoArrange)

        return item
    
    def addComposition(self, comp: Composition):
        function_items = set()
        for fun in comp.process:
            function_items.add(self.process[fun])
            if fun in self.internal_flows:
                flow = self.internal_flows[fun]
                function_items.update(self.flow_items[flow])

        item = CompositionGraphicsItem(comp, function_items)
        self.viewBox().addItem(item)
        self.compositions[comp] = item

        return item
    
    def addVariable(self, var: Variable):
        print("creating var", var.name)
        item = VariableGraphicsItem(var)
        item.setZValue(self.nextZVal*2)
        self.nextZVal += 1
        self.viewBox().addItem(item)
        if var not in self.variables:
            self.variables[var] = set()
        self.variables[var].add(item)
        
        item.visibleChanged.connect(self.autoArrange)

        return item
    
    def addMapping(self, source: ValueStore, target: ValueStore):
        if isinstance(source, Terminal):
            source = self.terminals[source]
        elif isinstance(source, Variable):
            print("source variable: ", source)
            source = self.addVariable(source)
        if isinstance(target, Terminal):
            target = self.terminals[target]
        elif isinstance(target, Variable):
            print("target variable: ", target)
            target = self.addVariable(target)
        
        item = MappingGraphicsItem(source, target, self)
        self.viewBox().addItem(item)
        self.mappings.add(item)

        return item

    def addControlFlow(self, comp: Composition, next: Composition, label: str):
        comp = self.compositions[comp]
        next = self.compositions[next]

        item = ControlFlowGraphicsItem(comp, next, label, self)
        self.viewBox().addItem(item)
        self.control_flows.add(item)
    
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
        """mapping_edges = [(mapping.source.parentItem(), mapping.target.parentItem()) for mapping in self.mappings if mapping.isVisible()]
        control_edges = [(control.source, control.target) for control in self.control_flows if control.isVisible()]
        layout_flow(self.process[self.flow.input], self.process[self.flow.output],
                    self.compositions.values(), mapping_edges, control_edges)
        
        self.viewBox().autoRange()"""
        
        edges = [mapping.edge() for mapping in self.mappings if mapping.isVisible()]

        if len(edges) > 0:
            start = self.process[self.flow.input]
            end = self.process[self.flow.output]
            positions = sugiyama_algorithm(edges, list(self.compositions.values()))

            for process in positions:
                process.setPos(*positions[process])
        
        self.viewBox().autoRange()