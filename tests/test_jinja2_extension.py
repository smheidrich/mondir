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

from fisyte.jinja2.extension import (
    ActualFilenameExtension,
    DirLevelExtension,
    FileCallbackNodes,
    FisyteData,
    ThisfileExtension,
    extensions,
)
from fisyte.jinja2.loaders import FilenameDictLoader

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
        dir_level_body=None,
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
                                        "fisyte.jinja2.extension."
                                        "ThisfileExtension",
                                        "start_rendering_file",
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
                            [],
                            [
                                CallBlock(
                                    Call(
                                        ExtensionAttribute(
                                            "fisyte.jinja2.extension."
                                            "ThisfileExtension",
                                            "set_fallback_filename",
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
                            ],
                            [
                                CallBlock(
                                    Call(
                                        ExtensionAttribute(
                                            "fisyte.jinja2.extension."
                                            "ThisfileExtension",
                                            "set_fallback_file_contents",
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
                                        "fisyte.jinja2.extension."
                                        "ThisfileExtension",
                                        "done_rendering_file",
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
@case(
    name="multiple_standalone_thisfile_static_filename_and_vars_in_with",
    template_filename="template.txt",
    source=(
        '{% thisfile with %}{% set x = "a" %}'
        "{% filename %}a.txt{% endfilename %}"
        "{% endthisfile %}"
        '{% thisfile with %}{% set x = "b" %}'
        "{% filename %}b.txt{% endfilename %}"
        "{% endthisfile %}"
        "x: {{x}}"
    ),
)
@case(
    name="multiple_standalone_thisfile_template_filename_via_vars_in_with",
    template_filename="{{ x }}.txt",
    source=(
        '{% thisfile with %}{% set x = "a" %}{% endthisfile %}'
        '{% thisfile with %}{% set x = "b" %}{% endthisfile %}'
        "x: {{x}}"
    ),
)
@case(
    name="multiple_standalone_thisfile_content_and_filename_in_with",
    template_filename="{{ x }}.txt",
    source=(
        "{% thisfile with %}{% content %}x: a{% endcontent %}"
        "{% filename %}a.txt{% endfilename %}{% endthisfile %}"
        "{% thisfile with %}{% content %}x: b{% endcontent %}"
        "{% filename %}b.txt{% endfilename %}{% endthisfile %}"
        "x: {{x}}"
    ),
)
@case(
    name="multiple_standalone_thisfile_mixed_fully_static_and_via_var_in_with",
    template_filename="{{ x }}.txt",
    source=(
        "{% thisfile with %}{% content %}x: a{% endcontent %}"
        "{% filename %}a.txt{% endfilename %}{% endthisfile %}"
        '{% thisfile with %}{% set x = "b" %}{% endthisfile %}'
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
          set fallback filename to 'myfile'
          set fallback output to:
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
          set filename to 'fn'
          set fallback filename to 'myfile'
          set fallback output to:
            hello
        done with file
        """
    )


def test_empty_dirlevel_means_no_output():
    """
    Test that empty dirlevel tags result in no output.
    """
    # prepare
    source = "{% dirlevel %}{% enddirlevel %}"
    environment = filename_dict_loader_environment({"myfile": source})
    # run
    t = environment.get_template("myfile")
    t.render()
    # check
    assert t.environment.fisyte.rendered_files_map == {}


def test_standalone_filename():
    """
    Test that standalone (i.e. top-level) filename tags work.
    """
    # prepare
    source = (
        "{% filename %}differentname{% endfilename %}"
        '{% set x = "a" %}x: {{ x }}'
    )
    environment = filename_dict_loader_environment({"myfile": source})
    # run
    t = environment.get_template("myfile")
    t.render()
    # check
    assert t.environment.fisyte.rendered_files_map == {"differentname": "x: a"}


@autodetect_parameters()
# Test that standalone filename and thisfile or dirlevel tags are mutually
# exclusive.
# This behavior might change in the future, but that should happen by a
# conscious decision, not introduction of a bug - hence this test.
@case(
    name="standalone_filename_not_possible_after_thisfile",
    source="{% thisfile %}{% filename %}fn{% endfilename %}hello",
    error="standalone filename encountered after thisfile",
)
@case(
    name="thisfile_not_possible_after_standalone_filename",
    source="{% filename %}fn{% endfilename %}{% thisfile %}hello",
    error="thisfile encountered after standalone filename",
)
@case(
    name="standalone_filename_not_possible_after_dirlevel",
    source="{% dirlevel %}{% enddirlevel %}{% filename %}fn{% endfilename %}",
    error="standalone filename encountered after dirlevel",
)
@case(
    name="dirlevel_not_possible_after_standalone_filename",
    source="{% filename %}fn{% endfilename %}{% dirlevel %}{% enddirlevel %}",
    error="dirlevel encountered after standalone filename",
)
@case(
    name="standalone_filename_inside_dirlevel",
    source=(
        "{% dirlevel %}{% thisfile %}{% filename %}fn{% endfilename %}"
        "{% enddirlevel %}hello"
    ),
    error="filename tags can't be used outside thisfile in dirlevel tags",
)
# Test that dirlevel and standalone thisfile tags preclude one another, no
# matter which comes first.
# This behavior could also change in the future if it turns out there is a
# good "natural" choice for what to do in this case.
@case(
    name="standalone_thisfile_not_possible_after_dirlevel",
    source="{% dirlevel %}{% thisfile %}{% enddirlevel %}{% thisfile %}",
    error="standalone thisfile encountered after dirlevel tags",
)
@case(
    name="dirlevel_not_possible_after_standalone_thisfile",
    source="{% thisfile %}{% dirlevel %}{% thisfile %}{% enddirlevel %}",
    error="dirlevel tags encountered after standalone thisfile",
)
def test_template_syntax_errors(source, error):
    """
    Test that various kinds of invalid usage raise exceptions.

    Grouped together in one test for DRY reasons, not necessarily because these
    cases have much to do with one another.
    """
    # prepare
    environment = filename_dict_loader_environment({"myfile": source})
    # run
    with pytest.raises(TemplateSyntaxError, match=error):
        environment.get_template("myfile")
