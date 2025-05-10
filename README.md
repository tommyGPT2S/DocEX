# DocFlow

<!-- Badges -->
![License](https://img.shields.io/github/license/tommyGPT2S/DocFlow)
![Python](https://img.shields.io/pypi/pyversions/docflow)
![Build](https://github.com/tommyGPT2S/DocFlow/actions/workflows/ci.yml/badge.svg)
<!-- Add PyPI badge here when ready -->

![DocFlow Architecture](docs/New%20Era%20of%20Supply%20Chain/image.png)

**DocFlow** is a robust, extensible document management and transport system for Python. It supports multiple storage backends, metadata management, and operation tracking, with a unified API for local, SFTP, HTTP, and other protocols.

## Features

- 📁 Document storage and metadata management
- 🔄 Transport layer with pluggable protocols (local, SFTP, HTTP, etc.)
- 🛣️ Configurable transport routes and routing rules
- 📝 Operation and audit tracking
- 🧩 Extensible architecture for new protocols and workflows

## Installation

Install from PyPI:

```sh
pip install pydocflow
```

If you want to use PDF processing features (e.g., custom PDF processors), also install:

```sh
pip install pdfminer.six
```

## Quick Start

Before using DocFlow in your code, you must initialize the system using the CLI:

```sh
# Run this once to set up configuration and database
$ docflow init
```

Then you can use the Python API (minimal example):

```python
from docflow import DocFlow
from pathlib import Path

# Create DocFlow instance (will check initialization internally)
docflow = DocFlow()

# Create a basket
basket = docflow.basket('mybasket')

# Create a simple text file
hello_file = Path('hello.txt')
hello_file.write_text('Hello scos.ai!')

# Add the document to the basket
doc = basket.add(str(hello_file))

# Print document details
print(doc.get_details())

hello_file.unlink()
```
Additional examples can be found in examples/ folder.

## Configuration

Configure routes and storage in `default_config.yaml`:

```yaml
transport_config:
  routes:
    - name: local_backup
      purpose: backup
      protocol: local
      config:
        type: local
        name: local_backup_transport
        base_path: /path/to/backup
        create_dirs: true
      can_upload: true
      can_download: true
      enabled: true
  default_route: local_backup
```

## Documentation

- [Developer Guide](docs/Developer_Guide.md)
- [Design Document](docs/DocFlow%20Design.md)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT License](LICENSE)
