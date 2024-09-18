import tkinter as tk
from .node import Node
from .containers import Container

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

        self.nodes["node1"].output_terminals["terminal1"].connect_to(self.nodes["node2"].input_terminals["terminal3"])

        self.containers = {}
        self.add_container("container1", [self.nodes["node1"], self.nodes["node3"]])

    def add_node(self, name, x0, y0, strings):
        """Adds a new draggable Node (rectangle) to the canvas."""
        node = Node(self, name, x0, y0, strings, strings)
        self.nodes[name] = node
    
    def add_container(self, name, nodes):
        self.containers[name] = Container(self, name, nodes)

    def on_resize(self, event):
        """Handle window resizing and adjust the canvas size."""
        self.config(width=event.width, height=event.height)