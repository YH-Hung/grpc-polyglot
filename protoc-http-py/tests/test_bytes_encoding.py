from pathlib import Path
import pytest
from protoc_http_py.main import parse_proto_via_descriptor, proto_has_bytes_field

REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    from google.protobuf import descriptor_pb2  # noqa: F401
    HAS_PROTOBUF = True
except ImportError:
    HAS_PROTOBUF = False


@pytest.mark.skipif(not HAS_PROTOBUF, reason="protobuf library not installed")
def test_proto_has_bytes_field_true_for_scalar():
    proto = parse_proto_via_descriptor(str(REPO_ROOT / "proto" / "bytes_test" / "bytes_only.proto"))
    assert proto_has_bytes_field(proto) is True


@pytest.mark.skipif(not HAS_PROTOBUF, reason="protobuf library not installed")
def test_proto_has_bytes_field_false_for_helloworld():
    proto = parse_proto_via_descriptor(str(REPO_ROOT / "proto" / "simple" / "helloworld.proto"))
    assert proto_has_bytes_field(proto) is False


from protoc_http_py.main import emit_bytes_helpers_vb_lines

def test_emit_bytes_helpers_contains_required_classes():
    lines = emit_bytes_helpers_vb_lines(indent=4)
    text = "\n".join(lines)
    assert "Public NotInheritable Class ProtoBytesEncoding" in text
    assert "Public Class BytesStringConverter" in text
    assert "Inherits JsonConverter" in text
    assert "Public Shared Property [Default] As Encoding" in text
    assert "Public Shared Sub UseEncoding(encodingName As String)" in text
    # Whitelist values present
    for enc in ("utf-8", "big5", "gb2312", "gbk", "shift_jis", "ascii", "iso-8859-1", "utf-16"):
        assert f'"{enc}"' in text
    # ReadJson decodes base64 then GetString
    assert "Convert.FromBase64String" in text
    assert "ProtoBytesEncoding.Default.GetString" in text
    # WriteJson encodes via current encoding then base64
    assert "ProtoBytesEncoding.Default.GetBytes" in text
    assert "Convert.ToBase64String" in text


from protoc_http_py.main import generate

@pytest.mark.skipif(not HAS_PROTOBUF, reason="protobuf library not installed")
def test_standalone_proto_emits_helpers_inline(tmp_path):
    proto = REPO_ROOT / "proto" / "bytes_test" / "bytes_only.proto"
    out_path = Path(generate(str(proto), str(tmp_path), None))
    text = out_path.read_text(encoding="utf-8")
    # Helpers present
    assert "Public NotInheritable Class ProtoBytesEncoding" in text
    assert "Public Class BytesStringConverter" in text
    # Scalar bytes field carries the converter attribute
    assert "<JsonConverter(GetType(BytesStringConverter))>" in text
    # Property still typed As String
    assert "Public Property Body As String" in text
    # Repeated bytes uses ItemConverterType, NOT a separate JsonConverter attribute
    assert "ItemConverterType:=GetType(BytesStringConverter)" in text
    # Nested message bytes field also gets the attribute
    # NestedHolder.Inner.NestedBlob should also be wrapped
    assert text.count("<JsonConverter(GetType(BytesStringConverter))>") >= 3  # body, top_level, nested_blob


@pytest.mark.skipif(not HAS_PROTOBUF, reason="protobuf library not installed")
def test_standalone_proto_without_bytes_skips_helpers(tmp_path):
    proto = REPO_ROOT / "proto" / "simple" / "helloworld.proto"
    out_path = Path(generate(str(proto), str(tmp_path), None))
    text = out_path.read_text(encoding="utf-8")
    assert "BytesStringConverter" not in text
    assert "ProtoBytesEncoding" not in text


from protoc_http_py.main import generate_directory_with_shared_utilities

@pytest.mark.skipif(not HAS_PROTOBUF, reason="protobuf library not installed")
def test_shared_utility_emits_helpers_once(tmp_path):
    proto_dir = REPO_ROOT / "proto" / "bytes_test" / "secrets"
    files = sorted(str(p) for p in proto_dir.glob("*.proto"))
    out_dir = tmp_path / "out_secrets"
    out_dir.mkdir()
    generated = generate_directory_with_shared_utilities(files, str(out_dir), None)

    utility_path = next(p for p in generated if p.endswith("HttpUtility.vb"))
    note_path = next(p for p in generated if p.endswith("note-service.vb"))
    audit_path = next(p for p in generated if p.endswith("audit-service.vb"))

    utility = Path(utility_path).read_text(encoding="utf-8")
    note = Path(note_path).read_text(encoding="utf-8")
    audit = Path(audit_path).read_text(encoding="utf-8")

    # Helpers emitted exactly once — in the shared utility
    assert "Public Class BytesStringConverter" in utility
    assert "Public NotInheritable Class ProtoBytesEncoding" in utility
    assert "Public Class BytesStringConverter" not in note
    assert "Public Class BytesStringConverter" not in audit

    # Both DTO files reference the converter on their bytes fields
    assert "<JsonConverter(GetType(BytesStringConverter))>" in note
    assert "<JsonConverter(GetType(BytesStringConverter))>" in audit


@pytest.mark.skipif(not HAS_PROTOBUF, reason="protobuf library not installed")
def test_shared_utility_no_bytes_skips_helpers(tmp_path):
    # Existing complex/ directory has no bytes fields
    proto_dir = REPO_ROOT / "proto" / "complex"
    files = sorted(str(p) for p in proto_dir.rglob("*.proto"))
    out_dir = tmp_path / "out_complex"
    out_dir.mkdir()
    generated = generate_directory_with_shared_utilities(files, str(out_dir), None)
    utility_path = next(p for p in generated if p.endswith("HttpUtility.vb"))
    text = Path(utility_path).read_text(encoding="utf-8")
    assert "BytesStringConverter" not in text
    assert "ProtoBytesEncoding" not in text


@pytest.mark.skipif(not HAS_PROTOBUF, reason="protobuf library not installed")
def test_cross_namespace_uses_qualified_converter(tmp_path):
    """When two protos in the same directory have different packages, the
    shared utility lives in one namespace; DTO files in other namespaces must
    fully-qualify the converter type."""
    d = tmp_path / "mixed"
    d.mkdir()
    (d / "alpha.proto").write_text(
        'syntax = "proto3";\npackage alpha;\nmessage A { bytes b = 1; }\nservice S1 { rpc F(A) returns (A) {} }\n'
    )
    (d / "beta.proto").write_text(
        'syntax = "proto3";\npackage beta;\nmessage B { bytes b = 1; }\nservice S2 { rpc G(B) returns (B) {} }\n'
    )
    out_dir = tmp_path / "out_mixed"
    out_dir.mkdir()
    files = sorted(str(p) for p in d.glob("*.proto"))
    generated = generate_directory_with_shared_utilities(files, str(out_dir), None)
    utility = next(p for p in generated if p.endswith("HttpUtility.vb"))
    utility_text = Path(utility).read_text(encoding="utf-8")
    import re
    m = re.search(r"^Namespace (\S+)$", utility_text, flags=re.MULTILINE)
    util_ns = m.group(1)

    for vb_name in ("alpha.vb", "beta.vb"):
        path = next(p for p in generated if p.endswith(vb_name))
        text = Path(path).read_text(encoding="utf-8")
        ns_match = re.search(r"^Namespace (\S+)$", text, flags=re.MULTILINE)
        dto_ns = ns_match.group(1)
        if dto_ns != util_ns:
            assert f"GetType({util_ns}.BytesStringConverter)" in text, (
                f"Expected qualified GetType({util_ns}.BytesStringConverter) in {vb_name} (ns={dto_ns}), got:\n{text}"
            )
        else:
            assert "GetType(BytesStringConverter)" in text


def test_shared_utility_emits_helpers_when_descriptor_parser_fails(tmp_path, monkeypatch):
    """Regression: pre-scan must fall back to the regex parser when descriptor
    parsing fails. Otherwise the utility skips helper emission while per-file
    DTO generation still emits <JsonConverter(...)> attributes — producing VB
    that references a class that doesn't exist."""
    from protoc_http_py import main as main_mod

    real_descriptor = main_mod.parse_proto_via_descriptor

    def always_fail(path):
        raise RuntimeError("simulated protoc failure")

    monkeypatch.setattr(main_mod, "parse_proto_via_descriptor", always_fail)

    proto_dir = REPO_ROOT / "proto" / "bytes_test" / "secrets"
    files = sorted(str(p) for p in proto_dir.glob("*.proto"))
    out_dir = tmp_path / "out_fallback"
    out_dir.mkdir()
    generated = main_mod.generate_directory_with_shared_utilities(
        files, str(out_dir), None,
    )

    utility_path = next(p for p in generated if p.endswith("HttpUtility.vb"))
    note_path = next(p for p in generated if p.endswith("note-service.vb"))
    utility = Path(utility_path).read_text(encoding="utf-8")
    note = Path(note_path).read_text(encoding="utf-8")

    # Helpers MUST be present in the utility even though the descriptor parser failed
    assert "Public Class BytesStringConverter" in utility, (
        "Pre-scan failed to detect bytes via regex fallback; utility is missing helpers."
    )
    # And the DTO file must still reference the (now-existing) converter
    assert "<JsonConverter(GetType(BytesStringConverter))>" in note


@pytest.mark.skipif(not HAS_PROTOBUF, reason="protobuf library not installed")
def test_converter_uses_default_encoding_at_runtime(tmp_path):
    """The generated converter must read encoding from ProtoBytesEncoding.Default,
    not from a captured/baked-in value, so the consuming app can switch at runtime."""
    proto = REPO_ROOT / "proto" / "bytes_test" / "bytes_only.proto"
    out_path = Path(generate(str(proto), str(tmp_path), None))
    text = out_path.read_text(encoding="utf-8")

    # Slice out just the BytesStringConverter class body
    converter_start = text.index("Public Class BytesStringConverter")
    converter_end = text.index("End Class", converter_start)
    converter_body = text[converter_start:converter_end]

    # No hard-coded encoding string literal anywhere in converter body
    assert '"utf-8"' not in converter_body
    assert '"big5"' not in converter_body
    # Both Read and Write paths route through the runtime-resolved Default encoding
    assert "ProtoBytesEncoding.Default.GetString" in converter_body
    assert "ProtoBytesEncoding.Default.GetBytes" in converter_body
