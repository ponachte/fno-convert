import tkinter as tk
from tkinter import font

class Terminal:

    def __init__(self, canvas: tk.Canvas, name: str, x0: float, y0: float, *, 
                 is_output=False, textfont=None) -> None:
        self.canvas = canvas
        self.name = name
        self.font = textfont if textfont is not None else font.Font(family="helvetica", size=10)
        self.is_output = is_output

        self.mappings = {}

        # Create a small black square
        self.square = self.canvas.create_rectangle(
                x0, y0, x0 + 10, y0 + 10, fill="black"
        )

        if is_output:
            # Create the text left to the square
            self.text = self.canvas.create_text(
                x0 - 20, y0 + 5, anchor="e", text=name, fill="black", font=self.font
            )
        else:
            # Create the text right to the square
            self.text = self.canvas.create_text(
                x0 + 20, y0 + 5, anchor="w", text=name, fill="black", font=self.font
            )
    
    def bind(self, tag, handler):
        self.canvas.tag_bind(self.square, tag, handler)
        self.canvas.tag_bind(self.text, tag, handler)
    
    def connect_to(self, target: "Terminal"):
        mapping = Mapping(self.canvas, self, target)
        self.mappings[target.name] = mapping
        target.mappings[self.name] = mapping
    
    def move(self, new_x0, new_y0):
        self.canvas.coords(self.square, new_x0, new_y0, new_x0 + 10, new_y0 + 10)
        if self.is_output:
            self.canvas.coords(self.text, new_x0 - 10, new_y0 + 5)
        else:    
            self.canvas.coords(self.text, new_x0 + 20, new_y0 + 5)
        
        for mapping in self.mappings.values():
            mapping.moved()
    
    def text_width(self):
        return self.font.measure(self.text)

class Mapping:

    def __init__(self, canvas: tk.Canvas, source: Terminal, target: Terminal) -> None:
        self.canvas = canvas
        self.source = source
        self.target = target

        # Get the bounding box of source rectangle
        _, y0_source, x1_source, y1_source = self.canvas.coords(self.source.square)
        # Middle of the right side of the source rectangle
        source_point = (x1_source, (y0_source + y1_source) / 2)

        # Get the bounding box of target rectangle
        x0_target, y0_target, _, y1_target = self.canvas.coords(self.target.square)
        # Middle of the left side of the target rectangle
        target_point = (x0_target, (y0_target + y1_target) / 2)

        # Draw a line between the source and target points
        self.line = self.canvas.create_line(source_point, target_point, arrow=tk.LAST, fill="black", width=2)
    
    def moved(self):
        # Get the bounding box of source rectangle
        _, y0_source, x1_source, y1_source = self.canvas.coords(self.source.square)
        # Middle of the right side of the source rectangle
        source_point = (x1_source, (y0_source + y1_source) / 2)

        # Get the bounding box of target rectangle
        x0_target, y0_target, _, y1_target = self.canvas.coords(self.target.square)
        # Middle of the left side of the target rectangle
        target_point = (x0_target, (y0_target + y1_target) / 2)

        # Draw a line between the source and target points
        self.canvas.coords(self.line, source_point, target_point)