"""AST node definitions for protobuf (.proto) files."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ProtoField:
    """A field declaration: [repeated] Type name = number;"""

    type_name: str
    field_name: str
    field_number: int
    is_repeated: bool = False


@dataclass
class ProtoMessage:
    """A message definition, possibly containing nested messages."""

    name: str
    fields: List[ProtoField] = field(default_factory=list)
    nested_messages: List[ProtoMessage] = field(default_factory=list)


@dataclass
class ProtoFile:
    """Top-level parsed representation of a .proto file."""

    messages: List[ProtoMessage] = field(default_factory=list)
