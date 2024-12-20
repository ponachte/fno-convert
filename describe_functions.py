from semantexe.descriptors.python import PythonDescriptor
from semantexe.graph import ExecutableGraph

DD_DOCKERFILE = "docker_examples/data-driven/Dockerfile"
SIMPLE_DOCKERFILE = "docker_examples/simple/Dockerfile"
PY_FILE = "python_examples/for_loop.py"

def simple_sum(a: int, b: int):
    return a + b

def triple_sum(a: int, b: int, c: int):
    return simple_sum(a, simple_sum(b, c))

def divide(numerator: int, denominator: int):
    if denominator > 0:
        return numerator / denominator
    else:
        return "niet delen door 0!"

if __name__ == "__main__":
  
  g = ExecutableGraph()
  descriptor = PythonDescriptor(g)
  s = descriptor.from_object(divide)
  g.serialize(destination="graphs/divide.ttl", format='ttl')