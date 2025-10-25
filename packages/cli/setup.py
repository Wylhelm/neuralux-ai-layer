"""Setup script for aish CLI tool."""

from setuptools import find_packages, setup

setup(
    name="aish",
    version="0.1.0",
    description="AI Shell - Natural language command interface for Neuralux",
    author="Neuralux Team",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.7",
        "rich>=13.7.0",
        "prompt-toolkit>=3.0.43",
        "httpx>=0.26.0",
    ],
    entry_points={
        "console_scripts": [
            "aish=aish.main:main",
        ],
    },
    python_requires=">=3.10",
)

