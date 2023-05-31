from jinja2 import Template
from jinja2.compiler import EvalContext, Frame
from jinja2_extension import ThisfileExtension  # TODO make pkg
from jinja2.nodes import For, Const
from jinja2.idtracking import find_symbols

if __name__ == "__main__":
    t = Template(
        source="{% for x in i %}{% endfor %}{% thisfile for * in files|reverse %}foo",
        extensions=[ThisfileExtension],
    )
    # t.environment.compile(t.parse())
    print(t.environment.fisyte_thisfile_opts)
    print(t.render())
    print(t.environment.fisyte_thisfile_opts)

    codegen = t.environment.code_generator_class(t.environment, "foo", "foo")
    codegen.pull_dependencies(
        [t.environment.fisyte_thisfile_opts.source_iterable],
    )
    codegen.writeline("")
    eval_ctx = EvalContext(codegen.environment, codegen.name)
    frame = Frame(eval_ctx)
    frame.symbols = find_symbols(
        [t.environment.fisyte_thisfile_opts.source_iterable],
    )
    print("vars:")
    print(frame.symbols.refs)
    codegen.visit(t.environment.fisyte_thisfile_opts.source_iterable, frame)
    print("generated code:")
    codegen.stream.seek(0)
    print(codegen.stream.read())
