import tkinter as tk
from tkinter import font
from abc import ABC, abstractmethod

class Mappable(ABC):

    def __init__(self, name: str, canvas: tk.Canvas, dependency):
        self.name = name
        self.canvas = canvas
        self.dependency = dependency
        self.mappings = {}
        self.depends_on = []

    @abstractmethod
    def source_point(self):
        pass

    @abstractmethod
    def target_point(self):
        pass

    def map_to(self, target: "Mappable"):
        mapping = Mapping(self.canvas, self, target)
        self.mappings[target.name] = mapping
        target.mappings[self.name] = mapping
        target.depends_on.append(self.dependency)

class Terminal(Mappable):

    def __init__(self, canvas: tk.Canvas, name: str, node, x0: float, y0: float, *, 
                 is_output=False, textfont=None) -> None:
        super().__init__(name, canvas, node)
        self.font = textfont if textfont is not None else font.Font(family="helvetica", size=10)
        self.is_output = is_output

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
    
    def move(self, new_x0, new_y0):
        self.canvas.coords(self.square, new_x0, new_y0, new_x0 + 10, new_y0 + 10)
        if self.is_output:
            self.canvas.coords(self.text, new_x0 - 10, new_y0 + 5)
        else:    
            self.canvas.coords(self.text, new_x0 + 20, new_y0 + 5)
        
        for mapping in self.mappings.values():
            mapping.update()
    
    def source_point(self):
        # Get the bounding box of source rectangle
        _, y0, x1, y1 = self.canvas.coords(self.square)
        # Middle of the right side of the source rectangle
        return (x1, (y0 + y1) / 2)
    
    def target_point(self):
        # Get the bounding box of target rectangle
        x0, y0, _, y1 = self.canvas.coords(self.square)
        # Middle of the left side of the target rectangle
        return (x0, (y0 + y1) / 2)
    
    def text_width(self):
        return self.font.measure(self.text)

class Variable(Mappable):

    def __init__(self, canvas: tk.Canvas, name: str, x: float = 0, y: float = 0) -> None:
        super().__init__(name, canvas, self)
        
        self.radius = 30
        self.width = self.height = 2 * self.radius

        self.circle = canvas.create_oval(x - self.radius, y - self.radius, x + self.radius, y + self.radius, 
                                         outline="black", width=2, fill="gray")
        
        name_font = font.Font(family='helvetica', size=12, weight='bold')
        self.text = self.canvas.create_text(x, y, text=name, font=name_font, fill='black')
        
        self.canvas.tag_bind(self.circle, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.circle, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.circle, "<ButtonRelease-1>", self.on_release)
        self.canvas.tag_bind(self.text, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.text, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.text, "<ButtonRelease-1>", self.on_release)
    
    def move(self, new_x0, new_y0):
        new_x1 = new_x0 + self.radius * 2
        new_y1 = new_y0 + self.radius * 2

        # Move the circle to the new position
        self.canvas.coords(self.circle, new_x0, new_y0, new_x1, new_y1)

        # Move the text with the circle
        self.canvas.coords(self.text, new_x0 + self.radius, new_y0 + self.radius)
            
        for mapping in self.mappings.values():
            mapping.update()
    
    def dependencies(self):
        return self.depends_on

    def on_click(self, event):
        """Start dragging when the circle is clicked."""
        self.dragging = True
        x0, y0, _, _ = self.canvas.coords(self.circle)
        self.offset_x = event.x - x0
        self.offset_y = event.y - y0

    def on_drag(self, event):
        """Update the position of the rectangle and its components while dragging."""
        if self.dragging:
            # Calculate the new coordinates for the rectangle
            new_x0 = event.x - self.offset_x
            new_y0 = event.y - self.offset_y
            self.move(new_x0, new_y0)
            
    def on_release(self, event):
        """Stop dragging when the mouse button is released."""
        self.dragging = False

    def source_point(self):
        _, _, x1, y1 = self.canvas.coords(self.circle)
        return(x1, y1 - self.radius)
    
    def target_point(self):
        x0, y0, _, _ = self.canvas.coords(self.circle)
        return(x0, y0 + self.radius)

class Mapping:

    def __init__(self, canvas: tk.Canvas, source: Mappable, target: Mappable) -> None:
        self.canvas = canvas
        self.source = source
        self.target = target

        source_point = source.source_point()
        target_point = target.target_point()

        # Draw a line between the source and target points
        self.line = self.canvas.create_line(source_point, target_point, arrow=tk.LAST, fill="black", width=2)
    
    def update(self):
        source_point = self.source.source_point()
        target_point = self.target.target_point()

        # Draw a line between the source and target points
        self.canvas.coords(self.line, source_point, target_point)