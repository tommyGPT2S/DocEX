from docflow.db.connection import Database
from docflow.transport.models import Route

db = Database()
with db.session() as session:
    routes = session.query(Route).all()
    print('Routes in database:')
    for route in routes:
        print(f'- {route.name}')
        print(f'  Protocol: {route.protocol}')
        print(f'  Purpose: {route.purpose}')
        print(f'  Permissions:')
        print(f'    - Upload: {route.can_upload}')
        print(f'    - Download: {route.can_download}')
        print(f'    - List: {route.can_list}')
        print(f'    - Delete: {route.can_delete}')
        print(f'  Config: {route.config}')
        print(f'  Enabled: {route.enabled}')
        print(f'  Created at: {route.created_at}')
        print(f'  Updated at: {route.updated_at}') 