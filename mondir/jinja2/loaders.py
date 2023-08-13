from collections.abc import Callable

from jinja2 import BaseLoader, Environment, TemplateNotFound


class FilenameDictLoader(BaseLoader):
    """
    Like :class:`~jinja2.class.DictLoader`, but returns dict keys as filenames.

    Mainly useful for testing.
    """

    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping

    def get_source(
        self, environment: Environment, template: str
    ) -> tuple[str, str, Callable[[], bool]]:
        if template not in self.mapping:
            raise TemplateNotFound(template)
        return (
            (source := self.mapping[template]),
            template,
            lambda: source == self.mapping.get(template),
        )

    def list_templates(self) -> list[str]:
        return sorted(self.mapping.keys())
