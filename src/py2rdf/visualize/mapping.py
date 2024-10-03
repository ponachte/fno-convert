from math import atan2, cos, sin
from pyqtgraph import GraphicsObject, Point
import pyqtgraph.functions as fn
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainterPath, QPainterPathStroker

from .store import StoreGraphicsItem

class MappingGraphicsItem(GraphicsObject):

    def __init__(self, source: StoreGraphicsItem, target: StoreGraphicsItem):
        GraphicsObject.__init__(self)
        self.source = source
        self.target = target

        self.length = 0
        self.path = None
        self.shapePath = None
        self.style = {
            'shape': 'line',
            'color': (100, 100, 250),
            'width': 3.0
        }

        if self.source.getViewBox():
            self.source.getViewBox().addItem(self)
        else:
            self.target.getViewBox().addItem(self)
            self.target.getViewBox().addItem(self.source)
        
        self.source.mappings[target] = self
        self.target.mappings[source] = self

        self.source.visibleChanged.connect(self.checkVisible)
        self.target.visibleChanged.connect(self.checkVisible)
        
        self.updateLine()
        self.setZValue(1)
    
    def updateLine(self):
        start = Point(self.source.sourcePoint())
        stop = Point(self.target.targetPoint())

        self.prepareGeometryChange()

        self.path = self.generatePath(start, stop)
        self.shapePath = None
        self.update()

    def generatePath(self, start, stop):
        path = QPainterPath()
        path.moveTo(start)

        # Calculate the direction vector from start to stop
        direction = stop - start

        # Calculate the length of the direction vector
        length = direction.length()

        # Normalize the direction vector
        if length != 0:
            direction /= length

        # Set the length of the arrowhead
        arrow_length = 10

        # Set the angle of the arrowhead
        arrow_angle = 70

        # Calculate the points for the two sides of the arrowhead
        side1 = stop + QPointF(
            -arrow_length * cos(arrow_angle + atan2(direction.y(), direction.x())),
            -arrow_length * sin(arrow_angle + atan2(direction.y(), direction.x()))
        )
        side2 = stop + QPointF(
            -arrow_length * cos(-arrow_angle + atan2(direction.y(), direction.x())),
            -arrow_length * sin(-arrow_angle + atan2(direction.y(), direction.x()))
        )

        # Add the arrowhead and the line to the path
        path.lineTo(stop)
        path.lineTo(side1)
        path.moveTo(stop)
        path.lineTo(side2)

        return path
    
    def checkVisible(self):
        self.setVisible(self.source.isVisible() and self.target.isVisible())
    
    def keyPressEvent(self, ev):
        ev.ignore()
        return

    def mousePressEvent(self, ev):
        ev.ignore()
        return

    def mouseClickEvent(self, ev):
        ev.ignore()
        return
    
    def boundingRect(self):
        return self.shape().boundingRect()
    
    def viewRangeChanged(self):
        self.shapePath = None
        self.prepareGeometryChange()

    def shape(self):
        if self.shapePath is None:
            if self.path is None:
                return QPainterPath()
            stroker = QPainterPathStroker()
            px = self.pixelWidth()
            stroker.setWidth(px * 8)
            self.shapePath = stroker.createStroke(self.path)
        return self.shapePath
    
    def paint(self, p, *args):
        p.setPen(fn.mkPen(self.style['color'], width=self.style['width']))
        p.drawPath(self.path)



