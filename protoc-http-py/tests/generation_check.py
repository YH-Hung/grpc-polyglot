import os
import shutil
import sys

# Allow running from repo root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Ensure package import works when run directly
sys.path.insert(0, REPO_ROOT)

# Import generator
try:
    from protoc_http_py.main import generate, generate_directory_with_shared_utilities
except Exception as e:
    raise RuntimeError(f"Failed to import generator: {e}")


def find_proto_files(root: str):
    matches = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith('.proto'):
                matches.append(os.path.join(dirpath, fn))
    matches.sort()
    return matches


def assert_contains(text: str, substring: str, file: str):
    if substring not in text:
        raise AssertionError(f"Expected to find {substring} in {file}")


def assert_not_contains(text: str, substring: str, file: str):
    if substring in text:
        raise AssertionError(f"Expected NOT to find {substring} in {file}")


def main():
    out_dir = os.path.join(REPO_ROOT, 'out_test')
    # Clean output dir
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    # Generate from proto/simple and proto/complex
    protos = []
    protos += find_proto_files(os.path.join(REPO_ROOT, 'proto', 'simple'))
    protos += find_proto_files(os.path.join(REPO_ROOT, 'proto', 'complex'))

    if not protos:
        raise AssertionError("No proto files found to generate")

    # Use new directory-based generation with shared utilities
    generated_files = generate_directory_with_shared_utilities(protos, out_dir, None)

    # Verify that shared utilities were generated for complex directory
    complex_utility_vb = os.path.join(out_dir, 'ComplexHttpUtility.vb')
    if not os.path.exists(complex_utility_vb):
        raise AssertionError(f"Expected shared utility file missing: {complex_utility_vb}")

    with open(complex_utility_vb, 'r', encoding='utf-8') as f:
        utility_text = f.read()

    # Verify shared utility contains PostJson function
    assert_contains(utility_text, 'Public Async Function PostJsonAsync', complex_utility_vb)
    assert_contains(utility_text, 'Class ComplexHttpUtility', complex_utility_vb)
    # Namespace now uses the first proto file's package (demo.nested -> DemoNested)
    assert_contains(utility_text, 'Namespace DemoNested', complex_utility_vb)

    # Verify complex/user-service expectations
    user_vb = os.path.join(out_dir, 'user-service.vb')
    if not os.path.exists(user_vb):
        raise AssertionError(f"Expected generated file missing: {user_vb}")
    with open(user_vb, 'r', encoding='utf-8') as f:
        user_text = f.read()
    # Should be camelCase
    assert_contains(user_text, 'JsonProperty("userId")', user_vb)
    assert_contains(user_text, 'JsonProperty("totalPrice")', user_vb)
    # Should not contain snake_case
    assert_not_contains(user_text, 'JsonProperty("user_id")', user_vb)
    assert_not_contains(user_text, 'JsonProperty("total_price")', user_vb)
    # Versioned routes should be present (default v1)
    assert_contains(user_text, '/user-service/get-user-information/v1', user_vb)
    assert_contains(user_text, '/user-service/trade-stock/v1', user_vb)
    # Should use shared utility instead of embedded PostJson
    assert_contains(user_text, '_httpUtility.PostJsonAsync', user_vb)
    assert_contains(user_text, 'Private ReadOnly _httpUtility As ComplexHttpUtility', user_vb)
    # Should NOT contain embedded PostJson function
    assert_not_contains(user_text, 'Private Async Function PostJsonAsync', user_vb)

    # Verify complex/stock-service expectations
    stock_vb = os.path.join(out_dir, 'stock-service.vb')
    if not os.path.exists(stock_vb):
        raise AssertionError(f"Expected generated file missing: {stock_vb}")
    with open(stock_vb, 'r', encoding='utf-8') as f:
        stock_text = f.read()
    assert_contains(stock_text, 'JsonProperty("ticker")', stock_vb)
    assert_contains(stock_text, 'JsonProperty("price")', stock_vb)
    # Versioned route should be present (default v1)
    assert_contains(stock_text, '/stock-service/get-stock-price/v1', stock_vb)
    # Should use shared utility instead of embedded PostJson
    assert_contains(stock_text, '_httpUtility.PostJsonAsync', stock_vb)
    assert_contains(stock_text, 'Private ReadOnly _httpUtility As ComplexHttpUtility', stock_vb)
    # Should NOT contain embedded PostJson function
    assert_not_contains(stock_text, 'Private Async Function PostJsonAsync', stock_vb)

    # Verify simple/helloworld expectations
    hello_vb = os.path.join(out_dir, 'helloworld.vb')
    if not os.path.exists(hello_vb):
        raise AssertionError(f"Expected generated file missing: {hello_vb}")
    with open(hello_vb, 'r', encoding='utf-8') as f:
        hello_text = f.read()
    assert_contains(hello_text, 'JsonProperty("name")', hello_vb)
    assert_contains(hello_text, 'JsonProperty("message")', hello_vb)
    # Versioned route should be present (default v1) and v2 RPC route if defined
    assert_contains(hello_text, '/helloworld/say-hello/v1', hello_vb)
    assert_contains(hello_text, '/helloworld/say-hello/v2', hello_vb)
    # Single file should still have embedded PostJson (no shared utility)
    assert_contains(hello_text, 'Private Async Function PostJsonAsync', hello_vb)
    # Should NOT use shared utility
    assert_not_contains(hello_text, '_httpUtility.PostJsonAsync', hello_vb)
    assert_not_contains(hello_text, 'ComplexHttpUtility', hello_vb)

    # Verify complex/nested expectations
    nested_vb = os.path.join(out_dir, 'nested.vb')
    if not os.path.exists(nested_vb):
        raise AssertionError(f"Expected generated file missing: {nested_vb}")
    with open(nested_vb, 'r', encoding='utf-8') as f:
        nested_text = f.read()
    # Nested classes should be emitted
    assert_contains(nested_text, 'Public Class Outer', nested_vb)
    assert_contains(nested_text, 'Public Class Inner', nested_vb)
    # Types referencing nested classes should use Outer.Inner
    assert_contains(nested_text, 'Public Property Inner As Outer.Inner', nested_vb)
    assert_contains(nested_text, 'Public Property Items As List(Of Outer.Inner)', nested_vb)
    assert_contains(nested_text, 'Public Property Value As Outer.Inner', nested_vb)
    assert_contains(nested_text, 'Public Property Values As List(Of Outer.Inner)', nested_vb)

    print("OK: Generation checks passed for proto/simple and proto/complex (including nested). CamelCase serialization, nested types, and shared HTTP utilities verified.")

    # Test VB.NET reserved keyword escaping
    test_vb_reserved_keywords(out_dir)

    return True


def test_vb_reserved_keywords(out_dir: str):
    """Test that VB.NET reserved keywords are properly escaped with square brackets."""
    import tempfile

    # Create a test proto with VB.NET reserved keywords as field names
    test_proto_content = '''syntax = "proto3";

package test_keywords;

message KeywordTest {
  string error = 1;
  string class = 2;
  string module = 3;
  int32 integer = 4;
  string string = 5;
  bool boolean = 6;
  string as = 7;
  string for = 8;
  string if = 9;
  string end = 10;
  string property = 11;
  string select = 12;
  string try = 13;
  string catch = 14;
  string public = 15;
  string private = 16;
}

service KeywordService {
  rpc TestMethod (KeywordTest) returns (KeywordTest) {}
}
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.proto', delete=False, encoding='utf-8') as f:
        f.write(test_proto_content)
        test_proto_path = f.name

    try:
        from protoc_http_py.main import generate

        # Generate VB.NET code
        test_out = os.path.join(out_dir, 'test_keywords')
        os.makedirs(test_out, exist_ok=True)
        generated_file = generate(test_proto_path, test_out, None)

        # Read generated file
        with open(generated_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verify that reserved keywords are escaped with square brackets
        expected_escaped = [
            'Public Property [Error] As String',
            'Public Property [Class] As String',
            'Public Property [Module] As String',
            'Public Property [Integer] As Integer',
            'Public Property [String] As String',
            'Public Property [Boolean] As Boolean',
            'Public Property [As] As String',
            'Public Property [For] As String',
            'Public Property [If] As String',
            'Public Property [End] As String',
            'Public Property [Property] As String',
            'Public Property [Select] As String',
            'Public Property [Try] As String',
            'Public Property [Catch] As String',
            'Public Property [Public] As String',
            'Public Property [Private] As String',
        ]

        for expected in expected_escaped:
            assert_contains(content, expected, generated_file)

        # Verify JSON property names are NOT escaped (lowercase camelCase)
        assert_contains(content, 'JsonProperty("error")', generated_file)
        assert_contains(content, 'JsonProperty("class")', generated_file)
        assert_contains(content, 'JsonProperty("string")', generated_file)
        assert_contains(content, 'JsonProperty("property")', generated_file)

        print("OK: VB.NET reserved keyword escaping verified. All keywords properly wrapped in square brackets.")
    finally:
        # Clean up temp file
        if os.path.exists(test_proto_path):
            os.unlink(test_proto_path)


if __name__ == '__main__':
    main()
