import os
import sys
from typing import List

from sphinx_pyproject import SphinxConfig

sys.path.insert(
    0, os.path.abspath("../..")
)  # Source code dir relative to this file

autosummary_generate = True  # Turn on sphinx.ext.autosummary

config = SphinxConfig("../../pyproject.toml", globalns=globals())
project = config.name
version = config.version
description = config.description
author = config.author
copyright = f"2025 {author}"

extensions = [
    "sphinx.ext.apidoc",
    "sphinx_autodoc_typehints",
    "sphinx.ext.autodoc",
]

apidoc_modules = [
    {
        "path": "../../aioasuswrt",
        "destination": "_apidocs",
    },
]

templates_path = ["_templates"]
exclude_patterns: List[str] = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "nature"
html_static_path = ["_static"]
