"""Shared fixtures for the intake test suite."""

import asyncio

import pytest


@pytest.fixture
def run():
    """Run a coroutine to completion without requiring pytest-asyncio."""

    def _run(coro):
        return asyncio.run(coro)

    return _run
