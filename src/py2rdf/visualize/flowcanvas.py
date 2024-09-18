import tkinter as tk
from .node import Node

class FlowCanvas(tk.Canvas):

    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.pack(fill="both", expand=True)

        # Create a few Node objects (rectangles) on the canvas
        self.nodes = []
        strings = ["terminal1", "terminal2", "terminal3"]
        self.add_node(50, 50, strings, "red")
        self.add_node(100, 100, strings, "blue")
        self.add_node(150, 150, strings, "green")

    def add_node(self, x0, y0, strings, color):
        """Adds a new draggable Node (rectangle) to the canvas."""
        node = Node(self, x0, y0, strings, strings, color=color)
        self.nodes.append(node)

    def on_resize(self, event):
        """Handle window resizing and adjust the canvas size."""
        self.config(width=event.width, height=event.height)