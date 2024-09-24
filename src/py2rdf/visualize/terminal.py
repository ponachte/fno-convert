from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PyQt5.QtCore import QRectF, Qt, QPoint
from pyqtgraph import GraphicsObject
import pyqtgraph.functions as fn

from ..execute.flow_executer import Terminal

class TerminalGraphicsItem(GraphicsObject):

    def __init__(self, terminal: Terminal, parent=None):
        GraphicsObject.__init__(self, parent)

        self.brush = fn.mkBrush(0,0,0)
        self.box = QGraphicsRectItem(0, 0, 10, 10, self)
        self.label = QGraphicsTextItem(terminal.name, self)
        self.label.setScale(0.7)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setFiltersChildEvents(True) # pick up mouse events on rectitem
        self.setZValue(1)

        self.terminal = terminal
    
    def setBrush(self, brush):
        self.brush = brush
        self.box.setBrush(brush)

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

        if not self.terminal.is_output:
            self.box.setPos(pos.x(), pos.y() - br.height()/2.)
            self.label.setPos(pos.x() + br.width(), pos.y() - lr.height()/2.)
        else:
            self.box.setPos(pos.x() - br.width(), pos.y() - br.height()/2.)
            self.label.setPos(pos.x() - br.width()-lr.width(), pos.y() - lr.height()/2.)
        # self.updateConnections()
    
    def paint(self, p, *args):
        pass
    
    def functionMoved(self):
        pass
    
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
            self.box.setBrush(fn.mkBrush('b'))
        else:
            self.box.setBrush(self.brush)
        self.update()