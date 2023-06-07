from dataclasses import dataclass
from typing import Iterable

from jinja2 import TemplateSyntaxError, nodes
from jinja2.ext import Extension
from jinja2.lexer import Token, TokenStream
from jinja2.nodes import CallBlock, Const, For, Name, OverlayScope


# TODO move to package of its own and/or Jinja PR to allow this at parser level
class SelfClosingTagsExtension(Extension):
    """
    Base class for extensions with 0-content tags that don't need to be closed.

    All this does is insert a closing tag right after the "opening" one at the
    token level, so you can parse it as if it was closed with no content.

    Regarding "self-closing" tags:

    Jinja itself has a few such tags built in, e.g. `extends` and `include`,
    but for some reason doesn't facilitate (easily) writing extensions that
    introduce new ones...

    Alternative names for such tags (inspired by
    [what people call them in HTML](https://stackoverflow.com/q/3741896))
    could be "singleton tags", "empty tags", "void tags" or "standalone tags".
    """

    def filter_stream(self, stream: TokenStream) -> Iterable[Token]:
        # we need to manually add closing tags because Jinja's parser throws a
        # fit otherwise (see todo above)...
        stream_iter = iter(stream)
        # this looks more complicated than it is, just because I wanted to make
        # it look sequential instead of the more typical "single for loop that
        # handles multiple phases" pattern
        while True:
            for token in stream_iter:
                yield token
                if token.type == "block_begin":
                    break
            else:
                break
            assert (tag_name_token := next(stream_iter)).type == "name"
            yield tag_name_token
            tag_name = tag_name_token.value
            if tag_name not in self.tags:
                continue
            for token in stream_iter:
                yield token
                if token.type == "block_end":
                    yield Token(
                        token.lineno,
                        "block_begin",
                        self.environment.block_start_string,
                    )
                    yield Token(token.lineno, "name", f"end{tag_name}")
                    yield Token(
                        token.lineno,
                        "block_end",
                        self.environment.block_end_string,
                    )
                    break
            else:
                break
            break
        # remainder
        for token in stream_iter:
            yield token


@dataclass
class ThisfileOpts:
    assignment_target: str
    source_iterable: str


class ThisfileExtension(SelfClosingTagsExtension):
    tags = {"thisfile"}

    def __init__(self, environment):
        super().__init__(environment)

        # storage of things we parse from extension blocks
        environment.extend(fisyte_thisfile_opts=None)

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

        # parse up to closing tag automatically inserted by our base class
        body = parser.parse_statements(["name:endthisfile"], drop_needle=True)

        # save what we've found
        self.environment.fisyte_thisfile_opts = ThisfileOpts(
            assignment_target, source_iterable_expr
        )

        return body


class ThisfileExtensionPhase2(Extension):
    tags = {"thisfilefileencl"}
    priority = 200

    def __init__(self, environment):
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
        yield Token(
            0,
            "block_begin",
            self.environment.block_start_string,
        )
        yield Token(0, "name", "thisfilefileencl")
        yield Token(0, "block_end", self.environment.block_end_string)
        for token in stream:
            yield token
        yield Token(
            token.lineno,
            "block_begin",
            self.environment.block_start_string,
        )
        yield Token(token.lineno, "name", "endthisfilefileencl")
        yield Token(
            token.lineno, "block_end", self.environment.block_end_string
        )

    def parse(self, parser):
        lineno = next(parser.stream).lineno

        # parse to end
        body = parser.parse_statements(
            ["name:endthisfilefileencl"], drop_needle=True
        )

        # wrap file contents in helper method call
        top_level_node = CallBlock(
            self.call_method("_process_file_content"), [], [], body
        ).set_lineno(lineno)

        # wrap file contents in loop if thisfile was used
        opts: ThisfileOpts = self.environment.fisyte_thisfile_opts
        if opts:
            assignment_target = opts.assignment_target
            loop_body = [top_level_node]
            if assignment_target == Const("*"):
                assignment_target = Name("_fysite_vars", "store")
                loop_body = [OverlayScope(assignment_target, loop_body)]
            top_level_node = For(
                assignment_target,
                opts.source_iterable,
                loop_body,
                None,
                None,
                False,
            )

        return top_level_node

    def _process_file_content(self, caller):
        output = caller()
        self.environment.fisyte_outputs.append(output)
        return "----- file: -----\n" + output + "\n"
