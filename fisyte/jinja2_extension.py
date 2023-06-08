from dataclasses import dataclass
from typing import Iterable

from jinja2 import TemplateSyntaxError
from jinja2.ext import Extension
from jinja2.lexer import Token, TokenStream
from jinja2.nodes import CallBlock, Const, For, Name, OverlayScope

from .utils.jinja2 import SelfClosingTagsExtension, tokens_for_tag


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
        (tag,) = list(self.tags)

        # first token is necessarily 'thisfile' tag name, sanity check & skip:
        parser.stream.expect(f"name:{tag}")

        # next token must say "for"
        parser.stream.expect("name:for")

        # next token(s) must be either "*" or an assignment target
        try:
            assignment_target = parser.parse_assign_target()
        except TemplateSyntaxError:
            if parser.stream.current.value != "*":
                raise TemplateSyntaxError(
                    "expected identifier or * for assignment target after "
                    "'{tag} for'",
                    parser.stream.current.lineno,
                )
            assignment_target = Const("*")
            next(parser.stream)

        # next token must say "in"
        parser.stream.expect("name:in")

        # next tokens must be the source iterable for the for loop
        source_iterable_expr = parser.parse_expression()

        # parse up to closing tag automatically inserted by our base class
        body = parser.parse_statements([f"name:end{tag}"], drop_needle=True)

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
        (tag,) = list(self.tags)
        # short preamble to indicate this is not a normal template
        yield Token(
            0,
            "data",
            "if you see this text, you might be using this library wrong:\n"
            "as a single template can correspond to multiple output files,\n"
            "rendering templates as usual doesn't make a lot of sense\n",
        )
        # enclose entire file in tags that let us parse it
        yield from tokens_for_tag(tag, 0, self.environment)
        for token in stream:
            yield token
        yield from tokens_for_tag(f"end{tag}", token.lineno, self.environment)

    def parse(self, parser):
        (tag,) = list(self.tags)

        # sanity check & get line number for later
        lineno = parser.stream.expect(f"name:{tag}").lineno

        # parse to end
        body = parser.parse_statements([f"name:end{tag}"], drop_needle=True)

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
