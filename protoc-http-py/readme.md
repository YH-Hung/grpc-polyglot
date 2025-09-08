# protoc-http-py

Generate simple VB.NET DTOs and HTTP client stubs from Protobuf (.proto) files.

This tool invokes protoc to compile .proto files into a descriptor set and maps that into VB.NET code. If protoc/protobuf are unavailable, it falls back to a legacy, constrained regex parser.

It emits a VB.NET file per proto with:
- Public Enums for proto enums
- DTO Classes for messages (with JsonProperty attributes using lowerCamelCase JSON names)
- Simple HttpClient-based client classes for unary RPCs (non-streaming)

It supports running on a single .proto or recursively over a directory of .proto files.

---

## Requirements
- Python 3.13+
- Protocol Buffers compiler (protoc) available on PATH
- Python package: protobuf>=4.25.0

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
- For `proto/complex` → `out/common.vb`, `out/stock-service.vb`, `out/user-service.vb`, `out/nested.vb`

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
  - Nested type chains that start with a Type (e.g., `Outer.Inner`) are treated as nested classes in the same VB namespace.
  - Dotted names with a package prefix then type chain (e.g., `foo.bar.Outer.Inner`) are mapped to the VB namespace derived from `foo.bar`, producing something like `Foo_Bar.Outer.Inner` unless the current file’s package matches.
  - For fields inside a message that reference a directly nested child by short name (e.g., `Inner` inside `Outer`), the generator automatically qualifies it to `Outer.Inner`.
  - `repeated` fields become `List(Of T)`.

## Services support
- Only unary RPC methods are generated. Streaming RPCs (client/serverside/bidi) are skipped.
- Each service produces a `{ServiceName}Client` with HttpClient calls to endpoints:
  - `POST {baseUrl}/{protoFileNameWithoutExt}/{rpc-name-in-kebab-case}`
    - Example: `GetStockPrice` -> `get-stock-price`

## Imports and multiple files
- protoc is invoked with `--include_imports`, and include paths (-I) are set to the proto file's directory and the repo `proto/` folder by default. This lets protoc resolve imports across files.
- You can point `--proto` at either a single file or a directory. In directory mode, each `.proto` file is compiled and generated individually, while types referenced across files are resolved by protoc via descriptors.
- If your imports live outside these roots, ensure they are available under the provided directory (e.g., vendor required `.proto` files or run the tool from a root that contains them).

## Limitations (important)
- Descriptor-based by default: The tool invokes protoc and reads descriptors. If protoc is not available, it falls back to a simplified regex parser.
- Generator capabilities/limitations:
  - Only unary RPC methods are generated. All streaming RPCs are skipped.
  - Map fields are not supported (map entries are not emitted and referenced types will not exist in generated code).
  - oneof fields are treated as plain fields (no union semantics in the output).
  - Nested enums are not generated (only top-level enums are emitted).
  - Custom options/annotations and comments/source locations are not propagated to the output.
  - No reserved/range handling beyond what descriptors provide for names/numbers.
- Fallback regex parser (used only when descriptor-based parsing is unavailable) has additional constraints and may fail on complex syntax (block comments, options, extensions, etc.). Prefer installing protoc for best results.

## Example
Using the repository samples:

- Simple:
  - `python -m protoc_http_py.main --proto proto/simple --out out`
  - Generates `out/helloworld.vb`.

- Complex:
  - `python -m protoc_http_py.main --proto proto/complex --out out`
  - Generates `out/common.vb`, `out/stock-service.vb`, `out/user-service.vb`, `out/nested.vb`.

## Testing
- From the project root, run tests:
  - `pytest`
  - or `python -m pytest`
- Or run the standalone generation check:
  - `python tests/generation_check.py`

## Troubleshooting
- 'protoc' not found: Install the Protocol Buffers compiler and ensure it is on your PATH.
  - macOS: `brew install protobuf`
  - Ubuntu/Debian: `sudo apt-get install -y protobuf-compiler`
  - Windows (Chocolatey): `choco install protoc`
  - After installing, re-run the command. Without protoc, the tool falls back to a limited regex parser which may miss features.
- protoc failed: The tool will report `protoc failed: ...` with stderr from protoc.
  - Check that your include paths are correct (the tool adds `-I <file_dir>` and `-I <repo>/proto` by default).
  - Ensure all imported `.proto` files are present under the searched roots.
  - Try running `protoc` manually with the same flags to see detailed errors.
  - Verify your `.proto` syntax version and that custom options/extensions are available on the include path.
- “No .proto files found under directory”: Check the path to `--proto` and that it contains `.proto` files.
- Compilation issues in VB.NET:
  - Verify that proto `package` values correspond to the expected VB namespaces.
  - Use fully qualified type names in your proto for cross-package references.
  - Ensure Newtonsoft.Json is referenced in your VB.NET project.
- Parser errors or missing members:
  - If you cannot install protoc, confirm your proto uses only the supported subset (see Limitations). Prefer installing protoc to use the descriptor-based parser for best accuracy.

## License
This repository follows the original project’s license (if present).