from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from protoc_adapter.models import FieldMapping, MessageMatch


def _get_template_env() -> Environment:
    template_dir = Path(__file__).parent.parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )


def _proto_getter_name(proto_field_name: str) -> str:
    """Convert a proto field name to its Java getter suffix.

    Protobuf Java convention: field_name -> getFieldName()
    So we need to produce the 'FieldName' part (CamelCase).
    """
    parts = proto_field_name.split("_")
    return "".join(p.capitalize() for p in parts)


def _build_reply_header_default_method(
    match: MessageMatch,
    proto_outer_class: str,
) -> Optional[Dict]:
    """Build template data for a default method mapping msgHeader -> WebServiceReplyHeader.

    Returns None if the match has no reply header field mapping.
    """
    from protoc_adapter.rep_message_handler import HEADER_FIELD_RENAMES, _camel_case_getter

    for fm in match.field_mappings:
        if not fm.is_reply_header:
            continue

        sub_fields = []
        if fm.proto_field.nested_type is not None:
            for sub_field in fm.proto_field.nested_type.fields:
                if sub_field.original_name not in HEADER_FIELD_RENAMES:
                    continue
                renamed = HEADER_FIELD_RENAMES[sub_field.original_name]
                sub_fields.append({
                    "dto_name": renamed,
                    "proto_getter": _camel_case_getter(sub_field.original_name),
                })

        # Derive the proto outer class for the msgHeader type from its source file
        header_type_name = fm.proto_field.type_name
        if fm.proto_field.nested_type and fm.proto_field.nested_type.source_file:
            header_stem = Path(fm.proto_field.nested_type.source_file).stem
            header_parts = header_stem.split("_")
            header_outer = "".join(p.capitalize() for p in header_parts) + "Proto"
        else:
            header_outer = proto_outer_class

        return {
            "proto_full_type": f"{header_outer}.{header_type_name}",
            "dto_type": "WebServiceReplyHeader",
            "sub_fields": sub_fields,
        }

    return None


def _build_mapper_method(
    match: MessageMatch,
    proto_outer_class: str,
) -> Dict:
    """Build a mapper method descriptor for the MapStruct interface."""
    return {
        "return_type": match.cpp_message.original_name,
        "proto_type": f"{proto_outer_class}.{match.proto_message.original_name}",
    }


def generate_mapstruct_mapper(
    matches: List[MessageMatch],
    proto_file_name: str,
    java_package: str,
) -> str:
    """Generate MapStruct mapper interface source for matches from one proto file."""
    env = _get_template_env()
    template = env.get_template("mapstruct_mapper.java.j2")

    stem = Path(proto_file_name).stem
    parts = stem.split("_")
    pascal_stem = "".join(p.capitalize() for p in parts)
    mapper_class_name = f"{pascal_stem}MapStructMapper"
    proto_outer_class = f"{pascal_stem}Proto"

    methods = []
    reply_header_method = None
    has_reply_header = False

    for match in matches:
        method = _build_mapper_method(match, proto_outer_class)
        methods.append(method)

        header_data = _build_reply_header_default_method(match, proto_outer_class)
        if header_data is not None:
            has_reply_header = True
            reply_header_method = header_data

    return template.render(
        java_package=java_package,
        mapper_class_name=mapper_class_name,
        methods=methods,
        has_reply_header=has_reply_header,
        reply_header_method=reply_header_method,
    )


def generate_mapstruct_mappers(
    matches_by_proto: Dict[str, List[MessageMatch]],
    java_package: str,
    output_dir: str,
) -> List[str]:
    """Generate MapStruct mapper interfaces, one per proto file.

    Returns list of generated file paths.
    """
    mapstruct_dir = os.path.join(output_dir, "mapstruct_mapper")
    os.makedirs(mapstruct_dir, exist_ok=True)

    generated: List[str] = []
    for proto_file, matches in matches_by_proto.items():
        if not matches:
            continue
        source = generate_mapstruct_mapper(matches, proto_file, java_package)
        stem = Path(proto_file).stem
        parts = stem.split("_")
        pascal_stem = "".join(p.capitalize() for p in parts)
        file_name = f"{pascal_stem}MapStructMapper.java"
        file_path = os.path.join(mapstruct_dir, file_name)
        Path(file_path).write_text(source)
        generated.append(file_path)

    return generated


def generate_naming_strategy(java_package: str, output_dir: str) -> List[str]:
    """Generate ProtobufAccessorNamingStrategy.java and SPI service file.

    Returns list of generated file paths.
    """
    env = _get_template_env()
    generated: List[str] = []

    # 1. Generate ProtobufAccessorNamingStrategy.java
    spi_dir = os.path.join(output_dir, "mapstruct_mapper", "spi")
    os.makedirs(spi_dir, exist_ok=True)

    template = env.get_template("protobuf_accessor_naming_strategy.java.j2")
    source = template.render(java_package=java_package)
    file_path = os.path.join(spi_dir, "ProtobufAccessorNamingStrategy.java")
    Path(file_path).write_text(source)
    generated.append(file_path)

    # 2. Generate META-INF/services/ file
    meta_dir = os.path.join(output_dir, "mapstruct_mapper", "META-INF", "services")
    os.makedirs(meta_dir, exist_ok=True)

    spi_file_path = os.path.join(
        meta_dir, "org.mapstruct.ap.spi.AccessorNamingStrategy"
    )
    spi_class_name = f"{java_package}.mapstruct_mapper.spi.ProtobufAccessorNamingStrategy"
    Path(spi_file_path).write_text(spi_class_name + "\n")
    generated.append(spi_file_path)

    return generated


def generate_maven_integration_doc(
    matches_by_proto: Dict[str, List[MessageMatch]],
    java_package: str,
    output_dir: str,
) -> str:
    """Generate MAVEN_INTEGRATION.md with project-specific names.

    Derives example mapper/DTO names from actual matches so the guide
    contains real class names instead of hardcoded placeholders.

    Returns the generated file path.
    """
    env = _get_template_env()
    template = env.get_template("mapstruct_maven_integration.md.j2")

    java_package_path = java_package.replace(".", "/")

    # Derive example names from actual matches
    example_mapper = ""
    example_dto = ""
    for proto_file, matches in matches_by_proto.items():
        if not matches:
            continue
        stem = Path(proto_file).stem
        parts = stem.split("_")
        pascal_stem = "".join(p.capitalize() for p in parts)
        example_mapper = f"{pascal_stem}MapStructMapper"
        example_dto = matches[0].cpp_message.original_name
        break

    source = template.render(
        java_package=java_package,
        java_package_path=java_package_path,
        example_mapper=example_mapper,
        example_dto=example_dto,
    )

    mapstruct_dir = os.path.join(output_dir, "mapstruct_mapper")
    os.makedirs(mapstruct_dir, exist_ok=True)

    file_path = os.path.join(mapstruct_dir, "MAVEN_INTEGRATION.md")
    Path(file_path).write_text(source)
    return file_path
