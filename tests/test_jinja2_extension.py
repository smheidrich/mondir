from textwrap import dedent

import pytest
from jinja2 import Environment, TemplateSyntaxError
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
    FileCallbackNodes,
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
        dir_level_body=[],
        standalone_thisfile=[
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
                        FileCallbackNodes(
                            CallBlock(
                                Call(
                                    ExtensionAttribute(
                                        "fisyte.jinja2_extension."
                                        "ThisfileExtension",
                                        "_start_rendering_file",
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
                            CallBlock(
                                Call(
                                    ExtensionAttribute(
                                        "fisyte.jinja2_extension."
                                        "ThisfileExtension",
                                        "_done_rendering_file",
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
                        ),
                    )
                ],
                None,
                None,
                False,
            )
        ],
        actual_filename=[Output([TemplateData("myfile")])],
        rendering_file=None,
        rendered_files=[],
    )
    assert rendered == "foo"


@autodetect_parameters()
@case(
    name="inline_loop_explicit_variable",
    template_filename="{{ x }}.txt",
    source='{% thisfile for x in ["b", "a"]|reverse %}x: {{x}}',
)
@case(
    name="inline_loop_star",
    template_filename="{{ x }}.txt",
    source='{% thisfile for * in [{"x": "a"}, {"x": "b"}] %}x: {{x}}',
)
@case(
    name="inline_loop_star_filename_in_with",
    template_filename="template.txt",
    source='{% thisfile for * in [{"x": "a"}, {"x": "b"}] with %}'
    "{% filename %}{{x}}.txt{% endfilename %}{% endthisfile %}x: {{x}}",
)
@case(
    name="jinja_loop_in_dirlevel",
    template_filename="{{ x }}.txt",
    source=(
        '{% dirlevel %}{% for x in ["a", "b"] %}'
        "{% thisfile %}{% endfor %}{% enddirlevel %}x: {{x}}"
    ),
)
@case(
    name="jinja_loop_in_dirlevel_filename_in_with",
    template_filename="template.txt",
    source=(
        '{% dirlevel %}{% for x in ["a", "b"] %}'
        "{% thisfile with %}{% filename %}{{x}}.txt{% endfilename %}"
        "{% endthisfile %}{% endfor %}{% enddirlevel %}x: {{x}}"
    ),
)
@case(
    name="multiple_thisfile_in_dirlevel",
    template_filename="{{ x }}.txt",
    source=(
        "{% dirlevel %}"
        '{% set x = "a" %}{% thisfile %}'
        '{% set x = "b" %}{% thisfile %}'
        "{% enddirlevel %}"
        "x: {{x}}"
    ),
)
@case(
    name="multiple_thisfile_in_dirlevel_filename_in_with",
    template_filename="template.txt",
    source=(
        "{% dirlevel %}"
        '{% set x = "a" %}{% thisfile with %}'
        "{% filename %}{{x}}.txt{% endfilename %}"
        "{% endthisfile %}"
        '{% set x = "b" %}{% thisfile with %}'
        "{% filename %}{{x}}.txt{% endfilename %}"
        "{% endthisfile %}"
        "{% enddirlevel %}"
        "x: {{x}}"
    ),
)
@case(
    name="multiple_dirlevel_with_thisfile_static_filename_in_with",
    template_filename="template.txt",
    source=(
        '{% dirlevel %}{% set x = "a" %}{% thisfile with %}'
        "{% filename %}a.txt{% endfilename %}"
        "{% endthisfile %}{% enddirlevel %}"
        '{% dirlevel %}{% set x = "b" %}{% thisfile with %}'
        "{% filename %}b.txt{% endfilename %}"
        "{% endthisfile %}{% enddirlevel %}"
        "x: {{x}}"
    ),
)
def test_render_different_ways(template_filename, source):
    """
    Test different ways of rendering the same text.
    """
    # prepare
    environment = filename_dict_loader_environment({template_filename: source})
    # run
    t = environment.get_template(template_filename)
    t.render()
    # check
    assert t.environment.fisyte.rendered_files_map == {
        "a.txt": "x: a",
        "b.txt": "x: b",
    }


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
    assert t.environment.fisyte.rendered_files_map == {"myfile": "x: a"}
    assert rendered == dedent(
        """\
        if you see this text, you might be using this library wrong:
        as a single template can correspond to multiple output files,
        rendering templates as usual doesn't make a lot of sense.
        log of operations:
        start new file
          set filename to 'myfile'
          set output to:
            x: a
        done with file
        """
    )


def test_render_filename_using_with():
    """
    Test that specifying filenames inside thisfile ... with tags works.
    """
    # prepare
    source = """
    {% thisfile with %}{% filename %}fn{% endfilename %}{% endthisfile %}hello
    """.strip()
    environment = filename_dict_loader_environment({"myfile": source})
    # run
    t = environment.get_template("myfile")
    rendered = t.render()
    # check
    assert t.environment.fisyte.rendered_files_map == {"fn": "hello"}
    assert rendered == dedent(
        """\
        if you see this text, you might be using this library wrong:
        as a single template can correspond to multiple output files,
        rendering templates as usual doesn't make a lot of sense.
        log of operations:
        start new file
          set filename to 'myfile'
          set output to:
            hello
          set filename to 'fn'
        done with file
        """
    )


@case(
    name="no_dirlevel",
    source="{% thisfile %}{% filename %}fn{% endfilename %}hello",
)
@case(
    name="inside_dirlevel",
    source=(
        "{% dirlevel %}{% thisfile %}{% filename %}fn{% endfilename %}"
        "{% enddirlevel %}hello"
    ),
)
@case(
    name="outside_dirlevel",
    source=(
        "{% dirlevel %}{% thisfile %}{% enddirlevel %}"
        "{% filename %}fn{% endfilename %}hello"
    ),
)
def test_filename_not_allowed_outside_thisfile(source):
    """
    Test that specifying filenames outside thisfile tags is not allowed.

    This behavior might change in the future, but that should happen by a
    conscious decision, not introduction of a bug - hence this test.
    """
    # prepare
    environment = filename_dict_loader_environment({"myfile": source})
    # run
    with pytest.raises(
        TemplateSyntaxError,
        match="filename tags can only be used inside thisfile tags",
    ):
        environment.get_template("myfile")


def test_standalone_thisfile_not_possible_after_dirlevel():
    """
    Test that dirlevel tags preclude subsequent standalone thisfile tags.

    This behavior could also change in the future if it turns out there is a
    good "natural" choice for what to do in this case.
    """
    # prepare
    source = "{% dirlevel %}{% thisfile %}{% enddirlevel %}{% thisfile %}"
    environment = filename_dict_loader_environment({"myfile": source})
    # run
    with pytest.raises(
        TemplateSyntaxError,
        match="standalone thisfile encountered after dirlevel tags",
    ):
        environment.get_template("myfile")


def test_dirlevel_not_possible_after_standalone_thisfile():
    """
    Test that standalone thisfile tags preclude subsequent dirlevel tags.

    This behavior could also change in the future if it turns out there is a
    good "natural" choice for what to do in this case.
    """
    # prepare
    source = "{% thisfile %}{% dirlevel %}{% thisfile %}{% enddirlevel %}"
    environment = filename_dict_loader_environment({"myfile": source})
    # run
    with pytest.raises(
        TemplateSyntaxError,
        match="dirlevel tags encountered after standalone thisfile",
    ):
        environment.get_template("myfile")
