# Mondir

[![pipeline status](https://gitlab.com/smheidrich/mondir/badges/main/pipeline.svg?style=flat-square)](https://gitlab.com/smheidrich/mondir/-/commits/main)
[![docs](https://img.shields.io/badge/docs-online-brightgreen?style=flat-square)](https://smheidrich.gitlab.io/mondir/)
[![pypi](https://img.shields.io/pypi/v/mondir)](https://pypi.org/project/mondir/)
[![supported python versions](https://img.shields.io/pypi/pyversions/mondir)](https://pypi.org/project/mondir/)

[Jinja2](https://jinja.palletsprojects.com/) templates for whole directories /
multiple files.

## Installation

```bash
pip3 install mondir
```

## Usage

Files in the input template directory can use both normal Jinja syntax and
[syntax extensions](https://smheidrich.gitlab.io/mondir/templates.html#syntax-extensions)
introduced by Mondir. File and directory names can contain Jinja syntax, too.

For instance, to output a file for each entry in a list of names, you could
place a file named `greeting-for-{{ name }}.txt` in a directory and fill it
with:

```jinja
{% thisfile for name in names -%}
Hello {{ name }}!
```

Templating this out is as simple as this:

```python
from mondir import DirTemplate
template = DirTemplate("template_input_dir")
template.render("output_dir", names=["John", "Jane", "Alice", "Bob"])
```

A [full tutorial](https://smheidrich.gitlab.io/mondir/tutorial.html) is
available in the docs.

## Similar projects

- [dirtempl](https://pypi.org/project/dirtempl/): Same idea as this one, but
  doesn't support Jinja2 template syntax.
- [dirtemplate](https://pypi.org/project/dirtemplate/): Also the same idea
  *and* also uses Jinja2. But I only found out about it after I wrote mine and
  now the sunk cost fallacy compels me to stick with it no matter what.
- [yamldirs](https://pypi.org/project/yamldirs/) creates whole directories from
  YAML specs. While working on Mondir, I considered having a similar file
  format as an intermediate step between the templates and the final output
  (which would have made a couple of things easier to implement and would have
  had the benefit of making the output of Jinja's regular `render()`
  meaningful), but dropped the idea over performance concerns.

## Name explanation

Given that the obvious names from the "Similar projects" section were taken and
my working title (*fisyte*, for **fi**le**sy**stem **te**mplates) sounded dumb,
I stole
[how Jinja got its name](https://jinja.palletsprojects.com/en/3.1.x/faq/#why-is-it-called-jinja),
i.e. by using a word that means *temple* (because that sounds a bit like
*template*) in another language.
The first translation of *temple*
[on Wiktionary](https://en.wiktionary.org/wiki/temple#Translations) that also
contains the fragment *dir* (for *directory*) is the Bengali word *mondir*.
So that's it.

## Changelog

### 0.2.0

- `DirTemplate.render()` now raises newly introduced exceptions
  `TemplateLoadingError`, `TemplateRenderingError`, and `TemplateOutputError`
  instead of merely passing along exceptions from Jinja/Python's `os`, allowing
  users to see which files/params were responsible.
