.. currentmodule:: mondir


Tutorial
========

This tutorial covers Mondir's basic functionality. For reference-style
documentation on *all* features, see :ref:`reference:API reference` and
:ref:`templates:Template reference` instead.

Example setup and data
----------------------

As an unrealistic but simple usage example, let's build an "employee directory"
in which there is one text file with some data for each employee. We also want
another file containing an index listing all employees.

We can imagine that we get the list of employees from some data source but will
just hardcode it in our example scripts. This is what it might look like:

.. code:: python

   employees = [
      {"name": "John Doe", "dept": "Sales"},
      {"name": "Jane Smith", "dept": "Accounting"},
      {"name": "Andy Nobody", "dept": "Marketing"},
      {"name": "Audrey Whatchamacallit", "dept": "Administration"},
   ]


Rendering setup
---------------

To render a template directory with this data, we create an instance of
:class:`~DirTemplate`, passing the template directory (which we have yet to set
up) as a constructor argument, then call its :meth:`~DirTemplate.render`
method, providing the desired output directory as a positional argument and any
template parameters as keyword arguments:

.. code:: python

    from mondir import DirTemplate

    dir_template = DirTemplate(template_dir)

    dir_template.render(output_path, employees=employees)

Here, ``employees`` is our template parameter. Its value will be accessible
within all templates contained in ``template_dir``.


Template directory setup
------------------------

Now let's set up the template directory itself.

For the individual employee files, inside whatever directory ``template_dir``
points to, we create a file ``{{ employee.name }}.txt`` with these contents:

.. code:: jinja

   {% dirlevel %}
     {% for employee in employees %}
       {% thisfile %}
     {% endfor %}
   {% enddirlevel -%}

   Name: {{ employee.name }}
   Department: {{ employee.dept }}

The first thing you might notice is that both the filename and the file's
contents may contain Jinja template syntax, in this case expression
substitution via ``{{ ... }}``.

Next we have those non-standard Jinja tags at the beginning of the file, which
as you might have guessed are Mondir instructions.

:ref:`templates:dirlevel` tags signal that everything inside of them is not
part of the file's (template) contents but should be considered
"directory-level" instructions (hence the name), usually involving the file
itself. Inside those, we can use Jinja tags for control flow etc. as normal,
which is what we did here by iterating over our ``employees`` template
parameter with a ``for`` loop.

:ref:`templates:thisfile` means simply to render and output the current file in
the current context. In this case, this is done for each iteration, with each
iteration's ``employee`` value accessible in the rendering context.

So in our output directory we'll get 3 files ``John Doe.txt``, ``Jane
Smith.txt`` and ``Alan Nobody.txt``, each with contents like

.. code:: text

   Name: John Doe
   Department: Sales


For the employee index, we add another file ``index.txt`` with these contents:

.. code:: jinja

   {% for employee in employees %}
   - {{ employee.name }}
   {% endfor %}

This will be rendered as a simple Jinja template and placed as ``index.txt`` in
the output directory, which goes to show that the absence of ``dirlevel``
instructions means to simply render the file once and put the result in the
output directory under its original name (and path).


Shorthands
----------

Because iterating over sequences, rendering the current file for each is such a
common occurrence, Mondir comes with several shorthands that make this case
easier.


Loop shorthand
~~~~~~~~~~~~~~

The first is a shorter form of the ``for`` loop, inspired by Python's list
comprehensions. Instead of the Jinja ``for`` loop with ``thisfile`` inside
like above, we can write:

.. code:: jinja

   {% dirlevel %}
     {% thisfile for employee in employees %}
   {% enddirlevel -%}

   ...


Implicit dirlevel
~~~~~~~~~~~~~~~~~

Now that we no longer have any Jinja instructions inside our ``dirlevel`` tags,
we can just leave them out:

.. code:: jinja

   {% thisfile for employee in employees -%}

   ...

Mondir will treat such tags as being surrounded by implicit ``dirlevel`` tags.

Note that, as mentioned above, this **only** works if the statement isn't
nested inside other tags. For example, getting rid of ``dirlevel`` without
getting rid of the Jinja ``for`` loop first wouldn't work:

.. code:: jinja
   :class: wont-work

   {% for employee in employees %}
     {% thisfile %}
   {% endfor -%}

   ...

There is no proper error handling for this yet, so for now it leads to
**undefined behavior**, probably resulting in incorrect and hard to debug
output or strange error messages.


Asterisk loop variable
~~~~~~~~~~~~~~~~~~~~~~

This one might not be a pure improvement in this specific situation and has
drawbacks, but is worth mentioning anyway: Instead of always referring to
variables ``employee.name``, ``employee.dept`` etc., we could use ``*`` ("star"
/ asterisk) as our loop variable instead of ``employee``, which automatically
merges the contents of the loop variable (if it's a dictionary) into the
evaluation context, allowing us to use them directly. So after renaming the
file to just ``{{ name }}.txt``, we could change its contents to:

.. code:: jinja

   {% thisfile for * in employees -%}

   Name: {{ name }}
   Department: {{ dept }}

If overused, this can make things confusing and so it should be used with
caution.


Overriding filenames
--------------------

Let's imagine that, for some reason, we want the administrative staff to have
their employee files in a separate folder called ``admin``.

To do this, we need to set different output file paths depending on each
employee's department (``dept``). While we could put the necessary expression
in our filename, this would not only make it quite unwieldy but also wouldn't
really work, because we need to set not only the filename itself but also the
parent directory name and ``/`` is not a valid filename character.

Luckily, there is a way to override output filenames and paths relative to the
output directory from *within* the template file itself:

.. code:: jinja

   {% thisfile for employee in employees with %}
     {% if dept == "Administration" %}
       {% filename %}admin/{{ employee.name }}.txt{% endfilename %}
     {% else %}
       {% filename %}{{ employee.name }}.txt{% endfilename %}
     {% endif %}
   {% endthisfile -%}

   ...

As the example shows, ``thisfile [...] with`` tags (which, unlike regular
``thisfile`` tags, must be closed!) can be used to set certain file properties.
In this case, we set the template for the output filename (and path relative to
the output directory) using :ref:`templates:filename` tags and do so within
Jinja conditional (``if``) tags.

Note once again that the nesting order here is important: We can nest ``if``
inside ``thisfile``, but nesting ``thisfile`` in ``if`` without surrounding
``dirlevel`` tags would lead to undefined behavior as mentioned in
`Implicit dirlevel`_.
