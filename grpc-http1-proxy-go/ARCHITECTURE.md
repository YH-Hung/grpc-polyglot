# gRPC HTTP/1 Proxy (Go) - Architecture Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Design Principles](#design-principles)
4. [Component Breakdown](#component-breakdown)
5. [Function Orchestration](#function-orchestration)
6. [Calling Stack](#calling-stack)
7. [Data Flow](#data-flow)
8. [Error Handling](#error-handling)
9. [Configuration Management](#configuration-management)
10. [Metrics and Observability](#metrics-and-observability)
11. [Lifecycle Management](#lifecycle-management)
12. [Testing Strategy](#testing-strategy)

---

## Overview

The `grpc-http1-proxy-go` is a Go-based HTTP/1.1 proxy service that translates JSON-over-HTTP requests into gRPC calls. It serves as a bridge between HTTP clients and gRPC backends, enabling REST-like access to gRPC services without requiring gRPC clients.

Built with the [Gin Web Framework](https://github.com/gin-gonic/gin) for improved development productivity, cleaner code, and declarative routing.

### Key Capabilities

- **Protocol Translation**: Converts HTTP/1.1 JSON requests to gRPC unary calls
- **Resilience**: Built-in retry logic for transient failures
- **Observability**: Prometheus metrics for monitoring
- **Graceful Shutdown**: Clean termination with configurable timeout
- **Configuration Flexibility**: Environment variables and CLI flags
- **Modern HTTP Framework**: Built with Gin for cleaner, more maintainable code

---

## Architecture

### High-Level Architecture

```
┌─────────────────┐
│  HTTP Client    │
│  (JSON/HTTP/1.1)│
└────────┬────────┘
         │ POST /helloworld/SayHello
         │ { "name": "Alice" }
         ▼
┌─────────────────────────────────────┐
│   HTTP Server (httpserver)          │
│   - Request parsing                 │
│   - JSON ↔ Protobuf conversion      │
│   - Metrics collection              │
└────────┬────────────────────────────┘
         │
         │ Greeter.SayHello(ctx, req)
         ▼
┌─────────────────────────────────────┐
│   gRPC Client (grpcclient)          │
│   - Connection management           │
│   - Retry logic                     │
│   - Deadline/timeout handling       │
└────────┬────────────────────────────┘
         │
         │ gRPC (HTTP/2)
         ▼
┌─────────────────┐
│  gRPC Backend   │
│  (Greeter)      │
└─────────────────┘
```

### Component Layers

1. **Entry Point Layer** (`cmd/grpc-http1-proxy-go/main.go`)
   - Application initialization
   - Signal handling
   - Lifecycle orchestration

2. **Configuration Layer** (`internal/config/`)
   - Environment variable parsing
   - CLI flag binding
   - Validation

3. **HTTP Server Layer** (`internal/httpserver/`)
   - HTTP request handling with Gin framework
   - JSON/protobuf marshaling
   - Declarative route registration
   - Middleware-based metrics collection
   - Metrics exposure

4. **gRPC Client Layer** (`internal/grpcclient/`)
   - Connection management
   - Retry interceptor
   - Deadline enforcement

5. **Generated Code Layer** (`internal/pb/`)
   - Protobuf message definitions
   - gRPC service stubs

---

## Design Principles

### 1. Separation of Concerns

Each package has a single, well-defined responsibility:

- **`config`**: Configuration management only
- **`httpserver`**: HTTP handling and protocol translation
- **`grpcclient`**: gRPC connection and call management
- **`main`**: Application lifecycle and wiring

### 2. Dependency Injection

Components accept dependencies through constructors:

```go
// HTTP server accepts greeter interface, logger, and metrics registry
func New(cfg Config, greeter Greeter, logger *slog.Logger, registry *prometheus.Registry)

// gRPC client accepts config and logger
func New(ctx context.Context, cfg Config, logger *slog.Logger)
```

This enables:
- **Testability**: Easy to mock dependencies
- **Flexibility**: Swap implementations without code changes
- **Explicit dependencies**: Clear contract for what each component needs

### 3. Interface-Based Design

The HTTP server depends on a `Greeter` interface rather than the concrete `grpcclient.Client`:

```go
type Greeter interface {
    SayHello(ctx context.Context, req *pb.HelloRequest) (*pb.HelloReply, error)
}
```

Benefits:
- Decouples HTTP layer from gRPC implementation
- Enables testing with stubs
- Allows future alternative implementations

### 4. Fail-Fast Validation

Configuration is validated early in the application lifecycle:

```go
if err := cfg.Validate(); err != nil {
    slog.Error("invalid configuration", slog.String("err", err.Error()))
    os.Exit(2)
}
```

### 5. Graceful Degradation

- Metrics are optional (nil-safe)
- Loggers default to no-op if not provided
- Health checks work independently of gRPC backend

### 6. Context Propagation

Contexts are propagated through the call chain to enable:
- Request-scoped timeouts
- Cancellation propagation
- Distributed tracing (future)

---

## Component Breakdown

### 1. Main Entry Point (`cmd/grpc-http1-proxy-go/main.go`)

**Responsibilities:**
- Parse configuration from environment and flags
- Initialize logger
- Create and wire components
- Start HTTP server in goroutine
- Handle shutdown signals (SIGINT, SIGTERM)
- Perform graceful shutdown

**Key Functions:**

```go
func main()
```

**Flow:**
1. Load config from environment (`config.FromEnv()`)
2. Bind CLI flags (`cfg.BindFlags(fs)`)
3. Validate configuration (`cfg.Validate()`)
4. Create structured logger
5. Initialize gRPC client (`grpcclient.New()`)
6. Create Prometheus registry
7. Initialize HTTP server (`httpserver.New()`)
8. Start HTTP server in background goroutine
9. Wait for shutdown signal
10. Perform graceful shutdown with timeout

### 2. Configuration Module (`internal/config/config.go`)

**Responsibilities:**
- Define configuration structure
- Load from environment variables
- Bind CLI flags
- Validate configuration values

**Data Structure:**

```go
type Config struct {
    HTTPListenAddr string        // HTTP server bind address
    MetricsPath    string        // Prometheus metrics endpoint
    HealthPath     string        // Health check endpoint
    
    GRPCBackendAddr string       // gRPC backend target
    GRPCDeadline    time.Duration // Per-request timeout
    GRPCDialTimeout time.Duration // Connection timeout
    ShutdownTimeout time.Duration // Graceful shutdown timeout
    MaxGRPCRetries  uint         // Maximum retry attempts
}
```

**Key Functions:**

- `Defaults() Config`: Returns configuration with sensible defaults
- `FromEnv() Config`: Loads configuration from environment variables
- `BindFlags(fs *flag.FlagSet)`: Binds configuration to CLI flags
- `Validate() error`: Validates all configuration values

**Environment Variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `HTTP_LISTEN_ADDR` | HTTP bind address | `:8080` |
| `METRICS_PATH` | Metrics endpoint | `/metrics` |
| `GRPC_BACKEND_ADDR` | gRPC backend target | `localhost:50051` |
| `GRPC_DEADLINE_MS` | Per-request timeout (ms) | `5000` |
| `GRPC_DIAL_TIMEOUT_MS` | Dial timeout (ms) | `5000` |
| `SHUTDOWN_TIMEOUT_MS` | Shutdown timeout (ms) | `10000` |
| `GRPC_MAX_RETRIES` | Max retry attempts | `2` |

**Precedence:** CLI flags > Environment variables > Defaults

### 3. HTTP Server Module (`internal/httpserver/`)

#### 3.1 Server (`server.go`)

**Responsibilities:**
- HTTP server lifecycle management
- Route registration
- Request routing to handlers

**Data Structure:**

```go
type Server struct {
    cfg     Config
    engine  *gin.Engine    // Gin HTTP engine
    srv     *http.Server   // HTTP server for graceful shutdown
    handler *handler
}
```

**Key Functions:**

- `New(cfg, greeter, logger, registry) (*Server, error)`: Creates and configures HTTP server
- `Start() error`: Starts HTTP server (blocks until shutdown)
- `Shutdown(ctx) error`: Gracefully shuts down server

**Routes Registered:**

1. `POST /helloworld/SayHello` → `handler.hello()` (Gin handler)
2. `GET /healthz` → Health check handler (Gin inline handler)
3. `GET /metrics` → Prometheus metrics handler (wrapped with gin.WrapH)

**Middleware:**

1. `gin.Recovery()` - Panic recovery middleware
2. `metrics.middleware()` - Custom metrics collection middleware

#### 3.2 Handler (`server.go`)

**Responsibilities:**
- HTTP request processing
- JSON to Protobuf conversion
- Protobuf to JSON conversion
- Error handling and status code mapping
- Metrics collection

**Data Structure:**

```go
type handler struct {
    greeter      Greeter
    logger       *slog.Logger
    metrics      *metrics
    marshaller   protojson.MarshalOptions
    unmarshaller protojson.UnmarshalOptions
}
```

**Key Functions:**

- `hello(c *gin.Context)`: Main request handler (Gin handler)

**Handler Flow:**

1. **Request Validation**
   - HTTP method validation handled by Gin route (POST only)
   - Read request body (max 1MB)
   - Unmarshal JSON to `pb.HelloRequest`

2. **gRPC Call**
   - Call `greeter.SayHello(ctx, req)`
   - Propagate request context

3. **Response Generation**
   - Marshal `pb.HelloReply` to JSON
   - Write response with `c.Data()` (sets Content-Type automatically)

4. **Error Handling**
   - Invalid body → 400 Bad Request (via `c.JSON()`)
   - Invalid JSON → 400 Bad Request (via `c.JSON()`)
   - gRPC error → 502 Bad Gateway (via `c.JSON()`)
   - Marshal error → 500 Internal Server Error (via `c.JSON()`)

5. **Metrics**
   - Automatically recorded by middleware
   - Metrics middleware tracks duration and status for all routes

**JSON/Protobuf Conversion:**

- Uses `google.golang.org/protobuf/encoding/protojson`
- `MarshalOptions`: `UseProtoNames: false` (camelCase), `EmitUnpopulated: false`
- `UnmarshalOptions`: `DiscardUnknown: true` (ignore unknown fields)

#### 3.3 Metrics (`metrics.go`)

**Responsibilities:**
- Prometheus metrics definition
- Gin middleware for automatic metrics collection
- Request duration tracking
- Status code categorization

**Metrics Exposed:**

- `grpc_http1_proxy_http_request_duration_seconds` (Histogram)
  - Labels: `route`, `status` (2xx, 3xx, 4xx, 5xx, other)
  - Buckets: Default Prometheus buckets

**Key Functions:**

- `newMetrics(registry) *metrics`: Creates and registers metrics
- `middleware() gin.HandlerFunc`: Returns Gin middleware for metrics collection
- `observe(route, status, duration)`: Records request metrics
- `httpStatusLabel(status) string`: Categorizes HTTP status codes

**Middleware Flow:**

```go
func (m *metrics) middleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        start := time.Now()
        c.Next()  // Process request
        m.observe(c.FullPath(), c.Writer.Status(), time.Since(start))
    }
}
```

### 4. gRPC Client Module (`internal/grpcclient/client.go`)

**Responsibilities:**
- gRPC connection management
- Retry logic for transient failures
- Deadline/timeout enforcement
- Connection pooling (via gRPC)

**Data Structure:**

```go
type Client struct {
    cfg     Config
    conn    *grpc.ClientConn
    greeter pb.GreeterClient
    logger  *slog.Logger
}
```

**Key Functions:**

- `New(ctx, cfg, logger) (*Client, error)`: Creates gRPC client with connection
- `SayHello(ctx, req) (*pb.HelloReply, error)`: Makes gRPC call with deadline
- `Close() error`: Closes gRPC connection

**Connection Configuration:**

1. **Transport**: Insecure (no TLS) - suitable for local development
2. **Retry Interceptor**: 
   - Retries on: `Unavailable`, `ResourceExhausted`, `DeadlineExceeded`
   - Max retries: Configurable (default: 2)
   - Per-retry timeout: Uses configured deadline
3. **Connection Parameters**:
   - `MinConnectTimeout`: Dial timeout
   - Backoff: Base 200ms, multiplier 1.6, max 2s

**Deadline Handling:**

Each `SayHello` call creates a context with timeout:

```go
callCtx, cancel := context.WithTimeout(ctx, c.cfg.Deadline)
defer cancel()
```

This ensures:
- Per-request timeout enforcement
- Context cancellation propagation
- Resource cleanup

**Retry Strategy:**

- **Retryable Errors**: `Unavailable`, `ResourceExhausted`, `DeadlineExceeded`
- **Non-Retryable**: All other gRPC errors (e.g., `InvalidArgument`)
- **Max Retries**: Configurable, default 2
- **Backoff**: Exponential backoff with jitter (handled by gRPC middleware)

### 5. Generated Protobuf Code (`internal/pb/`)

**Source**: `proto/helloworld/helloworld.proto`

**Generated Files:**
- `helloworld.pb.go`: Message definitions (`HelloRequest`, `HelloReply`)
- `helloworld_grpc.pb.go`: Service stubs (`GreeterClient`, `GreeterServer`)

**Service Definition:**

```protobuf
service Greeter {
  rpc SayHello (HelloRequest) returns (HelloReply) {}
  rpc SayHelloStreamReply (HelloRequest) returns (stream HelloReply) {}
  rpc SayHelloBidiStream (stream HelloRequest) returns (stream HelloReply) {}
}
```

**Note**: Currently only `SayHello` (unary) is implemented in the proxy.

---

## Function Orchestration

### Application Startup Sequence

```
main()
  ├─> config.FromEnv()                    [Load defaults + env vars]
  ├─> cfg.BindFlags(fs)                   [Bind CLI flags]
  ├─> cfg.Validate()                      [Validate configuration]
  ├─> slog.New(...)                       [Create logger]
  ├─> grpcclient.New(ctx, cfg, logger)    [Create gRPC client]
  │     ├─> Validate config
  │     ├─> Setup retry interceptor
  │     ├─> grpc.DialContext(...)          [Establish connection]
  │     └─> pb.NewGreeterClient(conn)      [Create service client]
  ├─> prometheus.NewRegistry()            [Create metrics registry]
  ├─> httpserver.New(cfg, grpcClient, ...) [Create HTTP server]
  │     ├─> newMetrics(registry)          [Register metrics]
  │     ├─> Create handler
  │     ├─> http.NewServeMux()            [Create router]
  │     ├─> Register routes
  │     └─> http.Server{...}               [Create server instance]
  └─> server.Start()                      [Start in goroutine]
        └─> http.Server.ListenAndServe()  [Block until shutdown]
```

### Request Processing Sequence

```
HTTP Request: POST /helloworld/SayHello
  │
  ▼
handler.hello(w, r)
  ├─> Start timer (for metrics)
  ├─> Validate HTTP method (POST)
  ├─> io.ReadAll(r.Body)                  [Read request body]
  ├─> unmarshaller.Unmarshal(body, req)   [JSON → pb.HelloRequest]
  │     └─> protojson.Unmarshal()
  ├─> greeter.SayHello(ctx, req)          [gRPC call]
  │     └─> grpcclient.Client.SayHello()
  │           ├─> context.WithTimeout()    [Apply deadline]
  │           └─> c.greeter.SayHello()    [gRPC stub call]
  │                 └─> [gRPC middleware: retry interceptor]
  │                       └─> [Network: gRPC backend]
  ├─> marshaller.Marshal(resp)            [pb.HelloReply → JSON]
  │     └─> protojson.Marshal()
  ├─> w.Header().Set("Content-Type", ...)
  ├─> w.WriteHeader(200)
  ├─> w.Write(data)
  └─> metrics.observe(route, status, duration)
```

### Shutdown Sequence

```
Signal Received (SIGINT/SIGTERM)
  │
  ▼
main()
  ├─> context.WithTimeout(ctx, shutdownTimeout)
  ├─> server.Shutdown(ctx)
  │     └─> http.Server.Shutdown(ctx)
  │           ├─> Stop accepting new connections
  │           ├─> Wait for active requests to complete
  │           └─> Close server
  └─> grpcClient.Close()
        └─> grpc.ClientConn.Close()
```

---

## Calling Stack

### Complete Call Stack: HTTP Request to gRPC Response

```
[HTTP Client]
  │ POST /helloworld/SayHello
  │ {"name": "Alice"}
  ▼
[net/http.Server]
  │ HTTP request received
  ▼
[handler.hello()]
  │ 1. Validate method
  │ 2. Read body
  │ 3. Unmarshal JSON
  ▼
[greeter.SayHello()] (interface)
  │
  ▼
[grpcclient.Client.SayHello()]
  │ 1. Validate request
  │ 2. Create timeout context
  ▼
[pb.GreeterClient.SayHello()] (generated stub)
  │
  ▼
[grpc_retry.UnaryClientInterceptor] (middleware)
  │ Retry logic:
  │ - Attempt 1
  │ - Attempt 2 (if needed)
  │ - Attempt 3 (if needed)
  ▼
[google.golang.org/grpc] (gRPC runtime)
  │ 1. Serialize protobuf
  │ 2. HTTP/2 framing
  │ 3. Network I/O
  ▼
[gRPC Backend]
  │ Process request
  │ Generate response
  ▼
[google.golang.org/grpc] (gRPC runtime)
  │ 1. Deserialize protobuf
  │ 2. Return to interceptor
  ▼
[grpc_retry.UnaryClientInterceptor]
  │ Return response (or retry)
  ▼
[pb.GreeterClient.SayHello()]
  │ Return pb.HelloReply
  ▼
[grpcclient.Client.SayHello()]
  │ Return response
  ▼
[handler.hello()]
  │ 1. Marshal to JSON
  │ 2. Write HTTP response
  │ 3. Record metrics
  ▼
[HTTP Response]
  │ 200 OK
  │ {"message": "Hello, Alice"}
  ▼
[HTTP Client]
```

### Error Handling Call Stack

```
[handler.hello()]
  │ Error detected
  ▼
[Error Type Detection]
  │
  ├─> Invalid method → 405
  ├─> Read error → 400
  ├─> Unmarshal error → 400
  ├─> gRPC error → 502
  └─> Marshal error → 500
  ▼
[http.Error() or w.WriteHeader()]
  │ Set status code
  │ Write error message
  ▼
[metrics.observe()]
  │ Record error status
  ▼
[HTTP Response]
```

---

## Data Flow

### Request Flow

```
┌─────────────────────────────────────────────────────────────┐
│ HTTP Request                                                │
│ POST /helloworld/SayHello                                  │
│ Content-Type: application/json                             │
│ Body: {"name": "Alice"}                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ handler.hello()                                            │
│ 1. Read body: []byte(`{"name":"Alice"}`)                   │
│ 2. Unmarshal: protojson → pb.HelloRequest                  │
│    Result: &pb.HelloRequest{Name: "Alice"}                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ grpcclient.Client.SayHello()                                │
│ Input: context.Context, *pb.HelloRequest{Name: "Alice"}     │
│ 1. Create timeout context                                   │
│ 2. Call gRPC stub                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ gRPC Network Layer                                          │
│ 1. Serialize: pb.HelloRequest → protobuf wire format       │
│ 2. HTTP/2 frame: HEADERS + DATA                             │
│ 3. Network transmission                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ gRPC Backend                                                │
│ Process: SayHello(HelloRequest{name: "Alice"})             │
│ Generate: HelloReply{message: "Hello, Alice"}               │
└──────────────────────┬──────────────────────────────────────┘
```

### Response Flow

```
┌─────────────────────────────────────────────────────────────┐
│ gRPC Backend                                                │
│ Response: pb.HelloReply{Message: "Hello, Alice"}           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ gRPC Network Layer                                          │
│ 1. HTTP/2 frame: HEADERS + DATA                             │
│ 2. Deserialize: protobuf → pb.HelloReply                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ grpcclient.Client.SayHello()                                │
│ Return: *pb.HelloReply{Message: "Hello, Alice"}, nil        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ handler.hello()                                             │
│ 1. Marshal: pb.HelloReply → JSON                           │
│    Result: []byte(`{"message":"Hello, Alice"}`)             │
│ 2. Set headers: Content-Type: application/json             │
│ 3. Write response                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ HTTP Response                                               │
│ 200 OK                                                      │
│ Content-Type: application/json                              │
│ Body: {"message": "Hello, Alice"}                          │
└─────────────────────────────────────────────────────────────┘
```

### Data Transformation Details

**JSON → Protobuf (Request):**

```json
{"name": "Alice"}
```

↓ `protojson.Unmarshal()`

```go
&pb.HelloRequest{
    Name: "Alice",
}
```

↓ Serialization (gRPC)

```
Protobuf wire format (binary)
```

**Protobuf → JSON (Response):**

```
Protobuf wire format (binary)
```

↓ Deserialization (gRPC)

```go
&pb.HelloReply{
    Message: "Hello, Alice",
}
```

↓ `protojson.Marshal()`

```json
{"message": "Hello, Alice"}
```

---

## Error Handling

### Error Categories

1. **Configuration Errors**
   - Invalid listen address
   - Invalid gRPC backend address
   - Invalid timeouts
   - **Handling**: Fail-fast at startup, exit with code 2

2. **Connection Errors**
   - gRPC dial timeout
   - Network unreachable
   - **Handling**: Return error from `grpcclient.New()`, exit with code 1

3. **HTTP Request Errors**
   - Invalid HTTP method → 405 Method Not Allowed
   - Body read failure → 400 Bad Request
   - Invalid JSON → 400 Bad Request
   - **Handling**: Return appropriate HTTP status, log error

4. **gRPC Call Errors**
   - Transient errors (Unavailable, ResourceExhausted, DeadlineExceeded)
     - **Handling**: Retry with exponential backoff
   - Permanent errors (InvalidArgument, NotFound, etc.)
     - **Handling**: Return 502 Bad Gateway, log error
   - Deadline exceeded
     - **Handling**: Return 502 Bad Gateway, log error

5. **Response Serialization Errors**
   - JSON marshal failure → 500 Internal Server Error
   - **Handling**: Log error, return generic error message

### Error Propagation

```
[gRPC Backend Error]
  │
  ▼
[gRPC Runtime]
  │ Returns gRPC status code
  ▼
[grpc_retry.Interceptor]
  │ Check if retryable
  │ ├─> Retryable → Retry
  │ └─> Not retryable → Return error
  ▼
[grpcclient.Client.SayHello()]
  │ Return error
  ▼
[handler.hello()]
  │ Detect gRPC error
  │ Set status: 502 Bad Gateway
  │ Log error
  │ Write error response
  ▼
[HTTP Client]
  │ Receives 502 with error message
```

### Retry Logic

**Retryable Status Codes:**
- `codes.Unavailable`: Service temporarily unavailable
- `codes.ResourceExhausted`: Rate limiting or resource constraints
- `codes.DeadlineExceeded`: Request timeout (may retry if transient)

**Retry Configuration:**
- Max retries: Configurable (default: 2)
- Per-retry timeout: Uses configured deadline
- Backoff: Exponential with jitter (handled by gRPC middleware)

**Retry Flow:**

```
Attempt 1
  │
  ├─> Success → Return response
  └─> Error
        │
        ├─> Retryable? → Attempt 2
        └─> Not retryable → Return error
              │
              ▼
Attempt 2
  │
  ├─> Success → Return response
  └─> Error
        │
        ├─> Retryable? → Attempt 3 (if max retries > 2)
        └─> Not retryable → Return error
              │
              ▼
Attempt 3 (if applicable)
  │
  ├─> Success → Return response
  └─> Error → Return error (max retries exceeded)
```

---

## Configuration Management

### Configuration Sources (Priority Order)

1. **CLI Flags** (Highest priority)
2. **Environment Variables**
3. **Defaults** (Lowest priority)

### Configuration Flow

```
Application Start
  │
  ├─> config.Defaults()              [Set default values]
  │
  ├─> config.FromEnv()               [Override with env vars]
  │     ├─> os.Getenv(HTTP_LISTEN_ADDR)
  │     ├─> os.Getenv(GRPC_BACKEND_ADDR)
  │     ├─> parseDurationFromMillis(GRPC_DEADLINE_MS)
  │     └─> ...
  │
  ├─> cfg.BindFlags(fs)              [Bind to flag set]
  │     ├─> fs.StringVar(&cfg.HTTPListenAddr, ...)
  │     ├─> fs.DurationVar(&cfg.GRPCDeadline, ...)
  │     └─> ...
  │
  ├─> fs.Parse(os.Args[1:])          [Parse CLI flags]
  │
  └─> cfg.Validate()                 [Validate all values]
        ├─> Check non-empty strings
        ├─> Check positive durations
        └─> Return error if invalid
```

### Configuration Validation

**Validation Rules:**

- `HTTPListenAddr`: Must not be empty
- `GRPCBackendAddr`: Must not be empty
- `GRPCDeadline`: Must be > 0
- `GRPCDialTimeout`: Must be > 0
- `ShutdownTimeout`: Must be > 0

**Validation Failure:**
- Log error with details
- Exit with code 2

---

## Metrics and Observability

### Prometheus Metrics

**Metric: `grpc_http1_proxy_http_request_duration_seconds`**

- **Type**: Histogram
- **Labels**:
  - `route`: HTTP route (e.g., `/helloworld/SayHello`)
  - `status`: HTTP status category (`2xx`, `3xx`, `4xx`, `5xx`, `other`)
- **Buckets**: Default Prometheus buckets (exponential)
- **Help**: Time spent serving HTTP requests

### Metrics Collection Flow

```
Request Start
  │
  ├─> handler.hello()
  │     ├─> start := time.Now()
  │     │
  │     ├─> [Process request]
  │     │
  │     └─> defer metrics.observe(route, status, duration)
  │           │
  │           └─> time.Since(start)
  │
  └─> metrics.observe()
        ├─> httpStatusLabel(status) → "2xx", "4xx", etc.
        └─> histogram.WithLabelValues(route, status).Observe(seconds)
```

### Endpoints

1. **`/metrics`** (GET)
   - Prometheus metrics in text format
   - Exposed via `promhttp.HandlerFor()`

2. **`/healthz`** (GET)
   - Health check endpoint
   - Returns `200 OK` with body `"ok"`
   - Does not check gRPC backend (liveness only)

### Logging

**Structured Logging with `slog`:**

- **Format**: Text handler (human-readable)
- **Level**: Info (default)
- **Fields**: Structured key-value pairs

**Log Events:**

1. **Startup**: HTTP proxy listening address
2. **Shutdown**: Received signal, shutdown completion
3. **Errors**: gRPC call failures, configuration errors
4. **Server Errors**: HTTP server stopped with error

---

## Lifecycle Management

### Startup Sequence

```
1. Load Configuration
   ├─> Defaults
   ├─> Environment variables
   └─> CLI flags

2. Validate Configuration
   └─> Exit if invalid

3. Initialize Components
   ├─> Logger
   ├─> gRPC Client (with connection)
   ├─> Prometheus Registry
   └─> HTTP Server

4. Start HTTP Server
   └─> Goroutine: server.Start()

5. Wait for Shutdown Signal
   └─> Block on signal channel
```

### Shutdown Sequence

```
1. Signal Received (SIGINT/SIGTERM)
   │
   ├─> Log: "received shutdown signal"
   │
   ├─> Create shutdown context with timeout
   │     └─> context.WithTimeout(..., shutdownTimeout)
   │
   ├─> server.Shutdown(ctx)
   │     ├─> Stop accepting new connections
   │     ├─> Wait for active requests (up to timeout)
   │     └─> Close server
   │
   ├─> grpcClient.Close()
   │     └─> Close gRPC connection
   │
   └─> Exit
```

### Graceful Shutdown Details

**HTTP Server Shutdown:**

- `http.Server.Shutdown()`:
  1. Stops accepting new connections
  2. Waits for active requests to complete
  3. Closes server after timeout or completion

**Timeout Handling:**

- If shutdown completes before timeout: Clean exit
- If timeout exceeded: Server forced to close, log error

**gRPC Connection Cleanup:**

- `grpc.ClientConn.Close()`:
  - Closes underlying connections
  - Cancels pending RPCs
  - Releases resources

---

## Testing Strategy

### Unit Testing

**Test Files:**
- `internal/httpserver/server_test.go`

**Test Cases:**

1. **`TestHandlerHello`**
   - Valid POST request with JSON body
   - Verifies: 200 status, correct response JSON

2. **`TestHandlerHelloError`**
   - gRPC error simulation
   - Verifies: 502 status, error message

**Testing Approach:**

- **Stub Implementation**: `stubGreeter` implements `Greeter` interface
- **HTTP Testing**: Uses `httptest` package for in-memory requests
- **Isolation**: Tests handler logic without real gRPC backend

### Test Structure

```go
type stubGreeter struct {
    resp *pb.HelloReply
    err  error
}

func (s *stubGreeter) SayHello(ctx context.Context, req *pb.HelloRequest) (*pb.HelloReply, error) {
    if s.err != nil {
        return nil, s.err
    }
    return s.resp, nil
}
```

**Benefits:**
- Fast execution (no network I/O)
- Deterministic behavior
- Easy error simulation
- No external dependencies

### Integration Testing

**Potential Areas:**
- End-to-end request flow
- gRPC connection handling
- Retry logic verification
- Metrics collection

**Note**: Currently, integration tests are not included in the codebase.

---

## Code Organization

### Package Structure

```
grpc-http1-proxy-go/
├── cmd/
│   └── grpc-http1-proxy-go/
│       └── main.go                    [Application entry point]
├── internal/
│   ├── config/
│   │   └── config.go                   [Configuration management]
│   ├── grpcclient/
│   │   └── client.go                   [gRPC client wrapper]
│   ├── httpserver/
│   │   ├── server.go                   [HTTP server and handler]
│   │   ├── metrics.go                  [Prometheus metrics]
│   │   └── server_test.go              [HTTP handler tests]
│   └── pb/
│       ├── helloworld.pb.go            [Generated protobuf messages]
│       └── helloworld_grpc.pb.go       [Generated gRPC stubs]
├── proto/
│   └── helloworld/
│       └── helloworld.proto            [Service definition]
├── go.mod                              [Go module definition]
├── Makefile                            [Build automation]
└── README.md                           [User documentation]
```

### Visibility Rules

- **`internal/`**: Package-private, not importable outside module
- **Public APIs**: Only exported functions/types needed by other packages
- **Interfaces**: Used for dependency injection and testing

---

## Dependencies

### Core Dependencies

1. **`github.com/gin-gonic/gin`**: HTTP web framework
2. **`google.golang.org/grpc`**: gRPC client library
3. **`google.golang.org/protobuf`**: Protobuf runtime and JSON support
4. **`github.com/prometheus/client_golang`**: Prometheus metrics
5. **`github.com/grpc-ecosystem/go-grpc-middleware/v2`**: Retry interceptor

### Dependency Roles

- **Gin**: HTTP server framework, routing, middleware
- **gRPC**: Protocol implementation, connection management
- **Protobuf**: Message serialization, JSON conversion
- **Prometheus**: Metrics collection and exposition
- **gRPC Middleware**: Retry logic, resilience patterns

---

## Future Enhancements

### Potential Improvements

1. **TLS Support**: Add TLS configuration for secure gRPC connections
2. **Streaming Support**: Implement streaming RPC endpoints
3. **OpenTelemetry**: Add distributed tracing
4. **Rate Limiting**: Add request rate limiting
5. **Circuit Breaker**: Add circuit breaker pattern for resilience
6. **Multiple Services**: Support multiple gRPC services/routes
7. **Request Validation**: Add request validation middleware
8. **Response Caching**: Add caching for idempotent requests
9. **Load Balancing**: Add gRPC load balancing
10. **Health Checks**: Add gRPC backend health checking

---

## Conclusion

The `grpc-http1-proxy-go` is a well-architected Go service that provides a clean HTTP/1.1 interface to gRPC backends. Its design emphasizes:

- **Separation of concerns** through modular packages
- **Testability** through interfaces and dependency injection
- **Resilience** through retry logic and graceful shutdown
- **Observability** through metrics and structured logging
- **Configuration flexibility** through multiple configuration sources

The codebase follows Go best practices and provides a solid foundation for production use and future enhancements.

