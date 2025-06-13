from setuptools import setup, find_packages

setup(
    name="docex",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'pdfminer.six',
        'pyyaml',
        'sqlalchemy'
    ]
)
