from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Iterable

from jinja2 import Environment, TemplateSyntaxError
from jinja2.lexer import Token, TokenStream
from jinja2.nodes import CallBlock, Const, For, Name, Node, OverlayScope
from jinja2.parser import Parser

from .utils.jinja2 import SingleTagExtension


@dataclass
class DirLevelOpts:
    file_contents_receptacles: list[list[Node]] = field(default_factory=list)
    dir_level_body: list[Node] = field(default_factory=list)


# make Mypy happy:
class ExtendedEnvironment(Environment):
    fisyte_dirlevel_opts: DirLevelOpts
    fisyte_outputs: list[str]


class ThisfileExtension(SingleTagExtension):
    tag = "thisfile"

    # make Mypy happy:
    environment: ExtendedEnvironment

    def parse(self, parser: Parser) -> Node | list[Node]:
        # first token is necessarily 'thisfile' tag name, sanity check & skip:
        parser.stream.expect(f"name:{self.tag}")

        # prepare receptacle that will hold the (non-dirlevel) template file
        # contents once we parse them at the end (we don't know them yet)...
        file_contents_receptacle: list[Node] = []
        # ... and a call block node that will contain them => process on render
        file_contents_call_node = CallBlock(
            self.call_method("_file_contents"),
            [],
            [],
            file_contents_receptacle,
        )

        # next we either have "for" signifying of an inline for loop...
        if parser.stream.skip_if("name:for"):
            dir_level_body_parts = self.parse_for(
                parser, file_contents_call_node
            )
        # ... or else just the end of the tag (nothing to parse)
        else:
            dir_level_body_parts = [file_contents_call_node]

        self.environment.fisyte_dirlevel_opts.file_contents_receptacles.append(
            file_contents_receptacle
        )

        # we need to make sure the dir-level subtree is stored outside the
        # template AST so that the latter contains the contents only
        if any(tag == "dirlevel" for tag in parser._tag_stack):
            # if we're already inside dirlevel tags, we have them handle this
            return dir_level_body_parts
        else:
            # if we're not, we have to do it ourselves
            self.environment.fisyte_dirlevel_opts.dir_level_body.extend(
                dir_level_body_parts
            )
            return []

    def parse_for(
        self, parser: Parser, file_contents_call_node: CallBlock
    ) -> list[Node]:
        # next token(s) must be either "*" or an assignment target
        assignment_target: Node
        try:
            assignment_target = parser.parse_assign_target()
        except TemplateSyntaxError:
            if parser.stream.current.value != "*":
                raise TemplateSyntaxError(
                    "expected identifier or * for assignment target after "
                    f"'{self.tag} for'",
                    parser.stream.current.lineno,
                )
            assignment_target = Const("*")
            next(parser.stream)

        # next token must say "in"
        parser.stream.expect("name:in")

        # next tokens must be the source iterable for the for loop
        source_iterable = parser.parse_expression()

        # prepare & return parsed AST subtree
        loop_body: list[Node] = [file_contents_call_node]
        if assignment_target == Const("*"):
            assignment_target = Name("_fysite_vars", "store")
            loop_body = [OverlayScope(assignment_target, loop_body)]
        loop_node = For(
            assignment_target,
            source_iterable,
            loop_body,
            None,
            None,
            False,
        )

        return [loop_node]

    def _file_contents(self, caller: Callable[..., str]) -> str:
        output = caller()
        self.environment.fisyte_outputs.append(output)
        return "----- file: -----\n" + output + "\n"


class DirLevelExtension(SingleTagExtension):
    tag = "dirlevel"

    # make Mypy happy:
    environment: ExtendedEnvironment

    def __init__(self, environment: Environment):
        super().__init__(environment)

        # storage of things we parse from extension blocks
        environment.extend(fisyte_dirlevel_opts=DirLevelOpts())

    def parse(self, parser: Parser) -> Node | list[Node]:
        # first token is always our tag name, just sanity check & get lineno:
        parser.stream.expect(f"name:{self.tag}")

        # parse body
        body = parser.parse_statements(
            (f"name:end{self.tag}",), drop_needle=True
        )

        # save body for later
        self.environment.fisyte_dirlevel_opts.dir_level_body.extend(body)

        # return nothing at this point, as dirlevel contents are inserted into
        # the AST at a later stage by ThisfileExtensionPhase2
        return []


class ThisfileExtensionPhase2(SingleTagExtension):
    tag = "thisfilefileencl"

    # make Mypy happy:
    environment: ExtendedEnvironment

    def __init__(self, environment: Environment):
        super().__init__(environment)

        environment.extend(fisyte_outputs=[])

    def filter_stream(self, stream: TokenStream) -> Iterable[Token]:
        # short preamble to indicate this is not a normal template
        yield Token(
            0,
            "data",
            "if you see this text, you might be using this library wrong:\n"
            "as a single template can correspond to multiple output files,\n"
            "rendering templates as usual doesn't make a lot of sense\n",
        )
        # enclose entire file in tags that let us parse it
        yield from self.tokens_for_own_tag(0)
        for token in stream:
            yield token
        yield from self.tokens_for_own_closing_tag(token.lineno)

    def parse(self, parser: Parser) -> list[Node]:
        # sanity check & get line number for later
        parser.stream.expect(f"name:{self.tag}").lineno

        # parse to end (contains entire file)
        body = parser.parse_statements(
            (f"name:end{self.tag}",), drop_needle=True
        )

        # insert this into file contents receptacles
        for (
            receptacle
        ) in self.environment.fisyte_dirlevel_opts.file_contents_receptacles:
            receptacle.extend(body)

        # re-insert dir-level block in place of regular file contents
        return self.environment.fisyte_dirlevel_opts.dir_level_body
