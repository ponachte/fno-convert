from math import atan2, cos, sin
from pyqtgraph import GraphicsObject, Point
import pyqtgraph.functions as fn
from PyQt6.QtCore import QPointF, QLineF
from PyQt6.QtGui import QPainterPath, QPainterPathStroker

from .store import StoreGraphicsItem
from .composition import CompositionGraphicsItem
from .process import ProcessGraphicsItem
from ..execute.process import FunctionLink

STD_COLOR = (100, 100, 250)
LINK_COLOR = (250, 100, 100)

class MappingGraphicsItem(GraphicsObject):

    def __init__(self, source: StoreGraphicsItem, target: StoreGraphicsItem, flow_view):
        GraphicsObject.__init__(self)
        self.source = source
        self.target = target
        self.flow_view = flow_view

        self.length = 0
        self.path = None
        self.shapePath = None
        if isinstance(source.parentItem().function, FunctionLink) or isinstance(target.parentItem().function, FunctionLink):
            color = LINK_COLOR
        else:
            color = STD_COLOR
        self.style = {
            'shape': 'line',
            'color': color,
            'width': 2.0
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
        # Step 1: Initialize a new QPainterPath starting at 'start'
        path = QPainterPath()
        path.moveTo(start)

        # Step 2: Set up some variables
        current_point = start
        next_point = None

        # Step 3: Get all items in the ViewBox (this is your obstacle set)
        obstacles = [item for item in self.flow_view.process.values()
                     if item.isVisible() 
                     if item not in [self.source.parentItem(), self.target.parentItem()]]

        # Step 4: Break the path into horizontal and vertical segments (Manhattan-style routing)
        mid_x = (start.x() + stop.x()) / 2

        # Move horizontally first, then vertically (for example)
        points = [
            QPointF(mid_x, start.y()),  # Move horizontally to the middle
            QPointF(mid_x, stop.y()),   # Move vertically to align with the target
            stop                        # Final segment to the stop point
        ]

        # Step 5: Check for collisions and adjust segments
        i = 0
        while i < len(points):
            segment = points[i:i+2]

            """# Check if the first part of the segment collides
            collision = self.collidesWithObstacles(segment[0], segment[1], obstacles)

            if collision:
                # If there is a collision, adjust the path (for simplicity, we move around obstacles)
                next_point = self.adjustPathAroundObstacle(current_point, next_point, collision)"""
            
            next_point = segment[0]
            i += 1
            # Add this segment to the path
            path.lineTo(next_point)
            current_point = next_point

        # Step 6: Add arrowhead at the end (optional)
        self.addArrowhead(path, stop, current_point)

        return path

    def collidesWithObstacles(self, start, end, obstacles):
        # Create a QPainterPath for the line between start and end
        line_path = QPainterPath()
        line_path.moveTo(start)
        line_path.lineTo(end)

        for obstacle in obstacles:
            # Check if line intersects with the obstacle bounds
            obstacle_bounds = obstacle.mapRectToParent(obstacle.boundingRect())
            if line_path.intersects(obstacle_bounds):
                return obstacle  # Return the first obstacle we hit

        return None  # No collisions
    
    def adjustPathAroundObstacle(self, start, mid, end, obstacle):
        pass
    
    def addArrowhead(self, path, stop, direction):
        arrow_length = 10
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

class ControlFlowGraphicsItem(GraphicsObject):

    def __init__(self, source: CompositionGraphicsItem, target: CompositionGraphicsItem, label: str, flow_view):
        GraphicsObject.__init__(self)
        self.source = source
        self.target = target
        self.flow_view = flow_view

        self.length = 0
        self.path = None
        self.shapePath = None
        self.style = {
            'shape': 'line',
            'color': (250, 175, 100),
            'width': 2.0
        }

        if self.source.getViewBox():
            self.source.getViewBox().addItem(self)
        else:
            self.target.getViewBox().addItem(self)
            self.target.getViewBox().addItem(self.source)
        
        self.source.control_flows[target] = self
        self.target.control_flows[source] = self

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
        # Step 1: Initialize a new QPainterPath starting at 'start'
        path = QPainterPath()
        path.moveTo(start)

        # Step 2: Set up some variables
        current_point = start
        next_point = None

        # Step 3: Get all items in the ViewBox (this is your obstacle set)
        obstacles = [item for item in self.flow_view.process.values()
                     if item.isVisible() 
                     if item not in [self.source.parentItem(), self.target.parentItem()]]

        # Step 4: Break the path into horizontal and vertical segments (Manhattan-style routing)
        mid_x = (start.x() + stop.x()) / 2

        # Move horizontally first, then vertically (for example)
        points = [
            QPointF(mid_x, start.y()),  # Move horizontally to the middle
            QPointF(mid_x, stop.y()),   # Move vertically to align with the target
            stop                        # Final segment to the stop point
        ]

        # Step 5: Check for collisions and adjust segments
        i = 0
        while i < len(points):
            segment = points[i:i+2]

            """# Check if the first part of the segment collides
            collision = self.collidesWithObstacles(segment[0], segment[1], obstacles)

            if collision:
                # If there is a collision, adjust the path (for simplicity, we move around obstacles)
                next_point = self.adjustPathAroundObstacle(current_point, next_point, collision)"""
            
            next_point = segment[0]
            i += 1
            # Add this segment to the path
            path.lineTo(next_point)
            current_point = next_point

        # Step 6: Add arrowhead at the end (optional)
        self.addArrowhead(path, stop, current_point)

        return path

    def collidesWithObstacles(self, start, end, obstacles):
        # Create a QPainterPath for the line between start and end
        line_path = QPainterPath()
        line_path.moveTo(start)
        line_path.lineTo(end)

        for obstacle in obstacles:
            # Check if line intersects with the obstacle bounds
            obstacle_bounds = obstacle.mapRectToParent(obstacle.boundingRect())
            if line_path.intersects(obstacle_bounds):
                return obstacle  # Return the first obstacle we hit

        return None  # No collisions
    
    def adjustPathAroundObstacle(self, start, mid, end, obstacle):
        pass
    
    def addArrowhead(self, path, stop, direction):
        arrow_length = 10
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


