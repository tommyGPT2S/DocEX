from setuptools import setup, find_packages

setup(
    name="docflow",
    version="0.1.0",
    description="A robust, extensible document management and transport system for Python.",
    author="Tommy Jiang",
    author_email="info@scos.ai",
    url="https://github.com/tommyGPT2S/DocFlow",
    packages=find_packages(),
    install_requires=[
        "pydantic>=1.10",
        "sqlalchemy>=1.4",
        "paramiko>=2.11",
        "aiohttp>=3.8",
        "click>=8.0.0",
        "pyyaml>=6.0.0",
        "psycopg2-binary>=2.9.0",
        "boto3>=1.26.0",
        "python-dotenv>=1.0.0",
        # Add any other dependencies here
    ],
    python_requires=">=3.8",
    include_package_data=True,
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'docflow=docflow.cli:cli',
        ],
    },
) 