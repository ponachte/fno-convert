from pyqtgraph import GraphicsObject
from PyQt6.QtGui import QColor, QPen, QBrush
from PyQt6.QtWidgets import QGraphicsTextItem
from PyQt6.QtCore import Qt, QRectF, QPointF
from typing import List

from ..execute.composition import Composition
from .process import ProcessGraphicsItem

STD_COLOR = QColor(200, 200, 200, 100)

class CompositionGraphicsItem(GraphicsObject):

    def __init__(self, comp: Composition, functions: List[ProcessGraphicsItem]):
        GraphicsObject.__init__(self)
        self.comp = comp
        self.functions = functions
        self.control_flows = {}

        self.child_comps = set()
        for fun in self.functions:
            if len(fun.compositions) == 0:
                fun.setParentItem(self)
            else:
                for comp in fun.compositions:
                    self.child_comps.add(comp)
            fun.compositions.add(self)

        self.pen = None
        self.setColor(STD_COLOR)

        flags = self.GraphicsItemFlag.ItemSendsGeometryChanges | self.GraphicsItemFlag.ItemIsMovable | self.GraphicsItemFlag.ItemIsFocusable
        self.setFlags(flags)

        self.bounds = QRectF(0, 0, 200, 100)
        self.nameItem = QGraphicsTextItem(self.comp.name, self)
        self.nameItem.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.titleOffset = 25
        self.margin = 10
        self.updateBounds()

        self.setZValue(0)

    def setColor(self, color: QColor):
        pen_color = color.darker(105)
        self.pen = QPen(pen_color, 4)

    def updateBounds(self):
        combined_bounds = None

        for item in self.functions:
            if item.isVisible():
                # Map each item's bounding rectangle to the parent (composition) coordinates
                item_bounds = item.mapRectToParent(item.boundingRect())
                if combined_bounds is None:
                    combined_bounds = item_bounds
                else:
                    combined_bounds = combined_bounds.united(item_bounds)
                
        for comp in self.child_comps:
            if comp.isVisible():
                comp_bounds = comp.boundingRect()
                if combined_bounds is None:
                    combined_bounds = item_bounds
                else:
                    combined_bounds = combined_bounds.united(comp_bounds)
        
        if combined_bounds is not None:
            # Adjust the combined bounds to add margin
            combined_bounds.adjust(-self.margin, -self.titleOffset, self.margin, self.margin)

            self.prepareGeometryChange()
            self.bounds = combined_bounds

            # Center the nameItem at the top of the composition, taking into account the titleOffset
            self.nameItem.setPos(
                self.bounds.left() + (self.bounds.width() / 2) - (self.nameItem.boundingRect().width() / 2),
                self.bounds.top()
            )

            self.update()  # Update the bounding rect

            for control_flow in self.control_flows.values():
                control_flow.updateLine()
    
    def checkVisible(self, item, closed):
        if not closed:
            self.setVisible(True)
            item.setVisible(True)
        else:
            self.setVisible(any([item.isVisible() for item in self.functions]))
        
        for control_flow in self.control_flows.values():
            control_flow.checkVisible()
    
    def boundingRect(self) -> QRectF:
        return self.bounds.adjusted(-5, -5, 5, 5)
    
    def sourcePoint(self):
        return self.mapToView(QPointF(self.boundingRect().right(), self.boundingRect().center().y()))
    
    def targetPoint(self):
        return self.mapToView(QPointF(self.boundingRect().left(), self.boundingRect().center().y()))

    def paint(self, p, *args):
        p.setPen(self.pen)
        p.drawRect(self.bounds)

    def mousePressEvent(self, ev):
        ev.ignore()

    def mouseClickEvent(self, ev):
        ev.ignore()
            
    def mouseDragEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            ev.accept()
            self.setPos(self.pos() + self.mapToParent(ev.pos()) - self.mapToParent(ev.lastPos()))

    def hoverEvent(self, ev):
        if not ev.isExit() and ev.acceptClicks(Qt.MouseButton.LeftButton):
            ev.acceptDrags(Qt.MouseButton.LeftButton)

    def keyPressEvent(self, ev):
        ev.ignore()
    
    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemPositionHasChanged:
            for function in self.functions:
                for item in function.terminals.values():
                    item.functionMoved()
            for control_flow in self.control_flows.values():
                control_flow.updateLine()
        return GraphicsObject.itemChange(self, change, value)