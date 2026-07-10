"""Sandboxed DocEX environment for extraction integration tests.

DOCEX_HOME is pointed at a temporary directory before docex is imported, so
these tests never touch a real ~/.docex configuration or database.
"""

import os
import tempfile
from pathlib import Path

import pytest

_SANDBOX = Path(tempfile.mkdtemp(prefix='docex_extraction_tests_'))
os.environ['DOCEX_HOME'] = str(_SANDBOX)


@pytest.fixture(scope='session')
def docex_instance():
    from docex import DocEX

    DocEX.setup(
        database={'type': 'sqlite', 'sqlite': {'path': str(_SANDBOX / 'docex.db')}},
        storage={'type': 'filesystem', 'filesystem': {'path': str(_SANDBOX / 'storage')}},
    )
    return DocEX()


@pytest.fixture(scope='session')
def basket(docex_instance):
    return docex_instance.basket('extraction_test_basket')
