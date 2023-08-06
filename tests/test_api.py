from textwrap import dedent

from parametrization import pytest

from fisyte.api import DirTemplate


def test_basic_rendering(tmp_path):
    DirTemplate(
        "examples/many-modules-1",
    ).render(
        tmp_path,
        modules=[
            {
                "module_name": "greeter",
                "module_name_camelcase": "Greeter",
                "module_author": "The Dayman",
                "module_version": "0.1",
            },
            {
                "module_name": "goodbyer",
                "module_name_camelcase": "GoodByer",
                "module_author": "The Nightman",
                "module_version": "0.2",
            },
        ],
    )
    assert (tmp_path / "greeter.py").read_text() == dedent(
        """\
        import sys

        __author__ = "The Dayman"
        __version__ = "0.1"

        class GreeterRunner:
          def run(self):
            print("Hello from greeter!")
        """
    )
    assert (tmp_path / "goodbyer.py").read_text() == dedent(
        """\
        import sys

        __author__ = "The Nightman"
        __version__ = "0.2"

        class GoodByerRunner:
          def run(self):
            print("Hello from goodbyer!")
        """
    )
    assert len(list(tmp_path.iterdir())) == 2  # ensure no other files present


def test_overwrite_protection(tmp_path):
    t = DirTemplate("examples/many-modules-1")
    t.render(tmp_path, modules=[{"module_name": "greeter"}])
    with pytest.raises(FileExistsError):
        t.render(tmp_path, modules=[{"module_name": "greeter"}])
