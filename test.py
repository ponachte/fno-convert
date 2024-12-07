from semantexe.descriptors.docker import DockerDescriptor
from semantexe.descriptors.python import PythonDescriptor

DD_DOCKERFILE = "/home/ponachte/projects/protego-data-driven-activity-recognition/phone_model/Dockerfile"

if __name__ == "__main__":
  
  descriptor = PythonDescriptor()
  g, s = descriptor.from_file('examples/for_loop.py')
  # descriptor = DockerDescriptor()
  # g, s = descriptor.from_file(DD_DOCKERFILE)
  print(g.serialize(format='ttl'))