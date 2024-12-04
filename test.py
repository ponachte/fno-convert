from py2rdf.describe.comp_descriptor import CompositionDescriptor
from py2rdf.execute.executeable import Function

if __name__ == "__main__":
  g, s = CompositionDescriptor().from_file("examples/for_loop.py")
  print(g.serialize(format="turtle"))