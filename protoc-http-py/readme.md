# protoc-http-py

Generate simple VB.NET DTOs, HTTP client stubs, and JSON Schemas from Protobuf (.proto) files.

This tool invokes protoc to compile .proto files into a descriptor set and maps that into VB.NET code and JSON Schema definitions. If protoc/protobuf are unavailable, it falls back to a legacy, constrained regex parser.

It emits:
- **VB.NET files** per proto with:
  - Public Enums for proto enums
  - DTO Classes for messages (with JsonProperty attributes using lowerCamelCase JSON names)
  - Simple HttpClient-based client classes for unary RPCs (non-streaming)
- **JSON Schema files** per proto with:
  - JSON Schema Draft 2020-12 definitions for all DTOs
  - Grouped by proto file name in a `json/` subdirectory

It supports running on a single .proto or recursively over a directory of .proto files.

---

## Requirements
- Python 3.13+
- Protocol Buffers compiler (protoc) available on PATH
- Python package: protobuf>=4.25.0

## Installation

### Install uv
- macOS/Linux (curl): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- macOS (Homebrew): `brew install uv`
- Windows (PowerShell): `iwr https://astral.sh/uv/install.ps1 -UseBasicParsing | iex`

### Set up with uv (recommended)
- Create a virtual environment in .venv: `uv venv`
- Activate it:
  - macOS/Linux (bash/zsh): `source .venv/bin/activate`
  - Windows (PowerShell): `.venv\\Scripts\\Activate.ps1`
  - Windows (CMD): `.venv\\Scripts\\activate.bat`
- Install the package in editable mode: `uv pip install -e .`
- Optional: install dev tools (pytest): `uv pip install --group dev`

After this, either use the console script or call the module:
- Console script: `protoc-http-py --proto <path> --out <dir> [--namespace <VB.Namespace>]`
- Module entry: `python -m protoc_http_py.main --proto <path> --out <dir> [--namespace <VB.Namespace>]`
- Without activating the venv, you can also run: `uv run protoc-http-py --proto <path> --out <dir>`

### Run without installing (from source)
You can also run directly from the repo without installation:
- From the project root, run the module entry point:
  - macOS/Linux/Windows (PowerShell):
    - `python -m protoc_http_py.main --proto <path> --out <dir> [--namespace <VB.Namespace>]`

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
- For `proto/simple` → `out/helloworld.vb` (single file, self-contained) + `out/json/helloworld.json`
- For `proto/complex` → `out/ComplexHttpUtility.vb`, `out/common.vb`, `out/stock-service.vb`, `out/user-service.vb`, `out/nested.vb` + corresponding JSON schemas in `out/json/`
  - **🆕 Note**: Multiple files in same directory generate a shared `ComplexHttpUtility.vb` to eliminate code duplication
  - **🆕 Note**: JSON schemas are automatically generated in `out/json/` directory

You can then include the generated .vb files in your VB.NET project.

## CLI

Arguments:
- `--proto` (required): Path to a single `.proto` file or a directory containing `.proto` files. Directories are scanned recursively.
- `--out` (required): Directory where generated `.vb` file(s) are written. Created if it doesn’t exist.
- `--namespace` (optional): Override VB.NET namespace for generated code. If omitted, the namespace is derived from the proto `package` or the file name.
- `--net45` (optional): Emit .NET Framework 4.5 compatible VB.NET code (HttpClient + async/await).
- `--net40hwr` (optional): Emit .NET Framework 4.0 compatible VB.NET code using synchronous HttpWebRequest (no async/await).
- `--net40` (optional, alias): Backward-compatible alias of `--net40hwr`. Use `--net40hwr` instead.

Examples:
- Single file with explicit namespace:
  - `python -m protoc_http_py.main --proto proto/simple/helloworld.proto --out out --namespace Demo.App`
  - `protoc-http-py --proto proto/simple/helloworld.proto --out out --namespace Demo.App`
- Entire folder, namespace derived from each file’s package:
  - `python -m protoc_http_py.main --proto proto/complex --out out`
  - `protoc-http-py --proto proto/complex --out out`
- Target .NET Framework variants:
  - .NET 4.5 (HttpClient + async/await):
    - `python -m protoc_http_py.main --proto proto/simple --out out --net45`
    - `protoc-http-py --proto proto/complex --out out --net45`
  - .NET 4.0 with HttpWebRequest (synchronous):
    - `python -m protoc_http_py.main --proto proto/simple --out out --net40hwr`
    - `protoc-http-py --proto proto/complex --out out --net40hwr`
  - Alias for legacy scripts:
    - `python -m protoc_http_py.main --proto proto/simple --out out --net40`
    - `protoc-http-py --proto proto/complex --out out --net40`

## 🆕 Shared HTTP Utilities Feature

**protoc-http-py now automatically eliminates code duplication by generating shared HTTP utility classes!**

### **How It Works**
- **Multiple `.proto` files in same directory** → Generates shared utility (e.g., `ComplexHttpUtility.vb`)
- **Single `.proto` file** → Generates self-contained client with embedded HTTP functions
- **Same Public API** → Service client APIs remain unchanged for backward compatibility

### **Before vs After**
| **Before** | **After** |
|------------|-----------|
| Each service: ~100 lines | Each service: ~50 lines |
| Each contained 50+ line PostJson function | Shared utility contains PostJson |
| Code duplication across services | **24-48% size reduction** |

### **Generated Structure Examples**
```
# Multiple files (proto/complex/):
out/
├── json/                      # 🆕 JSON Schema directory
│   ├── common.json            # Schema for common.proto
│   ├── stock-service.json     # Schema for stock-service.proto
│   ├── user-service.json      # Schema for user-service.proto
│   └── nested.json            # Schema for nested.proto
├── ComplexHttpUtility.vb      # 🆕 Shared HTTP utility
├── stock-service.vb           # Uses ComplexHttpUtility
├── user-service.vb            # Uses ComplexHttpUtility
├── common.vb                  # DTOs only
└── nested.vb                  # DTOs only

# Single file (proto/simple/):
out/
├── json/                      # 🆕 JSON Schema directory
│   └── helloworld.json        # Schema for helloworld.proto
└── helloworld.vb              # Self-contained (embedded PostJson)
```

### **Automatic Detection**
- **NET45**: Generates async `ComplexHttpUtility` with `PostJsonAsync`
- **NET40HWR**: Generates sync `ComplexHttpUtility` with `PostJson`
- **Directory-based**: Utility named after parent directory (e.g., `complex/` → `ComplexHttpUtility`)

## 🆕 JSON Schema Generation

**protoc-http-py now automatically generates JSON Schema Draft 2020-12 schemas for all DTOs!**

### **What Gets Generated**
- **One JSON schema file per proto file** in a `json/` subdirectory
- **Complete type definitions** for all messages and enums
- **Cross-file references** for imported types (e.g., `"$ref": "common.json#/$defs/Ticker"`)
- **Nested type support** with qualified names (e.g., `Outer.Inner`)
- **camelCase field names** matching JSON serialization

### **Output Structure**
```
out/
├── json/                         # 🆕 JSON Schema directory
│   ├── helloworld.json           # Schema for helloworld.proto
│   ├── common.json               # Schema for common.proto
│   ├── user-service.json         # Schema for user-service.proto
│   └── stock-service.json        # Schema for stock-service.proto
├── helloworld.vb                 # VB.NET code
├── common.vb
├── user-service.vb
└── stock-service.vb
```

### **Schema Format**
Each JSON schema file follows JSON Schema Draft 2020-12 specification:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/user-service.json",
  "title": "Schemas for user-service.proto",
  "description": "JSON Schema definitions for all messages and enums in user-service.proto (package: user)",
  "$defs": {
    "UserInformationRequest": {
      "type": "object",
      "properties": {
        "userId": { "type": "integer", "format": "int32" }
      },
      "additionalProperties": false
    },
    "TradeAction": {
      "type": "string",
      "enum": ["BUY", "SELL"],
      "description": "Enum values: BUY=0, SELL=1"
    }
  }
}
```

### **Type Mappings**
| Proto Type | JSON Schema Type | Notes |
|------------|------------------|-------|
| `string` | `{"type": "string"}` | Basic string |
| `int32`, `int64`, `sint32`, `sint64` | `{"type": "integer", "format": "..."}` | Integer types |
| `uint32`, `uint64`, `fixed32`, `fixed64` | `{"type": "integer", "minimum": 0, ...}` | Non-negative integers |
| `bool` | `{"type": "boolean"}` | Boolean values |
| `float`, `double` | `{"type": "number", "format": "..."}` | Floating-point numbers |
| `bytes` | `{"type": "string", "contentEncoding": "base64"}` | Base64-encoded strings |
| `repeated <type>` | `{"type": "array", "items": {...}}` | Array with typed items |
| `enum` | `{"type": "string", "enum": [...]}` | String enum with description |
| `message` | `{"type": "object", "properties": {...}}` | Object with typed properties |

### **Features**
- ✅ **Automatic generation** - No additional flags needed
- ✅ **Cross-package references** - Types from imported protos use relative file references
- ✅ **Nested messages** - Defined in `$defs` with qualified names (e.g., `"Outer.Inner"`)
- ✅ **Enum descriptions** - Includes numeric values in description field
- ✅ **Field validation** - `additionalProperties: false` prevents unknown fields
- ✅ **camelCase naming** - Field names match JSON serialization conventions

### **Usage with Validators**
The generated schemas can be used with any JSON Schema validator:

**Python (jsonschema):**
```python
import json
import jsonschema

# Load schema
with open('out/json/user-service.json') as f:
    schema_doc = json.load(f)

# Validate data
data = {"userId": 123}
jsonschema.validate(data, schema_doc['$defs']['UserInformationRequest'])
```

**Node.js (ajv):**
```javascript
const Ajv = require('ajv');
const schema = require('./out/json/user-service.json');

const ajv = new Ajv();
const validate = ajv.compile(schema.$defs.UserInformationRequest);

const valid = validate({ userId: 123 });
if (!valid) console.log(validate.errors);
```

### **Schema References**
- **Same-file types**: `{"$ref": "#/$defs/TypeName"}`
- **Cross-file types**: `{"$ref": "common.json#/$defs/Ticker"}`
- **Nested types**: `{"$ref": "#/$defs/Outer.Inner"}`

## How namespaces and types are determined
- VB Namespace per file:
  - If `--namespace` is provided, it's used for that file.
  - Otherwise derived from `package` (dots replaced with underscores and PascalCased).
  - If no `package`, derived from the proto file name.
- Type qualification:
  - Scalar proto types are mapped to VB (e.g., `int32` → `Integer`, `bytes` → `Byte()`).
  - Non-scalar non-dotted types are assumed to be in the same namespace.
  - Nested type chains that start with a Type (e.g., `Outer.Inner`) are treated as nested classes in the same VB namespace.
  - Dotted names with a package prefix then type chain (e.g., `foo.bar.Outer.Inner`) are mapped to the VB namespace derived from `foo.bar`, producing something like `Foo_Bar.Outer.Inner` unless the current file's package matches.
  - For fields inside a message that reference a directly nested child by short name (e.g., `Inner` inside `Outer`), the generator automatically qualifies it to `Outer.Inner`.
  - `repeated` fields become `List(Of T)`.

## VB.NET Reserved Keyword Handling
When proto field names conflict with VB.NET reserved keywords, the generated property names are automatically escaped by wrapping them in square brackets `[keyword]`. This ensures the generated VB.NET code compiles successfully while preserving the original JSON serialization names.

### Automatic Escaping
- **Property Names**: Reserved keywords in property names are escaped with square brackets
- **JSON Names**: JSON property names in `<JsonProperty>` attributes remain unchanged (lowerCamelCase)
- **Keywords**: All 148 VB.NET reserved keywords are recognized and escaped (e.g., `Error`, `Class`, `String`, `Integer`, `Property`, `For`, `If`, `End`, `Try`, `Catch`, etc.)

### Examples
```protobuf
// Proto definition
message ErrorMessage {
  string error = 1;
  string class = 2;
  int32 integer = 3;
  string property = 4;
}
```

```vb
' Generated VB.NET code
Public Class ErrorMessage
    <JsonProperty("error")>
    Public Property [Error] As String

    <JsonProperty("class")>
    Public Property [Class] As String

    <JsonProperty("integer")>
    Public Property [Integer] As Integer

    <JsonProperty("property")>
    Public Property [Property] As String

End Class
```

**JSON Serialization**: The escaped property names work seamlessly with JSON serialization:
```vb
' Usage in VB.NET
Dim msg As New ErrorMessage With {
    .[Error] = "Something went wrong",
    .[Class] = "ErrorClass",
    .[Integer] = 42,
    .[Property] = "Value"
}
' Serializes to: {"error":"Something went wrong","class":"ErrorClass","integer":42,"property":"Value"}
```

## Services support
- Only unary RPC methods are generated. Streaming RPCs (client/serverside/bidi) are skipped.
- Each service produces a `{ServiceName}Client` with HttpClient calls to endpoints:
  - `POST {baseUrl}/{protoFileNameWithoutExt}/{rpc-name-in-kebab-case}/{version}`
    - The `{rpc-name-in-kebab-case}` is derived from the RPC name with any trailing version suffix removed. If an RPC ends with `Vx` (e.g., `GetUserV2`), the base is `GetUser` → `get-user`.
    - The `{version}` segment is always required (even for V1) and is lower-case: `v1`, `v2`, `v3`, ... If the RPC name has no trailing `Vx`, it defaults to `v1`.
    - Examples:
      - `GetStockPrice` → `POST {baseUrl}/stock-service/get-stock-price/v1`
      - `GetUserInformationV2` → `POST {baseUrl}/user-service/get-user-information/v2`

### Client construction and HttpClient injection
- Generated clients now require HttpClient to be provided via constructor injection:
  - **NET45 Mode**: `Public Sub New(http As HttpClient, baseUrl As String)`
  - **NET40HWR Mode**: `Public Sub New(baseUrl As String)`
- Example (VB.NET):
  - **NET45**: `Dim http = New HttpClient()` then `Dim client = New Helloworld.GreeterClient(http, "https://api.example.com")`
  - **NET40HWR**: `Dim client = New Helloworld.GreeterClient("https://api.example.com")`
  - `Dim resp = Await client.SayHelloAsync(New Helloworld.HelloRequest With { .Name = "World" })` (NET45)
  - `Dim resp = client.SayHello(New Helloworld.HelloRequest With { .Name = "World" })` (NET40HWR)
- Notes:
  - **NET45**: The generator no longer creates a Shared HttpClient; you control its lifecycle (recommended for DI and reuse).
  - **NET40HWR**: Uses HttpWebRequest directly, no external dependencies.
  - `baseUrl` is validated and trimmed of any trailing '/' automatically.

### Method overloads and timeout support
- **NET45 Mode** generates 3 overloads per RPC method:
  - `MethodAsync(request)` - Simple call
  - `MethodAsync(request, cancellationToken)` - With cancellation support
  - `MethodAsync(request, cancellationToken, timeoutMs)` - With timeout and cancellation
- **NET40HWR Mode** generates 2 overloads per RPC method:
  - `Method(request)` - Simple call
  - `Method(request, timeoutMs)` - With timeout support
- **Timeout Examples**:
  - **NET45**: `Await client.SayHelloAsync(request, CancellationToken.None, 30000)` (30 seconds)
  - **NET40HWR**: `client.SayHello(request, 30000)` (30 seconds)
- **Error Handling**:
  - **NET45**: `HttpRequestException` may be thrown for HTTP errors. Status validation (IsSuccessStatusCode) and custom error messages are built into generated code.
  - **NET40HWR**: `WebException` may be thrown for network/HTTP errors. No exception handling is performed in the PostJson utility - errors propagate directly to the calling code.
  - Users must implement their own Try-Catch blocks to handle exceptions as needed for their use case.
- **Response Validation**: Both modes detect and throw `InvalidOperationException` for empty responses

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
  - Generates `out/helloworld.vb` and `out/json/helloworld.json`.

- Complex:
  - `python -m protoc_http_py.main --proto proto/complex --out out`
  - Generates `out/common.vb`, `out/stock-service.vb`, `out/user-service.vb`, `out/nested.vb` and corresponding JSON schemas in `out/json/`.

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

## Demo outputs (net45 and net40hwr)

The repository includes comprehensive pre-generated VB.NET files demonstrating all features:

### test_output_examples/ - Comprehensive Examples
- **net45/**: .NET Framework 4.5+ examples with HttpClient + async/await
- **net40hwr/**: .NET Framework 4.0 examples with HttpWebRequest + synchronous  
- **versioning/**: RPC versioning demonstration
- Includes detailed README.md explaining all features and improvements

### out_test/ - Legacy Examples  
- .default.vb: Generated with the default (modern) HttpClient + async/await style (equivalent to --net45).
- .net40hwr.vb: Generated with the .NET 4.0 HttpWebRequest synchronous style (--net40hwr).

You can reproduce these demo outputs locally:
- **Comprehensive Examples**: See `test_output_examples/README.md` for generation commands
- **Legacy Examples**: python3 tests/generate_variants.py
  - This will generate both variants for all sample protos under proto/simple and proto/complex into out_test/.
  - Note: The script may rename any existing out_test/*.vb to *.default.vb to avoid overwriting.

Tip: If you only want to run the baseline generation/verification (without creating variant files), use the standalone check:
- python3 tests/generation_check.py
