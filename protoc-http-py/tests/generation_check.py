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
    assert_contains(utility_text, 'Namespace Complex', complex_utility_vb)

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
    return True


if __name__ == '__main__':
    main()
