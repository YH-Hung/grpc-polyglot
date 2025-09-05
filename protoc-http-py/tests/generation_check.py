import os
import shutil
import sys

# Allow running from repo root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Ensure package import works when run directly
sys.path.insert(0, REPO_ROOT)

# Import generator
try:
    from protoc_http_py.main import generate
except Exception as e:
    print(f"ERROR: Failed to import generator: {e}")
    sys.exit(1)


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
        print(f"ASSERT FAIL: Expected to find {substring} in {file}")
        sys.exit(1)


def assert_not_contains(text: str, substring: str, file: str):
    if substring in text:
        print(f"ASSERT FAIL: Expected NOT to find {substring} in {file}")
        sys.exit(1)


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
        print("No proto files found to generate")
        sys.exit(1)

    generated_files = []
    for p in protos:
        out_path = generate(p, out_dir, None)
        generated_files.append(out_path)

    # Verify complex/user-service expectations
    user_vb = os.path.join(out_dir, 'user-service.vb')
    if not os.path.exists(user_vb):
        print(f"ASSERT FAIL: Expected generated file missing: {user_vb}")
        sys.exit(1)
    with open(user_vb, 'r', encoding='utf-8') as f:
        user_text = f.read()
    # Should be camelCase
    assert_contains(user_text, 'JsonProperty("userId")', user_vb)
    assert_contains(user_text, 'JsonProperty("totalPrice")', user_vb)
    # Should not contain snake_case
    assert_not_contains(user_text, 'JsonProperty("user_id")', user_vb)
    assert_not_contains(user_text, 'JsonProperty("total_price")', user_vb)

    # Verify complex/stock-service expectations
    stock_vb = os.path.join(out_dir, 'stock-service.vb')
    if not os.path.exists(stock_vb):
        print(f"ASSERT FAIL: Expected generated file missing: {stock_vb}")
        sys.exit(1)
    with open(stock_vb, 'r', encoding='utf-8') as f:
        stock_text = f.read()
    assert_contains(stock_text, 'JsonProperty("ticker")', stock_vb)
    assert_contains(stock_text, 'JsonProperty("price")', stock_vb)

    # Verify simple/helloworld expectations
    hello_vb = os.path.join(out_dir, 'helloworld.vb')
    if not os.path.exists(hello_vb):
        print(f"ASSERT FAIL: Expected generated file missing: {hello_vb}")
        sys.exit(1)
    with open(hello_vb, 'r', encoding='utf-8') as f:
        hello_text = f.read()
    assert_contains(hello_text, 'JsonProperty("name")', hello_vb)
    assert_contains(hello_text, 'JsonProperty("message")', hello_vb)

    print("OK: Generation checks passed for proto/simple and proto/complex. CamelCase serialization verified.")


if __name__ == '__main__':
    main()
