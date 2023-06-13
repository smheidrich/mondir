from textwrap import dedent

import pytest
from jinja2 import Environment
from jinja2.nodes import (
    Call,
    CallBlock,
    ExtensionAttribute,
    Filter,
    For,
    Name,
    OverlayScope,
)

from fisyte.jinja2_extension import (
    DirLevelExtension,
    FisyteData,
    ThisfileExtension,
    extensions,
)

from .utils.parametrization import autodetect_parameters, case


@pytest.fixture
def environment():
    """
    Environment with all fisyte extensions loaded.
    """
    yield Environment(extensions=extensions)


def test_parsing_and_storing_ast():
    """
    Test that the parser produces the desired AST.
    """
    # prepare
    # rendering is not tested so we don't need all extensions
    environment = Environment(
        extensions=[ThisfileExtension, DirLevelExtension]
    )
    source = (
        "{% for x in i %}{% endfor %}{% thisfile for * in files|reverse %}foo"
    )
    # run
    t = environment.from_string(source)
    rendered = t.render()
    # check
    assert t.environment.fisyte == FisyteData(
        file_contents_receptacles=[[]],
        dir_level_body=[
            For(
                Name("_fysite_vars", "store"),
                Filter(
                    Name("files", "load"),
                    "reverse",
                    [],
                    [],
                    None,
                    None,
                ),
                [
                    OverlayScope(
                        Name("_fysite_vars", "store"),
                        [
                            CallBlock(
                                Call(
                                    ExtensionAttribute(
                                        "fisyte.jinja2_extension."
                                        "ThisfileExtension",
                                        "_file_contents",
                                    ),
                                    [],
                                    [],
                                    None,
                                    None,
                                ),
                                [],
                                [],
                                [],
                            )
                        ],
                    )
                ],
                None,
                None,
                False,
            )
        ],
    )
    assert rendered == "foo"


@autodetect_parameters()
@case(
    name="inline_loop_explicit_variable",
    source='{% thisfile for x in ["b", "a"]|reverse %}x: {{x}}',
)
@case(
    name="inline_loop_star",
    source='{% thisfile for * in [{"x": "a"}, {"x": "b"}] %}x: {{x}}',
)
@case(
    name="jinja_loop_in_dirlevel",
    source=(
        '{% dirlevel %}{% for x in ["a", "b"] %}'
        "{% thisfile %}{% endfor %}{% enddirlevel %}x: {{x}}"
    ),
)
@case(
    name="multiple_thisfile_in_dirlevel",
    source=(
        "{% dirlevel %}"
        '{% set x = "a" %}{% thisfile %}'
        '{% set x = "b" %}{% thisfile %}'
        "{% enddirlevel %}"
        "x: {{x}}"
    ),
)
def test_render_different_ways(source, environment):
    """
    Test different ways of rendering the same text.
    """
    # run
    t = environment.from_string(source)
    rendered = t.render()
    # check
    assert t.environment.fisyte.outputs == ["x: a", "x: b"]
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


def test_render_static(environment):
    """
    Test that rendering files without any extension tags works too.
    """
    # prepare
    source = "x: a"
    # run
    t = environment.from_string(source)
    rendered = t.render()
    # check
    assert t.environment.fisyte.outputs == ["x: a"]
    assert rendered == dedent(
        """\
        if you see this text, you might be using this library wrong:
        as a single template can correspond to multiple output files,
        rendering templates as usual doesn't make a lot of sense
        ----- file: -----
        x: a
        """
    )
