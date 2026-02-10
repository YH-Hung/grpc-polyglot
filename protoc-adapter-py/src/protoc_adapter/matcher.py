from __future__ import annotations

from typing import Dict, List

from protoc_adapter.models import Field, FieldMapping, Message, MessageMatch, normalize


class MatchError(Exception):
    """Raised when proto fields cannot be fully matched to C++ fields."""


def match_messages(
    proto_messages: List[Message],
    cpp_messages: List[Message],
) -> List[MessageMatch]:
    """Match proto messages to C++ structs by normalized name.

    For each matched pair, every proto field must match a C++ field.
    Raises MatchError if any proto field is unmatched.
    """
    cpp_by_norm: Dict[str, Message] = {m.normalized_name: m for m in cpp_messages}
    matches: List[MessageMatch] = []

    for proto_msg in proto_messages:
        cpp_msg = cpp_by_norm.get(proto_msg.normalized_name)
        if cpp_msg is None:
            # Proto message with no C++ match is skipped (not an error)
            continue

        field_mappings = _match_fields(proto_msg, cpp_msg, cpp_by_norm)
        matches.append(
            MessageMatch(
                proto_message=proto_msg,
                cpp_message=cpp_msg,
                field_mappings=field_mappings,
            )
        )

    return matches


def _match_fields(
    proto_msg: Message,
    cpp_msg: Message,
    cpp_by_norm: Dict[str, Message],
) -> List[FieldMapping]:
    """Match every proto field to a C++ field by normalized name.

    Raises MatchError if any proto field has no corresponding C++ field.
    """
    cpp_fields_by_norm: Dict[str, Field] = {
        f.normalized_name: f for f in cpp_msg.fields
    }
    mappings: List[FieldMapping] = []

    for proto_field in proto_msg.fields:
        cpp_field = cpp_fields_by_norm.get(proto_field.normalized_name)
        if cpp_field is None:
            raise MatchError(
                f"Unmatched proto field '{proto_field.original_name}' "
                f"(normalized: {proto_field.normalized_name}) "
                f"in message '{proto_msg.original_name}'. "
                f"No matching C++ field found in struct '{cpp_msg.original_name}'. "
                f"Available C++ fields: {[f.original_name for f in cpp_msg.fields]}"
            )

        # If the field is a non-primitive type, resolve the nested C++ struct
        if proto_field.is_nested:
            if proto_field.nested_type is not None:
                nested_cpp = cpp_by_norm.get(proto_field.nested_type.normalized_name)
            else:
                nested_cpp = cpp_by_norm.get(normalize(proto_field.type_name))
            if nested_cpp is not None:
                cpp_field.is_nested = True
                cpp_field.nested_type = nested_cpp

        # If the proto field is repeated, mark the cpp field as repeated too
        if proto_field.is_repeated:
            cpp_field.is_repeated = True

        mappings.append(FieldMapping(proto_field=proto_field, cpp_field=cpp_field))

    return mappings
