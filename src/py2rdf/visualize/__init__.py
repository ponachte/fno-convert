from .flowcanvas import FlowCanvas

class App:

    def __init__(self, root):
        self.root = root
        self.root.title("Drag and Drop Rectangle")

        # Allow the window to be resizable
        self.root.geometry("400x400")  # Starting size of the window
        self.root.resizable(True, True)  # Make the window resizable

        self.canvas = FlowCanvas(root)

        # Bind resize event to the window to handle resizing
        self.root.bind("<Configure>", self.canvas.on_resize)