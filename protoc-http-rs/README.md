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

- **VB.NET Code Generation**: Generates VB.NET classes following .NET Framework best practices
- **Unary RPCs Only**: Supports only unary gRPC calls (no streaming)
- **Camel Case JSON**: All JSON fields are serialized in camelCase format
- **Cross-Package Support**: Handles multiple proto files with imports and package dependencies (resolved via descriptors)
- **Nested Messages**: Full support for nested message types
- **Enums**: Complete enum support with proper VB.NET mapping
- **Type Safety**: Proper type mapping from Protocol Buffers to VB.NET types

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

### Examples

#### Single File Generation

```bash
# Generate from single proto file
protoc-http-rs --proto proto/simple/helloworld.proto --out generated

# With custom namespace
protoc-http-rs --proto proto/simple/helloworld.proto --out generated --namespace MyApp.Services
```

#### Directory Generation

```bash
# Generate from all proto files in directory
protoc-http-rs --proto proto/complex --out generated

# Generate from all proto files with custom namespace
protoc-http-rs --proto proto --out generated --namespace MyCompany.ApiClients
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

For each gRPC service, a VB.NET client class is generated with:

- Async methods for all unary RPCs
- HTTP client using `HttpClient`
- Proper error handling and cancellation token support
- Two overloads per RPC: with and without `CancellationToken`

```vb
Public Class GreeterClient
    Private Shared ReadOnly _http As HttpClient = New HttpClient()
    Private ReadOnly _baseUrl As String

    Public Sub New(baseUrl As String)
        _baseUrl = baseUrl.TrimEnd("/"c)
    End Sub

    Public Function SayHelloAsync(request As HelloRequest) As Task(Of HelloReply)
        Return SayHelloAsync(request, CancellationToken.None)
    End Function

    Public Async Function SayHelloAsync(request As HelloRequest, cancellationToken As CancellationToken) As Task(Of HelloReply)
        ' Implementation...
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

RPC method names are converted from PascalCase to kebab-case for URLs:

- `SayHello` → `say-hello`
- `GetUserInfo` → `get-user-info`
- `ProcessHTTPRequest` → `process-http-request`

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

The generated VB.NET code requires the following NuGet packages:

- `Newtonsoft.Json` - For JSON serialization/deserialization
- `System.Net.Http` - For HTTP client functionality (part of .NET Framework)

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
