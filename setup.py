from setuptools import setup, find_namespace_packages

setup(
    name="OpenHands_TSB",
    version="0.1",
    packages=find_namespace_packages(include=["*"]),
    install_requires=[
        'anthropic>=0.7.0',
        'pytest>=7.0.0',
        'pytest-asyncio>=0.21.0',
        'pyyaml>=6.0.1',
        'python-dotenv>=1.0.0',
        'datasets>=3.2.0',
        'unidiff>=0.7.5',
        'gitpython>=3.1.43',
        'docker>=7.1.0'
    ]
) 