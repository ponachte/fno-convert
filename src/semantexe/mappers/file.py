import hashlib
from ..prefix import Prefix

class FileMapper:
    
    @staticmethod
    def uri(name, path):
        unique_hash = hashlib.sha256(path.encode()).hexdigest()[:8]
        return Prefix.base()[f"{name}{unique_hash}"]