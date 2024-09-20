from .flowcanvas import FlowCanvas
from ..execute.flow_executer import Flow, Terminal, Variable
from ..describe.flow_descriptor import FlowDescriptor
from tkinter import font

class App:

    def __init__(self, root, function):
        self.root = root
        self.root.title("Drag and Drop Rectangle")

        # Allow the window to be resizable
        self.root.geometry("400x400")  # Starting size of the window
        self.root.resizable(True, True)  # Make the window resizable

        self.canvas = FlowCanvas(root)
        self.graph, self.uri = FlowDescriptor(function).get_flow()
        print(self.graph.serialize(format='turtle'))
        self.flow = Flow(self.graph, self.uri)

        self.visualize_flow()

        # Bind resize event to the window to handle resizing
        self.root.bind("<Configure>", self.canvas.on_resize)
    
    def visualize_flow(self):

        ### FUNCTIONS ###

        for func in self.flow.functions.values():
            inputs = []
            outputs = []
            for term in func.terminals.values():
                (outputs if term.is_output else inputs).append(term.name)
            self.canvas.add_node(func.call_uri, func.name, 100, 100, inputs, outputs)
        
        for comp in self.flow.compositions.values():
            for mapping in comp.mappings:
                if isinstance(mapping.source, Terminal):
                    source = self.canvas.get_source_terminal(mapping.source.fun_uri, mapping.source.uri)
                else:
                    source = self.canvas.add_variable(mapping.source.name, 100, 100)
                if isinstance(mapping.target, Terminal):
                    target = self.canvas.get_target_terminal(mapping.target.fun_uri, mapping.target.uri)
                else:
                    target = self.canvas.add_variable(mapping.target.name, 100, 100)
                
                source.connect_to(target)
    
        self.canvas.layout_elements()