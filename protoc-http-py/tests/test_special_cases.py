import os
import tempfile
from pathlib import Path
import pytest
from protoc_http_py.main import generate, parse_proto_via_descriptor, generate_json_schema

REPO_ROOT = Path(__file__).resolve().parents[1]
PROTO_DIR = REPO_ROOT / "proto" / "test_special_cases"

# Check if protobuf is available
try:
    from google.protobuf import descriptor_pb2
    HAS_PROTOBUF = True
except ImportError:
    HAS_PROTOBUF = False


class TestMsgHdrSpecialLogic:
    """Test that msgHdr messages preserve exact field names (no camelCase)"""

    def test_msghdr_preserves_field_names(self, tmp_path):
        """Fields in msgHdr message should preserve exact casing (not converted)"""
        proto_path = PROTO_DIR / "test_msghdr.proto"
        out_path = Path(generate(str(proto_path), str(tmp_path), None))
        content = out_path.read_text(encoding='utf-8')

        # msgHdr fields should preserve exact proto casing
        assert 'JsonProperty("userId")' in content  # Preserved as-is (camelCase)
        assert 'JsonProperty("FirstName")' in content  # Preserved as-is (PascalCase)
        assert 'JsonProperty("accountNumber")' in content  # Preserved as-is (camelCase)

        # Check context: msgHdr should have exact field names
        lines = content.split('\n')
        in_msghdr = False
        msghdr_json_props = []
        for i, line in enumerate(lines):
            if 'Public Class msgHdr' in line:
                in_msghdr = True
            elif 'End Class' in line and in_msghdr:
                in_msghdr = False
            elif in_msghdr and 'JsonProperty' in line:
                msghdr_json_props.append(line)

        # Verify exact preservation
        assert any('JsonProperty("userId")' in prop for prop in msghdr_json_props)
        assert any('JsonProperty("FirstName")' in prop for prop in msghdr_json_props)
        assert any('JsonProperty("accountNumber")' in prop for prop in msghdr_json_props)

    def test_regular_message_uses_camelcase(self, tmp_path):
        """Regular messages should still use camelCase as before"""
        proto_path = PROTO_DIR / "test_msghdr.proto"
        out_path = Path(generate(str(proto_path), str(tmp_path), None))
        content = out_path.read_text(encoding='utf-8')

        # RegularMessage fields should be camelCase
        lines = content.split('\n')
        in_regular = False
        for i, line in enumerate(lines):
            if 'Public Class RegularMessage' in line:
                in_regular = True
            elif 'End Class' in line and in_regular:
                in_regular = False
            elif in_regular and 'JsonProperty' in line:
                # Within RegularMessage, should have camelCase
                if 'userId' in line or 'firstName' in line or 'accountNumber' in line:
                    assert True  # Found camelCase
                    break
        else:
            assert False, "RegularMessage should have camelCase fields"

    def test_nested_msghdr_preserves_field_names(self, tmp_path):
        """Nested msgHdr should also preserve field names exactly"""
        proto_path = PROTO_DIR / "test_msghdr.proto"
        out_path = Path(generate(str(proto_path), str(tmp_path), None))
        content = out_path.read_text(encoding='utf-8')

        # Nested msgHdr should preserve exact casing (InnerField with capital I)
        assert 'JsonProperty("InnerField")' in content
        # Outer message regular field should be converted to camelCase
        assert 'JsonProperty("regularField")' in content

    @pytest.mark.skipif(not HAS_PROTOBUF, reason="protobuf library not installed")
    def test_msghdr_json_schema_preserves_fields(self, tmp_path):
        """JSON Schema should also preserve field names for msgHdr"""
        proto_path = PROTO_DIR / "test_msghdr.proto"
        proto = parse_proto_via_descriptor(str(proto_path))
        json_path = generate_json_schema(proto, str(tmp_path))

        import json
        with open(json_path, 'r') as f:
            schema = json.load(f)

        # msgHdr should have exact field names preserved
        msghdr_schema = schema['$defs']['msgHdr']
        assert 'userId' in msghdr_schema['properties']  # Preserved as-is
        assert 'FirstName' in msghdr_schema['properties']  # Preserved as-is
        assert 'accountNumber' in msghdr_schema['properties']  # Preserved as-is


class TestN2KebabCaseHandling:
    """Test that N2 pattern converts to -n2- not -n-2- in kebab-case"""

    def test_n2_converts_to_dash_n2_dash(self, tmp_path):
        """N2 pattern should become -n2- in kebab-case"""
        proto_path = PROTO_DIR / "test_n2_kebab.proto"
        out_path = Path(generate(str(proto_path), str(tmp_path), None))
        content = out_path.read_text(encoding='utf-8')

        # N2 should convert to -n2- not -n-2-
        # Note: the base path varies (n2test for descriptor parser, test_n2_kebab for legacy parser)
        assert 'get-n2-data/v1' in content
        assert 'n2-service-call/v1' in content
        assert 'fetch-n2/v1' in content
        assert 'n2-to-n2-sync/v1' in content

        # Should NOT contain -n-2-
        assert '-n-2-' not in content

    def test_n2_unit_conversion(self):
        """Unit test for to_kebab function with N2"""
        from protoc_http_py.main import to_kebab

        assert to_kebab('GetN2Data') == 'get-n2-data'
        assert to_kebab('N2ServiceCall') == 'n2-service-call'
        assert to_kebab('FetchN2') == 'fetch-n2'
        assert to_kebab('N2ToN2Sync') == 'n2-to-n2-sync'

        # Control: N3 should still split
        assert to_kebab('GetN3Data') == 'get-n-3-data'

    def test_other_patterns_unchanged(self, tmp_path):
        """Other letter-digit patterns should still split normally"""
        proto_path = PROTO_DIR / "test_n2_kebab.proto"
        out_path = Path(generate(str(proto_path), str(tmp_path), None))
        content = out_path.read_text(encoding='utf-8')

        # N3 should still be split as -n-3-
        assert 'get-n-3-data/v1' in content


class TestNamespacePriority:
    """Test that proto package always takes priority over CLI --namespace"""

    def test_package_overrides_cli_namespace(self, tmp_path):
        """When proto has package, CLI --namespace should be ignored"""
        proto_path = PROTO_DIR / "test_namespace_priority.proto"

        # Try to override with CLI namespace
        out_path = Path(generate(str(proto_path), str(tmp_path), "MyCustomNamespace"))
        content = out_path.read_text(encoding='utf-8')

        # Should use package-derived namespace, not CLI
        assert 'Namespace ComExamplePriority' in content
        assert 'Namespace MyCustomNamespace' not in content

    def test_cli_namespace_used_when_no_package(self, tmp_path):
        """CLI --namespace should work as fallback when no package"""
        # Create temporary proto without package
        proto_content = '''syntax = "proto3";

message NoPackageTest {
  string field = 1;
}

service NoPackageService {
  rpc Call(NoPackageTest) returns (NoPackageTest) {}
}
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.proto',
                                         delete=False, encoding='utf-8') as f:
            f.write(proto_content)
            temp_proto_path = f.name

        try:
            out_path = Path(generate(temp_proto_path, str(tmp_path), "FallbackNamespace"))
            content = out_path.read_text(encoding='utf-8')

            # Should use CLI namespace as fallback
            assert 'Namespace FallbackNamespace' in content
        finally:
            os.unlink(temp_proto_path)

    def test_package_to_vb_namespace_function(self):
        """Unit test for package_to_vb_namespace priority"""
        from protoc_http_py.main import package_to_vb_namespace

        # Package should be used when present
        result = package_to_vb_namespace("com.example.test", "test.proto")
        assert result == "ComExampleTest"

        # File name fallback when no package
        result = package_to_vb_namespace(None, "my_service.proto")
        assert result == "MyService"
