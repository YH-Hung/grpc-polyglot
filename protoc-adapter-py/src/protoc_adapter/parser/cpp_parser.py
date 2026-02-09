from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from protoc_adapter.models import Field, Message, normalize

# Patterns for vector/list types
_VECTOR_RE = re.compile(r"(?:std::)?(?:vector|list)\s*<\s*(\w+)\s*>")

# Patterns for type aliases
_SIMPLE_TYPEDEF_RE = re.compile(r"^\s*typedef\s+([\w:]+)\s+(\w+)\s*;$")
_STRUCT_TYPEDEF_RE = re.compile(r"^\s*typedef\s+struct\s+(\w+)\s+(\w+)\s*;$")


def _resolve_alias(name: str, aliases: Dict[str, str]) -> str:
    """Resolve a type name through the alias chain."""
    seen: set[str] = set()
    while name in aliases and name not in seen:
        seen.add(name)
        name = aliases[name]
    return name


def parse_cpp_header(file_path: str) -> List[Message]:
    """Parse a C++ header file and extract all struct definitions."""
    text = Path(file_path).read_text()
    type_aliases: Dict[str, str] = {}
    return _parse_structs(text, source_file=file_path, type_aliases=type_aliases)


def _parse_structs(
    text: str,
    source_file: str,
    type_aliases: Dict[str, str] | None = None,
) -> List[Message]:
    """Parse struct definitions from C++ header text using brace-depth tracking."""
    if type_aliases is None:
        type_aliases = {}

    messages: List[Message] = []
    lines = text.split("\n")

    # Pre-pass: collect type aliases
    for raw_line in lines:
        stripped = raw_line.strip()
        # Struct alias: typedef struct TradeOrder TradeAlias;
        m = _STRUCT_TYPEDEF_RE.match(stripped)
        if m:
            type_aliases[m.group(2)] = m.group(1)
            continue
        # Simple alias: typedef int UserId;
        m = _SIMPLE_TYPEDEF_RE.match(stripped)
        if m and m.group(1) != "struct":
            type_aliases[m.group(2)] = m.group(1)

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect named struct: `struct <Name> {` or `typedef struct <Name> {`
        match = re.match(r"^(?:typedef\s+)?struct\s+(\w+)\s*\{?\s*$", line)
        anon_typedef = False

        if not match:
            # Detect anonymous typedef struct: `typedef struct {`
            if re.match(r"^typedef\s+struct\s*\{?\s*$", line):
                anon_typedef = True

        if match or anon_typedef:
            struct_name = match.group(1) if match else None
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
            closing_line = ""
            while i < len(lines) and brace_depth > 0:
                body_line = lines[i]
                brace_depth += body_line.count("{") - body_line.count("}")
                if brace_depth > 0:
                    body_lines.append(body_line)
                else:
                    before_close = body_line.rsplit("}", 1)[0]
                    if before_close.strip():
                        body_lines.append(before_close)
                    closing_line = body_line
                i += 1

            # For anonymous typedef struct, extract name from closing line
            if anon_typedef and struct_name is None:
                close_match = re.search(r"}\s*(\w+)\s*;", closing_line)
                if close_match:
                    struct_name = close_match.group(1)
                else:
                    continue

            body_text = "\n".join(body_lines)
            fields, anon_nested = _parse_cpp_fields(
                body_text, source_file, type_aliases
            )
            nested_structs = _parse_structs(body_text, source_file, type_aliases)
            nested_structs.extend(anon_nested)

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


def _parse_cpp_fields(
    body_text: str,
    source_file: str = "",
    type_aliases: Dict[str, str] | None = None,
) -> Tuple[List[Field], List[Message]]:
    """Parse field declarations from a struct body.

    Returns a tuple of (fields, anonymous_nested_messages).
    """
    if type_aliases is None:
        type_aliases = {}

    fields: List[Field] = []
    anon_messages: List[Message] = []
    lines = body_text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Handle anonymous nested struct: struct { ... } fieldName;
        if re.match(r"^struct\s*\{\s*$", line):
            brace_depth = 1
            i += 1
            anon_body_lines: List[str] = []
            anon_closing = ""
            while i < len(lines) and brace_depth > 0:
                anon_line = lines[i]
                brace_depth += anon_line.count("{") - anon_line.count("}")
                if brace_depth > 0:
                    anon_body_lines.append(anon_line)
                else:
                    before_close = anon_line.rsplit("}", 1)[0]
                    if before_close.strip():
                        anon_body_lines.append(before_close)
                    anon_closing = anon_line
                i += 1

            close_m = re.search(r"}\s*(\w+)\s*;", anon_closing)
            if close_m:
                field_name = close_m.group(1)
                synthetic_name = field_name[0].upper() + field_name[1:]
                anon_body_text = "\n".join(anon_body_lines)

                inner_fields, deeper_anon = _parse_cpp_fields(
                    anon_body_text, source_file, type_aliases
                )

                synthetic_msg = Message(
                    original_name=synthetic_name,
                    normalized_name=normalize(synthetic_name),
                    fields=inner_fields,
                    source_file=source_file,
                )
                anon_messages.append(synthetic_msg)
                anon_messages.extend(deeper_anon)

                fields.append(
                    Field(
                        original_name=field_name,
                        normalized_name=normalize(field_name),
                        type_name=synthetic_name,
                        is_nested=True,
                    )
                )
            continue

        # Skip named nested struct definitions
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

        # Skip typedef lines (already handled in pre-pass)
        if line.startswith("typedef"):
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
            inner_type = _resolve_alias(inner_type, type_aliases)
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
            type_name = _resolve_alias(type_name, type_aliases)
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
            type_name = _resolve_alias(type_name, type_aliases)
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

    return fields, anon_messages
