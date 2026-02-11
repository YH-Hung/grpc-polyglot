"""Transform C++ AST nodes into the application's Message/Field models."""

from __future__ import annotations

from typing import Dict, List, Tuple, Union

from protoc_adapter.models import Field, Message, normalize

from .cpp_ast import (
    CppAnonymousStructField,
    CppFieldDecl,
    CppHeader,
    CppStruct,
)


def transform_cpp(ast: CppHeader, source_file: str) -> List[Message]:
    """Transform a CppHeader AST into a flat list of Message objects."""
    # Build alias map from type aliases.
    aliases: Dict[str, str] = {}
    for alias in ast.type_aliases:
        aliases[alias.new_name] = alias.existing_type

    result: List[Message] = []
    for struct_node in ast.structs:
        result.extend(_transform_struct(struct_node, source_file, aliases))
    return result


def _resolve_alias(name: str, aliases: Dict[str, str]) -> str:
    """Resolve a type name through the alias chain."""
    seen: set[str] = set()
    while name in aliases and name not in seen:
        seen.add(name)
        name = aliases[name]
    return name


def _transform_struct(
    node: CppStruct,
    source_file: str,
    aliases: Dict[str, str],
) -> List[Message]:
    """Transform a CppStruct into Message objects.

    Returns a list where the struct's message is first, followed by
    nested struct messages and synthetic anonymous struct messages.
    """
    # Determine effective struct name.
    struct_name = node.typedef_name if node.is_anonymous_typedef else node.name
    if struct_name is None:
        return []

    # Recursively transform named nested structs.
    nested_messages: List[Message] = []
    for nested in node.nested_structs:
        nested_messages.extend(_transform_struct(nested, source_file, aliases))

    # Transform fields (including anonymous struct fields).
    fields: List[Field] = []
    anon_messages: List[Message] = []
    for f in node.fields:
        if isinstance(f, CppAnonymousStructField):
            field_obj, synth_msgs = _transform_anonymous_struct_field(
                f, source_file, aliases
            )
            fields.append(field_obj)
            anon_messages.extend(synth_msgs)
        else:
            fields.append(_transform_field_decl(f, aliases))

    all_nested = nested_messages + anon_messages

    msg = Message(
        original_name=struct_name,
        normalized_name=normalize(struct_name),
        fields=fields,
        source_file=source_file,
    )

    # Link nested type references on fields.
    nested_by_name = {m.original_name: m for m in all_nested}
    for f in msg.fields:
        if f.type_name in nested_by_name:
            f.is_nested = True
            f.nested_type = nested_by_name[f.type_name]

    return [msg] + all_nested


def _transform_anonymous_struct_field(
    node: CppAnonymousStructField,
    source_file: str,
    aliases: Dict[str, str],
) -> Tuple[Field, List[Message]]:
    """Transform an anonymous struct field into a Field + synthetic Message."""
    synthetic_name = node.field_name[0].upper() + node.field_name[1:]

    inner_fields: List[Field] = []
    deeper_anon: List[Message] = []
    for f in node.fields:
        if isinstance(f, CppAnonymousStructField):
            field_obj, synth_msgs = _transform_anonymous_struct_field(
                f, source_file, aliases
            )
            inner_fields.append(field_obj)
            deeper_anon.extend(synth_msgs)
        else:
            inner_fields.append(_transform_field_decl(f, aliases))

    synthetic_msg = Message(
        original_name=synthetic_name,
        normalized_name=normalize(synthetic_name),
        fields=inner_fields,
        source_file=source_file,
    )

    field = Field(
        original_name=node.field_name,
        normalized_name=normalize(node.field_name),
        type_name=synthetic_name,
        is_nested=True,
    )

    return field, [synthetic_msg] + deeper_anon


def _transform_field_decl(
    node: CppFieldDecl,
    aliases: Dict[str, str],
) -> Field:
    """Transform a CppFieldDecl into a Field."""
    type_name = node.type_name

    # Resolve aliases.
    type_name = _resolve_alias(type_name, aliases)

    if node.is_vector:
        return Field(
            original_name=node.field_name,
            normalized_name=normalize(node.field_name),
            type_name=type_name,
            is_repeated=True,
        )

    if node.is_char_array:
        return Field(
            original_name=node.field_name,
            normalized_name=normalize(node.field_name),
            type_name="char",
            is_repeated=False,
        )

    if node.is_array:
        return Field(
            original_name=node.field_name,
            normalized_name=normalize(node.field_name),
            type_name=type_name,
            is_repeated=True,
        )

    return Field(
        original_name=node.field_name,
        normalized_name=normalize(node.field_name),
        type_name=type_name,
    )
