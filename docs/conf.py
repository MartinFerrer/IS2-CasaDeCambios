# Configuration file for the Sphinx documentation builder.


import os
import sys

# Add the project's source code directory to the path so Sphinx can find it.
# The 'docs' directory is one level deep, so we go up one level ('..') and
# then into the 'app' directory.
sys.path.insert(0, os.path.abspath('../app'))

# -- Project information -----------------------------------------------------


project = 'IS2-CasaDeCambios'
copyright = '2025, Equipo 4'
author = "Martín Ferrer, Fabrizio Daisuke Kawabata Miyamoto, Atilio Sebastián Paredes Pérez, Ian Alexander Torres Marecos, Lucas Daniel Lamas Lezcano"
release = '0.1.0'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    # Enables automatic documentation from docstrings.
    'sphinx.ext.autodoc',
    # Adds support for Google-style docstrings. This is a key requirement from your teammate.
    'sphinx.ext.napoleon',
    # Automatically links Python type hints in the documentation.
    'sphinx_autodoc_typehints',
    # A modern and clean-looking theme for the documentation.
    'sphinx_rtd_theme',
]

#set manually the doc language to spanish
language = 'es'

# Set the source file suffixes to allow for reStructuredText (.rst) and Markdown (.md).
# This is optional but can be useful.
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# The master toctree document.
master_doc = 'index'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# The theme to use for HTML and HTML Help pages.
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files.
html_static_path = ['_static']
