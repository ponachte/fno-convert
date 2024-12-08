from semantexe.descriptors import Descriptor
from semantexe.graph import ExecutableGraph

DD_DOCKERFILE = "docker_examples/data-driven/Dockerfile"
SIMPLE_DOCKERFILE = "docker_examples/simple/Dockerfile"
PY_FILE = "python_examples/for_loop.py"

if __name__ == "__main__":
  
  g = ExecutableGraph()
  descriptor = Descriptor()
  s = descriptor.describe(g, SIMPLE_DOCKERFILE)
  print(g.serialize(format='ttl'))