from filecmp import dircmp
from importlib import resources

from parametrization import pytest

from mondir.api import DirTemplate

package_name = "mondir"


@pytest.fixture(scope="module")
def example1_dir():
    with resources.as_file(
        resources.files("mondir_resources_anchor") / "examples/greetings"
    ) as p:
        yield p


@pytest.fixture(scope="module")
def example1_expected_outputs_dir():
    with resources.as_file(
        resources.files() / "data/expected-outputs/greetings"
    ) as p:
        yield p


def test_basic_rendering(
    example1_dir, example1_expected_outputs_dir, tmp_path
):
    DirTemplate(example1_dir).render(
        tmp_path,
        greetings=[
            {"recipient": "Graham", "sender": "Eric"},
            {"recipient": "Terry", "sender": "Michael"},
        ],
    )
    comparison_result = dircmp(tmp_path, example1_expected_outputs_dir)
    assert comparison_result.left_only == []
    assert comparison_result.right_only == []
    assert comparison_result.diff_files == []
    assert comparison_result.funny_files == []


def test_overwrite_protection(example1_dir, tmp_path):
    t = DirTemplate(example1_dir)
    t.render(tmp_path, greetings=[{"sender": "John"}])
    with pytest.raises(FileExistsError):
        t.render(tmp_path, greetings=[{"sender": "John"}])
