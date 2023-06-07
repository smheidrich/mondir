from typing import Iterable

from jinja2.ext import Extension
from jinja2.lexer import Token, TokenStream


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
