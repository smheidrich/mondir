from dataclasses import dataclass
from jinja2 import nodes, TemplateSyntaxError
from jinja2.ext import Extension
from jinja2.lexer import TokenStream, Token
from jinja2.nodes import Const
from typing import Iterable


@dataclass
class ThisfileOpts:
    assignment_target: str
    source_iterable: str


class ThisfileExtension(Extension):
    tags = {"thisfile"}

    def __init__(self, environment):
        super().__init__(environment)

        # storage of things we parse from extension blocks
        environment.extend(fisyte_thisfile_opts=None)

    def filter_stream(self, stream: TokenStream) -> Iterable[Token]:
        # we need to manually add block end tags because we want users to be
        # able to leave them out for convenience but jinja doesn't like that
        in_begin_block_tag = False
        required_fake_block_ends = 0
        for token in stream:
            if token.type == "block_begin":
                in_begin_block_tag = True
            elif in_begin_block_tag:
                if token.value == "thisfile":
                    required_fake_block_ends += 1
                else:
                    in_begin_block_tag = False
            yield token
        # append fake {% endthisfile %} tags at end of file:
        for _ in range(required_fake_block_ends):
            yield Token(
                token.lineno,
                "block_begin",
                self.environment.block_start_string,
            )
            yield Token(token.lineno, "name", "endthisfile")
            yield Token(
                token.lineno, "block_end", self.environment.block_end_string
            )

    def parse(self, parser):
        # token will be name token with value "thisfile". need to get lineno
        # for subsequent token creation
        lineno = next(parser.stream).lineno

        # next token must say "for"
        tok = next(parser.stream)
        assert tok.value == "for"

        # next token must say either "*" or the name of a variable to store
        # stuff into
        try:
            assignment_target = parser.parse_assign_target()
        except TemplateSyntaxError as e:
            if parser.stream.current.value != "*":
                raise TemplateSyntaxError(
                    "expected identifier or * for assignment target after "
                    "'thisfile for'",
                    parser.stream.current.lineno,
                )
            assignment_target = Const("*")
            next(parser.stream)

        # next token must say "in"
        tok = next(parser.stream)
        assert tok.value == "in"

        # next token must be the name of an iterable from which to get the
        # above variable values => store in args
        source_iterable_expr = parser.parse_expression()

        # parse up to 'endthisfile' block (because jinja doesn't allow us to
        # not do this), which is automatically inserted by the custom
        # filter_stream() impl. above
        body = parser.parse_statements(["name:endthisfile"], drop_needle=True)

        return nodes.CallBlock(
            self.call_method(
                "_thisfile_support", [assignment_target, source_iterable_expr]
            ),
            [],
            [],
            body,
        ).set_lineno(lineno)

    def _thisfile_support(
        self, assignment_target, source_iterable_expr, caller
    ):
        """Helper callback."""
        self.environment.fisyte_thisfile_opts = ThisfileOpts(
            assignment_target, source_iterable_expr
        )

        return caller()  # = body, somehow
