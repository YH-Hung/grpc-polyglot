from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader

from protoc_adapter.models import FieldMapping, MessageMatch


def _proto_getter_name(proto_field_name: str) -> str:
    """Convert a proto field name to its Java getter suffix.

    Protobuf Java convention: field_name -> getFieldName()
    So we need to produce the 'FieldName' part (CamelCase).
    """
    parts = proto_field_name.split("_")
    return "".join(p.capitalize() for p in parts)


def _get_template_env() -> Environment:
    template_dir = Path(__file__).parent.parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )


def _build_method(
    match: MessageMatch,
    proto_outer_class: str,
) -> Dict:
    """Build a mapper method descriptor for a matched message pair."""
    fields = []
    for fm in match.field_mappings:
        field_desc = {
            "cpp_name": fm.cpp_field.original_name,
            "proto_getter": _proto_getter_name(fm.proto_field.original_name),
            "is_repeated": fm.proto_field.is_repeated,
            "is_nested": fm.proto_field.is_nested or fm.cpp_field.is_nested,
        }
        fields.append(field_desc)

    return {
        "return_type": match.cpp_message.original_name,
        "proto_type": f"{proto_outer_class}.{match.proto_message.original_name}",
        "fields": fields,
    }


def generate_mapper(
    matches: List[MessageMatch],
    proto_file_name: str,
    java_package: str,
) -> str:
    """Generate Java Mapper source code for a set of matched messages from one proto file."""
    env = _get_template_env()
    template = env.get_template("mapper.java.j2")

    # Mapper class name: proto file stem + "Mapper"
    stem = Path(proto_file_name).stem
    # Convert to PascalCase if needed (e.g., order_service -> OrderService)
    parts = stem.split("_")
    pascal_stem = "".join(p.capitalize() for p in parts)
    mapper_class_name = f"{pascal_stem}Mapper"

    # Proto outer class name (protobuf generates an outer class from the file name)
    proto_outer_class = f"{pascal_stem}Proto"

    methods = []
    has_list = False
    for match in matches:
        method = _build_method(match, proto_outer_class)
        methods.append(method)
        for field in method["fields"]:
            if field["is_repeated"] and field["is_nested"]:
                has_list = True

    return template.render(
        java_package=java_package,
        mapper_class_name=mapper_class_name,
        methods=methods,
        has_list=has_list,
    )


def generate_mappers(
    matches_by_proto: Dict[str, List[MessageMatch]],
    java_package: str,
    output_dir: str,
) -> List[str]:
    """Generate Mapper Java files, one per proto file.

    Args:
        matches_by_proto: Dict mapping proto file path to its matched messages.
        java_package: Java package name.
        output_dir: The working-path directory.

    Returns list of generated file paths.
    """
    mapper_dir = os.path.join(output_dir, "mapper")
    os.makedirs(mapper_dir, exist_ok=True)

    generated: List[str] = []
    for proto_file, matches in matches_by_proto.items():
        if not matches:
            continue
        source = generate_mapper(matches, proto_file, java_package)
        stem = Path(proto_file).stem
        parts = stem.split("_")
        pascal_stem = "".join(p.capitalize() for p in parts)
        file_name = f"{pascal_stem}Mapper.java"
        file_path = os.path.join(mapper_dir, file_name)
        Path(file_path).write_text(source)
        generated.append(file_path)

    return generated
