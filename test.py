from semantify.descriptors.docker import DockerDescriptor
from semantify.descriptors.python import PythonDescriptor

if __name__ == "__main__":
  # descriptor = DockerDescriptor()
  # descriptor.from_dir("/home/ponachte/projects/protego-data-driven-activity-recognition/phone_model/Dockerfile")
  
  descriptor = PythonDescriptor()
  g, s = descriptor.from_file('examples/for_loop.py')
  print(g.serialize(format='turtle'))