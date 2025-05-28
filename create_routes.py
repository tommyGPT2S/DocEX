from docex import DocEX
from docex.db.connection import Database
from docex.transport.models import Base, Route
from docex.transport.transporter_factory import TransporterFactory
from docex.transport.local import LocalTransport
from docex.transport.config import TransportType

# Setup DocEX
DocEX.setup(
    database={'type': 'sqlite', 'sqlite': {'path': 'docex.db'}},
    storage={'type': 'filesystem', 'path': 'storage'}
)

# Initialize database and create tables
db = Database()
Base.metadata.create_all(db.get_engine())

# Create DocEX instance
docex = DocEX()

# Delete any existing routes
with db.session() as session:
    session.query(Route).delete()
    session.commit()

# Create upload route
upload_route = docex.create_route(
    name='upload_route',
    transport_type='local',
    config={'base_path': 'storage/upload', 'create_dirs': True},
    purpose='distribution',
    can_upload=True,
    can_download=False,
    can_list=False,
    can_delete=False
)

# Create download route
download_route = docex.create_route(
    name='download_route',
    transport_type='local',
    config={'base_path': 'storage/download', 'create_dirs': True},
    purpose='distribution',
    can_upload=False,
    can_download=True,
    can_list=False,
    can_delete=False
)

print('Created routes:', upload_route.name, download_route.name) 