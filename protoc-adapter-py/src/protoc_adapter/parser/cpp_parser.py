from __future__ import annotations

import re
from pathlib import Path
from typing import List

from protoc_adapter.models import Field, Message, normalize

# Patterns for vector/list types
_VECTOR_RE = re.compile(r"(?:std::)?(?:vector|list)\s*<\s*(\w+)\s*>")


def parse_cpp_header(file_path: str) -> List[Message]:
    """Parse a C++ header file and extract all struct definitions."""
    text = Path(file_path).read_text()
    return _parse_structs(text, source_file=file_path)


def _parse_structs(text: str, source_file: str) -> List[Message]:
    """Parse struct definitions from C++ header text using brace-depth tracking."""
    messages: List[Message] = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Detect struct start: `struct <Name> {` or `struct <Name>`
        match = re.match(r"^(?:typedef\s+)?struct\s+(\w+)\s*\{?\s*$", line)
        if match:
            struct_name = match.group(1)
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
                    before_close = body_line.rsplit("}", 1)[0]
                    if before_close.strip():
                        body_lines.append(before_close)
                i += 1

            body_text = "\n".join(body_lines)
            fields = _parse_cpp_fields(body_text)
            nested_structs = _parse_structs(body_text, source_file)

            msg = Message(
                original_name=struct_name,
                normalized_name=normalize(struct_name),
                fields=fields,
                source_file=source_file,
            )

            # Link nested type references
            nested_by_name = {m.original_name: m for m in nested_structs}
            for f in msg.fields:
                if f.type_name in nested_by_name:
                    f.is_nested = True
                    f.nested_type = nested_by_name[f.type_name]

            messages.append(msg)
            messages.extend(nested_structs)
        else:
            i += 1

    return messages


def _parse_cpp_fields(body_text: str) -> List[Field]:
    """Parse field declarations from a struct body."""
    fields: List[Field] = []
    lines = body_text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip nested struct definitions
        if re.match(r"^(?:typedef\s+)?struct\s+\w+", line):
            brace_depth = line.count("{") - line.count("}")
            i += 1
            if brace_depth == 0:
                while i < len(lines):
                    brace_depth += lines[i].count("{") - lines[i].count("}")
                    i += 1
                    if brace_depth > 0:
                        break
            while i < len(lines) and brace_depth > 0:
                brace_depth += lines[i].count("{") - lines[i].count("}")
                i += 1
            continue

        # Skip comments, empty lines, preprocessor directives, access specifiers
        if (
            not line
            or line.startswith("//")
            or line.startswith("/*")
            or line.startswith("*")
            or line.startswith("#")
            or line in ("public:", "private:", "protected:")
        ):
            i += 1
            continue

        # Try to parse vector/list field: std::vector<Type> name;
        vec_match = re.match(
            r"^(?:std::)?(?:vector|list)\s*<\s*([\w:]+)\s*>\s+(\w+)\s*;",
            line,
        )
        if vec_match:
            inner_type = vec_match.group(1)
            # Strip std:: prefix from inner type for matching
            if inner_type.startswith("std::"):
                inner_type = inner_type[5:]
            field_name = vec_match.group(2)
            fields.append(
                Field(
                    original_name=field_name,
                    normalized_name=normalize(field_name),
                    type_name=inner_type,
                    is_repeated=True,
                )
            )
            i += 1
            continue

        # Try to parse char array field: char name[SIZE]; -> treated as a string field
        char_arr_match = re.match(r"^char\s+(\w+)\s*\[\s*\d*\s*\]\s*;", line)
        if char_arr_match:
            field_name = char_arr_match.group(1)
            fields.append(
                Field(
                    original_name=field_name,
                    normalized_name=normalize(field_name),
                    type_name="char",
                    is_repeated=False,
                )
            )
            i += 1
            continue

        # Try to parse C-style array field: Type name[SIZE]; -> treated as repeated
        arr_match = re.match(r"^([\w:]+)\s+(\w+)\s*\[\s*\d*\s*\]\s*;", line)
        if arr_match:
            type_name = arr_match.group(1)
            if type_name.startswith("std::"):
                type_name = type_name[5:]
            field_name = arr_match.group(2)
            fields.append(
                Field(
                    original_name=field_name,
                    normalized_name=normalize(field_name),
                    type_name=type_name,
                    is_repeated=True,
                )
            )
            i += 1
            continue

        # Try to parse simple field: <type> <name>; (type can be namespace-qualified like std::string)
        field_match = re.match(r"^([\w:]+)\s+(\w+)\s*;", line)
        if field_match:
            type_name = field_match.group(1)
            # Strip std:: prefix for matching
            if type_name.startswith("std::"):
                type_name = type_name[5:]
            field_name = field_match.group(2)
            fields.append(
                Field(
                    original_name=field_name,
                    normalized_name=normalize(field_name),
                    type_name=type_name,
                )
            )
            i += 1
            continue

        i += 1

    return fields
