from examples.example_functions import *
from examples.cycle_problem import *
from src.py2rdf.describe.flow_descriptor import FlowDescriptor
from src.py2rdf.visualize import App
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()