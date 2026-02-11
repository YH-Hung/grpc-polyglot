"""Tokenizer for protobuf (.proto) files."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List


class ProtoTokenType(Enum):
    # Keywords
    MESSAGE = auto()
    REPEATED = auto()
    SYNTAX = auto()
    PACKAGE = auto()
    OPTION = auto()
    RESERVED = auto()
    IMPORT = auto()
    ENUM = auto()
    ONEOF = auto()

    # Delimiters
    LBRACE = auto()
    RBRACE = auto()
    SEMICOLON = auto()
    EQUALS = auto()

    # Literals
    IDENT = auto()
    NUMBER = auto()
    STRING_LIT = auto()

    # Special
    EOF = auto()


_KEYWORDS = {
    "message": ProtoTokenType.MESSAGE,
    "repeated": ProtoTokenType.REPEATED,
    "syntax": ProtoTokenType.SYNTAX,
    "package": ProtoTokenType.PACKAGE,
    "option": ProtoTokenType.OPTION,
    "reserved": ProtoTokenType.RESERVED,
    "import": ProtoTokenType.IMPORT,
    "enum": ProtoTokenType.ENUM,
    "oneof": ProtoTokenType.ONEOF,
}


@dataclass
class ProtoToken:
    type: ProtoTokenType
    value: str
    line: int
    col: int


def tokenize_proto(text: str) -> List[ProtoToken]:
    """Tokenize a protobuf source string into a list of tokens."""
    tokens: List[ProtoToken] = []
    i = 0
    line = 1
    col = 1
    n = len(text)

    while i < n:
        ch = text[i]

        # Whitespace
        if ch in (" ", "\t", "\r"):
            i += 1
            col += 1
            continue

        if ch == "\n":
            i += 1
            line += 1
            col = 1
            continue

        # Single-line comment
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue

        # Multi-line comment
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            col += 2
            while i < n:
                if text[i] == "\n":
                    line += 1
                    col = 1
                elif text[i] == "*" and i + 1 < n and text[i + 1] == "/":
                    i += 2
                    col += 2
                    break
                else:
                    col += 1
                i += 1
            continue

        # Single-character tokens
        if ch == "{":
            tokens.append(ProtoToken(ProtoTokenType.LBRACE, "{", line, col))
            i += 1
            col += 1
            continue
        if ch == "}":
            tokens.append(ProtoToken(ProtoTokenType.RBRACE, "}", line, col))
            i += 1
            col += 1
            continue
        if ch == ";":
            tokens.append(ProtoToken(ProtoTokenType.SEMICOLON, ";", line, col))
            i += 1
            col += 1
            continue
        if ch == "=":
            tokens.append(ProtoToken(ProtoTokenType.EQUALS, "=", line, col))
            i += 1
            col += 1
            continue

        # String literal
        if ch == '"':
            start_col = col
            i += 1
            col += 1
            start = i
            while i < n and text[i] != '"':
                if text[i] == "\\":
                    i += 1
                    col += 1
                i += 1
                col += 1
            value = text[start:i]
            if i < n:
                i += 1  # consume closing quote
                col += 1
            tokens.append(ProtoToken(ProtoTokenType.STRING_LIT, value, line, start_col))
            continue

        # Number
        if ch.isdigit():
            start = i
            start_col = col
            while i < n and text[i].isdigit():
                i += 1
                col += 1
            tokens.append(ProtoToken(ProtoTokenType.NUMBER, text[start:i], line, start_col))
            continue

        # Identifier / keyword
        if ch.isalpha() or ch == "_":
            start = i
            start_col = col
            while i < n and (text[i].isalnum() or text[i] == "_"):
                i += 1
                col += 1
            word = text[start:i]
            tok_type = _KEYWORDS.get(word, ProtoTokenType.IDENT)
            tokens.append(ProtoToken(tok_type, word, line, start_col))
            continue

        # Skip any other character
        i += 1
        col += 1

    tokens.append(ProtoToken(ProtoTokenType.EOF, "", line, col))
    return tokens
