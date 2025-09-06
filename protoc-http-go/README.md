# protoc-http-go

Generate Go HTTP client stubs and DTOs from Protobuf (.proto) files for unary gRPC calls through HTTP proxy.

This tool parses protobuf definitions and generates Go code with:
- Go structs for messages with JSON tags (camelCase serialization)
- HTTP client implementations for unary RPCs (non-streaming)
- Support for enums and nested message types
- Works with single .proto files or recursively processes directories

The generated clients communicate with gRPC servers through an HTTP proxy (like [grpc-http1-proxy](../grpc-http1-proxy)) that converts HTTP POST requests to gRPC calls.

---

## Requirements
- Go 1.19+ 

## Installation

### Option 1: Build from source
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

### Command Line Options

```bash
protoc-http-go --proto <path> --out <dir> [--package <name>] [--baseurl <url>]
```

**Arguments:**
- `--proto` (required): Path to a single `.proto` file or directory containing `.proto` files
- `--out` (required): Directory where generated `.go` files will be written (created if doesn't exist)
- `--package` (optional): Override Go package name for generated code
- `--baseurl` (optional): Base URL for HTTP requests (can be set in code)

### Examples

**Generate from a single file:**
```bash
# Build first
go build -o protoc-http-go cmd/protoc-http-go/main.go

# Generate from single proto file
./protoc-http-go --proto proto/simple/helloworld.proto --out generated

# Or run directly
go run cmd/protoc-http-go/main.go --proto proto/simple/helloworld.proto --out generated
```

**Generate from a directory (recursive):**
```bash
# Generate from simple protos
./protoc-http-go --proto proto/simple --out generated

# Generate from complex protos with custom package name
./protoc-http-go --proto proto/complex --out generated --package myclient

# Run directly with custom package
go run cmd/protoc-http-go/main.go --proto proto/complex --out generated --package myclient
```

**Expected output:**
- For `proto/simple` → `generated/helloworld.go`
- For `proto/complex` → `generated/stock-service.go`, `generated/user-service.go`, `generated/nested.go`

## Generated Code Structure

For each `.proto` file, the tool generates:

### 1. Message Structs
```go
type HelloRequest struct {
    Name string `json:"name"`
}

type HelloReply struct {
    Message string `json:"message"`
}
```

### 2. Enum Types
```go
type TradeAction int32

const (
    TradeAction_BUY  TradeAction = 0
    TradeAction_SELL TradeAction = 1
)

func (e TradeAction) String() string {
    switch e {
    case 0: return "BUY"
    case 1: return "SELL"
    default: return fmt.Sprintf("Unknown_TradeAction(%d)", int32(e))
    }
}
```

### 3. HTTP Client Services
```go
type GreeterClient struct {
    BaseURL    string
    HTTPClient *http.Client
}

func NewGreeterClient(baseURL string) *GreeterClient {
    return &GreeterClient{
        BaseURL:    baseURL,
        HTTPClient: &http.Client{},
    }
}

func (c *GreeterClient) SayHello(ctx context.Context, req *HelloRequest) (*HelloReply, error) {
    // HTTP POST to {baseURL}/helloworld/say-hello
    // ...
}
```

## Using Generated Code

```go
package main

import (
    "context"
    "fmt"
    "log"
    
    "your-module/generated" // Import your generated package
)

func main() {
    // Create client with base URL of your HTTP proxy
    client := generated.NewGreeterClient("http://localhost:8080")
    
    // Or with custom HTTP client
    httpClient := &http.Client{Timeout: 30 * time.Second}
    client = generated.NewGreeterClientWithClient("http://localhost:8080", httpClient)
    
    // Make request
    req := &generated.HelloRequest{
        Name: "World",
    }
    
    resp, err := client.SayHello(context.Background(), req)
    if err != nil {
        log.Fatal(err)
    }
    
    fmt.Printf("Response: %s\n", resp.Message)
}
```

## HTTP Proxy Integration

The generated clients expect an HTTP proxy server that:
1. Accepts POST requests at `{baseURL}/{protoFileName}/{rpcMethodName}`
2. RPC method names in URLs are converted to kebab-case (e.g., `SayHello` → `say-hello`)
3. Request body contains JSON-serialized message (camelCase field names)
4. Response body contains JSON-serialized response message
5. Uses standard HTTP status codes (200 for success)

Example HTTP call:
```
POST http://localhost:8080/helloworld/say-hello
Content-Type: application/json

{
  "name": "World"
}
```

## Package Name Resolution

Go package names are determined as follows:
1. If `--package` is provided, use that name
2. If proto file has a `package` declaration, convert it to valid Go package name:
   - Replace dots with underscores: `foo.bar` → `foo_bar`
   - Convert to lowercase: `FOO.Bar` → `foo_bar`
3. Use the proto filename (without .proto extension) as package name

## Type Mapping

| Proto Type | Go Type | JSON Serialization |
|------------|---------|-------------------|
| `string` | `string` | `"value"` |
| `int32`, `sint32`, `sfixed32` | `int32` | `123` |
| `int64`, `sint64`, `sfixed64` | `int64` | `"123"` |
| `uint32`, `fixed32` | `uint32` | `123` |
| `uint64`, `fixed64` | `uint64` | `"123"` |
| `bool` | `bool` | `true/false` |
| `bytes` | `[]byte` | Base64 string |
| `double` | `float64` | `123.45` |
| `float` | `float32` | `123.45` |
| `repeated T` | `[]T` | `[...]` |
| Message types | Custom struct | `{...}` |
| Enum types | Custom type (int32) | `0` |

## Nested Types

The tool supports nested message and enum definitions:

```protobuf
message Outer {
  message Inner {
    string value = 1;
  }
  Inner nested = 1;
}
```

Generates:
```go
type Outer struct {
    Nested *Outer_Inner `json:"nested"`
}

type Outer_Inner struct {
    Value string `json:"value"`
}
```

## Cross-Package References

For imported types (e.g., `common.Ticker`), the generator creates qualified type names:
- `common.Ticker` → `Common_Ticker`
- Assumes all types are in the same Go package (works well when processing directories)

## Limitations

This tool implements a simplified proto parser and has some limitations:

- **Streaming RPCs**: Only unary RPCs are supported; streaming methods are ignored
- **Proto features**: No support for `map<K,V>`, `oneof`, field options, or advanced features
- **Comments**: Block comments (`/* */`) may interfere with parsing
- **Import resolution**: No sophisticated import path resolution; assumes flat namespace
- **Error handling**: Minimal error handling for malformed proto syntax

## Testing

Run the generation test:
```bash
# Test simple proto generation
go run cmd/protoc-http-go/main.go --proto proto/simple --out test_output_simple

# Test complex proto generation  
go run cmd/protoc-http-go/main.go --proto proto/complex --out test_output_complex

# Verify the generated files compile
cd test_output_simple && go mod init test && go mod tidy && go build ./...
cd test_output_complex && go mod init test && go mod tidy && go build ./...
```

## Example Proto Files

This repository includes test proto files:

### Simple Example (`proto/simple/helloworld.proto`)
```protobuf
syntax = "proto3";
package helloworld;

service Greeter {
  rpc SayHello (HelloRequest) returns (HelloReply) {}
}

message HelloRequest {
  string name = 1;
}

message HelloReply {
  string message = 1;
}
```

### Complex Example (see `proto/complex/`)
- Multiple services and messages
- Cross-file imports (`import "common/common.proto"`)
- Enums and nested types
- Realistic trading platform example

## Troubleshooting

**"No .proto files found"**: Verify the `--proto` path contains `.proto` files

**Compilation errors in generated code**: 
- Check that all referenced types are properly qualified
- Ensure proto files use supported syntax subset
- Verify import statements in proto files are correct

**HTTP client errors**:
- Verify the HTTP proxy server is running and accessible
- Check that proxy server supports the expected URL format
- Ensure JSON serialization matches expected format (camelCase fields)

## Contributing

This tool follows the same patterns as the other language implementations in this polyglot repository. When adding features:

1. Update the parser for new proto syntax support
2. Add corresponding Go code generation logic
3. Test with both simple and complex proto examples
4. Update this README with new features

## License

This repository follows the project's license terms.