from py2rdf.describe.comp_descriptor import CompositionDescriptor
from py2rdf.execute.executeable import Composition
import ast, astpretty, importlib

if __name__ == "__main__":
  # astpretty.pprint(ast.parse("str.join('', ['hey', 'hallo'])"), show_offsets=False)
  g, s = CompositionDescriptor().from_file("examples/for_loop.py")
  print(g.serialize(format="turtle"))
  exe = Composition(g, s)
  exe.execute()