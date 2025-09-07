# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This repository implements a **polyglot gRPC-to-HTTP proxy ecosystem** that enables HTTP/1.1 clients to communicate with gRPC servers through code generation and proxy services. The project consists of:

1. **Code Generators**: Tools that generate HTTP client libraries from Protocol Buffer definitions in multiple languages
2. **HTTP Proxy**: A Spring Boot service that converts HTTP/1.1 requests to gRPC calls
3. **Example Services**: Reference implementations demonstrating the ecosystem in action

## Architecture

### Core Pattern: HTTP-to-gRPC Proxy
```
HTTP Client → HTTP/1.1 Proxy → gRPC Server
     ↑              ↑              ↑
Generated Code    grpc-http1-proxy   gRPC Service
```

### Code Generation Pattern
The repository follows a consistent pattern across languages:
- **Input**: `.proto` files (Protocol Buffer definitions)
- **Output**: Language-specific HTTP client libraries with DTOs
- **Target**: VB.NET for .NET Framework (primary focus)
- **URL Convention**: `{base_url}/{proto_file_name}/{rpc_method_name}` (kebab-case)
- **JSON**: camelCase field serialization

### Multi-Language Implementation Strategy
Each `protoc-http-*` directory implements the same functionality in different languages:
- **Go**: `protoc-http-go` - Clean, modular Go implementation
- **Python**: `protoc-http-py` - Python implementation with pytest testing
- **Rust**: `protoc-http-rs` - Modern Rust with idiomatic patterns, traits, and rich error handling

## Component Structure

### Code Generators (`protoc-http-*`)
Each generator follows the same interface:
- **CLI**: `--proto <path> --out <dir> [--namespace/--package <name>]`
- **Input Support**: Single `.proto` file or recursive directory processing
- **Output**: VB.NET classes with JSON attributes and HTTP client implementations
- **Test Structure**: Simple and complex proto examples in `proto/` directory

### HTTP Proxy (`grpc-http1-proxy`)
- **Technology**: Spring Boot 3.5.0 with Kotlin
- **Purpose**: Converts HTTP POST requests to gRPC calls
- **Configuration**: gRPC backend address in `application.properties`
- **Port**: Default HTTP port 8080

### Reference Services
- **`client-mock-server`**: Java-based gRPC server for testing
- **`grpc-trading-platform`**: Multi-service example with user and aggregator services
- **`GrpcHttpProxyClient`**: C# client demonstration

## Common Development Commands

### Go Generator (`protoc-http-go`)
```bash
# Build
make build
# or
go build -o protoc-http-go cmd/protoc-http-go/main.go

# Install dependencies
make install
# or
go mod tidy

# Run tests
make test

# Generate from single proto
./protoc-http-go --proto proto/simple/helloworld.proto --out generated
# or
go run cmd/protoc-http-go/main.go --proto proto/simple/helloworld.proto --out generated

# Generate from directory
./protoc-http-go --proto proto/complex --out generated

# Clean up
make clean
```

### Rust Generator (`protoc-http-rs`)
```bash
# Build
cargo build --release

# Run tests
cargo test

# Generate from proto
cargo run -- --proto proto/simple --out test_output

# Generate with custom namespace  
cargo run -- --proto proto/complex --out generated --namespace MyCompany.ApiClients
```

### Python Generator (`protoc-http-py`)
```bash
# Run directly
python -m protoc_http_py.main --proto proto/simple/helloworld.proto --out out

# Run tests
pytest
# or
python -m pytest

# Generate with namespace
python -m protoc_http_py.main --proto proto/complex --out out --namespace Demo.App
```

### HTTP Proxy (`grpc-http1-proxy`)
```bash
# Run the proxy server
./mvnw spring-boot:run

# Run tests
./mvnw test

# Build
./mvnw clean package
```

### Test HTTP proxy endpoint
```bash
# Using curl
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice"}' \
  http://localhost:8080/helloworld/SayHello

# Using HTTPie
http POST :8080/helloworld/SayHello name=Alice
```

### Mock gRPC Server (`client-mock-server`)
```bash
# Run the mock gRPC server (port 50051)
./mvnw spring-boot:run

# Run tests
./mvnw test
```

## Testing Strategy

### Code Generator Testing
Each generator includes:
1. **Simple Example**: Basic `helloworld.proto` with single service
2. **Complex Example**: Multiple proto files with imports, nested types, and enums
3. **Compilation Verification**: Generated code must compile in target language

### Integration Testing Pattern
1. Start gRPC server (`client-mock-server` on port 50051)
2. Start HTTP proxy (`grpc-http1-proxy` on port 8080)
3. Use generated client code to make HTTP requests
4. Verify round-trip: HTTP → Proxy → gRPC → Response

### Test Command Examples
```bash
# Test Go generator
cd protoc-http-go
make test

# Test Python generator  
cd protoc-http-py
pytest

# Test Rust generator
cd protoc-http-rs
cargo test

# Test HTTP proxy
cd grpc-http1-proxy
./mvnw test
```

## Development Patterns

### Adding New Language Support
1. Create new `protoc-http-{lang}` directory
2. Implement CLI with standard arguments: `--proto`, `--out`, `--namespace`
3. Parse proto files (handle imports, nested types, enums)
4. Generate target language code with:
   - DTO classes with JSON serialization attributes
   - HTTP client classes for unary RPCs
   - Proper namespace/package handling
5. Add test proto files and verification

### Proto File Conventions
- **Simple protos**: `proto/simple/` - Basic single-file examples
- **Complex protos**: `proto/complex/` - Multi-file with imports and advanced types
- **Imports**: Use relative paths like `import "common/common.proto"`
- **Services**: Only unary RPCs are supported (no streaming)

### URL Routing Convention
- **Pattern**: `{base_url}/{proto_file_name}/{rpc_method_name}`
- **Method Naming**: Convert PascalCase to kebab-case
  - `SayHello` → `say-hello`
  - `GetUserInfo` → `get-user-info`
- **Proto File Naming**: Use filename without `.proto` extension

### JSON Serialization Rules
- **Field Names**: camelCase (e.g., `user_name` → `userName`)
- **Content-Type**: `application/json`
- **HTTP Method**: POST for all RPC calls

## Key Files and Directories

### Configuration Files
- `protoc-http-requirements.md` - Overall project requirements and constraints
- `grpc-http1-proxy/src/main/resources/application.properties` - Proxy server configuration
- `*/pom.xml` - Maven projects (Java/Kotlin components)
- `protoc-http-go/go.mod` - Go module definition
- `protoc-http-rs/Cargo.toml` - Rust project configuration
- `protoc-http-py/pyproject.toml` - Python project configuration

### Proto Definitions
- `*/proto/simple/helloworld.proto` - Basic test proto across all generators
- `*/proto/complex/` - Advanced proto examples with imports and nested types

### Generated Code Locations
- `*/generated/` or `*/test_output*` - Generated client libraries (gitignored)
- Look for `.vb` files (VB.NET target) in output directories

## Architecture Constraints

### Supported Features
- **Unary gRPC calls only** (no streaming)
- **VB.NET/.NET Framework target** for generated code
- **Cross-package imports** with proper namespace mapping
- **Nested message types** and enums
- **HTTP/1.1 to gRPC bridging** through proxy

### Limitations
- No support for `map<K,V>`, `oneof`, or advanced proto features
- Block comments (`/* */`) may interfere with parsing
- Streaming RPCs are ignored
- Limited error handling for malformed proto files

This repository demonstrates a comprehensive approach to bridging HTTP/1.1 and gRPC through code generation, providing multiple language implementations that follow consistent patterns and conventions.
