"""Setup script for neuralux-common package."""

from setuptools import find_packages, setup

setup(
    name="neuralux-common",
    version="0.1.0",
    description="Common utilities for Neuralux AI Layer",
    author="Neuralux Team",
    packages=find_packages(),
    install_requires=[
        "nats-py>=2.7.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "structlog>=24.1.0",
    ],
    python_requires=">=3.10",
)

