"""Setup script for Laravel Reductor ML package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="laravel-reductor-ml",
    version="1.0.0",
    author="Laravel Reductor Team",
    description="ML pipeline for test redundancy detection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/laravel-reductor/ml",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "scikit-learn>=1.0.0",
        "scipy>=1.7.0",
    ],
    entry_points={
        "console_scripts": [
            "reductor-ml=ml.cli:main",
        ],
    },
)