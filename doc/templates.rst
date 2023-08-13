Template reference
==================


Template directories
--------------------

Mondir can interpret any directory containing any number of files as a template
directory. Its subdirectories and their contents are recursively considered
part of the template directory as well.


Template files
--------------

All files inside template directories are treated as Mondir template files.


Template file contents
~~~~~~~~~~~~~~~~~~~~~~

Mondir's template syntax is just Jinja template syntax with a few extension
tags added (see `Syntax extensions`_).

Hence, files that don't contain any Mondir-specific instructions are rendered
the same as any Jinja template would, including being output verbatim if they
don't even contain any Jinja instructions.


Filenames / directory names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

File and directory names are treated as Jinja templates as well. This allows
you to e.g. have a file at ``books/{{ book }}/{{ section }}.txt`` and set both
``book`` and ``section`` as template arguments at render time.


Syntax extensions
-----------------

This section lists the tags with which Mondir extends Jinja's syntax.


dirlevel
~~~~~~~~

``dirlevel`` tags mark their contents for execution "outside" of the template
file itself, i.e. they contain instructions that pertain to the filesystem or
directory level (hence the name) rather than the simple string level at which
normal Jinja instructions operate.

Inside ``dirlevel`` tags, you can use any of Jinja's own control structures
like loops or conditions together with Mondir instructions like `thisfile`_ and
they will work as expected:

.. code:: jinja

    {% dirlevel %}
      {% for name in users %}
        {% if name != "admin" %}
          {% thisfile %}
        {% endif %}
      {% endfor %}
    {% enddirlevel -%}

    This is a message to user {{ name }}.

The same is not true outside of ``dirlevel`` tags. E.g. this leads to undefined
behavior:

.. code-block:: jinja
   :class: wont-work

    {% for name in users %}
      {% thisfile %}
    {% endfor -%}

    This is a message to user {{ name }}.

While certain Mondir instructions like `thisfile`_ or `filename`_ can be used
by themselves outside ``dirlevel`` tags, this should be considered a shorthand
for placing ``dirlevel`` tags immediately around them.

Note that the same restriction about placement within Jinja control structures
naturally applies to ``dirlevel`` tags themselves, so something like this leads
to undefined behavior, too:

.. code:: jinja
   :class: wont-work

   {% for name in users %}
     {% dirlevel %}
       {% thisfile %}
     {% enddirlevel %}
   {% endfor %}

Other than this prohibition on nesting within other tags, there is no
restriction on where ``dirlevel`` tags can appear in a Mondir template file.
However, it usually makes sense to put them at the very beginning so that their
effects on the file's output are visible at first glance.


thisfile
~~~~~~~~

``thisfile`` tags come in several forms, but all represent an instruction to
render the current file/template in the current context and to place its output
somewhere (read on for where exactly) in the output directory.

The natural placement of ``thisfile`` tags is within `dirlevel`_ tags.
Otherwise, they are interpreted as if surrounded by implicit ``dirlevel`` tags,
in which case the caveats on placement within other Jinja tags mentioned in
the `dirlevel`_ section apply.

Basic
^^^^^

The most basic form of ``thisfile`` is as a single, automatically closed tag
without further instructions. This corresponds to an instruction to render the
current file, using its actual filename as the template for the output
filename. E.g., given a file named ``greeting-for-{{ name }}.txt``:

.. code-block:: jinja

   {% dirlevel %}
      {% for name in names %}
         {% thisfile %}
      {% endfor %}
   {% enddirlevel -%}

   Hello {{ name }}!

Rendering this with ``names`` set to ``["Graham", "Michael"]`` will produce two
files named ``Greeting-for-Graham.txt`` and ``Greetings-for-Michael.txt``
containing ``Hello Graham!`` and ``Hello Michael!``, respectively.


thisfile with
^^^^^^^^^^^^^

To override options pertaining to file rendering such as the output filename
template, ``thisfile with`` tags can be used. In this form, the tag is no
longer self-closing and needs to be terminated with a ``endthisfile`` tag.
Inside the tags, you can use tags such as `filename`_ or `content`_ to set
the respective properties:

.. code-block:: jinja

   {% thisfile with %}
      {% filename %}other-filename.txt{% endfilename %}
   {% endthisfile %}


thisfile for ...
^^^^^^^^^^^^^^^^

Because templating out one file for each element of a sequence is a common
usage pattern, there is a shortcut for it that works similarly to Python list
comprehensions:

.. code-block:: jinja

   {% thisfile for name in names %}

This is equivalent to:

.. code-block:: jinja

   {% dirlevel %}
      {% for name in names %}
         {% thisfile %}
      {% endfor %}
   {% enddirlevel -%}

Because another common occurrence is to have a sequence of dictionaries whose
contents you want to use in your template and it is sometimes annoying to have
to refer to them via attribute access as ``some_dictionary.some_attr``, there
is a special syntax for automatically filling the local context with the
contents of the current iteration's dictionary:

.. code-block:: jinja

   {% thisfile for * in sequence_of_dicts %}


filename
~~~~~~~~

The ``filename`` tag sets the output path (relative to the output directory)
and filename. The contents of ``filename`` tags are evaluated as Jinja
templates.

Their "natural" place is within `thisfile with`_ tags:

.. code:: jinja

   {% thisfile with %}
      {% filename %}recipes/{{ recipe_name }}.txt{% endfilename %}
   {% endthisfile %}

But as a shorthand, it's also possible to use them at the top-level of a
template file, in which case they are treated as if surrounded by an implicit
``thisfile with``:

.. code:: jinja

   {% filename %}recipes/{{ recipe-name }}.txt{% endfilename -%}

   Ingredients: ...

content
~~~~~~~

The ``content`` tag can be used to set the template file's contents.

For now, they can only appear in ``thisfile with`` tags. The content will
override the template file's actual (non-dirlevel) contents.

.. code:: jinja

   {% thisfile with %}
      {% content %}This text will be used.{% endcontent %}
   {% endthisfile %}

   This text will be discarded.

There is probably no real use case for this tag in the current form and it was
mainly introduced for a planned ``file`` tag which has yet to be implemented.
