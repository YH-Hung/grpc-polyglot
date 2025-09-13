import argparse
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import subprocess
import tempfile
import sys


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


def to_camel(name: str) -> str:
    # Convert snake_case or kebab-case to lowerCamelCase
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
    return s.lower()


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


def generate_vb(proto: ProtoFile, namespace: Optional[str]) -> str:
    ns = namespace or package_to_vb_namespace(proto.package, proto.file_name)
    lines: List[str] = []
    # Imports
    lines.append("Imports System")
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
            json_name = to_camel(field.name)
            prop_name = to_pascal(field.name)
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
        # Only generate if there are unary rpc methods found
        lines.append(f"    Public Class {svc.name}Client")
        lines.append("        Private Shared ReadOnly _http As HttpClient = New HttpClient()")
        lines.append("        Private ReadOnly _baseUrl As String")
        lines.append("")
        lines.append("        Public Sub New(baseUrl As String)")
        lines.append("            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")")
        lines.append("            _baseUrl = baseUrl.TrimEnd(""/""c)")
        lines.append("        End Sub")
        lines.append("")
        for rpc in svc.rpcs:
            in_type = qualify_proto_type(rpc.input_type, proto.package, proto.file_name)
            out_type = qualify_proto_type(rpc.output_type, proto.package, proto.file_name)
            method_name = rpc.name + "Async"
            base_rpc_name, version_seg = split_rpc_name_and_version(rpc.name)
            kebab_rpc = to_kebab(base_rpc_name)
            url = f"\"{{0}}/{file_stub}/{kebab_rpc}/{version_seg}\""
            # Overload without token
            lines.append(f"        Public Function {method_name}(request As {in_type}) As Task(Of {out_type})")
            lines.append(f"            Return {method_name}(request, CancellationToken.None)")
            lines.append("        End Function")
            lines.append("")
            # With token
            lines.append(f"        Public Async Function {method_name}(request As {in_type}, cancellationToken As CancellationToken) As Task(Of {out_type})")
            lines.append("            If request Is Nothing Then Throw New ArgumentNullException(NameOf(request))")
            lines.append("            Dim url As String = String.Format(" + url + ", _baseUrl)")
            lines.append("            Dim json As String = JsonConvert.SerializeObject(request)")
            lines.append("            Using content As New StringContent(json, Encoding.UTF8, \"application/json\")")
            lines.append("                Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, cancellationToken).ConfigureAwait(False)")
            lines.append("                If Not response.IsSuccessStatusCode Then")
            lines.append("                    Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)")
            lines.append("                    Throw New HttpRequestException($\"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}\")")
            lines.append("                End If")
            lines.append("                Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)")
            lines.append(f"                Return JsonConvert.DeserializeObject(Of {out_type})(respJson)")
            lines.append("            End Using")
            lines.append("        End Function")
            lines.append("")
        lines.append("    End Class")
        lines.append("")

    lines.append("End Namespace")
    return "\n".join(lines)


def generate(proto_path: str, out_dir: str, namespace: Optional[str]) -> str:
    # Prefer descriptor-based parsing; fall back to legacy regex if protoc or protobuf is unavailable.
    try:
        proto = parse_proto_via_descriptor(proto_path)
    except Exception as e:
        print(
            f"Warning: descriptor-based parsing failed for '{proto_path}' with {type(e).__name__}: {e}. Falling back to legacy regex parser.",
            file=sys.stderr,
        )
        proto = parse_proto(proto_path)
    vb_code = generate_vb(proto, namespace)
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
    args = parser.parse_args()

    inputs: List[str]
    if os.path.isdir(args.proto):
        inputs = _find_proto_files(args.proto)
        if not inputs:
            print(f"No .proto files found under directory: {args.proto}")
            return
        generated: List[str] = []
        for p in inputs:
            out_path = generate(p, args.out, args.namespace)
            generated.append(out_path)
        print("Generated:\n" + "\n".join(generated))
    else:
        out_path = generate(args.proto, args.out, args.namespace)
        print(f"Generated: {out_path}")


if __name__ == "__main__":
    main()
