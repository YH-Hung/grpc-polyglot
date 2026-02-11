"""Parse C++ header files using a tokenizer + recursive descent AST pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import List

from protoc_adapter.models import Message

from .cpp_ast_parser import CppParser
from .cpp_tokenizer import tokenize_cpp
from .cpp_transform import transform_cpp


def parse_cpp_header(file_path: str) -> List[Message]:
    """Parse a C++ header file and extract all struct definitions."""
    text = Path(file_path).read_text()
    tokens = tokenize_cpp(text)
    ast = CppParser(tokens).parse()
    return transform_cpp(ast, source_file=file_path)
