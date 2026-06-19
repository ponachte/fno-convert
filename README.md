# FnO Function Converter

A tool to automatically semantically annotate pipelines written in Dockerfiles and/or Python files using FnO. These semantic representations allow execution to capture provenance across implementation framework using PROV-O.

[![Watch the demo video](https://github.com/user-attachments/assets/90b66d85-fc8a-45dc-9f25-c3874af953c0)](https://youtu.be/KqrxYbmYfPE)

## Installation

### Development

1. create virtual environment
```python
python -m venv <path to env folder>
```

2. activate environment
##### Linux
```bash
source <path to env folder>/bin/activate
```

##### Windows
```bash
./<path to env folder>/bin/activate.sh
```

3. install requirements
```python
pip install -r requirements.txt
```

4. install fno-convert for testing
```python
pip install -e .
```

## Usage

### Running the tool

```
python test_app.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
