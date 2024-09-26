from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PyQt6.QtCore import QRectF, Qt, QPoint
from PyQt6.QtGui import QColor, QPen, QBrush
from pyqtgraph import GraphicsObject
import pyqtgraph.functions as fn

from ..execute.store import Terminal, Variable, ValueStore

from abc import abstractmethod

STD_COLOR = QColor(170, 170, 170)

class StoreGraphicsItem(GraphicsObject):

    def __init__(self, store: ValueStore, parent=None):
        GraphicsObject.__init__(self, parent)
        self.store = store
        self.mappings = {}
    
    @abstractmethod
    def sourcePoint(self):
        pass

    @abstractmethod
    def targetPoint(self):
        pass

class TerminalGraphicsItem(StoreGraphicsItem):

    def __init__(self, terminal: Terminal, parent=None):
        StoreGraphicsItem.__init__(self, terminal, parent)

        self.std_brush = fn.mkBrush(0, 0, 0)    # Standard brush is black
        self.hover_brush = fn.mkBrush('b')      # Hover brush is blue
        self.accepted_brush = fn.mkBrush('g')   # Accepted brush is green
        self.error_brush = fn.mkBrush('r')      # Error brush is red
        self.brush = self.std_brush

        self.box = QGraphicsRectItem(0, 0, 10, 10, self)
        self.box.setBrush(self.brush)
        self.label = QGraphicsTextItem(terminal.name, self)
        self.label.setScale(0.7)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setFiltersChildEvents(True) # pick up mouse events on rectitem
        self.setZValue(1)

        terminal.valueChange.connect(self.valueChange)

    def boundingRect(self) -> QRectF:
        # Return the smallest rectangle that contains both the label and the box
        br = self.box.mapRectToParent(self.box.boundingRect())
        lr = self.label.mapRectToParent(self.label.boundingRect())
        return br | lr
    
    def setAnchor(self, x, y):
        pos = QPoint(x, y)
        self.anchorPos = pos
        br = self.box.mapRectToParent(self.box.boundingRect())
        lr = self.label.mapRectToParent(self.label.boundingRect())

        if not self.store.is_output:
            self.box.setPos(pos.x(), pos.y() - br.height()/2.)
            self.label.setPos(pos.x() + br.width(), pos.y() - lr.height()/2.)
        else:
            self.box.setPos(pos.x() - br.width(), pos.y() - br.height()/2.)
            self.label.setPos(pos.x() - br.width()-lr.width(), pos.y() - lr.height()/2.)
        # self.updateConnections()
    
    def sourcePoint(self):
        return self.mapToView(self.mapFromItem(self.box, self.box.boundingRect().right(), self.box.boundingRect().center().y()))
    
    def targetPoint(self):
        return self.mapToView(self.mapFromItem(self.box, self.box.boundingRect().left(), self.box.boundingRect().center().y()))
    
    def valueChange(self, accepted):
        if accepted:
            self.brush = self.accepted_brush
        else:
            self.brush = self.error_brush
            
        self.box.setBrush(self.brush)
        self.update()
    
    def paint(self, p, *args):
        pass
    
    def functionMoved(self):
        for mapping in self.mappings.values():
            mapping.updateLine()
    
    def mousePressEvent(self, event):
        event.ignore()
    
    def mouseClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self.label.setFocus(Qt.FocusReason.MouseFocusReason)
    
    def mouseDragEvent(self, event):
        event.ignore()
    
    def hoverEvent(self, event):
        if not event.isExit() and event.acceptDrags(Qt.MouseButton.LeftButton):
            event.acceptClicks(Qt.MouseButton.LeftButton)
            event.acceptClicks(Qt.MouseButton.RightButton)
            self.box.setBrush(self.hover_brush)
        else:
            self.box.setBrush(self.brush)
        self.update()

class VariableGraphicsItem(StoreGraphicsItem):

    def __init__(self, var: Variable, parent=None):
        StoreGraphicsItem.__init__(self, var, parent)

        self.pen = None
        self.brush = None
        self.hoverBrush = None
        self.selectPen = None
        self.selectBrush = None
        self.setColor(STD_COLOR)

        flags = self.GraphicsItemFlag.ItemIsMovable | self.GraphicsItemFlag.ItemIsSelectable | self.GraphicsItemFlag.ItemIsFocusable | self.GraphicsItemFlag.ItemSendsGeometryChanges
        self.setFlags(flags)

        self.nameItem = QGraphicsTextItem(var.name, self)
        self.nameItem.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.nameItem.setDefaultTextColor(QColor(50, 50, 50))
        name_width = self.nameItem.boundingRect().width()
        name_height = self.nameItem.boundingRect().height()
        radius = max(name_width + 10, name_height + 10)
        self.bounds = QRectF(0, 0, radius, radius)
    
    def setColor(self, color: QColor):
        pen_color = color.darker(105)
        brush_color = color.lighter(105)
        brush_color.setAlpha(150)
        hover_color = color.lighter(105)
        hover_color.setAlpha(200)

        self.setPenColor(pen_color)
        self.setBrushColor(brush_color)
        self.setHoverColor(hover_color)
    
    def setPenColor(self, color: QColor):
        self.pen = QPen(color)
        self.selectPen = QPen(color, 2)
        self.update()

    def setBrushColor(self, color: QColor):
        self.brush = QBrush(color)
        select_color = color.lighter(115)
        select_color.setAlpha(200)
        self.selectBrush = QBrush(select_color)
        self.update()
    
    def setHoverColor(self, color: QColor):
        self.hoverBrush = QBrush(color)
        self.update()
    
    def boundingRect(self) -> QRectF:
        return self.bounds.adjusted(-5, -5, 5, 5)
    
    def sourcePoint(self):
        return self.mapToView(self.mapFromItem(self.box, self.bounds.right(), self.bounds.center().y()))
    
    def targetPoint(self):
        return self.mapToView(self.mapFromItem(self.box, self.bounds.left(), self.bounds.center().y()))
    
    def paint(self, p, *args):
        if self.isSelected():
            p.setPen(self.selectPen)
            p.setBrush(self.selectBrush)
        else:
            p.setPen(self.pen)
            if self.hovered:
                p.setBrush(self.hoverBrush)
            else:
                p.setBrush(self.brush)
        p.drawEllipse(self.bounds)
    
    def mousePressEvent(self, event):
        event.ignore()

    def mouseClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            selected = self.isSelected()
            self.setSelected(True)
            if not selected and self.isSelected():
                self.update()
    
    def mouseDragEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self.setPos(self.pos() + self.mapToParent(event.pos()) - self.mapToParent(event.lastPos()))
    
    def hoverEvent(self, event):
        if not event.isExit() and event.acceptClicks(Qt.MouseButton.LeftButton):
            event.acceptDrags(Qt.MouseButton.LeftButton)
            self.hovered = True
        else:
            self.hovered = False
        self.update()
    
    def keyPressEvent(self, event) -> None:
        event.ignore()

    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemPositionHasChanged:
            for mapping in self.mappings.values():
                mapping.updateLine()
        return GraphicsObject.itemChange(self, change, value)