#!/usr/bin/env python
"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

__author__ = 'Magnus Knutas'
VERSION = '1.3.2'

with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = [
    'asyncssh'
]

tests_require = [
    'pytest',
    'pytest-cov',
    'pytest-mock',
    'pytest-asyncio'
]

extras_require = {
    'dev': ['check-manifest'],
}

setup(
    name='aioasuswrt',
    version=VERSION,
    description='Api wrapper for Asuswrt https://www.asus.com/ASUSWRT/',
    setup_requires=['pytest-runner'],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/kennedyshead/aioasuswrt',
    download_url='https://github.com/kennedyshead/aioasuswrt/archive/%s.tar.gz' % VERSION,
    author=__author__,
    author_email='magnusknutas@gmail.com',
    license="MIT",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    keywords='Asuswrt wrapper',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=install_requires,
    test_suite='tests',
    tests_require=tests_require,
    extras_require=extras_require,
)
