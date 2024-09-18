import tkinter as tk
from tkinter import font

class Terminal:

    def __init__(self, canvas: tk.Canvas, name: str, x0: float, y0: float, *, 
                 is_output=False, textfont=None) -> None:
        self.canvas = canvas
        self.font = textfont if textfont is not None else font.Font(family="Helvetica", size=12)
        self.is_output = is_output

        # Create a small black square
        self.square = self.canvas.create_rectangle(
                x0, y0, x0 + 10, y0 + 10, fill="black"
        )

        if is_output:
            # Create the text left to the square
            self.text = self.canvas.create_text(
                x0 - 20, y0 + 5, anchor="e", text=name, fill="black"
            )
        else:
            # Create the text right to the square
            self.text = self.canvas.create_text(
                x0 + 20, y0 + 5, anchor="w", text=name, fill="black"
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
    
    def text_width(self):
        return self.font.measure(self.text)