from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader

from protoc_adapter.models import FieldMapping, MessageMatch

# Proto type -> Java boxed type
PRIMITIVE_TYPE_MAP: Dict[str, str] = {
    "int32": "Integer",
    "sint32": "Integer",
    "sfixed32": "Integer",
    "uint32": "Integer",
    "fixed32": "Integer",
    "int64": "Long",
    "sint64": "Long",
    "sfixed64": "Long",
    "uint64": "Long",
    "fixed64": "Long",
    "float": "Float",
    "double": "Double",
    "bool": "Boolean",
    "string": "String",
    "bytes": "byte[]",
}

# C++ type -> Java boxed type
CPP_TYPE_MAP: Dict[str, str] = {
    "int": "Integer",
    "long": "Long",
    "float": "Float",
    "double": "Double",
    "bool": "Boolean",
    "string": "String",
    "char": "String",
}


def _get_java_type(field_mapping: FieldMapping) -> str:
    """Determine the Java type for a field based on its C++ type and proto type."""
    cpp_field = field_mapping.cpp_field
    proto_field = field_mapping.proto_field

    # Determine base type
    if cpp_field.is_nested:
        base_type = cpp_field.nested_type.original_name if cpp_field.nested_type else cpp_field.type_name
    elif proto_field.type_name in PRIMITIVE_TYPE_MAP:
        base_type = PRIMITIVE_TYPE_MAP[proto_field.type_name]
    elif cpp_field.type_name in CPP_TYPE_MAP:
        base_type = CPP_TYPE_MAP[cpp_field.type_name]
    else:
        base_type = cpp_field.type_name

    if proto_field.is_repeated:
        return f"List<{base_type}>"
    return base_type


def _get_template_env() -> Environment:
    template_dir = Path(__file__).parent.parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )


def generate_dto(match: MessageMatch, java_package: str) -> str:
    """Generate Java DTO source code for a matched message pair."""
    env = _get_template_env()
    template = env.get_template("dto.java.j2")

    fields = []
    has_list = False
    for fm in match.field_mappings:
        java_type = _get_java_type(fm)
        if java_type.startswith("List<"):
            has_list = True
        fields.append({
            "java_type": java_type,
            "name": fm.cpp_field.original_name,
        })

    return template.render(
        java_package=java_package,
        class_name=match.cpp_message.original_name,
        fields=fields,
        has_list=has_list,
    )


def generate_dtos(
    matches: List[MessageMatch],
    java_package: str,
    output_dir: str,
) -> List[str]:
    """Generate DTO Java files for all matched message pairs.

    Returns list of generated file paths.
    """
    dto_dir = os.path.join(output_dir, "dto")
    os.makedirs(dto_dir, exist_ok=True)

    generated: List[str] = []
    for match in matches:
        source = generate_dto(match, java_package)
        file_name = f"{match.cpp_message.original_name}.java"
        file_path = os.path.join(dto_dir, file_name)
        Path(file_path).write_text(source)
        generated.append(file_path)

    return generated
