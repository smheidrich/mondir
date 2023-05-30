from jinja2 import Template
from jinja2.compiler import EvalContext, Frame
from jinja2_extension import ThisfileExtension  # TODO make pkg
from jinja2.nodes import For, Const

if __name__ == "__main__":
    t = Template(
        source="{% thisfile for * in files %}foo",
        extensions=[ThisfileExtension],
    )
    print(t.environment.fisyte_thisfile_opts)
    print(t.render())
    print(t.environment.fisyte_thisfile_opts)

    codegen = t.environment.code_generator_class(t.environment, "foo", "foo")
    eval_ctx = EvalContext(codegen.environment, codegen.name)
    frame = Frame(eval_ctx)
    frame.symbols.analyze_node(
        For(
            Const("dontcare"),
            t.environment.fisyte_thisfile_opts.source_iterable,
            [Const("dontcare")],
            [Const("dontcare")],
            None,
            False,
        ),
        for_branch="body",
    )
    print(frame.symbols.refs)
    codegen.visit(t.environment.fisyte_thisfile_opts.source_iterable, frame)
