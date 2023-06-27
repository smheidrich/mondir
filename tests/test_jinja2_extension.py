from textwrap import dedent

from jinja2 import Environment
from jinja2.nodes import (
    Call,
    CallBlock,
    ExtensionAttribute,
    Filter,
    For,
    Name,
    Output,
    OverlayScope,
    TemplateData,
)

from fisyte.jinja2_extension import (
    ActualFilenameExtension,
    DirLevelExtension,
    FisyteData,
    ThisfileExtension,
    extensions,
)
from fisyte.jinja2_loaders import FilenameDictLoader

from .utils.parametrization import autodetect_parameters, case


def filename_dict_loader_environment(mapping, extensions=extensions):
    """
    Create a fisyte environment using the `FilenameDictLoader` template loader.

    Defaults to using all fisyte extensions loaded but this can be overridden
    via the `extensions` parameter.
    """
    loader = FilenameDictLoader(mapping)
    return Environment(loader=loader, extensions=extensions)


def test_parsing_and_storing_ast():
    """
    Test that the parser produces the desired AST.
    """
    # prepare
    environment = filename_dict_loader_environment(
        {
            "myfile": "{% for x in i %}{% endfor %}"
            "{% thisfile for * in files|reverse %}foo"
        },
        # rendering is not tested here so we don't need all extensions
        extensions=[
            ActualFilenameExtension,
            ThisfileExtension,
            DirLevelExtension,
        ],
    )
    # run
    t = environment.get_template("myfile")
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
                                        "_filename",
                                    ),
                                    [],
                                    [],
                                    None,
                                    None,
                                ),
                                [],
                                [],
                                [Output([TemplateData("myfile")])],
                            ),
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
                            ),
                        ],
                    )
                ],
                None,
                None,
                False,
            )
        ],
        actual_filename=[Output([TemplateData("myfile")])],
        rendered_filenames=[],
        rendered_contents=[],
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
def test_render_different_ways(source):
    """
    Test different ways of rendering the same text.
    """
    # prepare
    environment = filename_dict_loader_environment({"{{ x }}.txt": source})
    # run
    t = environment.get_template("{{ x }}.txt")
    rendered = t.render()
    # check
    assert t.environment.fisyte.rendered_files == {
        "a.txt": "x: a",
        "b.txt": "x: b",
    }
    assert rendered == dedent(
        """\
        if you see this text, you might be using this library wrong:
        as a single template can correspond to multiple output files,
        rendering templates as usual doesn't make a lot of sense
        ----- file: a.txt -----
        x: a
        ----- file: b.txt -----
        x: b
        """
    )


def test_render_static():
    """
    Test that rendering files without any extension tags works too.
    """
    # prepare
    source = "x: a"
    environment = filename_dict_loader_environment({"myfile": source})
    # run
    t = environment.get_template("myfile")
    rendered = t.render()
    # check
    assert t.environment.fisyte.rendered_files == {"myfile": "x: a"}
    assert rendered == dedent(
        """\
        if you see this text, you might be using this library wrong:
        as a single template can correspond to multiple output files,
        rendering templates as usual doesn't make a lot of sense
        ----- file: myfile -----
        x: a
        """
    )
