from examples.example_functions import *
from examples.cycle_problem import *
from src.py2rdf.describe.flow_descriptor import FlowDescriptor
from src.py2rdf.visualize import App
import tkinter as tk

import tkinter as tk

def list_fonts():
    root = tk.Tk()
    fonts = root.tk.call("font", "families")
    print("Available fonts:", fonts)
    root.destroy()

if __name__ == "__main__":
    list_fonts()
    root = tk.Tk()
    app = App(root)
    root.mainloop()