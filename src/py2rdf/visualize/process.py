from PyQt6.QtGui import QColor, QPen, QBrush
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtWidgets import QGraphicsTextItem
from pyqtgraph import GraphicsObject

from ..execute.processable import Processable
from .store import TerminalGraphicsItem

STD_COLOR = QColor(170, 170, 170)

class ProcessGraphicsItem(GraphicsObject):

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
        self.inps = self.function.inputs()
        self.outs = self.function.outputs()
        self.composition = None
        self.titleOffset = 25
        self.terminalOffset = 12

        flags = self.GraphicsItemFlag.ItemIsMovable | self.GraphicsItemFlag.ItemIsSelectable | self.GraphicsItemFlag.ItemIsFocusable | self.GraphicsItemFlag.ItemSendsGeometryChanges
        self.setFlags(flags)

        # calculate height
        numOfTerms = len(self.inps) + len(self.outs)
        height = self.titleOffset + numOfTerms * self.terminalOffset

        self.bounds = QRectF(0, 0, 200, height)
        self.nameItem = QGraphicsTextItem(function.name, self)
        self.nameItem.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.nameItem.setDefaultTextColor(QColor(50, 50, 50))
        self.nameItem.moveBy(self.bounds.width()/2. - self.nameItem.boundingRect().width()/2, 0)

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

        # Populate inputs
        y = self.titleOffset
        for name, term in self.inps.items():
            item = TerminalGraphicsItem(term, self)
            item.setZValue(self.zValue())
            item.setAnchor(0, y)
            self.terminals[term] = item
            y += self.terminalOffset
        
        # Populate outputs
        for name, term in self.outs.items():
            item = TerminalGraphicsItem(term, self)
            item.setZValue(self.zValue())
            item.setAnchor(int(self.bounds.width()), y)
            self.terminals[term] = item
            y += self.terminalOffset
    
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
            if self.composition is not None:
                self.composition.updateBounds()
        return GraphicsObject.itemChange(self, change, value)