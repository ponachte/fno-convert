from setuptools import setup, find_packages
from setuptools.command.install import install
import subprocess
import os

class ElkInstallCommand(install):
    
    def run(self):
        install.run(self)
        
        js_dir = os.path.join(os.path.dirname(__file__), "semantexe", "elk")
        
        try:
            subprocess.check_call(["npm", "install"], cwd=js_dir)
            print("✔ Node.js dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            print("⚠️ Failed to install Node.js dependencies:", e)

setup(
    name='semantexe',
    version='0.1',
    packages=find_packages(where='src'),
    cmdclass={
        'install': ElkInstallCommand
    },
    package_dir={'': 'src'},
    include_package_data=True,
    package_data={
        'semantexe/functions': ['*.ttl'],
        'semantexe': ["elk/package.json", "elk/elk_layout.js"]
    },
)