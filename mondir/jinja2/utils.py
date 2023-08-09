from collections.abc import Iterable, Set

from jaraco.classes.properties import classproperty  # type: ignore
from jinja2 import Environment
from jinja2.ext import Extension
from jinja2.lexer import Token
from jinja2.nodes import Node
from jinja2.parser import Parser


def tokens_for_tag(
    tag_name: str, lineno: int, environment: Environment
) -> Iterable[Token]:
    yield Token(
        lineno,
        "block_begin",
        environment.block_start_string,
    )
    yield Token(lineno, "name", tag_name)
    yield Token(
        lineno,
        "block_end",
        environment.block_end_string,
    )


# insane amount of effort to get around Python having removed class properties
# again... see https://discuss.python.org/t/18090
class SingleTagExtension(Extension, metaclass=classproperty.Meta):
    # must be set by subclasses (can't be abstract because not supported by
    # 3rd party classproperties lib, can't be property because Mypy doesn't get
    # it):
    tag: str

    @classproperty
    def tags(cls) -> Set[str]:
        return {cls.tag}

    def tokens_for_own_tag(self, lineno: int):
        yield from tokens_for_tag(self.tag, lineno, self.environment)

    def tokens_for_own_closing_tag(self, lineno: int):
        yield from tokens_for_tag(f"end{self.tag}", lineno, self.environment)

    def parse_own_body(self, parser: Parser) -> list[Node]:
        return parser.parse_statements(
            (f"name:end{self.tag}",), drop_needle=True
        )
