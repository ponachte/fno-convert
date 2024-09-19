import tkinter as tk
from .node import Node
from .containers import Container
from .store import Variable

class FlowCanvas(tk.Canvas):

    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.pack(fill="both", expand=True)

        # Create a few Node objects (rectangles) on the canvas
        self.nodes = {}
        strings = ["terminal1", "terminal2", "terminal3"]
        self.add_node("node1", 50, 50, strings)
        self.add_node("node2", 100, 100, strings)
        self.add_node("node3", 150, 150, strings)

        self.nodes["node1"].output_terminals["terminal1"].map_to(self.nodes["node2"].input_terminals["terminal3"])
        self.nodes["node3"].output_terminals["terminal2"].map_to(self.nodes["node1"].input_terminals["terminal3"])

        self.containers = {}
        self.add_container("container1", [self.nodes["node1"], self.nodes["node3"]])
        self.add_container("container2", [self.nodes["node2"]])

        self.containers["container1"].flow_to(self.containers["container2"])

        self.variables = {}
        self.add_variable("count", 300, 300)

        self.nodes["node2"].output_terminals["terminal2"].map_to(self.variables["count"])

        self.layout_nodes()

    def add_node(self, name, x0, y0, strings):
        """Adds a new draggable Node (rectangle) to the canvas."""
        node = Node(self, name, x0, y0, strings, strings)
        self.nodes[name] = node
    
    def add_container(self, name, nodes):
        self.containers[name] = Container(self, name, nodes)
    
    def add_variable(self, name, x, y):
        var = Variable(self, name, x, y)
        self.variables[name] = var

    def on_resize(self, event):
        """Handle window resizing and adjust the canvas size."""
        self.config(width=event.width, height=event.height)
    
    def layout_nodes(self):
        margin_x = 150
        margin_y = 100

        # Step 1: Create a dictionary to hold nodes by their level
        levels = {}
        
        # Step 2: Calculate the level for each node
        for node in self.nodes.values():
            level = self.calculate_level(node)
            if level not in levels:
                levels[level] = []
            levels[level].append(node)
        
        # Step 3: Place nodes in their appropriate levels (left to right)
        x_offset = margin_x
        for level in sorted(levels.keys()):
            y_offset = margin_y
            for node in levels[level]:
                # Step 4: Position the node at (x_offset, y_offset)
                node_x = x_offset
                node_y = y_offset
                node.move(node_x, node_y)
                
                # Increase vertical offset for next node in this level
                y_offset += node.height + margin_y
            
            # Increase horizontal offset for next column
            x_offset += node.width + margin_x

    def calculate_level(self, node):
        # Base case: If node has no dependencies, it belongs to level 0
        if node.dependencies() == []:
            return 0
        
        # Otherwise, it's 1 level greater than the max level of its dependencies
        return 1 + max(self.calculate_level(input_node) for input_node in node.dependencies())