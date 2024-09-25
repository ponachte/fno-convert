from PyQt6.QtGui import QColor, QPen, QBrush
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtWidgets import QGraphicsTextItem
from pyqtgraph import GraphicsObject

from ..execute.flow_executer import Processable
from .store import TerminalGraphicsItem

STD_COLOR = QColor(170, 170, 170)

class FunctionGraphicsItem(GraphicsObject):

    def __init__(self, function: Processable):
        GraphicsObject.__init__(self)

        self.hovered = False
        self.pen = None
        self.brush = None
        self.hoverBrush = None
        self.selectPen = None
        self.selectBrush = None
        self.setColor(STD_COLOR)

        self.function = function
        self.terminals = {}

        flags = self.GraphicsItemFlag.ItemIsMovable | self.GraphicsItemFlag.ItemIsSelectable | self.GraphicsItemFlag.ItemIsFocusable | self.GraphicsItemFlag.ItemSendsGeometryChanges
        self.setFlags(flags)

        self.bounds = QRectF(0, 0, 200, 100)
        self.nameItem = QGraphicsTextItem(function.name, self)
        self.nameItem.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.nameItem.setDefaultTextColor(QColor(50, 50, 50))
        self.nameItem.moveBy(self.bounds.width()/2. - self.nameItem.boundingRect().width()/2, 0)
        
        self._titleOffset = 25
        self._terminalOffset = 12

        self.updateTerminals()
    
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
    
    def updateTerminals(self):
        self.terminals = {}
        inps = self.function.inputs()
        outs = self.function.outputs()

        numOfTerms = len(inps) + len(outs)

        # calculate new height
        newHeight = self._titleOffset + numOfTerms * self._terminalOffset

        # if current height is not equal to new height, update
        if not self.bounds.height() == newHeight:
            self.bounds.setHeight(newHeight)
            self.update()
        
        # Populate inputs
        y = self._titleOffset
        for name, term in inps.items():
            item = TerminalGraphicsItem(term, self)
            item.setZValue(self.zValue())
            item.setAnchor(0, y)
            self.terminals[term] = item
            y += self._terminalOffset
        
        # Populate outputs
        for name, term in outs.items():
            item = TerminalGraphicsItem(term, self)
            item.setZValue(self.zValue())
            item.setAnchor(int(self.bounds.width()), y)
            self.terminals[term] = item
            y += self._terminalOffset
    
    def boundingRect(self) -> QRectF:
        return self.bounds.adjusted(-5, -5, 5, 5)
    
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
        p.drawRect(self.bounds)

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
            for item in self.terminals.values():
                item.functionMoved()
        return GraphicsObject.itemChange(self, change, value)