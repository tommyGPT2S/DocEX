"""Sandboxed DocEX environment for batch ingestion tests.

DOCEX_HOME is pointed at a temporary directory before docex is imported, so
these tests never touch a real ~/.docex configuration or database.
"""

import os
import tempfile
from pathlib import Path

import pytest

_SANDBOX = Path(tempfile.mkdtemp(prefix='docex_batch_tests_'))
os.environ.setdefault('DOCEX_HOME', str(_SANDBOX))


@pytest.fixture(scope='session')
def docex_instance():
    home = Path(os.environ['DOCEX_HOME'])
    from docex import DocEX

    DocEX.setup(
        database={'type': 'sqlite', 'sqlite': {'path': str(home / 'docex.db')}},
        storage={'type': 'filesystem', 'filesystem': {'path': str(home / 'storage')}},
    )
    return DocEX()
