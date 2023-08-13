# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

from importlib import metadata

# -- Project information -----------------------------------------------------

project = "mondir"
copyright = "2023, smheidrich <smheidrich@weltenfunktion.de>"
author = "smheidrich <smheidrich@weltenfunktion.de>"

# The full version, including alpha/beta/rc tags
release = metadata.version(project)


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.intersphinx",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "insipid"

# Options for theme
html_theme_options = {
    # Insipid:
    "initial_sidebar_visibility_threshold": "60rem",
    "breadcrumbs": True,
    # Alabaster:
    # "page_width": "960px",
    # not sure:
    # 'logo': 'logo.png',
    # 'logo_name': True,
    # 'logo_text_align': 'center',
}

html_context = {
    "display_gitlab": True,
    "gitlab_user": "smheidrich",
    "gitlab_repo": project,
    "display_github": True,
    "github_user": "smheidrich",
    "github_repo": project,
}

# html_favicon = '_static/favicon.png'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Custom CSS
html_css_files = ["custom.css"]


# -- Autodoc configuration ---------------------------------------------------

# don't show argument type hints in function signature, which looks really bad
# - show in description instead
autodoc_typehints = "description"
# autodoc_default_options = {"show-inheritance": True}

# -- Intersphinx configuration -----------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "jinja2": ("https://jinja.palletsprojects.com/en/3.1.x/", None),
}

# -- Cross-referencing defaults ----------------------------------------------

# this shed doesn't flexing work: `any` doesn't work at all for some founding
# reason while `py:obj` doesn't mark methods and functions with `()` like it
# does if the role is specified explicitly. so better to just leave it off.
default_role = "any"

# Prefix autosectionlabels with document names
autosectionlabel_prefix_document = True
