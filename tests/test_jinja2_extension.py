from textwrap import dedent

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
    DirLevelOpts,
    ThisfileExtension,
    ThisfileExtensionPhase2,
)


def test_jinja2_thisfile_extension():
    # prepare
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
    assert t.environment.fisyte_dirlevel_opts == DirLevelOpts(
        file_contents_body=[],
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


def test_jinja2_thisfile_extension_both_phases():
    # prepare
    environment = Environment(
        extensions=[
            ThisfileExtension,
            ThisfileExtensionPhase2,
            DirLevelExtension,
        ]
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
    environment = Environment(
        extensions=[
            ThisfileExtension,
            ThisfileExtensionPhase2,
            DirLevelExtension,
        ]
    )
    source = '{% thisfile for * in [{"x": "a"}, {"x": "b"}] %}x: {{x}}'
    # run
    t = environment.from_string(source)
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


def test_jinja2_thisfile_extension_both_phases_regular_loop_dirlevel():
    # prepare
    environment = Environment(
        extensions=[
            ThisfileExtension,
            ThisfileExtensionPhase2,
            DirLevelExtension,
        ]
    )
    source = (
        '{% dirlevel %}{% for x in ["a", "b"] %}'
        "{% thisfile %}{% endfor %}{% enddirlevel %}x: {{x}}"
    )
    # run
    t = environment.from_string(source)
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
