from py2rdf.describe.comp_descriptor import CompositionDescriptor
from py2rdf.execute.executeable import Function

def n_sum(n: int):
    total = 0
    for i in range(n):
        total += i
    return total

if __name__ == "__main__":
  g, s = CompositionDescriptor().from_function(n_sum)
  exe = Function(g, s)
  exe["n"].set_value(5)
  exe.execute()
  print(f"output: {exe.output.value}")