import tkinter as tk
from tkinter import font
from .terminal import Terminal
from itertools import chain

class Node:
    
    def __init__(self, canvas: tk.Canvas, x0, y0, inputs, outputs, color="red"):
        """
        Initialize a draggable node (rectangle) on the canvas that displays a list of strings,
        each with a small black square next to it.
        
        :param canvas: The Tkinter canvas where the node is drawn.
        :param x0: X-coordinate of the top-left corner of the rectangle.
        :param y0: Y-coordinate of the top-left corner of the rectangle.
        :param width: Width of the rectangle.
        :param strings: List of strings to display inside the rectangle.
        :param color: Color of the rectangle.
        :param margin: Vertical margin between items inside the rectangle.
        """
        self.canvas = canvas
        self.x0 = x0
        self.y0 = y0
        self.inputs = inputs
        self.outputs = outputs
        self.color = color

        self.margin = 10
        self.height_per_string = 20
        self.min_width = 200
        self.width = self.min_width
        self.min_gap = 50

        self.font = font.Font(family="Helvetica", size=12)
        
        # Calculate the height based on the number of strings
        max_len = max(len(inputs), len(outputs))
        self.height = max_len * self.height_per_string + max_len * self.margin


        # Create the main rectangle for the node
        self.rect = self.canvas.create_rectangle(
            x0, y0, x0 + self.min_width, y0 + self.height, fill=color
        )
        
        # Create input terminals
        self.input_terminals = {}
        for index, name in enumerate(inputs):
            # Calculate the y position for each string and square
            y_pos = y0 + index * (self.height_per_string + self.margin) + self.margin

            # Create input terminal
            self.input_terminals[name] =Terminal(canvas, name, x0, y_pos)
        
        # Create output terminals
        self.output_terminals = {}
        for index, name in enumerate(outputs):
            # Calculate the y position for each string and square
            y_pos = y0 + index * (self.height_per_string + self.margin) + self.margin
            self.output_terminals[name] = Terminal(canvas, name, x0 + self.width - 10, y_pos, is_output=True)

        self.adjust_width()
        
        # Variables for drag and drop behavior
        self.dragging = False
        self.offset_x = 0
        self.offset_y = 0

        # Bind events for clicking and dragging
        self.canvas.tag_bind(self.rect, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.rect, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.rect, "<ButtonRelease-1>", self.on_release)

        # Ensure terminals are also draggable
        for ter in chain(self.input_terminals.values(), self.output_terminals.values()):
            ter.bind("<Button-1>", self.on_click)
            ter.bind("<B1-Motion>", self.on_drag)
            ter.bind("<ButtonRelease-1>", self.on_release)
    
    def adjust_width(self):
        # Calculate the width based on the sum of the longest texts
        left_text_max_width = max(ter.text_width() for ter in self.input_terminals.values())
        right_text_max_width = max(ter.text_width() for ter in self.output_terminals.values())

        total_required_width = left_text_max_width + self.min_gap + right_text_max_width
        self.width = max(self.min_width, total_required_width)

        self.canvas.coords(self.rect, self.x0, self.y0, self.x0 + self.width, self.y0 + self.height)

        for index, ter in enumerate(self.output_terminals.values()):
            y_offset = index * (self.height_per_string + self.margin) + self.margin
            ter.move(self.x0 + self.width - 10, self.y0 + y_offset)

    def on_click(self, event):
        """Start dragging when the rectangle or its components are clicked."""
        self.dragging = True
        rect_coords = self.canvas.coords(self.rect)
        self.offset_x = event.x - rect_coords[0]
        self.offset_y = event.y - rect_coords[1]

    def on_drag(self, event):
        """Update the position of the rectangle and its components while dragging."""
        if self.dragging:
            # Calculate the new coordinates for the rectangle
            new_x0 = event.x - self.offset_x
            new_y0 = event.y - self.offset_y
            new_x1 = new_x0 + self.width
            new_y1 = new_y0 + self.height

            # Move the rectangle to the new position
            self.canvas.coords(self.rect, new_x0, new_y0, new_x1, new_y1)

            # Move each input terminal accordingly
            for index, ter in enumerate(self.input_terminals.values()):
                # Calculate the new y position for each square and text
                y_offset = index * (self.height_per_string + self.margin) + self.margin
                ter.move(new_x0, new_y0 + y_offset)
            
            # Move each output terminal accordingly
            for index, ter in enumerate(self.output_terminals.values()):
                # Calculate the new y position for each square and text
                y_offset = index * (self.height_per_string + self.margin) + self.margin
                ter.move(new_x1 - 10, new_y0 + y_offset)

    def on_release(self, event):
        """Stop dragging when the mouse button is released."""
        self.dragging = False