# gRPC HTTP/1 Proxy (Go)

This project re-implements the `grpc-http1-proxy` Spring Boot service using Go. It accepts JSON over HTTP/1.1 and proxies requests to the `helloworld.Greeter/SayHello` gRPC backend.

Built with the [Gin Web Framework](https://github.com/gin-gonic/gin) for improved development productivity and declarative routing.

## Features

- `POST /helloworld/SayHello` that accepts `{ "name": "Alice" }` and returns `{ "message": "Hello, Alice" }`
- Configurable via environment variables or flags (listen address, gRPC backend, deadlines, retries)
- Prometheus metrics and health endpoint
- Graceful shutdown on SIGINT/SIGTERM
- Built with Gin framework for cleaner, more maintainable code

## Prerequisites

- Go 1.22+
- `protoc` with `protoc-gen-go` and `protoc-gen-go-grpc` on your `PATH`
- Running gRPC Greeter backend (default `localhost:50051` – see `proto/helloworld/helloworld.proto`)

## Setup

```bash
cd grpc-http1-proxy-go
make proto   # regenerate protobuf stubs if you change the proto
```

## Run

```bash
go run ./cmd/grpc-http1-proxy-go \
  -http-listen :8080 \
  -grpc-backend localhost:50051
```

Override via env vars:

| Environment variable | Description | Default |
| --- | --- | --- |
| `HTTP_LISTEN_ADDR` | HTTP bind address | `:8080` |
| `GRPC_BACKEND_ADDR` | gRPC backend target | `localhost:50051` |
| `GRPC_DEADLINE_MS` | Per-request timeout | `5000` |
| `GRPC_DIAL_TIMEOUT_MS` | Dial timeout | `5000` |
| `GRPC_MAX_RETRIES` | Max retry attempts | `2` |
| `METRICS_PATH` | Metrics path | `/metrics` |
| `SHUTDOWN_TIMEOUT_MS` | Shutdown grace period | `10000` |

## Example

```bash
curl -X POST http://localhost:8080/helloworld/SayHello \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice"}'
```

Expected response:

```json
{ "message": "Hello, Alice" }
```

## Tests

```bash
go test ./...
```

## Telemetry

Prometheus metrics are exposed at `/metrics`. Integrate with OpenTelemetry collectors via the Prom exporter or add OTEL interceptors where needed.
