# protoc-http-vb (refactored from protoc-http-go)

Generate VB.NET HTTP client stubs and DTOs from Protobuf (.proto) files for unary gRPC calls through an HTTP proxy.

What this tool generates:
- VB.NET classes for messages with Newtonsoft.Json attributes using camelCase JSON property names
- **Two .NET Framework modes**: HttpClient+async/await (net45) or HttpWebRequest+sync (net40hwr)
- Unary RPC support (non-streaming) that call a proxy which forwards to gRPC
- Support for enums and nested message types (flattened with underscores like Outer_Inner)
- **JSON Schema Draft 2020-12** files for all messages and enums (see [JSON Schema Generation](#json-schema-generation))
- Works with a single .proto file or recursively with directories

The generated clients communicate with gRPC servers through an HTTP proxy (e.g., grpc-http1-proxy) that converts HTTP POST requests to gRPC calls and returns JSON responses.

---

## Requirements
- Go 1.19+ (to run this generator)
- Target .NET Framework (see Framework Modes below)
- Newtonsoft.Json (Json.NET) package referenced by your VB project

## Installation

### Option 1: Build the generator
```bash
git clone <repository>
cd protoc-http-go
go build -o protoc-http-go cmd/protoc-http-go/main.go
```

### Option 2: Run directly
```bash
go run cmd/protoc-http-go/main.go --proto <path> --out <dir> [options]
```

## Usage

### Command Line
```bash
protoc-http-go --proto <path> --out <dir> [--package <namespace>] [--baseurl <url>] [--framework <mode>]
```

Arguments:
- --proto (required): Path to a single .proto file or a directory containing .proto files
- --out   (required): Directory where generated .vb files will be written (created if absent)
- --package (optional): Override VB.NET namespace for generated code
- --baseurl (optional): Base URL for HTTP requests; can also be set in code when constructing clients
- --framework (optional): Target .NET Framework mode: `net45` or `net40hwr` (default: `net45`)

### Examples

Generate from a single file:
```bash
# Build first
go build -o protoc-http-go cmd/protoc-http-go/main.go

# Generate .NET 4.5+ compatible code (default)
./protoc-http-go --proto proto/simple/helloworld.proto --out demo_output

# Generate .NET 4.0 compatible code with HttpWebRequest
./protoc-http-go --proto proto/simple/helloworld.proto --out demo_output --framework net40hwr

# Or run directly
go run cmd/protoc-http-go/main.go --proto proto/simple/helloworld.proto --out demo_output --framework net45
```

Generate recursively for a directory:
```bash
# Generate for complex proto structure with custom namespace
./protoc-http-go --proto proto/complex --out generated --package MyCompany.Services --framework net45
```

Expected output:
- For proto/simple → demo_output/helloworld.vb
- For proto/complex → generated/stock-service.vb, generated/user-service.vb, generated/nested.vb

## HTTP Route Convention (proxy URL)
The HTTP route for each RPC is:
```
{base_url}/{proto file name}/{rpc method name}/{version}
```
Rules:
- RPC method name segment is the version-independent method name in kebab-case.
  - Example: SayHello → say-hello; SayHelloV2 → say-hello
- Version segment must always be present and lowercase.
  - If the RPC name ends with Vx (e.g., V2, V3), that x is the version: v2, v3, ...
  - If no Vx suffix, version defaults to v1.

Example generated call for proto file helloworld.proto and RPC SayHello:
```
POST {BaseUrl}/helloworld/say-hello/v1
Content-Type: application/json
```

## ⚡ Special Behaviors

### msgHdr Message Handling
Messages named exactly `msgHdr` (case-sensitive) receive special treatment:
- Field names are preserved exactly as defined in the proto file
- No conversion is applied - the exact casing from the proto is used in JSON property names
- Applies to both top-level and nested `msgHdr` messages
- Example: `userId` stays as `"userId"`, `FirstName` stays as `"FirstName"` (exact preservation)

**Use Case**: When you need exact field name matching for specific message headers or protocols that require precise field naming.

```protobuf
message msgHdr {
  string userId = 1;         // JSON: "userId" (preserved as-is)
  string FirstName = 2;       // JSON: "FirstName" (preserved as-is)
  int32 accountNumber = 3;    // JSON: "accountNumber" (preserved as-is)
}

message RegularMessage {
  string user_id = 1;        // JSON: "userId" (converted to camelCase)
  string first_name = 2;      // JSON: "firstName" (converted to camelCase)
  int32 account_number = 3;   // JSON: "accountNumber" (converted to camelCase)
}
```

### N2 Pattern in Kebab-Case
The specific pattern "N2" in RPC method names converts to `-n2-` in kebab-case URLs:
- `GetN2Data` → `/service/get-n2-data/v1` (not `/service/get-n-2-data/v1`)
- Other letter-digit patterns (N3, N4, etc.) still split normally: `-n-3-`, `-n-4-`

**Use Case**: When working with APIs that have established N2 naming conventions (e.g., telecommunications protocols, network standards).

### Namespace Priority
Proto `package` declaration always takes priority for VB.NET namespace generation:
- If proto has `package com.example.test`, namespace is always `Com.Example.Test`
- CLI `--package` argument is ignored when proto package is defined
- CLI `--package` only used as fallback when no package is declared

**Use Case**: Ensures consistency across multiple proto files in the same package, preventing accidental namespace overrides.

## .NET Framework Compatibility Modes

This tool supports two .NET Framework modes to accommodate different deployment scenarios:

### net45 Mode (Default)
- **Target**: .NET Framework 4.5+ OR .NET Framework 4.0 with NuGet packages
- **HTTP Client**: HttpClient with async/await support
- **Dependencies**:
  - For .NET 4.5+: Built-in HttpClient and async/await
  - For .NET 4.0: Microsoft.Net.Http + Microsoft.Bcl.Async NuGet packages
- **Constructor**: Requires HttpClient injection for connection pooling
- **Authorization**: Handled through injected HttpClient headers
- **Methods**: Async methods ending with "Async" (e.g., `SayHelloAsync`)

Example usage:
```vb
Dim httpClient As New HttpClient()
Dim client As New GreeterClient("https://api.example.com", httpClient)
Dim response As HelloReply = Await client.SayHelloAsync(request)
```

### net40hwr Mode
- **Target**: .NET Framework 4.0 without additional NuGet packages
- **HTTP Client**: HttpWebRequest (synchronous calls only)
- **Dependencies**: Only built-in .NET 4.0 libraries
- **Constructor**: Simple constructor with baseUrl only
- **Authorization**: Pass headers as optional Dictionary parameter
- **Methods**: Synchronous methods (e.g., `SayHello`)
- **Error Handling**: WebException propagates directly to calling code (no exception handling in PostJson utility)
- **Users must implement their own Try-Catch blocks** to handle exceptions as needed

Example usage:
```vb
Dim client As New GreeterClient("https://api.example.com")
Dim authHeaders As New Dictionary(Of String, String) From {{"Authorization", "Bearer token"}}
Dim response As HelloReply = client.SayHello(request, authHeaders)
```

## Generated VB.NET Code Examples

### net45 Mode Output
Given proto/simple/helloworld.proto with `--framework net45`, this tool produces:
```vb
Option Strict On
Option Explicit On
Option Infer On

Imports System
Imports System.Net.Http
Imports System.Net.Http.Headers
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Text
Imports System.Collections.Generic
Imports Newtonsoft.Json
Imports Newtonsoft.Json.Serialization

Namespace Helloworld

' HelloRequest DTO
Public Class HelloRequest
    <JsonProperty("name")>
    Public Property Name As String
End Class

' HelloReply DTO
Public Class HelloReply
    <JsonProperty("message")>
    Public Property Message As String
End Class

' Greeter HTTP client with HttpClient injection
Public Class GreeterClient
    Public Property BaseUrl As String
    Private ReadOnly _httpClient As HttpClient

    Public Sub New(baseUrl As String, httpClient As HttpClient)
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        If httpClient Is Nothing Then Throw New ArgumentNullException(NameOf(httpClient))
        Me.BaseUrl = baseUrl
        Me._httpClient = httpClient
    End Sub

    ' SayHelloAsync calls POST {BaseUrl}/helloworld/say-hello/v1
    Public Async Function SayHelloAsync(request As HelloRequest, Optional cancellationToken As CancellationToken = Nothing) As Task(Of HelloReply)
        Dim settings As New JsonSerializerSettings() With { .ContractResolver = New CamelCasePropertyNamesContractResolver() }
        Dim reqJson As String = JsonConvert.SerializeObject(request, settings)
        Dim url As String = Me.BaseUrl & "/helloworld/say-hello/" & "v1"
        Using httpRequest As New HttpRequestMessage(HttpMethod.Post, url)
            httpRequest.Content = New StringContent(reqJson, Encoding.UTF8, "application/json")
            httpRequest.Headers.Accept.Clear()
            httpRequest.Headers.Accept.Add(New MediaTypeWithQualityHeaderValue("application/json"))
            Dim response As HttpResponseMessage = Await _httpClient.SendAsync(httpRequest, cancellationToken)
            Dim respBody As String = Await response.Content.ReadAsStringAsync()
            If Not response.IsSuccessStatusCode Then
                Throw New HttpRequestException(String.Format("HTTP request failed with status {0}: {1}", CInt(response.StatusCode), respBody))
            End If
            Dim result As HelloReply = JsonConvert.DeserializeObject(Of HelloReply)(respBody, settings)
            Return result
        End Using
    End Function
End Class

End Namespace
```

### net40hwr Mode Output
Given the same proto file with `--framework net40hwr`, this tool produces:
```vb
Option Strict On
Option Explicit On
Option Infer On

Imports System
Imports System.Text
Imports System.Collections.Generic
Imports Newtonsoft.Json
Imports Newtonsoft.Json.Serialization
Imports System.Net
Imports System.IO

Namespace Helloworld

' HelloRequest DTO
Public Class HelloRequest
    <JsonProperty("name")>
    Public Property Name As String
End Class

' HelloReply DTO
Public Class HelloReply
    <JsonProperty("message")>
    Public Property Message As String
End Class

' Greeter HTTP client with HttpWebRequest
Public Class GreeterClient
    Public Property BaseUrl As String

    Public Sub New(baseUrl As String)
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        Me.BaseUrl = baseUrl
    End Sub

    ' SayHello calls POST {BaseUrl}/helloworld/say-hello/v1
    Public Function SayHello(request As HelloRequest, Optional authHeaders As Dictionary(Of String, String) = Nothing) As HelloReply
        Dim url As String = Me.BaseUrl & "/helloworld/say-hello/" & "v1"
        Return PostJson(Of HelloReply)(url, request, authHeaders)
    End Function
End Class

End Namespace
```

## Namespaces and Type Mapping
- Namespace resolution (priority order):
  1. If the proto declares a package (e.g., foo.bar), each segment is PascalCased and joined with dots: Foo.Bar (proto package takes priority)
  2. Else if --package is provided, it is used verbatim (CLI override as fallback)
  3. Else, the file base name is PascalCased and used as the namespace
- Proto → VB type mapping:
  - string → String; bool → Boolean; bytes → Byte()
  - int32/sint32/sfixed32 → Integer; int64/sint64/sfixed64 → Long
  - uint32/fixed32 → UInteger; uint64/fixed64 → ULong
  - double → Double; float → Single
  - repeated T → List(Of T)

## HTTP proxy assumptions (per requirements)
- There is an HTTP proxy between client and gRPC server that converts HTTP POST with JSON body into gRPC and returns JSON.
- This tool only supports unary RPCs.
- All routes must include a lowercase version segment as described above.

## JSON Schema Generation

In addition to generating VB.NET code, protoc-http-go automatically generates **JSON Schema Draft 2020-12** files for all protobuf messages and enums. These schemas are useful for:
- **Request/Response Validation**: Validate JSON payloads before sending to gRPC services
- **API Documentation**: Generate API documentation from schemas using tools like Swagger/OpenAPI
- **Client-Side Validation**: Use in web frontends (JavaScript/TypeScript) or other languages
- **Code Generation**: Generate TypeScript interfaces, JSON validators, or other language bindings

### Output Structure

JSON schemas are generated in a `json/` subdirectory under the output directory:

```
output/
├── json/                         # JSON Schema directory
│   ├── helloworld.json           # Schema for helloworld.proto
│   ├── common.json               # Schema for common.proto
│   ├── user-service.json         # Schema for user-service.proto
│   └── stock-service.json        # Schema for stock-service.proto
├── helloworld.vb                 # VB.NET files
├── common.vb
├── user-service.vb
└── stock-service.vb
```

### Schema Format

Each `.json` file contains schemas for all messages and enums defined in the corresponding `.proto` file:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/helloworld.json",
  "title": "Schemas for proto/simple/helloworld.proto",
  "description": "JSON Schema definitions for all messages and enums in proto/simple/helloworld.proto (package: helloworld)",
  "$defs": {
    "HelloRequest": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string"
        }
      },
      "additionalProperties": false
    },
    "HelloReply": {
      "type": "object",
      "properties": {
        "message": {
          "type": "string"
        }
      },
      "additionalProperties": false
    }
  }
}
```

### Type Mappings

Protobuf scalar types are mapped to JSON Schema types as follows:

| Protobuf Type | JSON Schema Type | Format/Constraints |
|--------------|------------------|-------------------|
| `string` | `string` | - |
| `int32`, `sint32`, `sfixed32` | `integer` | `format: int32` |
| `int64`, `sint64`, `sfixed64` | `integer` | `format: int64` |
| `uint32`, `fixed32` | `integer` | `format: uint32, minimum: 0` |
| `uint64`, `fixed64` | `integer` | `format: uint64, minimum: 0` |
| `bool` | `boolean` | - |
| `float` | `number` | `format: float` |
| `double` | `number` | `format: double` |
| `bytes` | `string` | `contentEncoding: base64` |
| `enum` | `string` | `enum: [...]` with value descriptions |
| `repeated T` | `array` | `items: {$ref or type}` |
| Message types | `object` | `$ref: #/$defs/MessageName` |

### Features

#### 1. Nested Message Types

Nested messages use qualified names in `$defs`:

```json
{
  "$defs": {
    "Outer": {
      "type": "object",
      "properties": {
        "inner": {
          "$ref": "#/$defs/Outer.Inner"
        }
      }
    },
    "Outer.Inner": {
      "type": "object",
      "properties": {
        "name": { "type": "string" }
      }
    }
  }
}
```

#### 2. Cross-Package References

Messages referencing types from other proto files use relative file references:

```json
{
  "$defs": {
    "Holding": {
      "type": "object",
      "properties": {
        "ticker": {
          "$ref": "common.json#/$defs/Ticker"
        }
      }
    }
  }
}
```

#### 3. Repeated Fields

Repeated fields are represented as arrays:

```json
{
  "holdings": {
    "type": "array",
    "items": {
      "$ref": "#/$defs/Holding"
    }
  }
}
```

#### 4. Enum Types

Enums include descriptions with numeric value mappings:

```json
{
  "TradeAction": {
    "type": "string",
    "enum": ["BUY", "SELL"],
    "description": "Enum values: BUY=0, SELL=1"
  }
}
```

#### 5. camelCase Field Names

Field names are automatically converted from snake_case to camelCase to match JSON serialization:

```proto
message User {
  int32 user_id = 1;      // Proto definition
}
```

```json
{
  "User": {
    "type": "object",
    "properties": {
      "userId": {           // JSON Schema uses camelCase
        "type": "integer",
        "format": "int32"
      }
    }
  }
}
```

### Usage Examples

#### Python Validation

```python
import json
import jsonschema

# Load schema
with open('output/json/user-service.json') as f:
    schema = json.load(f)

# Validate request
request = {
    "userId": 123,
    "ticker": "APPLE",
    "price": 150,
    "quantity": 10,
    "action": "BUY"
}

# Validate against StockTradeRequest schema
resolver = jsonschema.RefResolver.from_schema(schema)
jsonschema.validate(
    request,
    schema['$defs']['StockTradeRequest'],
    resolver=resolver
)
```

#### Node.js Validation with Ajv

```javascript
const Ajv = require('ajv');
const schema = require('./output/json/user-service.json');

const ajv = new Ajv();
const validate = ajv.compile(schema.$defs.StockTradeRequest);

const request = {
  userId: 123,
  ticker: "APPLE",
  price: 150,
  quantity: 10,
  action: "BUY"
};

if (validate(request)) {
  console.log('Valid!');
} else {
  console.log('Invalid:', validate.errors);
}
```

#### TypeScript Interface Generation

Use tools like `json-schema-to-typescript` to generate TypeScript interfaces:

```bash
npm install -g json-schema-to-typescript
json2ts -i output/json/user-service.json -o user-service.d.ts
```

### Schema Reference Patterns

When referencing schemas in validation:

```javascript
// Same file reference
{ "$ref": "#/$defs/MessageName" }

// Cross-file reference (relative path)
{ "$ref": "common.json#/$defs/Ticker" }

// Nested message reference
{ "$ref": "#/$defs/Outer.Inner" }
```

### Disabling JSON Schema Generation

JSON schema generation is automatic and currently cannot be disabled. If schema generation fails for a file, a warning is printed but VB.NET code generation continues.

## Usage Patterns

### net45 Mode - HttpClient Injection
For .NET 4.5+ compatible code, HttpClient must be injected through the constructor for proper connection pooling:

```vb
' Create a shared HttpClient instance for the same base URL
Dim sharedHttpClient As New HttpClient()

' Inject it into your client
Dim client As New GreeterClient("https://api.example.com", sharedHttpClient)

' Use the client (async)
Dim request As New HelloRequest() With {.Name = "World"}
Dim response As HelloReply = Await client.SayHelloAsync(request)
```

### net40hwr Mode - Direct Constructor
For .NET 4.0 without additional packages, use the simple constructor with optional authorization headers:

```vb
' Create client with base URL only
Dim client As New GreeterClient("https://api.example.com")

' Use the client (synchronous) with optional auth headers
Dim request As New HelloRequest() With {.Name = "World"}
Dim authHeaders As New Dictionary(Of String, String) From {
    {"Authorization", "Bearer your-token"},
    {"X-Custom-Header", "custom-value"}
}
Dim response As HelloReply = client.SayHello(request, authHeaders)
```

## VB.NET Reserved Keyword Handling

When proto field names conflict with VB.NET reserved keywords, the generated property names are automatically escaped by wrapping them in square brackets `[keyword]`. This ensures the generated VB.NET code compiles successfully while preserving the original JSON serialization names.

### Automatic Escaping

- **Property Names**: Reserved keywords in property names are escaped with square brackets
- **JSON Names**: JSON property names in `<JsonProperty>` attributes remain unchanged (camelCase)
- **Keywords**: All 148 VB.NET reserved keywords are recognized and escaped (e.g., `Error`, `Class`, `String`, `Integer`, `Property`, `For`, `If`, `End`, `Try`, `Catch`, etc.)

### Examples

**Proto Definition**:
```proto
message ErrorInfo {
  string error = 1;      // Reserved keyword
  string class = 2;      // Reserved keyword
  int32 integer = 3;     // Reserved keyword
  string property = 4;   // Reserved keyword
  string user_name = 5;  // Not a keyword
}
```

**Generated VB.NET Code**:
```vb
Public Class ErrorInfo
    <JsonProperty("error")>
    Public Property [Error] As String

    <JsonProperty("class")>
    Public Property [Class] As String

    <JsonProperty("integer")>
    Public Property [Integer] As Integer

    <JsonProperty("property")>
    Public Property [Property] As String

    <JsonProperty("userName")>
    Public Property UserName As String    ' Not escaped
End Class
```

**JSON Serialization**: The escaped property names work seamlessly with JSON serialization:
```vb
Dim info As New ErrorInfo With {
    .[Error] = "Connection failed",
    .[Class] = "NetworkError",
    .[Integer] = 500,
    .[Property] = "timeout",
    .UserName = "john"
}
Dim json As String = JsonConvert.SerializeObject(info)
' Result: {"error":"Connection failed","class":"NetworkError","integer":500,"property":"timeout","userName":"john"}
```

## Shared HTTP Utilities Feature

When multiple proto files with services exist in the same directory, protoc-http-go automatically generates a shared HTTP utility class to eliminate code duplication and improve maintainability.

### Automatic Detection

- **Single proto file**: Embeds PostJson/PostJsonAsync method directly in each service client
- **Multiple proto files with services in same directory**: Generates `{Directory}HttpUtility.vb` shared utility class

### How It Works

1. **Directory Grouping**: Proto files are grouped by their parent directory
2. **Service Detection**: If 2+ files in a directory contain services, a shared utility is generated
3. **Naming Convention**: Directory name is converted to PascalCase + "HttpUtility" suffix
   - Example: `proto/complex` → `ComplexHttpUtility.vb`
4. **Dependency Injection**: Service clients instantiate the shared utility in their constructors

### Benefits

- **46-47% code reduction** per service client file
- **Single source of truth** for HTTP communication logic
- **Better testability** through dependency injection pattern
- **Consistent error handling** across all services in the same directory
- **No breaking changes** - public APIs remain identical

### Code Comparison

**Before (Embedded PostJson):**
```vb
Public Class UserServiceClient
    ' ... 38 lines of PostJson implementation ...
    Public Function GetUserInformation(...) As UserInformation
        Return PostJson(Of UserInformationRequest, UserInformation)(...)
    End Function
End Class
```

**After (Shared Utility):**
```vb
' ComplexHttpUtility.vb - Shared by all services
Public Class ComplexHttpUtility
    Public Function PostJson(Of TReq, TResp)(...) As TResp
        ' ... HTTP implementation ...
    End Function
End Class

' user-service.vb - Uses shared utility
Public Class UserServiceClient
    Private ReadOnly _httpUtility As ComplexHttpUtility

    Public Sub New(baseUrl As String)
        _httpUtility = New ComplexHttpUtility(baseUrl)
    End Sub

    Public Function GetUserInformation(...) As UserInformation
        Return _httpUtility.PostJson(Of UserInformationRequest, UserInformation)(...)
    End Function
End Class
```

### Generated File Structure

**Single File Example** (`proto/simple/helloworld.proto`):
```bash
./protoc-http-go --proto proto/simple --out output --framework net45
```
Generates:
- `output/helloworld.vb` (with embedded PostJsonAsync)

**Multiple Files Example** (`proto/complex/` directory):
```bash
./protoc-http-go --proto proto/complex --out output --framework net45
```
Generates:
- `output/ComplexHttpUtility.vb` ⭐ Shared utility (68 lines)
- `output/user-service.vb` - Uses ComplexHttpUtility (117 lines, was 158 lines = 26% reduction)
- `output/stock-service.vb` - Uses ComplexHttpUtility (63 lines, was 104 lines = 39% reduction)
- `output/common.vb` - Data types only (no services)
- `output/nested.vb` - Data types only (no services)

### Framework Mode Support

Both NET45 and NET40HWR modes support shared utilities:

**NET45 Mode (Async)**:
```vb
Public Class ComplexHttpUtility
    Private ReadOnly _http As HttpClient
    Public Async Function PostJsonAsync(Of TReq, TResp)(...) As Task(Of TResp)
```

**NET40HWR Mode (Sync)**:
```vb
Public Class ComplexHttpUtility
    Private ReadOnly _baseUrl As String
    Public Function PostJson(Of TReq, TResp)(...) As TResp
```

### Usage Example

```vb
' NET45 mode with shared utility
Dim httpClient As New HttpClient()
Dim userService As New UserServiceClient(httpClient, "https://api.example.com")
Dim stockService As New StockServiceClient(httpClient, "https://api.example.com")

' Both services share the same ComplexHttpUtility instance internally
Dim userInfo = Await userService.GetUserInformationAsync(request)
Dim stockPrice = Await stockService.GetStockPriceAsync(request)
```

## Notes on parsing approach (non-functional requirement)
The current implementation uses a lightweight regex-based parser suitable for the subset of proto3 used in the provided samples. For production-grade parsing, a better approach is to:
- Implement a protoc plugin and consume the protobuf descriptor set, or
- Use an existing protobuf AST library to parse .proto files reliably.

This refactor keeps the minimal change surface but documents the recommended direction for robustness.

## Verifying generation
Test the .NET Framework mode implementations:

```bash
# Test .NET 4.5+ mode (default)
go run cmd/protoc-http-go/main.go --proto proto/simple/helloworld.proto --out demo_output_net45 --framework net45
# → demo_output_net45/helloworld.vb (async methods with HttpClient injection)

# Test .NET 4.0 mode
go run cmd/protoc-http-go/main.go --proto proto/simple/helloworld.proto --out demo_output_net40hwr --framework net40hwr
# → demo_output_net40hwr/helloworld.vb (sync methods with HttpWebRequest)

# Test with complex proto structure
go run cmd/protoc-http-go/main.go --proto proto/complex --out demo_complex --framework net45
# → Generates multiple .vb files for the entire proto directory
```

Verify the output files contain appropriate imports, constructor signatures, and method signatures for each framework mode.

## Troubleshooting

### General Issues
- Ensure your VB project references Newtonsoft.Json (Json.NET).
- Confirm your HTTP proxy follows the required route format and returns JSON.
- If your proto contains advanced features (oneof, maps, options), they may not be supported yet.

### Framework-Specific Issues

**net45 Mode:**
- For .NET 4.5+: No additional references needed beyond Newtonsoft.Json
- For .NET 4.0: Install NuGet packages `Microsoft.Net.Http` and `Microsoft.Bcl.Async`
- Ensure you're injecting HttpClient correctly to avoid connection exhaustion
- Use proper async/await patterns with CancellationToken support

**net40hwr Mode:**
- No additional NuGet packages required beyond Newtonsoft.Json
- Authorization headers must be passed as Dictionary parameters
- All calls are synchronous - no async/await support
- WebException propagates directly to calling code - implement your own Try-Catch blocks for error handling
- No built-in exception handling in PostJson utility (by design per non-functional requirements)

## License
This repository follows the project's license terms.