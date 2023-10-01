from filecmp import dircmp
from importlib import resources

import pytest

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


# regression test for https://gitlab.com/smheidrich/mondir/-/issues/3


@pytest.fixture(scope="module")
def example_nested_dir():
    with resources.as_file(
        resources.files("mondir_resources_anchor") / "examples/nested"
    ) as p:
        yield p


@pytest.fixture(scope="module")
def example_nested_expected_outputs_dir():
    with resources.as_file(
        resources.files() / "data/expected-outputs/nested"
    ) as p:
        yield p


def test_nested_template_happy_path(
    example_nested_dir, example_nested_expected_outputs_dir, tmp_path
):
    DirTemplate(example_nested_dir).render(tmp_path)
    comparison_result = dircmp(tmp_path, example_nested_expected_outputs_dir)
    assert comparison_result.left_only == []
    assert comparison_result.right_only == []
    assert comparison_result.diff_files == []
    assert comparison_result.funny_files == []


def test_nested_template_overwrite_happy_path(
    example_nested_dir, example_nested_expected_outputs_dir, tmp_path
):
    DirTemplate(example_nested_dir).render(tmp_path)
    DirTemplate(example_nested_dir, overwrite=True).render(tmp_path)
    comparison_result = dircmp(tmp_path, example_nested_expected_outputs_dir)
    assert comparison_result.left_only == []
    assert comparison_result.right_only == []
    assert comparison_result.diff_files == []
    assert comparison_result.funny_files == []


def test_nested_template_overwrite_fails_if_not_set(
    example_nested_dir, example_nested_expected_outputs_dir, tmp_path
):
    DirTemplate(example_nested_dir).render(tmp_path)
    with pytest.raises(FileExistsError):
        DirTemplate(example_nested_dir).render(tmp_path)


def test_nested_template_target_dir_does_not_exist(
    example_nested_dir, example_nested_expected_outputs_dir, tmp_path
):
    t = DirTemplate(example_nested_dir)
    with pytest.raises(FileNotFoundError):
        t.render(tmp_path / "target")
