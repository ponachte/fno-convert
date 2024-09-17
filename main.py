from examples.example_functions import *
from examples.cycle_problem import *
from src.py2rdf.describe.flow_descriptor import FlowDescriptor

fd = FlowDescriptor(binarycount2)

print(fd.g.serialize(format='turtle'))