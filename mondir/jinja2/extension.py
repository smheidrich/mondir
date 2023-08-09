from collections import deque
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import indent
from typing import cast

from jinja2 import Environment, TemplateSyntaxError
from jinja2.ext import Extension
from jinja2.lexer import Token, TokenStream
from jinja2.nodes import CallBlock, Const, For, Name, Node, OverlayScope
from jinja2.parser import Parser

from ..utils.pseudo_list import PseudoList
from .utils import SingleTagExtension


@dataclass
class RenderedFile:
    filename: str
    contents: str


@dataclass
class RenderingFile:
    """
    File for which rendering information is still being collected.

    Basically a builder (yes, like in Java) to allow gradually adding required
    parts of a `RenderedFile` without having to add `| None` to the the
    latter's attribute types.
    """

    filename: str | None = None
    fallback_filename: str | None = None
    contents: str | None = None
    fallback_contents: str | None = None

    def done(self) -> RenderedFile:
        assert (
            self.fallback_filename is not None
        ), "bug: no fallback filename specified"
        assert (
            self.fallback_contents is not None
        ), "bug: no fallback contents specified"
        if self.filename is not None:
            filename = self.filename
            # re-prepend directory, if any, of original filename
            original_filename_path = Path(self.fallback_filename)
            if len(original_filename_path.parts) > 1:
                filename = str(original_filename_path.parent / filename)
        else:
            filename = self.fallback_filename
        contents = (
            self.contents
            if self.contents is not None
            else self.fallback_contents
        )
        return RenderedFile(filename, contents)


@dataclass
class MondirData:
    # parsing
    file_contents_receptacles: list[list[Node]] = field(default_factory=list)
    # note: unlike the other two top-level callback node holders below
    # (standalone_*), this one needs a distinction between having never been
    # called (None) and having been called but without contents ([])
    dir_level_body: list[Node] | None = None
    actual_filename: list[Node] = field(default_factory=list)
    # instructions that would normally be inside other tags but are allowed
    # outside (with reduced functionality) as a shortcut
    standalone_filename: list[Node] = field(default_factory=list)
    standalone_thisfile: list[Node] = field(default_factory=list)
    # info on parsing context (only required because Jinja's _tag_stack is
    # private...)
    tag_stack: deque[str] = field(default_factory=deque)
    # collecting rendered parts
    rendering_file: RenderingFile | None = None
    # final output
    rendered_files: list[RenderedFile] = field(default_factory=list)
    "Final rendered files"

    @property
    def rendered_files_map(self) -> dict[str, str]:
        return {
            rendered.filename: rendered.contents
            for rendered in self.rendered_files
        }

    def set_actual_file_contents(self, contents: list[Node]):
        for receptacle in self.file_contents_receptacles:
            receptacle.extend(contents)


# make Mypy happy:
class ExtendedEnvironment(Environment):
    mondir: MondirData


class MondirStateExtension(Extension):
    """
    Jinja2 extension that needs access to mondir state.
    """

    # make Mypy happy:
    environment: ExtendedEnvironment

    def __init__(self, environment: Environment):
        super().__init__(environment)

        # storage of things we parse from extension blocks
        environment.extend(mondir=MondirData())

    @property
    def state(self) -> MondirData:
        """
        Shortcut to access mondir state (shorter than `environment.mondir`).
        """
        return self.environment.mondir


class MondirStateWithTagStackExtension(
    SingleTagExtension, MondirStateExtension
):
    def parse(self, parser: Parser) -> Node | list[Node]:
        self.state.tag_stack.append(self.tag)
        try:
            # first token is necessarily own tag name, get lineno & skip:
            lineno = parser.stream.expect(f"name:{self.tag}").lineno
            return self.parse_own_tag(parser, lineno)
        finally:
            self.state.tag_stack.pop()

    # should be abstract but metaclass already set by SingleTagExtension...
    def parse_own_tag(self, parser: Parser, lineno: int) -> Node | list[Node]:
        raise NotImplementedError(
            "f{self.__class__} subclasses must implement parse_own_tag()"
        )


@dataclass
class FileCallbackNodes(PseudoList):
    start: CallBlock
    'The "start file" callback node.'
    meta: list[Node]
    """
    Callback nodes responsible for setting metadata (e.g. filenames).

    Note that, confusingly, this can *also* contain file contents, namely if
    `contents` tags are used within `thisfile` tags. Maybe this needs a
    rename...
    """
    post_meta: list[Node]
    """
    Callback nodes that must run after `meta` but which likewise set metadata.

    Currently only used for the `actual_filename` template to let it access
    variables set by the `meta` nodes.
    """
    content: list[Node]
    "Callback nodes responsible for setting the rendered file contents."
    end: CallBlock
    'The "end file" callback node.'

    def __iter__(self) -> Iterator[Node]:
        yield self.start
        yield from self.meta
        yield from self.post_meta
        yield from self.content
        yield self.end

    def __len__(self) -> int:
        return 2 + len(self.meta) + len(self.post_meta) + len(self.content)

    def __getitem__(self, index_or_slice, /):
        return (
            self.start,
            *self.meta,
            *self.post_meta,
            *self.content,
            self.end,
        )[index_or_slice]

    def extend_meta(self, iterable: Iterable[Node]) -> None:
        self.meta.extend(iterable)


class ExtensionWithFileCallbacks(MondirStateExtension):
    """
    Base for extensions that need to create call blocks for setting file data.
    """

    def make_file_callback_nodes(self) -> FileCallbackNodes:
        return FileCallbackNodes(
            start=self.make_file_rendering_start_block(),
            meta=[],
            post_meta=[self.make_fallback_filename_call_block()],
            content=[self.make_fallback_file_contents_call_block()],
            end=self.make_file_rendering_done_block(),
        )

    # indiv. block creation methods

    def make_file_rendering_start_block(self) -> CallBlock:
        return self._make_method_call_block(self.start_rendering_file, [])

    def make_file_rendering_done_block(self) -> CallBlock:
        return self._make_method_call_block(self.done_rendering_file, [])

    # these don't need receptacles because we know the filename template
    # either from the start (based on the actual filename) or at the point of
    # parsing the thisfile instruction (based on custom template there)

    def make_filename_call_block(
        self, filename_template: list[Node]
    ) -> CallBlock:
        return self._make_method_call_block(
            self.set_filename, filename_template
        )

    def make_fallback_filename_call_block(self) -> CallBlock:
        return self._make_method_call_block(
            self.set_fallback_filename,
            self.state.actual_filename,
        )

    def make_file_contents_call_block(self, contents: list[Node]) -> CallBlock:
        return self._make_method_call_block(self.set_file_contents, contents)

    def make_fallback_file_contents_call_block(self) -> CallBlock:
        # receptacle that will have the actual file contents inserted once we
        # parse them at the end (we don't know them yet)...
        file_contents_receptacle: list[Node] = []
        self.state.file_contents_receptacles.append(file_contents_receptacle)
        return self._make_method_call_block(
            self.set_fallback_file_contents, file_contents_receptacle
        )

    # shortcut for creating ^

    def _make_method_call_block(
        # Callable isn't exactly right, as we only care about its __name__...
        self,
        method: Callable,
        body: list[Node],
    ) -> CallBlock:
        return CallBlock(self.call_method(method.__name__), [], [], body)

    # callbacks

    def start_rendering_file(self, caller: Callable[..., str]) -> str:
        assert (
            self.state.rendering_file is None
        ), "bug: started rendering new file before previous was done"
        self.state.rendering_file = RenderingFile()
        return "start new file\n"

    def done_rendering_file(self, caller: Callable[..., str]) -> str:
        assert (
            self.state.rendering_file is not None
        ), "bug: file rendering done callback called but no file in progress"
        self.state.rendered_files.append(self.state.rendering_file.done())
        self.state.rendering_file = None
        return "done with file\n"

    def set_filename(self, caller: Callable[..., str]) -> str:
        assert (
            self.state.rendering_file is not None
        ), "bug: filename callback called but no file in progress"
        filename = caller()
        if not filename:
            raise ValueError("empty filename encountered")
        self.state.rendering_file.filename = filename
        return f"  set filename to {filename!r}\n"

    def set_fallback_filename(self, caller: Callable[..., str]) -> str:
        assert (
            self.state.rendering_file is not None
        ), "bug: fallback filename callback called but no file in progress"
        filename = caller()
        if not filename:
            raise ValueError("empty filename encountered")
        self.state.rendering_file.fallback_filename = filename
        return f"  set fallback filename to {filename!r}\n"

    def set_file_contents(self, caller: Callable[..., str]) -> str:
        assert (
            self.state.rendering_file is not None
        ), "bug: file contents callback called but no file in progress"
        output = caller()
        self.state.rendering_file.contents = output
        return "  set output to:\n" + indent(output, "    ") + "\n"

    def set_fallback_file_contents(self, caller: Callable[..., str]) -> str:
        assert self.state.rendering_file is not None, (
            "bug: fallback file contents callback called but no file in "
            "progress"
        )
        output = caller()
        self.state.rendering_file.fallback_contents = output
        return "  set fallback output to:\n" + indent(output, "    ") + "\n"


class ThisfileExtension(
    ExtensionWithFileCallbacks, MondirStateWithTagStackExtension
):
    tag = "thisfile"

    def parse_own_tag(self, parser: Parser, lineno: int) -> Node | list[Node]:
        # check obvious usage context incompatibilities first
        if self.state.standalone_filename:
            raise TemplateSyntaxError(
                "thisfile encountered after standalone filename; "
                "for now, these are mutually exclusive",
                lineno,
            )
        if "filename" in self.state.tag_stack:
            raise TemplateSyntaxError(
                "thisfile tags encountered inside filename tags; "
                "that doesn't make any sense, so the template is invalid",
                lineno,
            )

        # nodes w/ call blocks that output the rendered file on render
        file_callback_nodes = self.make_file_callback_nodes()

        # initial tag name is already parsed, so next we either have "for"
        # signifying of an inline for loop...
        if parser.stream.skip_if("name:for"):
            dir_level_body_parts = self.parse_for(parser, file_callback_nodes)
        # ... or else just the end of the tag (nothing to parse)
        else:
            dir_level_body_parts = cast(list[Node], file_callback_nodes)

        # lastly, if the block ends in "with", it's an opening tag to further
        # thisfile-level template instructions (like setting a filename)
        if parser.stream.skip_if("name:with"):
            tag_contents = self.parse_own_body(parser)
            file_callback_nodes.extend_meta(tag_contents)

        # we need to make sure the dir-level subtree is stored outside the
        # template AST so that the latter contains the contents only
        if "dirlevel" in self.state.tag_stack:
            # if we're already inside dirlevel tags, we have them handle this
            return dir_level_body_parts
        else:
            # if we're not, we have to do it ourselves
            if self.state.dir_level_body is not None:
                raise TemplateSyntaxError(
                    "standalone thisfile encountered after dirlevel tags; "
                    "for now, these are mutually exclusive",
                    lineno,
                )
            self.state.standalone_thisfile.extend(dir_level_body_parts)
            return []

    def parse_for(
        self, parser: Parser, file_callback_nodes: list[Node]
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


class ActualFilenameExtension(ExtensionWithFileCallbacks, SingleTagExtension):
    """
    For internal use only for now.

    Used for processing the filename of the actual file, which is inserted into
    the template at the string level so that it can be rendered according to
    Jinja's rules, replacing variables and expressions etc.
    """

    tag = "thisfileactualfilename"

    def preprocess(self, source, name, filename=None) -> str:
        if filename is None:
            raise ValueError(
                "for now, mondir only works with templates that have filenames"
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
        body = self.parse_own_body(parser)

        # save body for later
        assert not self.state.actual_filename
        self.state.actual_filename.extend(body)

        # return nothing because the only purpose of this is to capture the
        # filename
        return []


class FilenameExtension(
    ExtensionWithFileCallbacks, MondirStateWithTagStackExtension
):
    """
    Allows setting the desired output filename template.
    """

    tag = "filename"

    def parse_own_tag(self, parser: Parser, lineno: int) -> Node | list[Node]:
        # parse body
        body = self.parse_own_body(parser)

        # make block with callback that sets filename
        call_block = self.make_filename_call_block(body)

        # what exactly we do with that depends on usage context:
        if "thisfile" in self.state.tag_stack:
            return call_block
        elif "dirlevel" in self.state.tag_stack:
            raise TemplateSyntaxError(
                "filename tags can't be used outside thisfile in dirlevel "
                "tags",
                lineno,
            )
        else:
            if self.state.standalone_thisfile:
                raise TemplateSyntaxError(
                    "standalone filename encountered after thisfile; "
                    "for now, these are mutually exclusive",
                    lineno,
                )
            if self.state.dir_level_body is not None:
                raise TemplateSyntaxError(
                    "standalone filename encountered after dirlevel; "
                    "for now, these are mutually exclusive",
                    lineno,
                )
            self.state.standalone_filename = [call_block]
            return []


class ContentExtension(
    ExtensionWithFileCallbacks, MondirStateWithTagStackExtension
):
    """
    Allows overriding the desired output content template.

    Only usable within `thisfile ... with` tags for now.
    """

    tag = "content"

    def parse_own_tag(self, parser: Parser, lineno: int) -> Node | list[Node]:
        # check if usage context is ok
        if "thisfile" not in parser._tag_stack:
            raise TemplateSyntaxError(
                "content tags can only be used inside thisfile tags",
                lineno,
            )

        # parse body
        body = self.parse_own_body(parser)

        # return block with callback that sets filename
        return self.make_file_contents_call_block(body)


class DirLevelExtension(MondirStateWithTagStackExtension):
    tag = "dirlevel"

    def parse_own_tag(self, parser: Parser, lineno: int) -> Node | list[Node]:
        # check obvious usage context incompatibilities first
        if self.state.standalone_thisfile:
            raise TemplateSyntaxError(
                "dirlevel tags encountered after standalone thisfile; "
                "for now, these are mutually exclusive",
                lineno,
            )
        if self.state.standalone_filename:
            raise TemplateSyntaxError(
                "dirlevel encountered after standalone filename; "
                "for now, these are mutually exclusive",
                lineno,
            )
        if "filename" in self.state.tag_stack:
            raise TemplateSyntaxError(
                "dirlevel tags encountered inside filename tags; "
                "that doesn't make any sense, so the template is invalid",
                lineno,
            )
        if "thisfile" in self.state.tag_stack:
            raise TemplateSyntaxError(
                "dirlevel tags encountered inside thisfile tags; "
                "that doesn't make any sense, so the template is invalid",
                lineno,
            )

        # parse body
        body = self.parse_own_body(parser)

        # save body for later
        if self.state.dir_level_body is None:
            self.state.dir_level_body = []
        self.state.dir_level_body.extend(body)

        # return nothing at this point, as dirlevel contents are inserted into
        # the AST at a later stage by EnclosingExtension
        return []


class EnclosingExtension(ExtensionWithFileCallbacks, SingleTagExtension):
    """
    For internal use only.

    Encloses the whole file contents in a block so that we can capture them at
    the parsing stage.
    """

    tag = "thisfilefileencl"

    def filter_stream(self, stream: TokenStream) -> Iterable[Token]:
        # short preamble to indicate this is not a normal template
        yield Token(
            0,
            "data",
            "if you see this text, you might be using this library wrong:\n"
            "as a single template can correspond to multiple output files,\n"
            "rendering templates as usual doesn't make a lot of sense.\n"
            "log of operations:\n",
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
        body = self.parse_own_body(parser)

        # if there was no dirlevel tag, insert a default one
        if self.state.dir_level_body is None:
            self.state.dir_level_body = []
            # if there was no standalone thisfile tag either, insert a default
            # one of that, too
            if not self.state.standalone_thisfile:
                file_callback_nodes = self.make_file_callback_nodes()
                if self.state.standalone_filename:
                    file_callback_nodes.extend_meta(
                        self.state.standalone_filename
                    )
                self.state.dir_level_body.extend(file_callback_nodes)
            else:
                self.state.dir_level_body.extend(
                    self.state.standalone_thisfile
                )

        # insert parsed actual file contents into file contents receptacles
        self.state.set_actual_file_contents(body)

        # re-insert dir-level block in place of regular file contents
        return self.state.dir_level_body


extensions = [
    ActualFilenameExtension,
    ThisfileExtension,
    FilenameExtension,
    ContentExtension,
    DirLevelExtension,
    EnclosingExtension,
]
