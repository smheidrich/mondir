from textwrap import dedent

from jinja2 import Environment, Template
from jinja2.compiler import EvalContext, Frame
from jinja2.idtracking import find_symbols
from jinja2.nodes import Const, Filter, For, Name

from fisyte.jinja2_extension import (
    ThisfileExtension,
    ThisfileExtensionPhase2,
    ThisfileOpts,
)


def test_jinja2_thisfile_extension():
    # prepare
    environment = Environment(extensions=[ThisfileExtension])
    source = (
        "{% for x in i %}{% endfor %}{% thisfile for * in files|reverse %}foo"
    )
    # run
    t = environment.from_string(source)
    rendered = t.render()
    # check
    assert t.environment.fisyte_thisfile_opts == ThisfileOpts(
        assignment_target=Const("*"),
        source_iterable=Filter(
            Name("files", "load"),
            "reverse",
            [],
            [],
            None,
            None,
        ),
    )
    assert rendered == "foo"


def test_jinja2_thisfile_extension_both_phases():
    # prepare
    environment = Environment(
        extensions=[ThisfileExtension, ThisfileExtensionPhase2]
    )
    source = '{% thisfile for x in ["a", "b"]|reverse %}x: {{x}}'
    # run
    t = environment.from_string(source)
    rendered = t.render()
    # check
    assert t.environment.fisyte_outputs == ["x: b", "x: a"]
    assert rendered == dedent(
        """\
        if you see this text, you might be using this library wrong:
        as a single template can correspond to multiple output files,
        rendering templates as usual doesn't make a lot of sense
        ----- file: -----
        x: b
        ----- file: -----
        x: a
        """
    )


def test_jinja2_thisfile_extension_both_phases_star_assignment():
    # prepare
    source = '{% thisfile for * in [{"x": "a"}, {"x": "b"}] %}x: {{x}}'
    # run
    t = Template(
        source=source, extensions=[ThisfileExtension, ThisfileExtensionPhase2]
    )
    rendered = t.render()
    # check
    assert t.environment.fisyte_outputs == ["x: a", "x: b"]
    assert rendered == dedent(
        """\
        if you see this text, you might be using this library wrong:
        as a single template can correspond to multiple output files,
        rendering templates as usual doesn't make a lot of sense
        ----- file: -----
        x: a
        ----- file: -----
        x: b
        """
    )