from jinja2 import Template
from jinja2_extension import ThisfileExtension  # TODO make pkg

if __name__ == "__main__":
    t = Template(
        source="{% thisfile for * in files %}foo",
        extensions=[ThisfileExtension],
    )
    print(t.environment.fisyte_thisfile_opts)
    print(t.render())
    print(t.environment.fisyte_thisfile_opts)
