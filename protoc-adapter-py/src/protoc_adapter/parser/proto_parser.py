from __future__ import annotations

import re
from pathlib import Path
from typing import List

from protoc_adapter.models import Field, Message, normalize


def parse_proto_file(file_path: str) -> List[Message]:
    """Parse a .proto file and extract all message definitions."""
    text = Path(file_path).read_text()
    messages = _parse_messages(text, source_file=file_path)
    return messages


def _parse_messages(text: str, source_file: str) -> List[Message]:
    """Parse message definitions from proto text using brace-depth tracking."""
    messages: List[Message] = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Detect message start: `message <Name> {`
        match = re.match(r"^message\s+(\w+)\s*\{?\s*$", line)
        if match:
            msg_name = match.group(1)
            # Find the opening brace
            brace_depth = line.count("{") - line.count("}")
            if brace_depth == 0:
                # Opening brace might be on the next line
                i += 1
                while i < len(lines) and lines[i].strip() == "":
                    i += 1
                if i < len(lines) and "{" in lines[i]:
                    brace_depth = 1
                    i += 1
                else:
                    continue
            else:
                i += 1

            # Collect the body until brace_depth returns to 0
            body_lines: List[str] = []
            while i < len(lines) and brace_depth > 0:
                body_line = lines[i]
                brace_depth += body_line.count("{") - body_line.count("}")
                if brace_depth > 0:
                    body_lines.append(body_line)
                else:
                    # The closing brace line — include content before the closing brace
                    before_close = body_line.rsplit("}", 1)[0]
                    if before_close.strip():
                        body_lines.append(before_close)
                i += 1

            body_text = "\n".join(body_lines)
            fields = _parse_fields(body_text, source_file)
            # Also parse nested messages from the body
            nested_messages = _parse_messages(body_text, source_file)

            msg = Message(
                original_name=msg_name,
                normalized_name=normalize(msg_name),
                fields=fields,
                source_file=source_file,
            )

            # Link nested type references in fields
            nested_by_name = {m.original_name: m for m in nested_messages}
            for f in msg.fields:
                if f.type_name in nested_by_name:
                    f.is_nested = True
                    f.nested_type = nested_by_name[f.type_name]

            messages.append(msg)
            # Also add nested messages as top-level (they can be referenced)
            messages.extend(nested_messages)
        else:
            i += 1

    return messages


def _parse_fields(body_text: str, source_file: str) -> List[Field]:
    """Parse field definitions from a message body (excluding nested messages)."""
    fields: List[Field] = []
    lines = body_text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip nested message definitions (consume them without parsing as fields)
        if re.match(r"^message\s+\w+", line):
            brace_depth = line.count("{") - line.count("}")
            i += 1
            if brace_depth == 0:
                # Find opening brace
                while i < len(lines):
                    brace_depth += lines[i].count("{") - lines[i].count("}")
                    i += 1
                    if brace_depth > 0:
                        break
            while i < len(lines) and brace_depth > 0:
                brace_depth += lines[i].count("{") - lines[i].count("}")
                i += 1
            continue

        # Skip comments, empty lines, reserved, option, etc.
        if not line or line.startswith("//") or line.startswith("option") or line.startswith("reserved"):
            i += 1
            continue

        # Parse field: [repeated] <type> <name> = <number>;
        field_match = re.match(
            r"^(repeated\s+)?(\w+)\s+(\w+)\s*=\s*\d+\s*;",
            line,
        )
        if field_match:
            is_repeated = field_match.group(1) is not None
            type_name = field_match.group(2)
            field_name = field_match.group(3)

            fields.append(
                Field(
                    original_name=field_name,
                    normalized_name=normalize(field_name),
                    type_name=type_name,
                    is_repeated=is_repeated,
                )
            )

        i += 1

    return fields
