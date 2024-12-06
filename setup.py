from setuptools import setup, find_packages

setup(
    name='semantify',
    version='0.1',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    package_data={'semantify': ['*.ttl']}
)