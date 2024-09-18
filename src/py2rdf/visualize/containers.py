import tkinter as tk

class Container:

    def __init__(self, canvas: tk.Canvas, name, nodes) -> None:
        self.canvas = canvas
        self.name = name

        self.padding = 15
        self.name_height = 30
        
        # Initialize the container rectangle
        self.rect = self.canvas.create_rectangle(0, 0, 0, 0, outline="black", width=3, fill="")

        # Draw the name at the top center
        self.name_id = self.canvas.create_text(0, 0, text=self.name, font=("helvetica", 12, "bold"), anchor="center")
        
        # Initialize an empty list to hold nodes
        self.nodes = {}
        for node in nodes:
            self.nodes[node.name] = node
            node.container = self
        self.update_container()

    def update_container(self):
        """Adjust the container rectangle to fit all nodes."""
        if not self.nodes:
            return
        
        # Get the bounds of all nodes
        min_x = min(self.canvas.coords(node.rect)[0] for node in self.nodes.values())
        min_y = min(self.canvas.coords(node.rect)[1] for node in self.nodes.values())
        max_x = max(self.canvas.coords(node.rect)[2] for node in self.nodes.values())
        max_y = max(self.canvas.coords(node.rect)[3] for node in self.nodes.values())
        
        # Adjust container size and position with padding
        self.canvas.coords(self.rect, min_x - self.padding, min_y - self.padding - self.name_height, max_x + self.padding, max_y + self.padding)
        self.canvas.coords(self.name_id, (min_x + max_x) / 2, min_y - self.padding - self.name_height / 2)