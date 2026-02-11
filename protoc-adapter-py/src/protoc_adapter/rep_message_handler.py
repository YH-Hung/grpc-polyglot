"""Special handling for Rep* messages with msgHeader fields.

Rep messages (proto messages whose names start with "Rep") have a msgHeader-typed
field that maps to a synthetic WebServiceReplyHeader DTO with renamed fields:
  - retCode    -> returnCode
  - msgOwnId   -> returnMessage
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from protoc_adapter.models import Field, FieldMapping, Message, MessageMatch, normalize


# The proto type name that triggers special handling.
MSG_HEADER_TYPE_NAME = "msgHeader"

# The synthetic Java DTO class name.
WEB_SERVICE_REPLY_HEADER_CLASS = "WebServiceReplyHeader"

# Field rename mapping: proto field original_name -> DTO field name
HEADER_FIELD_RENAMES: Dict[str, str] = {
    "retCode": "returnCode",
    "msgOwnId": "returnMessage",
}


def _camel_case_getter(name: str) -> str:
    """Capitalize first letter of a camelCase name for Java getter suffix.

    Unlike _proto_getter_name (which splits on underscores), this handles
    camelCase proto field names: retCode -> RetCode -> getRetCode().
    """
    if not name:
        return name
    return name[0].upper() + name[1:]


def _snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def is_rep_message(proto_message: Message) -> bool:
    """Check whether a proto message is a Rep* message."""
    return proto_message.original_name.startswith("Rep")


def find_msg_header_field(proto_message: Message) -> Optional[Field]:
    """Find the msgHeader-typed field in a proto message, if present."""
    for field in proto_message.fields:
        if field.is_nested and normalize(field.type_name) == normalize(MSG_HEADER_TYPE_NAME):
            return field
    return None


def strip_msg_header_fields(
    proto_messages: List[Message],
) -> Tuple[List[Message], Dict[str, Field]]:
    """Strip msgHeader fields from Rep* messages before matching.

    Returns:
        - The proto messages list (msgHeader fields removed from Rep* messages)
        - Dict mapping proto message original_name -> the removed msgHeader Field
    """
    stripped: Dict[str, Field] = {}

    for msg in proto_messages:
        if not is_rep_message(msg):
            continue
        header_field = find_msg_header_field(msg)
        if header_field is not None:
            msg.fields = [f for f in msg.fields if f is not header_field]
            stripped[msg.original_name] = header_field

    return proto_messages, stripped


def resolve_msg_header_definition(
    proto_messages: List[Message],
) -> Optional[Message]:
    """Find the msgHeader message definition from the proto messages list."""
    for msg in proto_messages:
        if normalize(msg.original_name) == normalize(MSG_HEADER_TYPE_NAME):
            return msg
    return None


def build_web_service_reply_header_match(
    msg_header_definition: Message,
) -> MessageMatch:
    """Build a synthetic MessageMatch for WebServiceReplyHeader.

    Creates a MessageMatch with only the renamed fields (retCode -> returnCode,
    msgOwnId -> returnMessage), not all fields from msgHeader.
    """
    renamed_fields: List[Field] = []
    field_mappings: List[FieldMapping] = []

    for proto_field in msg_header_definition.fields:
        if proto_field.original_name not in HEADER_FIELD_RENAMES:
            continue

        renamed_name = HEADER_FIELD_RENAMES[proto_field.original_name]

        cpp_field = Field(
            original_name=renamed_name,
            normalized_name=normalize(renamed_name),
            type_name=proto_field.type_name,
            is_repeated=proto_field.is_repeated,
            is_nested=proto_field.is_nested,
        )
        renamed_fields.append(cpp_field)
        field_mappings.append(FieldMapping(proto_field=proto_field, cpp_field=cpp_field))

    synthetic_cpp_msg = Message(
        original_name=WEB_SERVICE_REPLY_HEADER_CLASS,
        normalized_name=normalize(WEB_SERVICE_REPLY_HEADER_CLASS),
        fields=renamed_fields,
        source_file="<synthetic>",
    )

    return MessageMatch(
        proto_message=msg_header_definition,
        cpp_message=synthetic_cpp_msg,
        field_mappings=field_mappings,
    )


def remove_msg_header_message(
    proto_messages: List[Message],
) -> List[Message]:
    """Remove the msgHeader message definition from the proto messages list.

    This prevents it from being matched or generating mapper methods.
    """
    return [
        m for m in proto_messages
        if normalize(m.original_name) != normalize(MSG_HEADER_TYPE_NAME)
    ]


def inject_header_field_mappings(
    matches: List[MessageMatch],
    stripped_fields: Dict[str, Field],
    msg_header_def: Optional[Message],
) -> List[MessageMatch]:
    """Inject synthetic msgHeader -> WebServiceReplyHeader field mappings
    into Rep* MessageMatches."""
    for match in matches:
        proto_name = match.proto_message.original_name
        if proto_name not in stripped_fields:
            continue

        original_header_field = stripped_fields[proto_name]

        # Link nested_type so the mapper generator can access sub-fields
        if original_header_field.nested_type is None and msg_header_def is not None:
            original_header_field.nested_type = msg_header_def

        # Convert proto snake_case field name to camelCase for the DTO field name
        field_name = original_header_field.original_name
        if "_" in field_name:
            field_name = _snake_to_camel(field_name)

        synthetic_cpp_field = Field(
            original_name=field_name,
            normalized_name=original_header_field.normalized_name,
            type_name=WEB_SERVICE_REPLY_HEADER_CLASS,
            is_nested=True,
            is_repeated=False,
        )

        mapping = FieldMapping(
            proto_field=original_header_field,
            cpp_field=synthetic_cpp_field,
            is_reply_header=True,
        )
        match.field_mappings.insert(0, mapping)

    return matches
