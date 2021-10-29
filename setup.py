#!/usr/bin/env python
"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import find_packages, setup

__author__ = "Magnus Knutas"
VERSION = "1.4.0"

with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = ["asyncssh"]

extras_requires = {
    "dev": ["check-manifest"],
}

github_url = "https://github.com/kennedyshead/aioasuswrt"

setup(
    name="aioasuswrt",
    version=VERSION,
    description="Api wrapper for Asuswrt https://www.asus.com/ASUSWRT/",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=github_url,
    download_url=f"{github_url}/archive/{VERSION}.tar.gz",
    author=__author__,
    author_email="magnusknutas@gmail.com",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    keywords="Asuswrt wrapper",
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    install_requires=install_requires,
    extras_require=extras_requires,
    test_suite="tests",
)
