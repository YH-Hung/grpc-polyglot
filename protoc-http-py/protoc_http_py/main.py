import argparse
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Simple representations
@dataclass
class ProtoField:
    name: str
    type: str

@dataclass
class ProtoMessage:
    name: str
    fields: List[ProtoField] = field(default_factory=list)

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
    with open(proto_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Remove comments (// ... endline)
    text = re.sub(r"//.*", "", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    package_match = re.search(r"\bpackage\s+([a-zA-Z_][\w\.]*)\s*;", text)
    package = package_match.group(1) if package_match else None

    # Enums
    enums: Dict[str, ProtoEnum] = {}
    for e in re.finditer(r"enum\s+([A-Za-z_][\w]*)\s*\{(.*?)\}", text):
        enum_name = e.group(1)
        body = e.group(2)
        values: Dict[str, int] = {}
        for val in re.finditer(r"([A-Za-z_][\w]*)\s*=\s*(\d+)\s*;", body):
            values[val.group(1)] = int(val.group(2))
        enums[enum_name] = ProtoEnum(name=enum_name, values=values)

    # Messages
    messages: Dict[str, ProtoMessage] = {}
    for m in re.finditer(r"message\s+([A-Za-z_][\w]*)\s*\{(.*?)\}", text):
        msg_name = m.group(1)
        body = m.group(2)
        fields: List[ProtoField] = []
        # field lines like: type name = number;
        for field_match in re.finditer(r"(repeated\s+)?([A-Za-z_][\w\.]*)\s+([A-Za-z_][\w]*)\s*=\s*\d+\s*;", body):
            repeated = field_match.group(1)
            ftype = field_match.group(2)
            fname = field_match.group(3)
            # For this generator, we handle only scalar and message types; repeated treated as List(Of T)
            fields.append(ProtoField(name=fname, type=("repeated " + ftype) if repeated else ftype))
        messages[msg_name] = ProtoMessage(name=msg_name, fields=fields)

    # Services and RPCs
    services: List[ProtoService] = []
    for s in re.finditer(r"service\s+([A-Za-z_][\w]*)\s*\{(.*?)\}", text):
        svc_name = s.group(1)
        body = s.group(2)
        rpcs: List[ProtoRpc] = []
        for rpc in re.finditer(r"rpc\s+([A-Za-z_][\w]*)\s*\(\s*(stream\s+)?([A-Za-z_][\w\.]*)\s*\)\s*returns\s*\(\s*(stream\s+)?([A-Za-z_][\w\.]*)\s*\)\s*\{?\s*\}?", body):
            rpc_name = rpc.group(1)
            in_stream = rpc.group(2)
            in_type = rpc.group(3)
            out_stream = rpc.group(4)
            out_type = rpc.group(5)
            # Only unary: no stream prefix allowed
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


def package_to_vb_namespace(pkg: Optional[str], file_name: str) -> str:
    if pkg:
        return to_pascal(pkg.replace('.', '_'))
    # fallback to file name (without extension)
    return to_pascal(os.path.splitext(file_name)[0])


def qualify_proto_type(proto_type: str, current_pkg: Optional[str], file_name: str) -> str:
    # Map scalar first
    if proto_type in SCALAR_TYPE_MAP_VB:
        return SCALAR_TYPE_MAP_VB[proto_type]
    # Dotted types: package.type
    if '.' in proto_type:
        parts = proto_type.split('.')
        type_name = parts[-1]
        pkg = '.'.join(parts[:-1])
        # If same package as current, we can use unqualified type name
        if current_pkg and pkg == current_pkg:
            return type_name
        target_ns = package_to_vb_namespace(pkg, file_name)
        return f"{target_ns}.{type_name}"
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
    for msg in proto.messages.values():
        lines.append(f"    Public Class {msg.name}")
        if not msg.fields:
            lines.append("    End Class")
            lines.append("")
            continue
        for field in msg.fields:
            prop_type = vb_type(field.type, proto.package, proto.file_name)
            json_name = field.name
            prop_name = to_pascal(field.name)
            lines.append(f"        <JsonProperty(\"{json_name}\")>")
            lines.append(f"        Public Property {prop_name} As {prop_type}")
            lines.append("")
        lines.append("    End Class")
        lines.append("")

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
        lines.append("            _baseUrl = baseUrl.TrimEnd('/'c)")
        lines.append("        End Sub")
        lines.append("")
        for rpc in svc.rpcs:
            in_type = qualify_proto_type(rpc.input_type, proto.package, proto.file_name)
            out_type = qualify_proto_type(rpc.output_type, proto.package, proto.file_name)
            method_name = rpc.name + "Async"
            url = f"\"{{0}}/{file_stub}/{rpc.name}\""
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
    proto = parse_proto(proto_path)
    vb_code = generate_vb(proto, namespace)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, os.path.splitext(os.path.basename(proto_path))[0] + ".vb")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(vb_code)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate VB.NET Http proxy client and DTOs from a .proto (unary RPCs only)")
    parser.add_argument("--proto", required=True, help="Path to the .proto file")
    parser.add_argument("--out", required=True, help="Output directory for generated .vb file(s)")
    parser.add_argument("--namespace", required=False, help="VB.NET namespace for generated code (defaults to proto package or file name)")
    args = parser.parse_args()

    out_path = generate(args.proto, args.out, args.namespace)
    print(f"Generated: {out_path}")


if __name__ == "__main__":
    main()
