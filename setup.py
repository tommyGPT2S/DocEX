"""
Legacy setup.py - kept for compatibility.

Note: This project now uses pyproject.toml for configuration.
The version and dependencies are defined in pyproject.toml.
This file is maintained for backward compatibility only.
"""

from setuptools import setup, find_packages

# Version should match pyproject.toml
setup(
    name="docex",
    version="2.2.0",  # Must match pyproject.toml
    packages=find_packages(),
    install_requires=[
        'pdfminer.six',
        'pyyaml',
        'sqlalchemy'
    ]
)
