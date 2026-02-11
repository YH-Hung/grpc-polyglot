"""Recursive descent parser for protobuf (.proto) files.

Consumes a token stream from proto_tokenizer and produces proto AST nodes.
"""

from __future__ import annotations

from typing import List, Tuple

from .proto_ast import ProtoField, ProtoFile, ProtoMessage
from .proto_tokenizer import ProtoToken, ProtoTokenType


class ProtoParseError(Exception):
    """Raised when the parser encounters unexpected input."""

    def __init__(self, message: str, token: ProtoToken | None = None):
        if token:
            super().__init__(f"Line {token.line}:{token.col}: {message}")
        else:
            super().__init__(message)


class ProtoParser:
    """Recursive descent parser for .proto files."""

    def __init__(self, tokens: List[ProtoToken]):
        self._tokens = tokens
        self._pos = 0

    # -- public API --

    def parse(self) -> ProtoFile:
        """Parse the full token stream into a ProtoFile AST."""
        messages: List[ProtoMessage] = []

        while not self._at_end():
            tt = self._peek().type

            if tt == ProtoTokenType.MESSAGE:
                messages.append(self._parse_message())
            elif tt in (
                ProtoTokenType.SYNTAX,
                ProtoTokenType.PACKAGE,
                ProtoTokenType.OPTION,
                ProtoTokenType.IMPORT,
                ProtoTokenType.RESERVED,
            ):
                self._skip_statement()
            elif tt == ProtoTokenType.ENUM:
                self._skip_block()
            else:
                # Skip any unrecognised top-level token (e.g. service blocks)
                self._advance()

        return ProtoFile(messages=messages)

    # -- message parsing --

    def _parse_message(self) -> ProtoMessage:
        """Parse: MESSAGE IDENT LBRACE body RBRACE"""
        self._expect(ProtoTokenType.MESSAGE)
        name_tok = self._expect(ProtoTokenType.IDENT)
        self._expect(ProtoTokenType.LBRACE)
        fields, nested = self._parse_message_body()
        self._expect(ProtoTokenType.RBRACE)
        return ProtoMessage(name=name_tok.value, fields=fields, nested_messages=nested)

    def _parse_message_body(
        self,
    ) -> Tuple[List[ProtoField], List[ProtoMessage]]:
        """Parse the contents between { and } of a message."""
        fields: List[ProtoField] = []
        nested: List[ProtoMessage] = []

        while not self._at_end() and self._peek().type != ProtoTokenType.RBRACE:
            tt = self._peek().type

            if tt == ProtoTokenType.MESSAGE:
                nested.append(self._parse_message())
            elif tt == ProtoTokenType.REPEATED:
                fields.append(self._parse_field(is_repeated=True))
            elif tt == ProtoTokenType.IDENT:
                fields.append(self._parse_field(is_repeated=False))
            elif tt in (
                ProtoTokenType.OPTION,
                ProtoTokenType.RESERVED,
            ):
                self._skip_statement()
            elif tt == ProtoTokenType.ENUM:
                self._skip_block()
            elif tt == ProtoTokenType.ONEOF:
                self._skip_block()
            else:
                self._advance()

        return fields, nested

    def _parse_field(self, *, is_repeated: bool) -> ProtoField:
        """Parse: [REPEATED] IDENT(type) IDENT(name) EQUALS NUMBER SEMICOLON"""
        if is_repeated:
            self._expect(ProtoTokenType.REPEATED)

        type_tok = self._expect(ProtoTokenType.IDENT)
        name_tok = self._expect(ProtoTokenType.IDENT)
        self._expect(ProtoTokenType.EQUALS)
        num_tok = self._expect(ProtoTokenType.NUMBER)
        self._expect(ProtoTokenType.SEMICOLON)

        return ProtoField(
            type_name=type_tok.value,
            field_name=name_tok.value,
            field_number=int(num_tok.value),
            is_repeated=is_repeated,
        )

    # -- skip helpers --

    def _skip_statement(self) -> None:
        """Skip tokens until (and including) the next semicolon."""
        while not self._at_end():
            tok = self._advance()
            if tok.type == ProtoTokenType.SEMICOLON:
                return

    def _skip_block(self) -> None:
        """Skip a keyword + IDENT + braced block (e.g. enum, oneof, service)."""
        self._advance()  # keyword
        # Skip until opening brace
        while not self._at_end() and self._peek().type != ProtoTokenType.LBRACE:
            self._advance()
        if not self._at_end():
            self._advance()  # consume LBRACE
        depth = 1
        while not self._at_end() and depth > 0:
            tok = self._advance()
            if tok.type == ProtoTokenType.LBRACE:
                depth += 1
            elif tok.type == ProtoTokenType.RBRACE:
                depth -= 1

    # -- token helpers --

    def _peek(self) -> ProtoToken:
        return self._tokens[self._pos]

    def _advance(self) -> ProtoToken:
        tok = self._tokens[self._pos]
        if tok.type != ProtoTokenType.EOF:
            self._pos += 1
        return tok

    def _expect(self, expected: ProtoTokenType) -> ProtoToken:
        tok = self._peek()
        if tok.type != expected:
            raise ProtoParseError(
                f"Expected {expected.name}, got {tok.type.name} ({tok.value!r})",
                tok,
            )
        return self._advance()

    def _at_end(self) -> bool:
        return self._tokens[self._pos].type == ProtoTokenType.EOF
