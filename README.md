# DocFlow

**DocFlow** is a robust, extensible document management and transport system for Python. It supports multiple storage backends, metadata management, and operation tracking, with a unified API for local, SFTP, HTTP, and other protocols.

## Features

- 📁 Document storage and metadata management
- 🔄 Transport layer with pluggable protocols (local, SFTP, HTTP, etc.)
- 🛣️ Configurable transport routes and routing rules
- 📝 Operation and audit tracking
- 🧩 Extensible architecture for new protocols and workflows

## Installation

Install directly from GitHub:

```sh
pip install git+https://github.com/tommyGPT2S/DocFlow.git
```

## Quick Start

```python
from docflow import DocFlow

# Initialize DocFlow (loads config from default_config.yaml)
docflow = DocFlow()

# List available routes
for route in docflow.list_routes():
    print(f"Route: {route.name}, Protocol: {route.protocol}, Purpose: {route.purpose}")

# Download a file
download_route = docflow.get_route("my_download_route")
result = download_route.download("remote_file.txt", "local_file.txt")
print(result.message)

# Add a document to a basket and upload
basket = docflow.create_basket("my_basket")
doc = basket.add("local_file.txt", metadata={"source": "example"})
upload_route = docflow.get_route("my_upload_route")
upload_result = upload_route.upload_document(doc)
print(upload_result.message)
```

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

- [Design Document](docs/DocFlow%20Design.md)


## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT License](LICENSE)
