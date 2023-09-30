from pathlib import Path


def mkdir_parents_up_to(path: Path, up_to: Path, exist_ok: bool = False):
    """
    Create every parent directory of `path` up (!) to `up_to`.

    In other words, this will fail if `up_to` itself does not exist, but
    otherwise will create every directory between it and `path`.
    """
    relative_path = path.relative_to(up_to)
    parent = up_to
    for part in relative_path.parts[:-1]:
        parent /= part
        parent.mkdir(exist_ok=exist_ok)
