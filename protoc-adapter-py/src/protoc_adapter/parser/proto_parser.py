"""Parse .proto files using a tokenizer + recursive descent AST pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import List

from protoc_adapter.models import Message

from .proto_ast_parser import ProtoParser
from .proto_tokenizer import tokenize_proto
from .proto_transform import PROTO_PRIMITIVES, transform_proto

# Re-export for backward compatibility.
__all__ = ["parse_proto_file", "PROTO_PRIMITIVES"]


def parse_proto_file(file_path: str) -> List[Message]:
    """Parse a .proto file and extract all message definitions."""
    text = Path(file_path).read_text()
    tokens = tokenize_proto(text)
    ast = ProtoParser(tokens).parse()
    return transform_proto(ast, source_file=file_path)
