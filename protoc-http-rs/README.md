# protoc-http-rs

A **modern, idiomatic Rust implementation** of a Protocol Buffer compiler plugin that generates VB.NET HTTP proxy client code and DTOs from `.proto` files for unary gRPC calls.

## ✨ What's New in Version 2.0

This version features a complete architectural overhaul with **idiomatic Rust patterns**:

- **🏗️ Modular Architecture**: Clean separation of concerns with dedicated modules
- **🛡️ Strong Type Safety**: Domain types with built-in validation (e.g., `Identifier`, `PackageName`)
- **🔧 Builder Patterns**: Ergonomic APIs using derive-based builders
- **⚡ Iterator Chains**: Functional programming patterns replacing imperative loops
- **🎯 Trait-Based Design**: Extensible code generation system via `CodeGenerator` trait
- **🚨 Enhanced Error Handling**: Rich error types using `thiserror` with context
- **📋 Declarative Style**: Template-based code generation with `indoc`

## Architecture

The refactored codebase follows modern Rust patterns with clear separation of concerns:

```
protoc-http-rs/
├── src/
│   ├── main.rs           # CLI interface with functional composition
│   ├── error.rs          # Rich error types with thiserror
│   ├── types.rs          # Strong domain types with validation
│   ├── parser.rs         # Descriptor-based parsing via protox + prost-types (pure Rust)
│   ├── codegen.rs        # Trait-based code generation system
│   ├── vb_codegen.rs     # VB.NET generator implementation
│   └── utils.rs          # Utility functions
├── proto/                # Test protocol buffer files
└── tests/                # Integration tests
```

### Key Traits

- **`CodeGenerator`**: Extensible trait for different target languages
- **`ProtoParser`**: Descriptor-based parsing (protox + prost-types), comprehensive error handling, no protoc required
- **Strong Domain Types**: `Identifier`, `PackageName`, `ProtoType` with built-in validation
- **Builder Pattern**: All complex types use `derive_builder` for ergonomic construction

## Overview

This tool assumes there is an HTTP proxy between HTTP client and gRPC server that:
- Converts HTTP POST requests with request body as message content to gRPC requests
- Converts gRPC responses to JSON as response body
- Routes RPCs using the format: `{base_url}/{proto_file_name}/{rpc_method_name}`
- Uses kebab-case for RPC method names in URLs

## Features

- **🆕 Shared HTTP Utilities**: Automatic generation of shared utility classes to eliminate code duplication
- **VB.NET Code Generation**: Generates VB.NET classes following .NET Framework best practices
- **.NET Framework Compatibility**: Multiple compatibility modes for different .NET Framework versions
- **Optional Timeout Support**: Caller-controlled timeouts with sensible defaults
- **Robust Error Handling**: Comprehensive error handling with proper exception types
- **Unary RPCs Only**: Supports only unary gRPC calls (no streaming)
- **Camel Case JSON**: All JSON fields are serialized in camelCase format
- **Cross-Package Support**: Handles multiple proto files with imports and package dependencies (resolved via descriptors)
- **Nested Messages**: Full support for nested message types
- **Enums**: Complete enum support with proper VB.NET mapping
- **Type Safety**: Proper type mapping from Protocol Buffers to VB.NET types
- **RPC Versioning**: Automatic version extraction from method names (V1, V2, V3, etc.)
- **VB.NET Reserved Keyword Handling**: Automatic escaping of VB.NET reserved keywords in property names
- **Special Logic for Custom Requirements**: Support for msgHdr field preservation, N2 kebab-case handling, and namespace priority

## Special Logic Features

### msgHdr Field Preservation

When a message is named exactly `msgHdr` (case-sensitive), the generator preserves the exact casing of field names in JSON properties instead of converting them to camelCase. This applies to both top-level and nested `msgHdr` messages.

**Example**:
```proto
message msgHdr {
  string userId = 1;        // Preserved as "userId"
  string FirstName = 2;     // Preserved as "FirstName"
  int32 user_age = 3;       // Preserved as "user_age"
}

message RegularMessage {
  string user_id = 1;       // Converted to "userId"
  string first_name = 2;    // Converted to "firstName"
}
```

**Generated VB.NET**:
```vb
Public Class msgHdr
    <JsonProperty("userId")>      ' Exact casing preserved
    Public Property UserId As String

    <JsonProperty("FirstName")>    ' Exact casing preserved
    Public Property FirstName As String

    <JsonProperty("user_age")>     ' Exact casing preserved
    Public Property UserAge As Integer
End Class

Public Class RegularMessage
    <JsonProperty("userId")>       ' Converted to camelCase
    Public Property UserId As String

    <JsonProperty("firstName")>    ' Converted to camelCase
    Public Property FirstName As String
End Class
```

### N2 Kebab-Case Handling

The pattern "N2" (capital N followed by digit 2) in RPC method names converts to `-n2-` (keeping them together) instead of `-n-2-` in kebab-case URLs. This is a special case only for N2; other patterns like N3, N4, etc., still split normally.

**Example**:
```proto
service N2TestService {
  rpc GetN2Data(Request) returns (Response);      // URL: get-n2-data
  rpc N2ToN2Sync(Request) returns (Response);     // URL: n2-to-n2-sync
  rpc GetN3Data(Request) returns (Response);      // URL: get-n-3-data (control)
}
```

### Namespace Priority

When generating VB.NET namespace declarations, the priority order is:
1. **Proto package** (highest priority) - Always used if present
2. **CLI --namespace argument** - Only used as fallback when proto has no package
3. **Filename-based** (lowest priority) - Used when neither package nor CLI argument exists

**Example**:
```bash
# Proto with package declaration
protoc-http-rs --proto myservice.proto --namespace CustomNamespace --out ./output

# If myservice.proto contains "package com.example.api;", the generated namespace will be:
# Namespace ComExampleApi  (proto package takes priority, CLI namespace ignored)
```

## VB.NET Reserved Keyword Handling

When proto field names conflict with VB.NET reserved keywords, the generated property names are automatically escaped by wrapping them in square brackets `[keyword]`. This ensures the generated VB.NET code compiles successfully while preserving the original JSON serialization names.

### Automatic Escaping

- **Property Names**: Reserved keywords in property names are escaped with square brackets
- **JSON Names**: JSON property names in `<JsonProperty>` attributes remain unchanged (lowerCamelCase)
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

The JSON keys remain lowercase camelCase without escaping, ensuring API compatibility while allowing VB.NET code to compile correctly.

## 🆕 Shared HTTP Utilities Feature

When multiple protobuf files exist in the same directory, protoc-http-rs automatically generates shared HTTP utility classes to eliminate code duplication and significantly reduce generated file sizes.

### Automatic Detection and Generation

```bash
# Multiple proto files in same directory triggers shared utility generation
protoc-http-rs --proto proto/complex --out generated
```

**Generated Structure:**
```
generated/
├── ComplexHttpUtility.vb    # ⭐ Shared HTTP utility class
├── stock-service.vb         # Uses shared utility (24-48% smaller)
├── user-service.vb          # Uses shared utility (24-48% smaller)
└── common.vb                # Common types and messages
```

### Code Reduction Achieved

| Compatibility Mode | Before | After | Reduction |
|--------------------|--------|-------|-----------|
| **NET45** (async) | ~104 lines | ~56 lines | **~46%** |
| **NET40HWR** (sync) | ~98 lines | ~52 lines | **~47%** |

### Benefits

- **✅ Eliminates Duplication**: Consolidates ~50 lines of PostJson functions per service
- **✅ Maintains Identical APIs**: No breaking changes for consumers
- **✅ Dependency Injection**: Clean architecture with constructor injection
- **✅ Both Compatibility Modes**: Works with NET45 async and NET40HWR sync patterns
- **✅ Automatic Fallback**: Single files continue to use embedded functions

## .NET Framework Compatibility Modes

This tool supports multiple .NET Framework versions through compatibility modes:

### **NET45 Mode (Default)** - `--net45`

**Target**: .NET Framework 4.5+ or .NET Framework 4.0 with Microsoft.Net.Http + Microsoft.Bcl.Async

**Features**:
- HttpClient + async/await patterns
- HttpClient constructor injection for proper instance sharing
- CancellationToken support with multiple overloads
- Optional timeout support via CancellationTokenSource
- Modern error handling with HttpRequestException

**Generated Constructor**:
```vb
Public Sub New(http As HttpClient, baseUrl As String)
```

**Generated Method Overloads**:
```vb
' Simple overload
Public Function SayHelloAsync(request As HelloRequest) As Task(Of HelloReply)

' With cancellation token
Public Function SayHelloAsync(request As HelloRequest, cancellationToken As CancellationToken) As Task(Of HelloReply)

' With cancellation token and optional timeout
Public Async Function SayHelloAsync(request As HelloRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of HelloReply)
```

**Usage Example**:
```vb
Dim httpClient As New HttpClient()
Dim client As New GreeterClient(httpClient, "https://api.example.com")
Dim response = Await client.SayHelloAsync(request, CancellationToken.None, 30000) ' 30 second timeout
```

### **NET40HWR Mode** - `--net40hwr`

**Target**: .NET Framework 4.0 without additional packages

**Features**:
- HttpWebRequest + synchronous patterns (no async/await)
- Simple constructor with baseUrl only
- Optional timeout support via HttpWebRequest.Timeout
- WebException propagates directly to calling code (no exception handling in PostJson utility)
- Response validation and empty response detection
- Users must implement their own Try-Catch blocks to handle exceptions as needed

**Generated Constructor**:
```vb
Public Sub New(baseUrl As String)
```

**Generated Method Overloads**:
```vb
' Simple overload
Public Function SayHello(request As HelloRequest) As HelloReply

' With optional timeout
Public Function SayHello(request As HelloRequest, Optional timeoutMs As Integer? = Nothing) As HelloReply
```

**Usage Example**:
```vb
Dim client As New GreeterClient("https://api.example.com")
Dim response = client.SayHello(request, 30000) ' 30 second timeout
```

### **Mode Comparison**

| Feature | NET45 Mode | NET40HWR Mode |
|---------|------------|---------------|
| **Target Framework** | .NET 4.5+ | .NET 4.0 |
| **HTTP Client** | HttpClient (injected) | HttpWebRequest |
| **Async Support** | ✅ async/await | ❌ Synchronous only |
| **Timeout Support** | ✅ CancellationTokenSource | ✅ HttpWebRequest.Timeout |
| **Error Handling** | HttpRequestException with custom validation | WebException propagates directly to caller |
| **Constructor** | `(HttpClient, String)` | `(String)` |
| **Method Suffix** | `Async` | None |
| **Dependencies** | System.Net.Http | System.Net (built-in) |

## Parsing Approach (Pure Rust)

This project uses a descriptor-based parser implemented entirely in Rust:
- Parses .proto files using the protox crate and loads FileDescriptorProtos via prost-types.
- No protoc binary is required at runtime or build time.
- Include paths: the directory of each input .proto and the repository's `proto/` directory are added by default for import resolution.
- The generator consumes the canonical descriptors to produce VB.NET code.

## Limitations

- Code generation targets only unary RPCs. Methods with client/server streaming are parsed but not generated.
- Some Protocol Buffers features are parsed but not yet reflected in codegen (e.g., oneof, map-specific VB shapes, custom options).
- Options and annotations are currently ignored by the generator.

## Installation

### Prerequisites

- Rust 1.70+
- Cargo
- No protoc required (pure Rust parsing via protox)

### Build from Source

```bash
git clone <repository>
cd protoc-http-rs
cargo build --release
```

The binary will be available at `target/release/protoc-http-rs`.

## Usage

### Basic Usage

Generate VB.NET code from a single `.proto` file:

```bash
protoc-http-rs --proto path/to/file.proto --out output_directory
```

Generate VB.NET code from all `.proto` files in a directory (recursive):

```bash
protoc-http-rs --proto proto_directory --out output_directory
```

### Command Line Options

- `--proto <PATH>`: Path to a `.proto` file or directory containing `.proto` files (required)
- `--out <PATH>`: Output directory for generated `.vb` files (required)  
- `--namespace <NAMESPACE>`: Custom VB.NET namespace (optional, defaults to proto package or file name)
- `--net45`: Generate .NET Framework 4.5+ compatible code (HttpClient + async/await) - **default**
- `--net40hwr`: Generate .NET Framework 4.0 compatible code (HttpWebRequest + synchronous)
- `--net40`: Legacy alias for `--net40hwr` (backward compatibility)

### Examples

#### Single File Generation

```bash
# Generate from single proto file (default: NET45 mode)
protoc-http-rs --proto proto/simple/helloworld.proto --out generated

# With custom namespace
protoc-http-rs --proto proto/simple/helloworld.proto --out generated --namespace MyApp.Services

# Explicit NET45 mode (HttpClient + async/await)
protoc-http-rs --proto proto/simple/helloworld.proto --out generated --net45

# NET40HWR mode (HttpWebRequest + synchronous)
protoc-http-rs --proto proto/simple/helloworld.proto --out generated --net40hwr
```

#### Directory Generation

```bash
# Generate from all proto files in directory (default: NET45 mode)
protoc-http-rs --proto proto/complex --out generated

# Generate for .NET Framework 4.0 with HttpWebRequest
protoc-http-rs --proto proto/complex --out generated --net40hwr

# Generate with custom namespace and compatibility mode
protoc-http-rs --proto proto --out generated --namespace MyCompany.ApiClients --net45
```

#### Compatibility Mode Examples

```bash
# .NET Framework 4.5+ with HttpClient injection
protoc-http-rs --proto proto/simple/helloworld.proto --out generated/net45 --net45

# .NET Framework 4.0 with HttpWebRequest (no dependencies)
protoc-http-rs --proto proto/simple/helloworld.proto --out generated/net40 --net40hwr

# Legacy compatibility (alias for --net40hwr)
protoc-http-rs --proto proto/simple/helloworld.proto --out generated/legacy --net40
```

## Generated Code Structure

### DTO Classes

For each Protocol Buffer message, a VB.NET class is generated with:

- `<JsonProperty>` attributes for camelCase JSON serialization
- Public properties with proper VB.NET type mapping
- Support for nested message types

```vb
Public Class HelloRequest
    <JsonProperty("name")>
    Public Property Name As String
End Class
```

### Service Clients

For each gRPC service, a VB.NET client class is generated based on the compatibility mode and whether shared utilities are used.

#### **Service Clients with Shared Utilities (Multiple Proto Files)**

When multiple proto files exist in the same directory, service clients use dependency injection with shared HTTP utility classes:

```vb
Public Class UserServiceClient
    Private ReadOnly _httpUtility As ComplexHttpUtility

    Public Sub New(http As HttpClient, baseUrl As String)
        If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        _httpUtility = New ComplexHttpUtility(http, baseUrl)
    End Sub

    ' All RPC methods delegate to shared utility
    Public Async Function GetUserInformationAsync(request As UserInformationRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of UserInformation)
        Return Await _httpUtility.PostJsonAsync(Of UserInformationRequest, UserInformation)("/user-service/get-user-information/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
    End Function
End Class
```

**Benefits:**
- **~46-47% code reduction** compared to embedded HTTP functions
- **Dependency injection pattern** for better testability
- **Shared error handling logic** across all services
- **Identical public APIs** - no breaking changes

#### **Service Clients with Embedded Functions (Single Proto File)**

For single proto files, clients continue to use embedded HTTP functions for backward compatibility:

```vb
Public Class GreeterClient
    Private ReadOnly _http As HttpClient
    Private ReadOnly _baseUrl As String

    Public Sub New(http As HttpClient, baseUrl As String)
        If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        _http = http
        _baseUrl = baseUrl.TrimEnd("/"c)
    End Sub

    ' Embedded PostJsonAsync function (~50 lines of HTTP logic)
    Private Async Function PostJsonAsync(Of TReq, TResp)(relativePath As String, request As TReq, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of TResp)
        ' Full HTTP implementation with error handling...
    End Function

    ' RPC methods use embedded helper
    Public Async Function SayHelloAsync(request As HelloRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of HelloReply)
        Return Await PostJsonAsync(Of HelloRequest, HelloReply)("/helloworld/say-hello/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
    End Function
End Class
```

#### **Common Features (Both Patterns)**

- **HttpClient Constructor Injection**: Follows .NET Framework best practices
- **Async/await support**: All methods return `Task(Of T)`
- **Multiple overloads**: Simple, with CancellationToken, and with timeout
- **Robust error handling**: HttpRequestException with detailed error messages
- **Response validation**: Empty response detection

#### **NET40HWR Mode Client**

- **Simple constructor**: Only requires baseUrl parameter
- **Synchronous methods**: No async/await (compatible with .NET 4.0)
- **Optional timeout**: Via HttpWebRequest.Timeout property
- **WebException handling**: Proper error extraction from HTTP responses
- **Resource management**: Comprehensive Using statements

```vb
Public Class GreeterClient
    Private ReadOnly _baseUrl As String

    Public Sub New(baseUrl As String)
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        _baseUrl = baseUrl.TrimEnd("/"c)
    End Sub

    ' Simple overload
    Public Function SayHello(request As HelloRequest) As HelloReply
        Return SayHello(request, Nothing)
    End Function

    ' With optional timeout support
    Public Function SayHello(request As HelloRequest, Optional timeoutMs As Integer? = Nothing) As HelloReply
        ' Uses PostJson helper with HttpWebRequest and timeout...
    End Function
End Class
```

### Enums

Protocol Buffer enums are mapped to VB.NET enums:

```vb
Public Enum TradeAction
    BUY = 0
    SELL = 1
End Enum
```

## Type Mapping

| Protocol Buffer Type | VB.NET Type |
|---------------------|-------------|
| `string` | `String` |
| `int32` | `Integer` |
| `int64` | `Long` |
| `uint32` | `UInteger` |
| `uint64` | `ULong` |
| `bool` | `Boolean` |
| `float` | `Single` |
| `double` | `Double` |
| `bytes` | `Byte()` |
| `repeated T` | `List(Of T)` |

## Package and Namespace Handling

- Proto packages are converted to PascalCase VB.NET namespaces
- Dots in package names become underscores, then converted to PascalCase
- Cross-package type references are properly qualified
- Nested message types use dot notation: `Outer.Inner`

Example:
- Proto package `com.example.api` becomes VB namespace `ComExampleApi`
- Type reference `common.Ticker` becomes `Common.Ticker` in VB.NET

## URL Generation

RPC URLs follow the pattern: `{base_url}/{proto_file_name}/{rpc_method_name}/{version}`

### Method Name Processing

RPC method names are converted from PascalCase to kebab-case:
- `SayHello` → `say-hello`
- `GetUserInfo` → `get-user-info`
- `ProcessHTTPRequest` → `process-http-request`

### Version Extraction

The tool automatically extracts version information from RPC method names:
- Methods ending with `V{number}` have the version extracted
- Methods without version suffix default to `v1`
- Version segments are always lowercase in URLs

**Examples**:
- `GetUser` → `/proto-file/get-user/v1`
- `GetUserV2` → `/proto-file/get-user/v2`
- `GetUserV3` → `/proto-file/get-user/v3`
- `CreateOrderV10` → `/proto-file/create-order/v10`

### Complete URL Examples

Given a proto file `user-service.proto` with base URL `https://api.example.com`:

```
GetUserInformation    → https://api.example.com/user-service/get-user-information/v1
GetUserInformationV2  → https://api.example.com/user-service/get-user-information/v2
TradeStock           → https://api.example.com/user-service/trade-stock/v1
ProcessPaymentV3     → https://api.example.com/user-service/process-payment/v3
```

## Testing

### Run Unit Tests

```bash
cargo test
```

### Run Integration Tests

The integration tests generate actual VB.NET code and verify the output:

```bash
cargo test --test integration_tests
```

### Manual Testing

Test with the provided sample proto files:

```bash
# Test simple proto
cargo run -- --proto proto/simple --out test_output

# Test complex proto with imports
cargo run -- --proto proto/complex --out test_output
```

## Project Structure

```
protoc-http-rs/
├── Cargo.toml              # Rust project configuration
├── README.md               # This file
├── src/
│   └── main.rs             # Main implementation
├── proto/                  # Test protocol buffer files
│   ├── simple/
│   │   └── helloworld.proto
│   └── complex/
│       ├── common/
│       │   └── common.proto
│       ├── nested.proto
│       ├── stock-service.proto
│       └── user-service.proto
└── tests/
    └── integration_tests.rs # Integration tests
```

## Generated Dependencies

The generated VB.NET code requires different dependencies based on the compatibility mode:

### **NET45 Mode Dependencies**

Required NuGet packages:
- `Newtonsoft.Json` - For JSON serialization/deserialization
- `System.Net.Http` - For HttpClient functionality
  - Included in .NET Framework 4.5+
  - For .NET Framework 4.0: Install `Microsoft.Net.Http` package
- `Microsoft.Bcl.Async` - For async/await support in .NET Framework 4.0 (if targeting .NET 4.0)

### **NET40HWR Mode Dependencies**

Required NuGet packages:
- `Newtonsoft.Json` - For JSON serialization/deserialization

Built-in dependencies (no additional packages needed):
- `System.Net` - For HttpWebRequest functionality (built into .NET Framework 4.0)
- `System.IO` - For stream handling (built into .NET Framework)

### **Dependency Comparison**

| Mode | Newtonsoft.Json | System.Net.Http | Microsoft.Bcl.Async | Additional Packages |
|------|----------------|-----------------|---------------------|-------------------|
| **NET45** | ✅ Required | ✅ Required | ⚠️ .NET 4.0 only | 1-3 packages |
| **NET40HWR** | ✅ Required | ❌ Not used | ❌ Not needed | 1 package only |

**Recommendation**: Use NET40HWR mode for minimal dependencies and maximum .NET Framework 4.0 compatibility.

## Limitations

- **Unary RPCs Only**: Streaming RPCs are not supported
- **No Custom Options**: Protocol Buffer custom options are ignored
- **Simple Import Resolution**: Only basic import handling is implemented
- **VB.NET Target**: Only generates VB.NET code, not other languages

## Comparison with Python Version

This modern Rust implementation provides significant improvements:

### Performance & Safety
- **⚡ Better Performance**: Faster parsing and code generation with zero-cost abstractions
- **🛡️ Memory Safety**: Rust's memory safety guarantees prevent common bugs
- **🔒 Type Safety**: Compile-time type checking for the generator itself

### Code Quality & Maintainability  
- **🎯 Idiomatic Patterns**: Uses traits, iterators, and functional programming
- **🚨 Rich Error Handling**: Context-aware errors with `thiserror`
- **🔧 Modular Design**: Clean separation of concerns and extensible architecture
- **✨ Declarative Style**: Template-based generation with `indoc`

### Bug Fixes
- **Fixed VB.NET Syntax**: Corrects character literal syntax issues (`"/"c` instead of `/c`)
- **Improved Validation**: Strong typing prevents invalid proto constructs
- **Better Testing**: Comprehensive unit and integration tests

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run `cargo test` to ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the same terms as the parent project.

## Support

For issues, questions, or contributions, please refer to the main project repository.
