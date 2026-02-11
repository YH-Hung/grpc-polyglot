from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


def normalize(name: str) -> str:
    """Remove underscores and convert to uppercase for comparison."""
    return name.replace("_", "").upper()


@dataclass
class Field:
    original_name: str
    normalized_name: str
    type_name: str
    is_repeated: bool = False
    is_nested: bool = False
    nested_type: Optional[Message] = None


@dataclass
class Message:
    original_name: str
    normalized_name: str
    fields: List[Field] = field(default_factory=list)
    source_file: str = ""


@dataclass
class FieldMapping:
    proto_field: Field
    cpp_field: Field
    is_reply_header: bool = False


@dataclass
class MessageMatch:
    proto_message: Message
    cpp_message: Message
    field_mappings: List[FieldMapping] = field(default_factory=list)
