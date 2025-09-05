# protoc-http-py

Generate simple VB.NET DTOs and HTTP client stubs from Protobuf (.proto) files.

This tool parses a constrained subset of .proto definitions and emits a VB.NET file per proto with:
- Public Enums for proto enums
- DTO Classes for messages (with JsonProperty attributes using lowerCamelCase JSON names)
- Simple HttpClient-based client classes for unary RPCs (non-streaming)

It supports running on a single .proto or recursively over a directory of .proto files.

---

## Requirements
- Python 3.13+

## Installation
You can run directly from the repo without installation:

- From the project root, run the module entry point:
  - macOS/Linux/Windows (PowerShell):
    - `python -m protoc_http_py.main --proto <path> --out <dir> [--namespace <VB.Namespace>]`
- If installed (via pip/uv), you can use the console script:
  - `protoc-http-py --proto <path> --out <dir> [--namespace <VB.Namespace>]`

If you prefer, add this project to your Python environment so the package is importable.

## Quick start

- Generate from a single file:
  - `python -m protoc_http_py.main --proto proto/simple/helloworld.proto --out out`
  - `protoc-http-py --proto proto/simple/helloworld.proto --out out`

- Generate from a directory (recursively finds all .proto files):
  - `python -m protoc_http_py.main --proto proto/simple --out out`
  - `protoc-http-py --proto proto/simple --out out`
  - `python -m protoc_http_py.main --proto proto/complex --out out`
  - `protoc-http-py --proto proto/complex --out out`

Expected output (examples):
- For `proto/simple` → `out/helloworld.vb`
- For `proto/complex` → `out/common.vb`, `out/stock-service.vb`, `out/user-service.vb`

You can then include the generated .vb files in your VB.NET project.

## CLI

Arguments:
- `--proto` (required): Path to a single `.proto` file or a directory containing `.proto` files. Directories are scanned recursively.
- `--out` (required): Directory where generated `.vb` file(s) are written. Created if it doesn’t exist.
- `--namespace` (optional): Override VB.NET namespace for generated code. If omitted, the namespace is derived from the proto `package` or the file name.

Examples:
- Single file with explicit namespace:
  - `python -m protoc_http_py.main --proto proto/simple/helloworld.proto --out out --namespace Demo.App`
  - `protoc-http-py --proto proto/simple/helloworld.proto --out out --namespace Demo.App`
- Entire folder, namespace derived from each file’s package:
  - `python -m protoc_http_py.main --proto proto/complex --out out`
  - `protoc-http-py --proto proto/complex --out out`

## How namespaces and types are determined
- VB Namespace per file:
  - If `--namespace` is provided, it’s used for that file.
  - Otherwise derived from `package` (dots replaced with underscores and PascalCased).
  - If no `package`, derived from the proto file name.
- Type qualification:
  - Scalar proto types are mapped to VB (e.g., `int32` → `Integer`, `bytes` → `Byte()`).
  - Non-scalar non-dotted types are assumed to be in the same namespace.
  - Dotted types (e.g., `foo.bar.Msg`) are qualified to the VB namespace derived from the dotted package when different from the current file’s package.
  - `repeated` fields become `List(Of T)`.

## Services support
- Only unary RPC methods are generated. Streaming RPCs (client/serverside/bidi) are skipped.
- Each service produces a `{ServiceName}Client` with HttpClient calls to endpoints:
  - `POST {baseUrl}/{protoFileNameWithoutExt}/{RpcName}`

## Imports and multiple files
- When you run against a directory, all `.proto` files in that directory tree are processed in one run. This covers common import/include layouts (e.g., `import "common/common.proto";`).
- There is no separate import graph resolver. Ensure that referenced types across files either:
  - Share the same proto `package` (so unqualified type names work), or
  - Use fully qualified dotted type names so the tool can map them to the correct VB namespace.

## Limitations (important)
- Parser is regex-based and supports a simplified subset of Protobuf:
  - Top-level enums, messages (simple fields), and services with unary RPCs.
  - No `map<,>`, `oneof`, field options/annotations, nested message/enum declarations, reserved/ranges.
  - Block comments (`/* ... */`) are not removed and may break parsing.
  - Streaming RPCs are ignored.
- Error handling is minimal; malformed or complex proto constructs may not be parsed.

## Example
Using the repository samples:

- Simple:
  - `python -m protoc_http_py.main --proto proto/simple --out out`
  - Generates `out/helloworld.vb`.

- Complex:
  - `python -m protoc_http_py.main --proto proto/complex --out out`
  - Generates `out/common.vb`, `out/stock-service.vb`, `out/user-service.vb`.

## Testing
- From the project root, run tests:
  - `pytest`
  - or `python -m pytest`
- Or run the standalone generation check:
  - `python tests/generation_check.py`

## Troubleshooting
- “No .proto files found under directory”: Check the path to `--proto` and that it contains `.proto` files.
- Compilation issues in VB.NET:
  - Verify that proto `package` values correspond to the expected VB namespaces.
  - Use fully qualified type names in your proto for cross-package references.
  - Ensure Newtonsoft.Json is referenced in your VB.NET project.
- Parser errors or missing members:
  - Confirm your proto uses only the supported subset (see Limitations).

## License
This repository follows the original project’s license (if present).