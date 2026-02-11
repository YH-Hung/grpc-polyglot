"""Tokenizer for C++ header files."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List


class CppTokenType(Enum):
    # Keywords
    STRUCT = auto()
    TYPEDEF = auto()
    CHAR = auto()

    # Delimiters
    LBRACE = auto()
    RBRACE = auto()
    SEMICOLON = auto()
    LANGLE = auto()
    RANGLE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COLONCOLON = auto()
    COLON = auto()

    # Literals
    IDENT = auto()
    NUMBER = auto()

    # Special
    EOF = auto()


_KEYWORDS = {
    "struct": CppTokenType.STRUCT,
    "typedef": CppTokenType.TYPEDEF,
    "char": CppTokenType.CHAR,
}


@dataclass
class CppToken:
    type: CppTokenType
    value: str
    line: int
    col: int


def tokenize_cpp(text: str) -> List[CppToken]:
    """Tokenize a C++ header source string into a list of tokens."""
    tokens: List[CppToken] = []
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

        # Preprocessor directive — skip entire line
        if ch == "#":
            while i < n and text[i] != "\n":
                i += 1
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
                    i += 1
                elif text[i] == "*" and i + 1 < n and text[i + 1] == "/":
                    i += 2
                    col += 2
                    break
                else:
                    col += 1
                    i += 1
            continue

        # Double-character token: ::
        if ch == ":" and i + 1 < n and text[i + 1] == ":":
            tokens.append(CppToken(CppTokenType.COLONCOLON, "::", line, col))
            i += 2
            col += 2
            continue

        # Single colon (for access specifiers like public:)
        if ch == ":":
            tokens.append(CppToken(CppTokenType.COLON, ":", line, col))
            i += 1
            col += 1
            continue

        # Single-character tokens
        if ch == "{":
            tokens.append(CppToken(CppTokenType.LBRACE, "{", line, col))
            i += 1
            col += 1
            continue
        if ch == "}":
            tokens.append(CppToken(CppTokenType.RBRACE, "}", line, col))
            i += 1
            col += 1
            continue
        if ch == ";":
            tokens.append(CppToken(CppTokenType.SEMICOLON, ";", line, col))
            i += 1
            col += 1
            continue
        if ch == "<":
            tokens.append(CppToken(CppTokenType.LANGLE, "<", line, col))
            i += 1
            col += 1
            continue
        if ch == ">":
            tokens.append(CppToken(CppTokenType.RANGLE, ">", line, col))
            i += 1
            col += 1
            continue
        if ch == "[":
            tokens.append(CppToken(CppTokenType.LBRACKET, "[", line, col))
            i += 1
            col += 1
            continue
        if ch == "]":
            tokens.append(CppToken(CppTokenType.RBRACKET, "]", line, col))
            i += 1
            col += 1
            continue

        # Number
        if ch.isdigit():
            start = i
            start_col = col
            while i < n and text[i].isdigit():
                i += 1
                col += 1
            tokens.append(CppToken(CppTokenType.NUMBER, text[start:i], line, start_col))
            continue

        # Identifier / keyword
        if ch.isalpha() or ch == "_":
            start = i
            start_col = col
            while i < n and (text[i].isalnum() or text[i] == "_"):
                i += 1
                col += 1
            word = text[start:i]
            tok_type = _KEYWORDS.get(word, CppTokenType.IDENT)
            tokens.append(CppToken(tok_type, word, line, start_col))
            continue

        # Skip any other character (e.g. *, &, commas, etc.)
        i += 1
        col += 1

    tokens.append(CppToken(CppTokenType.EOF, "", line, col))
    return tokens
