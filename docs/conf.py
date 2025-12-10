project = "auntie-sounds"
copyright = "2025, Kieran Hogg"
author = "Kieran Hogg"
extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.apidoc",
    "autoapi.extension",
]
autoapi_dirs = ["../src/sounds"]
autoapi_type = "python"
autoapi_template_dir = "_templates/autoapi"
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
]

apidoc_modules = [
    {
        "path": "src/sounds/",
        "destination": "source/",
        "exclude_patterns": ["**/test*"],
        "max_depth": 4,
        "follow_links": False,
        "separate_modules": False,
        "include_private": False,
        "no_headings": False,
        "module_first": False,
        "implicit_namespaces": False,
        "automodule_options": {"members", "show-inheritance", "undoc-members"},
    },
]
intersphinx_mapping = {
    "rtd": ("https://docs.readthedocs.io/en/stable/", None),
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}
intersphinx_disabled_domains = ["std"]
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
html_theme = "alabaster"
