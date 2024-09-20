import tkinter as tk
from tkinter import font
from itertools import chain
from .node import Node
from .containers import Container
from .store import Variable

class FlowCanvas(tk.Canvas):

    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.pack(fill="both", expand=True)

        self.nodes = {}
        self.containers = {}
        self.variables = []

        ### SCALING ###

        # Bind mouse scroll for zooming
        self.bind("<MouseWheel>", self.zoom)  # Windows scroll event
        self.bind("<Button-4>", self.zoom)    # Linux scroll event
        self.bind("<Button-5>", self.zoom)    # Linux scroll event
        
        # Store initial scaling factor
        self.current_scale = 1.0

        # Bind arrow keys to scroll events
        self.bind_all("<Left>", self.on_left_arrow)
        self.bind_all("<Right>", self.on_right_arrow)
        self.bind_all("<Up>", self.on_up_arrow)
        self.bind_all("<Down>", self.on_down_arrow)

    def add_node(self, subject, name, x0, y0, inputs, outputs):
        """Adds a new draggable Node (rectangle) to the canvas."""
        node = Node(self, name, x0, y0, inputs, outputs)
        self.nodes[subject] = node
    
    def add_link_nodes(self, subject, name, x0, y0, inputs, outputs):
        self.input = Node(self, subject, f"{name} input", x0, y0, [], inputs)
        self.output = Node(self, subject, f"{name} output", x0, y0, outputs, [])
    
    def add_container(self, name, nodes):
        self.containers[name] = Container(self, name, nodes)
    
    def add_variable(self, name, x, y):
        var = Variable(self, name, x, y)
        self.variables.append(var)
        return var
    
    def get_source_terminal(self, fun, ter):
        if fun in self.nodes:
            return self.nodes[fun].output_terminals[ter]
        self.input.output_terminals[ter]
    
    def get_target_terminal(self, fun, ter):
        if fun in self.nodes:
            return self.nodes[fun].input_terminals[ter]
        self.output.input_terminals[ter]
    
    def zoom(self, event):
        """Zoom in or out based on scroll direction."""
        # Handle zoom direction differently for each platform
        if event.num == 4 or event.delta > 0:
            scale_factor = 1.1  # Zoom in
        elif event.num == 5 or event.delta < 0:
            scale_factor = 0.9  # Zoom out
        else:
            return
        self.current_scale *= scale_factor

        # Center of the zoom (mouse position or center of canvas)
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)

        # Scale all items on the canvas
        self.scale("all", x, y, scale_factor, scale_factor)

        # Scale fonts
        self.update_text_fonts(scale_factor)
        
        # Adjust the scroll region so the canvas expands/contracts correctly
        self.configure(scrollregion=self.bbox("all"))
    
    def update_text_fonts(self, scale_factor):
        """Update font sizes of text objects based on scale factor."""
        for item in self.find_all():
            if self.type(item) == "text":
                # Get the current font object
                current_font = font.Font(self, self.itemcget(item, "font"))
                
                # Calculate new font size based on scale factor
                new_size = int(float(current_font.cget("size")) * scale_factor)
                
                # Update the font size while keeping other properties unchanged
                current_font.config(size=new_size)
                self.itemconfig(item, font=current_font)

    def on_left_arrow(self, event):
        """Move canvas left when left arrow is pressed."""
        self.xview_scroll(-1, "units")  # Scroll left by 1 unit

    def on_right_arrow(self, event):
        """Move canvas right when right arrow is pressed."""
        self.xview_scroll(1, "units")  # Scroll right by 1 unit

    def on_up_arrow(self, event):
        """Move canvas up when up arrow is pressed."""
        self.yview_scroll(-1, "units")  # Scroll up by 1 unit

    def on_down_arrow(self, event):
        """Move canvas down when down arrow is pressed."""
        self.yview_scroll(1, "units")  # Scroll down by 1 unit

    def on_resize(self, event):
        """Handle window resizing and adjust the canvas size."""
        self.config(width=event.width, height=event.height)
    
    def layout_elements(self):
        margin_x = 150
        margin_y = 100

        # Step 1: Create a dictionary to hold nodes by their level
        levels = {}
        
        # Step 2: Calculate the level for each node
        for element in chain(self.nodes.values(), self.variables):
            level = self.calculate_level(element)
            if level not in levels:
                levels[level] = []
            levels[level].append(element)
        
        # Step 3: Place nodes in their appropriate levels (left to right)
        x_offset = margin_x
        for level in sorted(levels.keys()):
            y_offset = margin_y
            for element in levels[level]:
                # Step 4: Position the node at (x_offset, y_offset)
                element.move(x_offset, y_offset)
                
                # Increase vertical offset for next node in this level
                y_offset += element.height + margin_y
            
            # Increase horizontal offset for next column
            x_offset += element.width + margin_x

    def calculate_level(self, element):
        # Base case: If node has no dependencies, it belongs to level 0
        if element.dependencies() == []:
            return 0
        
        # Otherwise, it's 1 level greater than the max level of its dependencies
        return 1 + max(self.calculate_level(input) for input in element.dependencies())