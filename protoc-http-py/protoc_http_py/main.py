import argparse
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import subprocess
import tempfile
import sys
import json


# Simple representations
@dataclass
class ProtoField:
    name: str
    type: str

@dataclass
class ProtoMessage:
    name: str
    fields: List[ProtoField] = field(default_factory=list)
    nested_messages: Dict[str, 'ProtoMessage'] = field(default_factory=dict)

@dataclass
class ProtoEnum:
    name: str
    values: Dict[str, int] = field(default_factory=dict)

@dataclass
class ProtoRpc:
    name: str
    input_type: str
    output_type: str

@dataclass
class ProtoService:
    name: str
    rpcs: List[ProtoRpc] = field(default_factory=list)

@dataclass
class ProtoFile:
    package: Optional[str]
    file_name: str
    messages: Dict[str, ProtoMessage]
    enums: Dict[str, ProtoEnum]
    services: List[ProtoService]


SCALAR_TYPE_MAP_VB = {
    'string': 'String',
    'int32': 'Integer',
    'int64': 'Long',
    'uint32': 'UInteger',
    'uint64': 'ULong',
    'bool': 'Boolean',
    'float': 'Single',
    'double': 'Double',
    'bytes': 'Byte()',  # represent bytes as byte array
}

SCALAR_TYPE_MAP_JSON = {
    'string': {'type': 'string'},
    'int32': {'type': 'integer', 'format': 'int32'},
    'int64': {'type': 'integer', 'format': 'int64'},
    'uint32': {'type': 'integer', 'format': 'uint32', 'minimum': 0},
    'uint64': {'type': 'integer', 'format': 'uint64', 'minimum': 0},
    'sint32': {'type': 'integer', 'format': 'int32'},
    'sint64': {'type': 'integer', 'format': 'int64'},
    'fixed32': {'type': 'integer', 'format': 'uint32', 'minimum': 0},
    'fixed64': {'type': 'integer', 'format': 'uint64', 'minimum': 0},
    'sfixed32': {'type': 'integer', 'format': 'int32'},
    'sfixed64': {'type': 'integer', 'format': 'int64'},
    'bool': {'type': 'boolean'},
    'float': {'type': 'number', 'format': 'float'},
    'double': {'type': 'number', 'format': 'double'},
    'bytes': {'type': 'string', 'contentEncoding': 'base64'},
}

# VB.NET reserved keywords that must be escaped with square brackets when used as identifiers
# Source: https://learn.microsoft.com/en-us/dotnet/visual-basic/language-reference/keywords/
VB_RESERVED_KEYWORDS = frozenset([
    'AddHandler', 'AddressOf', 'Alias', 'And', 'AndAlso', 'As', 'Boolean', 'ByRef', 'Byte', 'ByVal',
    'Call', 'Case', 'Catch', 'CBool', 'CByte', 'CChar', 'CDate', 'CDbl', 'CDec', 'Char', 'CInt',
    'Class', 'CLng', 'CObj', 'Const', 'Continue', 'CSByte', 'CShort', 'CSng', 'CStr', 'CType',
    'CUInt', 'CULng', 'CUShort', 'Date', 'Decimal', 'Declare', 'Default', 'Delegate', 'Dim',
    'DirectCast', 'Do', 'Double', 'Each', 'Else', 'ElseIf', 'End', 'EndIf', 'Enum', 'Erase',
    'Error', 'Event', 'Exit', 'False', 'Finally', 'For', 'Friend', 'Function', 'Get', 'GetType',
    'GetXMLNamespace', 'Global', 'GoTo', 'Handles', 'If', 'Implements', 'Imports', 'In', 'Inherits',
    'Integer', 'Interface', 'Is', 'IsNot', 'Lib', 'Like', 'Long', 'Loop', 'Me', 'Mod', 'Module',
    'MustInherit', 'MustOverride', 'MyBase', 'MyClass', 'NameOf', 'Namespace', 'Narrowing', 'New',
    'Next', 'Not', 'Nothing', 'NotInheritable', 'NotOverridable', 'Object', 'Of', 'Operator',
    'Option', 'Optional', 'Or', 'OrElse', 'Overloads', 'Overridable', 'Overrides', 'ParamArray',
    'Partial', 'Private', 'Property', 'Protected', 'Public', 'RaiseEvent', 'ReadOnly', 'ReDim',
    'REM', 'RemoveHandler', 'Resume', 'Return', 'SByte', 'Select', 'Set', 'Shadows', 'Shared',
    'Short', 'Single', 'Static', 'Step', 'Stop', 'String', 'Structure', 'Sub', 'SyncLock', 'Then',
    'Throw', 'To', 'True', 'Try', 'TryCast', 'TypeOf', 'UInteger', 'ULong', 'UShort', 'Using',
    'When', 'While', 'Widening', 'With', 'WithEvents', 'WriteOnly', 'Xor'
])


def parse_proto(proto_path: str) -> ProtoFile:
    # Deprecated regex-based parser retained for fallback but not used by default.
    with open(proto_path, 'r', encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"\s+", " ", text)
    package_match = re.search(r"\bpackage\s+([a-zA-Z_][\w\.]*)\s*;", text)
    package = package_match.group(1) if package_match else None

    def _extract_top_level_blocks(s: str, keyword: str):
        blocks = []
        i = 0
        depth = 0
        while i < len(s):
            ch = s[i]
            if ch == '{':
                depth += 1
                i += 1
                continue
            if ch == '}':
                depth -= 1
                i += 1
                continue
            if depth == 0:
                m = re.match(rf"\b{keyword}\s+([A-Za-z_][\w]*)\s*\{{", s[i:])
                if m:
                    name = m.group(1)
                    brace_pos = i + m.end() - 1
                    d = 1
                    j = brace_pos + 1
                    while j < len(s) and d > 0:
                        cj = s[j]
                        if cj == '{':
                            d += 1
                        elif cj == '}':
                            d -= 1
                        j += 1
                    end_brace = j - 1
                    body = s[brace_pos + 1:end_brace]
                    blocks.append((name, body, i, end_brace + 1))
                    i = end_brace + 1
                    continue
            i += 1
        return blocks

    def _extract_direct_blocks(s: str, keyword: str):
        blocks = []
        i = 0
        depth = 0
        while i < len(s):
            ch = s[i]
            if ch == '{':
                depth += 1
                i += 1
                continue
            if ch == '}':
                depth -= 1
                i += 1
                continue
            if depth == 0:
                m = re.match(rf"\b{keyword}\s+([A-Za-z_][\w]*)\s*\{{", s[i:])
                if m:
                    name = m.group(1)
                    brace_pos = i + m.end() - 1
                    d = 1
                    j = brace_pos + 1
                    while j < len(s) and d > 0:
                        cj = s[j]
                        if cj == '{':
                            d += 1
                        elif cj == '}':
                            d -= 1
                        j += 1
                    end_brace = j - 1
                    body = s[brace_pos + 1:end_brace]
                    blocks.append((name, body, i, end_brace + 1))
                    i = end_brace + 1
                    continue
            i += 1
        return blocks

    def _parse_message(name: str, body: str, parent_path: List[str]) -> ProtoMessage:
        nested_blocks = _extract_direct_blocks(body, 'message')
        parts = []
        last = 0
        for _, _, start, end in nested_blocks:
            parts.append(body[last:start])
            last = end
        parts.append(body[last:])
        field_src = ''.join(parts)

        fields: List[ProtoField] = []
        current_path = parent_path + [name]
        for field_match in re.finditer(r"(repeated\s+)?([A-Za-z_][\w\.]*)\s+([A-Za-z_][\w]*)\s*=\s*\d+\s*;", field_src):
            repeated = field_match.group(1)
            ftype = field_match.group(2)
            fname = field_match.group(3)
            if '.' not in ftype:
                for child_name, _, _, _ in nested_blocks:
                    if ftype == child_name:
                        ftype = '.'.join(current_path + [ftype])
                        break
            fields.append(ProtoField(name=fname, type=("repeated " + ftype) if repeated else ftype))

        nested_messages: Dict[str, ProtoMessage] = {}
        for child_name, child_body, _, _ in nested_blocks:
            child_msg = _parse_message(child_name, child_body, current_path)
            nested_messages[child_name] = child_msg

        return ProtoMessage(name=name, fields=fields, nested_messages=nested_messages)

    enums: Dict[str, ProtoEnum] = {}
    for e in re.finditer(r"\benum\s+([A-Za-z_][\w]*)\s*\{(.*?)\}", text):
        enum_name = e.group(1)
        body = e.group(2)
        values: Dict[str, int] = {}
        for val in re.finditer(r"([A-Za-z_][\w]*)\s*=\s*(\d+)\s*;", body):
            values[val.group(1)] = int(val.group(2))
        enums[enum_name] = ProtoEnum(name=enum_name, values=values)

    messages: Dict[str, ProtoMessage] = {}
    for msg_name, body, _, _ in _extract_top_level_blocks(text, 'message'):
        messages[msg_name] = _parse_message(msg_name, body, [])

    services: List[ProtoService] = []
    for svc_name, body, _, _ in _extract_top_level_blocks(text, 'service'):
        rpcs: List[ProtoRpc] = []
        for rpc in re.finditer(r"\brpc\s+([A-Za-z_][\w]*)\s*\(\s*(stream\s+)?([A-Za-z_][\w\.]*)\s*\)\s*returns\s*\(\s*(stream\s+)?([A-Za-z_][\w\.]*)\s*\)\s*\{?\s*\}?", body):
            rpc_name = rpc.group(1)
            in_stream = rpc.group(2)
            in_type = rpc.group(3)
            out_stream = rpc.group(4)
            out_type = rpc.group(5)
            if in_stream or out_stream:
                continue
            rpcs.append(ProtoRpc(name=rpc_name, input_type=in_type, output_type=out_type))
        services.append(ProtoService(name=svc_name, rpcs=rpcs))

    return ProtoFile(
        package=package,
        file_name=os.path.basename(proto_path),
        messages=messages,
        enums=enums,
        services=services,
    )


def parse_proto_via_descriptor(proto_path: str) -> ProtoFile:
    """Parse a .proto by invoking protoc to get a descriptor set and mapping it into our simple model."""
    try:
        from google.protobuf import descriptor_pb2 as d2
    except ImportError as e:
        raise RuntimeError("Missing dependency 'protobuf'. Please install protobuf>=4 to use descriptor-based parsing.") from e

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    includes = []
    # include the directory of the file and the repo proto root
    file_dir = os.path.dirname(os.path.abspath(proto_path))
    includes.append(file_dir)
    proto_root = os.path.join(repo_root, 'proto')
    if os.path.isdir(proto_root):
        includes.append(proto_root)

    # de-dup while preserving order
    seen = set()
    inc_args: List[str] = []
    for inc in includes:
        if inc and inc not in seen:
            seen.add(inc)
            inc_args.extend(['-I', inc])

    with tempfile.TemporaryDirectory() as td:
        desc_path = os.path.join(td, 'descriptor_set.pb')
        cmd = ['protoc', '--include_imports', f'--descriptor_set_out={desc_path}'] + inc_args + [proto_path]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except FileNotFoundError as e:
            raise RuntimeError("'protoc' not found. Please install Protocol Buffers compiler and ensure it is in PATH.") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"protoc failed: {e.stderr.decode('utf-8', errors='ignore')}") from e

        fds = d2.FileDescriptorSet()
        with open(desc_path, 'rb') as f:
            fds.ParseFromString(f.read())

    # Find the target file in the descriptor set (match by basename)
    base = os.path.basename(proto_path)
    target = None
    for f in fds.file:
        if f.name.endswith(base):
            target = f
            break
    if target is None:
        # Fallback: if only one file, use it
        if len(fds.file) == 1:
            target = fds.file[0]
        else:
            names = ', '.join(ff.name for ff in fds.file)
            raise RuntimeError(f"Could not locate target file '{base}' in descriptor set. Found: {names}")

    def type_name_from_field(fd) -> str:
        # handle scalar vs message/enum
        if fd.type in (
            d2.FieldDescriptorProto.TYPE_MESSAGE,
            d2.FieldDescriptorProto.TYPE_ENUM,
        ):
            tname = fd.type_name.lstrip('.')
            return tname
        SCALAR_MAP = {
            d2.FieldDescriptorProto.TYPE_STRING: 'string',
            d2.FieldDescriptorProto.TYPE_INT32: 'int32',
            d2.FieldDescriptorProto.TYPE_INT64: 'int64',
            d2.FieldDescriptorProto.TYPE_UINT32: 'uint32',
            d2.FieldDescriptorProto.TYPE_UINT64: 'uint64',
            d2.FieldDescriptorProto.TYPE_BOOL: 'bool',
            d2.FieldDescriptorProto.TYPE_FLOAT: 'float',
            d2.FieldDescriptorProto.TYPE_DOUBLE: 'double',
            d2.FieldDescriptorProto.TYPE_BYTES: 'bytes',
        }
        return SCALAR_MAP.get(fd.type, 'string')  # default fallback

    def build_message(desc: 'd2.DescriptorProto') -> ProtoMessage:
        # fields
        fields: List[ProtoField] = []
        for f in desc.field:
            tname = type_name_from_field(f)
            is_repeated = f.label == d2.FieldDescriptorProto.LABEL_REPEATED
            if is_repeated:
                tname = 'repeated ' + tname
            fields.append(ProtoField(name=f.name, type=tname))
        # nested: skip map_entry types
        nested: Dict[str, ProtoMessage] = {}
        for n in desc.nested_type:
            if getattr(n.options, 'map_entry', False):
                continue
            nested[n.name] = build_message(n)
        return ProtoMessage(name=desc.name, fields=fields, nested_messages=nested)

    # top-level enums
    enums: Dict[str, ProtoEnum] = {}
    for e in target.enum_type:
        values = {v.name: v.number for v in e.value}
        enums[e.name] = ProtoEnum(name=e.name, values=values)

    # top-level messages
    messages: Dict[str, ProtoMessage] = {}
    for m in target.message_type:
        if getattr(m.options, 'map_entry', False):
            continue
        messages[m.name] = build_message(m)

    # services (unary only)
    services: List[ProtoService] = []
    for svc in target.service:
        rpcs: List[ProtoRpc] = []
        for method in svc.method:
            if method.client_streaming or method.server_streaming:
                continue
            in_type = method.input_type.lstrip('.')
            out_type = method.output_type.lstrip('.')
            rpcs.append(ProtoRpc(name=method.name, input_type=in_type, output_type=out_type))
        services.append(ProtoService(name=svc.name, rpcs=rpcs))

    return ProtoFile(
        package=target.package or None,
        file_name=os.path.basename(proto_path),
        messages=messages,
        enums=enums,
        services=services,
    )


def package_to_vb_namespace(pkg: Optional[str], file_name: str) -> str:
    if pkg:
        return to_pascal(pkg.replace('.', '_'))
    # fallback to file name (without extension)
    return to_pascal(os.path.splitext(file_name)[0])


def qualify_proto_type(proto_type: str, current_pkg: Optional[str], file_name: str) -> str:
    # Map scalar first
    if proto_type in SCALAR_TYPE_MAP_VB:
        return SCALAR_TYPE_MAP_VB[proto_type]
    # Handle dotted types: could be nested (Outer.Inner) or package-qualified (pkg.Outer.Inner)
    if '.' in proto_type:
        parts = proto_type.split('.')
        # Find the first segment that looks like a Type (starts with uppercase)
        type_start = None
        for idx, seg in enumerate(parts):
            if seg and seg[0].isupper():
                type_start = idx
                break
        if type_start is None:
            # No uppercase segments: treat last as type in a package
            pkg = '.'.join(parts[:-1])
            type_name = parts[-1]
            if current_pkg and pkg == current_pkg:
                return type_name
            target_ns = package_to_vb_namespace(pkg, file_name)
            return f"{target_ns}.{type_name}"
        elif type_start == 0:
            # Starts with a Type: nested type within current namespace/file
            return proto_type
        else:
            # Has a package prefix then type chain
            pkg = '.'.join(parts[:type_start])
            type_chain = '.'.join(parts[type_start:])
            if current_pkg and pkg == current_pkg:
                return type_chain
            target_ns = package_to_vb_namespace(pkg, file_name)
            return f"{target_ns}.{type_chain}"
    # Non-dotted: assume within same namespace as current file
    return proto_type


def vb_type(proto_type: str, current_pkg: Optional[str], file_name: str) -> str:
    repeated = False
    if proto_type.startswith('repeated '):
        repeated = True
        proto_type = proto_type[len('repeated '):]
    base = qualify_proto_type(proto_type, current_pkg, file_name)
    if repeated:
        return f"List(Of {base})"
    return base


def to_pascal(name: str) -> str:
    parts = re.split(r"[_\-]", name)
    return ''.join(p[:1].upper() + p[1:] for p in parts if p)


def to_camel(name: str, message_name: Optional[str] = None) -> str:
    """Convert snake_case or kebab-case to lowerCamelCase.

    Special case: If message_name is exactly "msgHdr", preserve the
    original field name without conversion.

    Args:
        name: Field name to convert
        message_name: Name of the containing message (for special logic)

    Returns:
        Converted field name (or original if msgHdr special case)
    """
    # Special case: msgHdr messages preserve exact field names
    if message_name == "msgHdr":
        return name

    # Standard conversion: Convert snake_case or kebab-case to lowerCamelCase
    parts = re.split(r"[_\-]", name)
    if not parts:
        return name
    first = parts[0].lower() if parts[0] else ""
    rest = ''.join(p[:1].upper() + p[1:] for p in parts[1:] if p)
    return first + rest


def to_kebab(name: str) -> str:
    """Convert names to kebab-case.
    Handles:
    - PascalCase/camelCase: SayHello -> say-hello, GetHTTPInfo -> get-http-info
    - snake_case: say_hello -> say-hello
    - already-kebab: say-hello -> say-hello
    - digits boundaries: Foo2Bar -> foo-2-bar
    - Special case: N2 pattern converts to -n2- (not -n-2-)
    """
    if not name:
        return name
    # If contains separators, split and re-join lowercased
    if '_' in name or '-' in name:
        parts = re.split(r"[_\-]+", name)
        return '-'.join(p.lower() for p in parts if p)
    s = name
    # Split acronym followed by normal case: HTTPInfo -> HTTP-Info
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", s)
    # Split lower/digit to upper: sayHello -> say-Hello, v2API -> v2-API
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s)
    # Split letters and digits boundaries
    s = re.sub(r"([A-Za-z])([0-9])", r"\1-\2", s)
    s = re.sub(r"([0-9])([A-Za-z])", r"\1-\2", s)
    # Normalize multiple dashes and lowercase
    s = re.sub(r"-{2,}", "-", s)
    result = s.lower()

    # Special case: N2 should be -n2- not -n-2-
    # Replace any occurrence of "-n-2-" with "-n2-"
    result = result.replace('-n-2-', '-n2-')
    # Handle edge cases: starting with "n-2-" or ending with "-n-2"
    if result.startswith('n-2-'):
        result = 'n2-' + result[4:]
    if result.endswith('-n-2'):
        result = result[:-4] + '-n2'
    # Handle standalone "n-2"
    if result == 'n-2':
        result = 'n2'

    return result


def escape_vb_identifier(name: str) -> str:
    """Escape VB.NET reserved keywords by wrapping them in square brackets.

    Args:
        name: The identifier name (e.g., property name)

    Returns:
        The escaped identifier if it's a reserved keyword, otherwise the name unchanged.

    Examples:
        escape_vb_identifier("Error") -> "[Error]"
        escape_vb_identifier("String") -> "[String]"
        escape_vb_identifier("UserName") -> "UserName"
    """
    if name in VB_RESERVED_KEYWORDS:
        return f"[{name}]"
    return name


def split_rpc_name_and_version(name: str) -> (str, str):
    """Split an RPC method name into (base_name, version_segment).
    - If name ends with 'V' followed by digits (e.g., FooV2), returns (Foo, 'v2').
    - Otherwise returns (name, 'v1').
    The version segment is always lower-case.
    """
    if not name:
        return name, "v1"
    m = re.match(r"^(?P<base>.+?)V(?P<ver>[0-9]+)$", name)
    if m and m.group('base'):
        base = m.group('base')
        ver = m.group('ver')
        return base, f"v{ver.lower()}"
    return name, "v1"


# JSON Schema Generation Functions

def qualify_json_schema_ref(proto_type: str, current_pkg: Optional[str], file_name: str) -> str:
    """Generate JSON Schema $ref for a proto type.

    Handles:
    - Nested types: Outer.Inner → "#/$defs/Outer.Inner"
    - Same package: Foo → "#/$defs/Foo"
    - Cross-package: common.Ticker → "common.json#/$defs/Ticker"

    Args:
        proto_type: Proto type name (possibly qualified)
        current_pkg: Current proto package name
        file_name: Name of current proto file

    Returns:
        JSON Schema $ref string
    """
    # Handle nested types and cross-package refs
    if '.' in proto_type:
        parts = proto_type.split('.')
        # Check if starts with uppercase (type name, not package)
        if parts[0] and parts[0][0].isupper():
            # Nested type in current file
            return f"#/$defs/{proto_type}"
        # Find where package ends and type begins
        type_start = next((i for i, p in enumerate(parts) if p and p[0].isupper()), None)
        if type_start is None or type_start == 0:
            # All lowercase or starts with type - same file
            return f"#/$defs/{proto_type}"
        # Cross-package reference
        pkg = '.'.join(parts[:type_start])
        type_name = '.'.join(parts[type_start:])
        if pkg == current_pkg:
            return f"#/$defs/{type_name}"
        # Different package - use file reference
        pkg_file = pkg.split('.')[-1]  # Last segment as filename
        return f"{pkg_file}.json#/$defs/{type_name}"
    # Simple type in current file
    return f"#/$defs/{proto_type}"


def get_json_schema_type(proto_type: str, current_pkg: Optional[str], file_name: str) -> dict:
    """Convert proto type to JSON Schema type definition.

    Args:
        proto_type: Proto type string (may include 'repeated ' prefix)
        current_pkg: Current proto package name
        file_name: Name of the proto file

    Returns:
        JSON Schema type dict (may be {'type': 'array', 'items': {...}} for repeated)
    """
    # Handle repeated fields
    if proto_type.startswith('repeated '):
        base_type = proto_type[len('repeated '):]
        base_schema = get_json_schema_type(base_type, current_pkg, file_name)
        return {'type': 'array', 'items': base_schema}

    # Check scalar types
    if proto_type in SCALAR_TYPE_MAP_JSON:
        return SCALAR_TYPE_MAP_JSON[proto_type].copy()

    # Complex type - use $ref
    return {'$ref': qualify_json_schema_ref(proto_type, current_pkg, file_name)}


def build_enum_schema(enum: ProtoEnum) -> dict:
    """Build JSON Schema for an enum type.

    Args:
        enum: ProtoEnum to convert

    Returns:
        JSON Schema dict for the enum
    """
    enum_values = list(enum.values.keys())
    value_descriptions = ', '.join(f"{k}={v}" for k, v in enum.values.items())
    return {
        'type': 'string',
        'enum': enum_values,
        'description': f'Enum values: {value_descriptions}'
    }


def collect_message_schemas(msg: ProtoMessage, parent_path: List[str],
                           schemas: Dict[str, dict], current_pkg: Optional[str],
                           file_name: str):
    """Recursively collect message and nested message schemas.

    Args:
        msg: ProtoMessage to process
        parent_path: Path of parent messages (for nested types)
        schemas: Dict to populate with schema definitions
        current_pkg: Current proto package name
        file_name: Name of the proto file
    """
    current_path = parent_path + [msg.name]
    qualified_name = '.'.join(current_path)

    # Build schema for this message
    schema = {
        'type': 'object',
        'properties': {},
        'additionalProperties': False
    }

    for field in msg.fields:
        field_name = to_camel(field.name, msg.name)  # Pass message name for msgHdr special case
        field_schema = get_json_schema_type(field.type, current_pkg, file_name)
        schema['properties'][field_name] = field_schema

    schemas[qualified_name] = schema

    # Process nested messages recursively
    for nested in msg.nested_messages.values():
        collect_message_schemas(nested, current_path, schemas, current_pkg, file_name)


def generate_json_schema(proto: ProtoFile, output_dir: str) -> str:
    """Generate JSON Schema file for a single proto file.

    Args:
        proto: Parsed proto file structure
        output_dir: Base output directory (json/ will be created inside)

    Returns:
        Path to generated JSON schema file
    """
    # Create json/ subdirectory
    json_dir = os.path.join(output_dir, 'json')
    os.makedirs(json_dir, exist_ok=True)

    # Build base schema structure
    base_name = os.path.splitext(proto.file_name)[0]
    schema_doc = {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': f'https://example.com/schemas/{base_name}.json',
        'title': f'Schemas for {proto.file_name}',
        'description': f'JSON Schema definitions for all messages and enums in {proto.file_name}',
        '$defs': {}
    }

    if proto.package:
        schema_doc['description'] += f' (package: {proto.package})'

    # Add enum schemas
    for enum in proto.enums.values():
        schema_doc['$defs'][enum.name] = build_enum_schema(enum)

    # Collect all message schemas (including nested)
    for msg in proto.messages.values():
        collect_message_schemas(msg, [], schema_doc['$defs'], proto.package, proto.file_name)

    # Write schema file
    output_path = os.path.join(json_dir, f'{base_name}.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schema_doc, f, indent=2, ensure_ascii=False)

    return output_path


def generate_json_schemas_for_directory(proto_files: List[str], out_dir: str) -> List[str]:
    """Generate JSON schemas for multiple proto files.

    Args:
        proto_files: List of proto file paths
        out_dir: Base output directory

    Returns:
        List of generated JSON schema file paths
    """
    generated = []
    for proto_file in proto_files:
        try:
            proto = parse_proto_via_descriptor(proto_file)
        except Exception as e:
            print(f"Warning: Failed to parse {proto_file} for JSON schema generation: {e}",
                  file=sys.stderr)
            continue

        try:
            json_path = generate_json_schema(proto, out_dir)
            generated.append(json_path)
        except Exception as e:
            print(f"Warning: Failed to generate JSON schema for {proto_file}: {e}",
                  file=sys.stderr)

    return generated


def generate_vb(proto: ProtoFile, namespace: Optional[str], compat: Optional[str] = None, shared_utility_name: Optional[str] = None) -> str:
    # Package takes priority: if proto has package, always use it
    # namespace parameter only used as fallback when no package
    if proto.package:
        ns = package_to_vb_namespace(proto.package, proto.file_name)
    else:
        ns = namespace or package_to_vb_namespace(None, proto.file_name)
    lines: List[str] = []
    # Imports
    lines.append("Imports System")
    use_hwr = (compat == "net40hwr")
    if use_hwr:
        lines.append("Imports System.Net")
        lines.append("Imports System.IO")
        lines.append("Imports System.Text")
        lines.append("Imports System.Collections.Generic")
        lines.append("Imports Newtonsoft.Json")
    else:
        lines.append("Imports System.Net.Http")
        lines.append("Imports System.Text")
        lines.append("Imports System.Threading")
        lines.append("Imports System.Threading.Tasks")
        lines.append("Imports System.Collections.Generic")
        lines.append("Imports Newtonsoft.Json")
    lines.append("")
    lines.append(f"Namespace {ns}")
    lines.append("")

    # Enums
    for enum in proto.enums.values():
        lines.append(f"    Public Enum {enum.name}")
        for k, v in enum.values.items():
            lines.append(f"        {k} = {v}")
        lines.append("    End Enum")
        lines.append("")

    # DTO classes
    def emit_message(msg: ProtoMessage, indent: int = 4):
        ind = ' ' * indent
        lines.append(f"{ind}Public Class {msg.name}")
        # Properties for fields
        for field in msg.fields:
            prop_type = vb_type(field.type, proto.package, proto.file_name)
            json_name = to_camel(field.name, msg.name)  # Pass message name for msgHdr special case
            prop_name = escape_vb_identifier(to_pascal(field.name))
            lines.append(f"{ind}    <JsonProperty(\"{json_name}\")>")
            lines.append(f"{ind}    Public Property {prop_name} As {prop_type}")
            lines.append("")
        # Nested messages
        for child in msg.nested_messages.values():
            emit_message(child, indent + 4)
        lines.append(f"{ind}End Class")
        lines.append("")

    for msg in proto.messages.values():
        emit_message(msg)

    # Service clients
    file_stub = os.path.splitext(proto.file_name)[0]
    for svc in proto.services:
        if use_hwr:
            lines.append(f"    Public Class {svc.name}Client")
            if shared_utility_name:
                # Use shared utility
                lines.append(f"        Private ReadOnly _httpUtility As {shared_utility_name}")
                lines.append("")
                lines.append("        Public Sub New(baseUrl As String)")
                lines.append("            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")")
                lines.append(f"            _httpUtility = New {shared_utility_name}(baseUrl)")
                lines.append("        End Sub")
                lines.append("")
                lines.append("        Public Sub New(baseUrl As String, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing)")
                lines.append("            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")")
                lines.append(f"            _httpUtility = New {shared_utility_name}(baseUrl)")
                lines.append("        End Sub")
            else:
                # Embed PostJson function
                lines.append("        Private ReadOnly _baseUrl As String")
                lines.append("")
                lines.append("        Public Sub New(baseUrl As String)")
                lines.append("            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")")
                lines.append("            _baseUrl = baseUrl.TrimEnd(\"/\"c)")
                lines.append("        End Sub")
                lines.append("")
                # Shared HTTP helper (synchronous) to reduce duplication
                lines.append("        Private Function PostJson(Of TReq, TResp)(relativePath As String, request As TReq, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As TResp")
                lines.append("            If request Is Nothing Then Throw New ArgumentNullException(\"request\")")
                lines.append("            Dim url As String = String.Format(\"{0}/{1}\", _baseUrl, relativePath.TrimStart(\"/\"c))")
                lines.append("            Dim json As String = JsonConvert.SerializeObject(request)")
                lines.append("            Dim data As Byte() = Encoding.UTF8.GetBytes(json)")
                lines.append("            Dim req As HttpWebRequest = CType(WebRequest.Create(url), HttpWebRequest)")
                lines.append("            req.Method = \"POST\"")
                lines.append("            req.ContentType = \"application/json\"")
                lines.append("            req.ContentLength = data.Length")
                lines.append("            If timeoutMs.HasValue Then req.Timeout = timeoutMs.Value")
                lines.append("            ")
                lines.append("            ' Add authorization headers if provided")
                lines.append("            If authHeaders IsNot Nothing Then")
                lines.append("                For Each kvp In authHeaders")
                lines.append("                    req.Headers.Add(kvp.Key, kvp.Value)")
                lines.append("                Next")
                lines.append("            End If")
                lines.append("            ")
                lines.append("            Using reqStream As Stream = req.GetRequestStream()")
                lines.append("                reqStream.Write(data, 0, data.Length)")
                lines.append("            End Using")
                lines.append("            Using resp As HttpWebResponse = CType(req.GetResponse(), HttpWebResponse)")
                lines.append("                Using respStream As Stream = resp.GetResponseStream()")
                lines.append("                    Using reader As New StreamReader(respStream, Encoding.UTF8)")
                lines.append("                        Dim respJson As String = reader.ReadToEnd()")
                lines.append("                        If String.IsNullOrWhiteSpace(respJson) Then")
                lines.append("                            Throw New InvalidOperationException(\"Received empty response from server\")")
                lines.append("                        End If")
                lines.append("                        Return JsonConvert.DeserializeObject(Of TResp)(respJson)")
                lines.append("                    End Using")
                lines.append("                End Using")
                lines.append("            End Using")
                lines.append("        End Function")
                lines.append("")
            lines.append("")
            for rpc in svc.rpcs:
                in_type = qualify_proto_type(rpc.input_type, proto.package, proto.file_name)
                out_type = qualify_proto_type(rpc.output_type, proto.package, proto.file_name)
                method_name = rpc.name
                base_rpc_name, version_seg = split_rpc_name_and_version(rpc.name)
                kebab_rpc = to_kebab(base_rpc_name)
                relative = f"\"/{file_stub}/{kebab_rpc}/{version_seg}\""

                if shared_utility_name:
                    # Use shared utility
                    lines.append(f"        Public Function {method_name}(request As {in_type}) As {out_type}")
                    lines.append(f"            Return {method_name}(request, Nothing, Nothing)")
                    lines.append("        End Function")
                    lines.append("")
                    lines.append(f"        Public Function {method_name}(request As {in_type}, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As {out_type}")
                    lines.append(f"            Return _httpUtility.PostJson(Of {in_type}, {out_type})({relative}, request, timeoutMs, authHeaders)")
                    lines.append("        End Function")
                    lines.append("")
                else:
                    # Use embedded PostJson
                    lines.append(f"        Public Function {method_name}(request As {in_type}) As {out_type}")
                    lines.append(f"            Return {method_name}(request, Nothing, Nothing)")
                    lines.append("        End Function")
                    lines.append("")
                    lines.append(f"        Public Function {method_name}(request As {in_type}, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As {out_type}")
                    lines.append(f"            Return PostJson(Of {in_type}, {out_type})({relative}, request, timeoutMs, authHeaders)")
                    lines.append("        End Function")
                    lines.append("")
            lines.append("    End Class")
            lines.append("")
        else:
            # net45 mode (async/await)
            lines.append(f"    Public Class {svc.name}Client")
            if shared_utility_name:
                # Use shared utility
                lines.append(f"        Private ReadOnly _httpUtility As {shared_utility_name}")
                lines.append("")
                lines.append("        Public Sub New(http As HttpClient, baseUrl As String)")
                lines.append("            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))")
                lines.append("            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")")
                lines.append(f"            _httpUtility = New {shared_utility_name}(http, baseUrl)")
                lines.append("        End Sub")
            else:
                # Embed PostJsonAsync function
                lines.append("        Private ReadOnly _http As HttpClient")
                lines.append("        Private ReadOnly _baseUrl As String")
                lines.append("")
                lines.append("        Public Sub New(http As HttpClient, baseUrl As String)")
                lines.append("            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))")
                lines.append("            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")")
                lines.append("            _http = http")
                lines.append("            _baseUrl = baseUrl.TrimEnd(\"/\"c)")
                lines.append("        End Sub")
                lines.append("")
                # Shared HTTP helper to reduce duplication
                lines.append("        Private Async Function PostJsonAsync(Of TReq, TResp)(relativePath As String, request As TReq, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of TResp)")
                lines.append("            If request Is Nothing Then Throw New ArgumentNullException(NameOf(request))")
                lines.append("            Dim url As String = String.Format(\"{0}/{1}\", _baseUrl, relativePath.TrimStart(\"/\"c))")
                lines.append("            Dim json As String = JsonConvert.SerializeObject(request)")
                lines.append("            Dim effectiveToken As CancellationToken = cancellationToken")
                lines.append("            If timeoutMs.HasValue Then")
                lines.append("                Using timeoutCts As New CancellationTokenSource(timeoutMs.Value)")
                lines.append("                    Using combined As CancellationTokenSource = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, timeoutCts.Token)")
                lines.append("                        effectiveToken = combined.Token")
                lines.append("                        Using content As New StringContent(json, Encoding.UTF8, \"application/json\")")
                lines.append("                            Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, effectiveToken).ConfigureAwait(False)")
                lines.append("                            If Not response.IsSuccessStatusCode Then")
                lines.append("                                Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)")
                lines.append("                                Throw New HttpRequestException($\"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}\")")
                lines.append("                            End If")
                lines.append("                            Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)")
                lines.append("                            If String.IsNullOrWhiteSpace(respJson) Then")
                lines.append("                                Throw New InvalidOperationException(\"Received empty response from server\")")
                lines.append("                            End If")
                lines.append("                            Return JsonConvert.DeserializeObject(Of TResp)(respJson)")
                lines.append("                        End Using")
                lines.append("                    End Using")
                lines.append("                End Using")
                lines.append("            Else")
                lines.append("                Using content As New StringContent(json, Encoding.UTF8, \"application/json\")")
                lines.append("                    Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, cancellationToken).ConfigureAwait(False)")
                lines.append("                    If Not response.IsSuccessStatusCode Then")
                lines.append("                        Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)")
                lines.append("                        Throw New HttpRequestException($\"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}\")")
                lines.append("                    End If")
                lines.append("                    Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)")
                lines.append("                    If String.IsNullOrWhiteSpace(respJson) Then")
                lines.append("                        Throw New InvalidOperationException(\"Received empty response from server\")")
                lines.append("                    End If")
                lines.append("                    Return JsonConvert.DeserializeObject(Of TResp)(respJson)")
                lines.append("                End Using")
                lines.append("            End If")
                lines.append("        End Function")
                lines.append("")
            lines.append("")
            for rpc in svc.rpcs:
                in_type = qualify_proto_type(rpc.input_type, proto.package, proto.file_name)
                out_type = qualify_proto_type(rpc.output_type, proto.package, proto.file_name)
                method_name = rpc.name + "Async"
                base_rpc_name, version_seg = split_rpc_name_and_version(rpc.name)
                kebab_rpc = to_kebab(base_rpc_name)
                relative = f"\"/{file_stub}/{kebab_rpc}/{version_seg}\""

                if shared_utility_name:
                    # Use shared utility
                    lines.append(f"        Public Function {method_name}(request As {in_type}) As Task(Of {out_type})")
                    lines.append(f"            Return {method_name}(request, CancellationToken.None)")
                    lines.append("        End Function")
                    lines.append("")
                    lines.append(f"        Public Function {method_name}(request As {in_type}, cancellationToken As CancellationToken) As Task(Of {out_type})")
                    lines.append(f"            Return {method_name}(request, cancellationToken, Nothing)")
                    lines.append("        End Function")
                    lines.append("")
                    lines.append(f"        Public Async Function {method_name}(request As {in_type}, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of {out_type})")
                    lines.append(f"            Return Await _httpUtility.PostJsonAsync(Of {in_type}, {out_type})({relative}, request, cancellationToken, timeoutMs).ConfigureAwait(False)")
                    lines.append("        End Function")
                    lines.append("")
                else:
                    # Use embedded PostJsonAsync
                    lines.append(f"        Public Function {method_name}(request As {in_type}) As Task(Of {out_type})")
                    lines.append(f"            Return {method_name}(request, CancellationToken.None)")
                    lines.append("        End Function")
                    lines.append("")
                    lines.append(f"        Public Function {method_name}(request As {in_type}, cancellationToken As CancellationToken) As Task(Of {out_type})")
                    lines.append(f"            Return {method_name}(request, cancellationToken, Nothing)")
                    lines.append("        End Function")
                    lines.append("")
                    lines.append(f"        Public Async Function {method_name}(request As {in_type}, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of {out_type})")
                    lines.append(f"            Return Await PostJsonAsync(Of {in_type}, {out_type})({relative}, request, cancellationToken, timeoutMs).ConfigureAwait(False)")
                    lines.append("        End Function")
                    lines.append("")
            lines.append("    End Class")
            lines.append("")

    lines.append("End Namespace")
    return "\n".join(lines)


def generate_http_utility_vb(utility_name: str, namespace: str, compat: Optional[str] = None) -> str:
    """Generate a shared HTTP utility class for the specified namespace and compatibility mode."""
    lines: List[str] = []
    # Imports
    lines.append("Imports System")
    use_hwr = (compat == "net40hwr")
    if use_hwr:
        lines.append("Imports System.Net")
        lines.append("Imports System.IO")
        lines.append("Imports System.Text")
        lines.append("Imports System.Collections.Generic")
        lines.append("Imports Newtonsoft.Json")
    else:
        lines.append("Imports System.Net.Http")
        lines.append("Imports System.Text")
        lines.append("Imports System.Threading")
        lines.append("Imports System.Threading.Tasks")
        lines.append("Imports System.Collections.Generic")
        lines.append("Imports Newtonsoft.Json")
    lines.append("")
    lines.append(f"Namespace {namespace}")
    lines.append("")

    lines.append(f"    Public Class {utility_name}")
    lines.append("        Private ReadOnly _baseUrl As String")
    if not use_hwr:
        lines.append("        Private ReadOnly _http As HttpClient")
    lines.append("")

    # Constructor
    if use_hwr:
        lines.append("        Public Sub New(baseUrl As String)")
        lines.append("            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")")
        lines.append("            _baseUrl = baseUrl.TrimEnd(\"/\"c)")
        lines.append("        End Sub")
    else:
        lines.append("        Public Sub New(http As HttpClient, baseUrl As String)")
        lines.append("            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))")
        lines.append("            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")")
        lines.append("            _http = http")
        lines.append("            _baseUrl = baseUrl.TrimEnd(\"/\"c)")
        lines.append("        End Sub")
    lines.append("")

    # PostJson function
    if use_hwr:
        lines.append("        Public Function PostJson(Of TReq, TResp)(relativePath As String, request As TReq, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As TResp")
        lines.append("            If request Is Nothing Then Throw New ArgumentNullException(\"request\")")
        lines.append("            Dim url As String = String.Format(\"{0}/{1}\", _baseUrl, relativePath.TrimStart(\"/\"c))")
        lines.append("            Dim json As String = JsonConvert.SerializeObject(request)")
        lines.append("            Dim data As Byte() = Encoding.UTF8.GetBytes(json)")
        lines.append("            Dim req As HttpWebRequest = CType(WebRequest.Create(url), HttpWebRequest)")
        lines.append("            req.Method = \"POST\"")
        lines.append("            req.ContentType = \"application/json\"")
        lines.append("            req.ContentLength = data.Length")
        lines.append("            If timeoutMs.HasValue Then req.Timeout = timeoutMs.Value")
        lines.append("            ")
        lines.append("            ' Add authorization headers if provided")
        lines.append("            If authHeaders IsNot Nothing Then")
        lines.append("                For Each kvp In authHeaders")
        lines.append("                    req.Headers.Add(kvp.Key, kvp.Value)")
        lines.append("                Next")
        lines.append("            End If")
        lines.append("            ")
        lines.append("            Using reqStream As Stream = req.GetRequestStream()")
        lines.append("                reqStream.Write(data, 0, data.Length)")
        lines.append("            End Using")
        lines.append("            Using resp As HttpWebResponse = CType(req.GetResponse(), HttpWebResponse)")
        lines.append("                Using respStream As Stream = resp.GetResponseStream()")
        lines.append("                    Using reader As New StreamReader(respStream, Encoding.UTF8)")
        lines.append("                        Dim respJson As String = reader.ReadToEnd()")
        lines.append("                        If String.IsNullOrWhiteSpace(respJson) Then")
        lines.append("                            Throw New InvalidOperationException(\"Received empty response from server\")")
        lines.append("                        End If")
        lines.append("                        Return JsonConvert.DeserializeObject(Of TResp)(respJson)")
        lines.append("                    End Using")
        lines.append("                End Using")
        lines.append("            End Using")
        lines.append("        End Function")
    else:
        lines.append("        Public Async Function PostJsonAsync(Of TReq, TResp)(relativePath As String, request As TReq, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of TResp)")
        lines.append("            If request Is Nothing Then Throw New ArgumentNullException(NameOf(request))")
        lines.append("            Dim url As String = String.Format(\"{0}/{1}\", _baseUrl, relativePath.TrimStart(\"/\"c))")
        lines.append("            Dim json As String = JsonConvert.SerializeObject(request)")
        lines.append("            Dim effectiveToken As CancellationToken = cancellationToken")
        lines.append("            If timeoutMs.HasValue Then")
        lines.append("                Using timeoutCts As New CancellationTokenSource(timeoutMs.Value)")
        lines.append("                    Using combined As CancellationTokenSource = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, timeoutCts.Token)")
        lines.append("                        effectiveToken = combined.Token")
        lines.append("                        Using content As New StringContent(json, Encoding.UTF8, \"application/json\")")
        lines.append("                            Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, effectiveToken).ConfigureAwait(False)")
        lines.append("                            If Not response.IsSuccessStatusCode Then")
        lines.append("                                Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)")
        lines.append("                                Throw New HttpRequestException($\"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}\")")
        lines.append("                            End If")
        lines.append("                            Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)")
        lines.append("                            If String.IsNullOrWhiteSpace(respJson) Then")
        lines.append("                                Throw New InvalidOperationException(\"Received empty response from server\")")
        lines.append("                            End If")
        lines.append("                            Return JsonConvert.DeserializeObject(Of TResp)(respJson)")
        lines.append("                        End Using")
        lines.append("                    End Using")
        lines.append("                End Using")
        lines.append("            Else")
        lines.append("                Using content As New StringContent(json, Encoding.UTF8, \"application/json\")")
        lines.append("                    Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, cancellationToken).ConfigureAwait(False)")
        lines.append("                    If Not response.IsSuccessStatusCode Then")
        lines.append("                        Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)")
        lines.append("                        Throw New HttpRequestException($\"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}\")")
        lines.append("                    End If")
        lines.append("                    Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)")
        lines.append("                    If String.IsNullOrWhiteSpace(respJson) Then")
        lines.append("                        Throw New InvalidOperationException(\"Received empty response from server\")")
        lines.append("                    End If")
        lines.append("                    Return JsonConvert.DeserializeObject(Of TResp)(respJson)")
        lines.append("                End Using")
        lines.append("            End If")
        lines.append("        End Function")

    lines.append("    End Class")
    lines.append("")
    lines.append("End Namespace")
    return "\n".join(lines)


def generate_directory_with_shared_utilities(proto_files: List[str], out_dir: str, namespace: Optional[str], compat: Optional[str] = None) -> List[str]:
    """Generate VB.NET files for multiple proto files with shared utilities when appropriate."""
    if not proto_files:
        return []

    # Group files by directory
    files_by_dir: Dict[str, List[str]] = {}
    for proto_file in proto_files:
        dir_path = os.path.dirname(proto_file)
        if dir_path not in files_by_dir:
            files_by_dir[dir_path] = []
        files_by_dir[dir_path].append(proto_file)

    generated: List[str] = []

    for dir_path, files in files_by_dir.items():
        if len(files) > 1:
            # Multiple files in same directory: generate shared utility
            dir_name = os.path.basename(dir_path) or "Root"
            utility_name = f"{to_pascal(dir_name)}HttpUtility"

            # Determine namespace for the utility - proto package takes priority
            try:
                first_proto = parse_proto_via_descriptor(files[0]) if files else None
                if first_proto and first_proto.package:
                    # Package exists, always use it (ignore CLI namespace)
                    utility_namespace = package_to_vb_namespace(first_proto.package, dir_name)
                else:
                    # No package, use CLI namespace or fallback to dir_name
                    utility_namespace = namespace or to_pascal(dir_name)
            except Exception:
                utility_namespace = namespace or to_pascal(dir_name)

            # Generate shared utility file
            utility_code = generate_http_utility_vb(utility_name, utility_namespace, compat=compat)
            os.makedirs(out_dir, exist_ok=True)
            utility_path = os.path.join(out_dir, f"{utility_name}.vb")
            with open(utility_path, 'w', encoding='utf-8') as f:
                f.write(utility_code)
            generated.append(utility_path)

            # Generate individual proto files using shared utility
            for proto_file in files:
                out_path = generate_with_shared_utility(proto_file, out_dir, namespace, utility_name, compat=compat)
                generated.append(out_path)
        else:
            # Single file in directory: generate without shared utility
            for proto_file in files:
                out_path = generate(proto_file, out_dir, namespace, compat=compat)
                generated.append(out_path)

    return generated


def generate_with_shared_utility(proto_path: str, out_dir: str, namespace: Optional[str], shared_utility_name: str, compat: Optional[str] = None) -> str:
    """Generate a VB.NET file using a shared utility class."""
    try:
        proto = parse_proto_via_descriptor(proto_path)
    except Exception as e:
        print(
            f"Warning: descriptor-based parsing failed for '{proto_path}' with {type(e).__name__}: {e}. Falling back to legacy regex parser.",
            file=sys.stderr,
        )
        proto = parse_proto(proto_path)

    vb_code = generate_vb(proto, namespace, compat=compat, shared_utility_name=shared_utility_name)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, os.path.splitext(os.path.basename(proto_path))[0] + ".vb")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(vb_code)
    return out_path


def generate(proto_path: str, out_dir: str, namespace: Optional[str], compat: Optional[str] = None) -> str:
    # Prefer descriptor-based parsing; fall back to legacy regex if protoc or protobuf is unavailable.
    try:
        proto = parse_proto_via_descriptor(proto_path)
    except Exception as e:
        print(
            f"Warning: descriptor-based parsing failed for '{proto_path}' with {type(e).__name__}: {e}. Falling back to legacy regex parser.",
            file=sys.stderr,
        )
        proto = parse_proto(proto_path)
    vb_code = generate_vb(proto, namespace, compat=compat)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, os.path.splitext(os.path.basename(proto_path))[0] + ".vb")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(vb_code)
    return out_path


def _find_proto_files(root: str) -> List[str]:
    files: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(".proto"):
                files.append(os.path.join(dirpath, fn))
    # Sort for deterministic output
    files.sort()
    return files


def main():
    parser = argparse.ArgumentParser(description="Generate VB.NET Http proxy client and DTOs from .proto files (unary RPCs only)")
    parser.add_argument("--proto", required=True, help="Path to a .proto file or a directory containing .proto files (recursively)")
    parser.add_argument("--out", required=True, help="Output directory for generated .vb file(s)")
    parser.add_argument("--namespace", required=False, help="VB.NET namespace for generated code (defaults to proto package or file name)")
    # Compatibility switches
    parser.add_argument("--net45", action="store_true", help="Emit .NET Framework 4.5 compatible VB.NET code (HttpClient + async/await)")
    parser.add_argument("--net40hwr", action="store_true", help="Emit .NET Framework 4.0 compatible VB.NET code using synchronous HttpWebRequest (no async/await)")
    # Backward-compat alias
    parser.add_argument("--net40", action="store_true", help="Alias of --net40hwr for backward compatibility")
    args = parser.parse_args()

    # Determine compatibility mode
    compat = None
    if args.net40hwr or args.net40:
        compat = "net40hwr"
    elif args.net45:
        compat = "net45"

    inputs: List[str]
    if os.path.isdir(args.proto):
        inputs = _find_proto_files(args.proto)
        if not inputs:
            print(f"No .proto files found under directory: {args.proto}")
            return
        generated = generate_directory_with_shared_utilities(inputs, args.out, args.namespace, compat=compat)
        print("Generated VB.NET:\n" + "\n".join(generated))

        # Generate JSON schemas
        json_schemas = generate_json_schemas_for_directory(inputs, args.out)
        if json_schemas:
            print("\nGenerated JSON Schemas:\n" + "\n".join(json_schemas))
    else:
        out_path = generate(args.proto, args.out, args.namespace, compat=compat)
        print(f"Generated VB.NET: {out_path}")

        # Generate JSON schema
        try:
            proto = parse_proto_via_descriptor(args.proto)
            json_path = generate_json_schema(proto, args.out)
            print(f"Generated JSON Schema: {json_path}")
        except Exception as e:
            print(f"Warning: Failed to generate JSON schema: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
