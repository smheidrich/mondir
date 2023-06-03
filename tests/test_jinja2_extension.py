from jinja2 import Template
from jinja2.compiler import EvalContext, Frame
from jinja2.idtracking import find_symbols
from jinja2.nodes import Const, Filter, For, Name

from fisyte.jinja2_extension import ThisfileExtension, ThisfileOpts


def test_jinja2_thisfile_extension():
    # prepare
    source = (
        "{% for x in i %}{% endfor %}{% thisfile for * in files|reverse %}foo"
    )
    # run
    t = Template(source=source, extensions=[ThisfileExtension])
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
