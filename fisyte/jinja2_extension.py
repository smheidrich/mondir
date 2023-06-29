from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import cast

from jinja2 import Environment, TemplateSyntaxError
from jinja2.ext import Extension
from jinja2.lexer import Token, TokenStream
from jinja2.nodes import CallBlock, Const, For, Name, Node, OverlayScope
from jinja2.parser import Parser

from .utils.jinja2 import SingleTagExtension


@dataclass
class FisyteData:
    # parsing
    file_contents_receptacles: list[list[Node]] = field(default_factory=list)
    dir_level_body: list[Node] = field(default_factory=list)
    actual_filename: list[Node] = field(default_factory=list)
    # output
    rendered_filenames: list[str] = field(default_factory=list)
    rendered_contents: list[str] = field(default_factory=list)
    "Mapping from filenames to rendered content"

    @property
    def rendered_files(self) -> dict[str, str]:
        n_filenames = len(self.rendered_filenames)
        n_contents = len(self.rendered_contents)
        if n_filenames != n_contents:
            raise RuntimeError(
                f"number of rendered filenames ({n_filenames}) does not match "
                f"number of rendered contents ({n_contents}), which should "
                "never happen - please report this as a bug"
            )
        return {
            filename: contents
            for filename, contents in zip(
                self.rendered_filenames, self.rendered_contents
            )
        }


# make Mypy happy:
class ExtendedEnvironment(Environment):
    fisyte: FisyteData


class ExtensionWithFileContentsCallback(Extension):
    """
    Base for extensions that need to create call blocks calling _file_contents.
    """

    # make Mypy happy:
    environment: ExtendedEnvironment

    def _make_file_callback_nodes(
        self,
        filename_template: list[Node],
        file_contents_receptacle: list[Node],
    ) -> list[CallBlock]:
        return [
            self._make_filename_call_block(filename_template),
            self._make_file_contents_call_block(file_contents_receptacle),
        ]

    # this doesn't need a receptacle because we know the filename template
    # either from the start (based on the actual filename) or at the point of
    # parsing the thisfile instruction (based on custom template there)
    def _make_filename_call_block(
        self, filename_template: list[Node]
    ) -> CallBlock:
        return CallBlock(
            self.call_method("_filename"),
            [],
            [],
            filename_template,
        )

    def _make_file_contents_call_block(
        self, file_contents_receptacle: list[Node]
    ) -> CallBlock:
        return CallBlock(
            self.call_method("_file_contents"),
            [],
            [],
            file_contents_receptacle,
        )

    def _filename(self, caller: Callable[..., str]) -> str:
        output = caller()
        self.environment.fisyte.rendered_filenames.append(output)
        return f"----- file: {output} -----\n"

    def _file_contents(self, caller: Callable[..., str]) -> str:
        output = caller()
        self.environment.fisyte.rendered_contents.append(output)
        return output + "\n"


class ThisfileExtension(ExtensionWithFileContentsCallback, SingleTagExtension):
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
        file_callback_nodes = self._make_file_callback_nodes(
            self.environment.fisyte.actual_filename, file_contents_receptacle
        )

        # next we either have "for" signifying of an inline for loop...
        if parser.stream.skip_if("name:for"):
            dir_level_body_parts = self.parse_for(parser, file_callback_nodes)
        # ... or else just the end of the tag (nothing to parse)
        else:
            dir_level_body_parts = cast(list[Node], file_callback_nodes)

        self.environment.fisyte.file_contents_receptacles.append(
            file_contents_receptacle
        )

        # we need to make sure the dir-level subtree is stored outside the
        # template AST so that the latter contains the contents only
        if any(tag == "dirlevel" for tag in parser._tag_stack):
            # if we're already inside dirlevel tags, we have them handle this
            return dir_level_body_parts
        else:
            # if we're not, we have to do it ourselves
            self.environment.fisyte.dir_level_body.extend(dir_level_body_parts)
            return []

    def parse_for(
        self, parser: Parser, file_callback_nodes: list[CallBlock]
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
        loop_body = cast(list[Node], file_callback_nodes)
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


class ActualFilenameExtension(
    ExtensionWithFileContentsCallback, SingleTagExtension
):
    """
    For internal use only for now.

    Used for processing the filename of the actual file, which is inserted into
    the template at the string level so that it can be rendered according to
    Jinja's rules, replacing variables and expressions etc.
    """

    tag = "thisfileactualfilename"

    # make Mypy happy:
    environment: ExtendedEnvironment

    def __init__(self, environment: Environment):
        super().__init__(environment)

        # storage of things we parse from extension blocks
        environment.extend(fisyte=FisyteData())

    def preprocess(self, source, name, filename=None) -> str:
        if filename is None:
            raise ValueError(
                "for now, fisyte only works with templates that have filenames"
            )
        # put filename tag at the beginning so it can be tokenized, parsed, and
        # processed as a Jinja template:
        block_start = self.environment.block_start_string
        block_end = self.environment.block_end_string
        return (
            f"{block_start}{self.tag}{block_end}"
            f"{filename}"
            f"{block_start}end{self.tag}{block_end}"
            f"{source}"
        )

    def parse(self, parser: Parser) -> Node | list[Node]:
        # first token is always our tag name, just sanity check & get lineno:
        parser.stream.expect(f"name:{self.tag}")

        # parse body
        body = parser.parse_statements(
            (f"name:end{self.tag}",), drop_needle=True
        )

        # save body for later
        assert not self.environment.fisyte.actual_filename
        self.environment.fisyte.actual_filename.extend(body)

        # return nothing because the only purpose of this is to capture the
        # filename
        return []


class DirLevelExtension(SingleTagExtension):
    tag = "dirlevel"

    # make Mypy happy:
    environment: ExtendedEnvironment

    def __init__(self, environment: Environment):
        super().__init__(environment)

        # storage of things we parse from extension blocks
        environment.extend(fisyte=FisyteData())

    def parse(self, parser: Parser) -> Node | list[Node]:
        # first token is always our tag name, just sanity check & get lineno:
        parser.stream.expect(f"name:{self.tag}")

        # parse body
        body = parser.parse_statements(
            (f"name:end{self.tag}",), drop_needle=True
        )

        # save body for later
        self.environment.fisyte.dir_level_body.extend(body)

        # return nothing at this point, as dirlevel contents are inserted into
        # the AST at a later stage by EnclosingExtension
        return []


class EnclosingExtension(
    ExtensionWithFileContentsCallback, SingleTagExtension
):
    """
    For internal use only.

    Encloses the whole file contents in a block so that we can capture them at
    the parsing stage.
    """

    tag = "thisfilefileencl"

    # make Mypy happy:
    environment: ExtendedEnvironment

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

        # if there was no thisfile or dirlevel tag, insert a default one
        if not (
            self.environment.fisyte.dir_level_body
            or self.environment.fisyte.file_contents_receptacles
        ):
            # TODO refactor with same code in ThisfileExtension? difficult...
            file_contents_receptacle: list[Node] = []
            file_callback_nodes = self._make_file_callback_nodes(
                self.environment.fisyte.actual_filename,
                file_contents_receptacle,
            )
            self.environment.fisyte.file_contents_receptacles.append(
                file_contents_receptacle
            )
            self.environment.fisyte.dir_level_body.extend(file_callback_nodes)

        # insert this into file contents receptacles
        for receptacle in self.environment.fisyte.file_contents_receptacles:
            receptacle.extend(body)

        # re-insert dir-level block in place of regular file contents
        return self.environment.fisyte.dir_level_body


extensions = [
    ActualFilenameExtension,
    ThisfileExtension,
    DirLevelExtension,
    EnclosingExtension,
]
