# Package metadata lives in pyproject.toml. This shim keeps tools that still
# invoke setup.py directly (e.g. Debian pybuild) working.
from setuptools import setup


setup()
