# Package metadata lives in pyproject.toml. This shim keeps tools that still
# invoke setup.py directly (e.g. Debian pybuild) working; they need
# setuptools >= 77 for the PEP 639 license fields.
from setuptools import setup


setup()
