from dockerfile_parse import DockerfileParser

class DockerDescriptor:
    
    def __init__(self) -> None:
        self.parser = DockerfileParser()
        self.f_counter = {}
    
    def from_dir(self, path):
        self.parser.dockerfile_path = path
        print(self.parser.structure)
    
    def handle_inst(self, inst):
        if inst['instruction'] == 'FROM':
            self.handle_from(inst['value'])
    
    def handle_from(self, value):
        instruction = 'from'