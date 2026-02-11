"""Transform proto AST nodes into the application's Message/Field models."""

from __future__ import annotations

from typing import List

from protoc_adapter.models import Field, Message, normalize

from .proto_ast import ProtoFile, ProtoMessage

# Proto scalar types — any field type not in this set is a message reference.
PROTO_PRIMITIVES = {
    "int32", "sint32", "sfixed32", "uint32", "fixed32",
    "int64", "sint64", "sfixed64", "uint64", "fixed64",
    "float", "double", "bool", "string", "bytes",
}


def transform_proto(ast: ProtoFile, source_file: str) -> List[Message]:
    """Transform a ProtoFile AST into a flat list of Message objects.

    Nested messages are flattened: the parent message appears first,
    followed by its nested messages.
    """
    result: List[Message] = []
    for msg_node in ast.messages:
        result.extend(_transform_message(msg_node, source_file))
    return result


def _transform_message(node: ProtoMessage, source_file: str) -> List[Message]:
    """Transform a single ProtoMessage and its nested messages.

    Returns a list where the parent message is first, followed by all
    recursively flattened nested messages.
    """
    # Recursively transform nested messages first so we can link them.
    nested_messages: List[Message] = []
    for nested_node in node.nested_messages:
        nested_messages.extend(_transform_message(nested_node, source_file))

    # Build lookup of direct-child nested messages by name.
    direct_nested_names = {n.name for n in node.nested_messages}
    nested_by_name = {
        m.original_name: m
        for m in nested_messages
        if m.original_name in direct_nested_names
    }

    # Transform fields.
    fields: List[Field] = []
    for f in node.fields:
        is_nested = f.type_name not in PROTO_PRIMITIVES
        field = Field(
            original_name=f.field_name,
            normalized_name=normalize(f.field_name),
            type_name=f.type_name,
            is_repeated=f.is_repeated,
            is_nested=is_nested,
        )
        # Link nested_type only for messages defined inside this message.
        if f.type_name in nested_by_name:
            field.nested_type = nested_by_name[f.type_name]
        fields.append(field)

    msg = Message(
        original_name=node.name,
        normalized_name=normalize(node.name),
        fields=fields,
        source_file=source_file,
    )

    return [msg] + nested_messages
