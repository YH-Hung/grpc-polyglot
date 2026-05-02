# AGENTS.md

Guidance for coding agents working in this repository.

## Project Overview

This repository is a polyglot gRPC-to-HTTP proxy ecosystem. It contains code generators, proxy services, and examples that let HTTP/1.1 clients call gRPC services through generated client code and proxy adapters.

Core flow:

```text
HTTP client -> HTTP/1.1 proxy -> gRPC server
     ^              ^              ^
Generated code   proxy service   gRPC service
```

## Repository Layout

- `protoc-http-go/`: Go implementation of the protoc-to-HTTP client generator.
- `protoc-http-py/`: Python implementation of the generator.
- `protoc-http-rs/`: Rust implementation of the generator.
- `protoc-adapter-py/`: Python protoc adapter utilities.
- `grpc-http1-proxy/`: Spring Boot/Kotlin HTTP-to-gRPC proxy.
- `grpc-http1-proxy-go/`: Go HTTP-to-gRPC proxy implementation.
- `client-mock-server/`: Java gRPC mock server used for testing.
- `grpc-trading-platform/`: Multi-service Java/Kotlin example platform.
- `GrpcHttpProxyClient/`: C#/.NET client demonstration.
- `routing/`: Routing examples with Go/Rust servers and clients.
- `protoc-http-requirements.md`: Project requirements and constraints.
- `WARP.md`: Existing human/tooling guidance; keep it consistent with this file when changing project-wide workflows.

## Architecture And Conventions

- Generators read `.proto` files and emit VB.NET/.NET Framework HTTP client code.
- The standard generator CLI shape is `--proto <path> --out <dir> [--namespace/--package <name>]`.
- Inputs may be a single `.proto` file or a directory processed recursively, depending on implementation.
- Generated HTTP routes follow `{base_url}/{proto_file_name}/{rpc_method_name}`.
- RPC method names should be kebab-case in URLs, for example `SayHello` -> `say-hello`.
- JSON field names should be camelCase, for example `user_name` -> `userName`.
- HTTP calls use `POST` with `Content-Type: application/json`.
- Only unary gRPC calls are in scope. Streaming RPCs are unsupported or ignored.
- Advanced proto features such as `map<K,V>` and `oneof` are generally out of scope unless a component explicitly supports them.

## Development Commands

Run commands from the component directory unless noted otherwise.

### Go Generator

```bash
cd protoc-http-go
make build
make test
go run cmd/protoc-http-go/main.go --proto proto/simple/helloworld.proto --out generated
```

### Python Generator

```bash
cd protoc-http-py
python -m protoc_http_py.main --proto proto/simple/helloworld.proto --out out
python -m pytest
```

### Rust Generator

```bash
cd protoc-http-rs
cargo build --release
cargo test
cargo run -- --proto proto/simple --out test_output
```

### Spring HTTP Proxy

```bash
cd grpc-http1-proxy
./mvnw spring-boot:run
./mvnw test
./mvnw clean package
```

### Mock gRPC Server

```bash
cd client-mock-server
./mvnw spring-boot:run
./mvnw test
```

### Go HTTP Proxy

```bash
cd grpc-http1-proxy-go
make build
make test
```

## Testing Strategy

- Prefer the smallest component-level test that validates the change.
- For generator changes, run that generator's unit tests and, when practical, generate code from both simple and complex proto fixtures.
- For proxy changes, run the relevant Maven/Go tests and consider an integration path through the mock gRPC server.
- Integration flow: start `client-mock-server` on port `50051`, start the HTTP proxy on port `8080`, then call an HTTP endpoint and verify the gRPC round trip.
- Generated output directories such as `generated/`, `out/`, and `test_output*` are usually disposable; avoid committing generated artifacts unless the component already tracks them as fixtures.

Example proxy request:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice"}' \
  http://localhost:8080/helloworld/say-hello
```

## Coding Guidance

- Preserve each component's language idioms and existing project structure.
- Keep cross-language behavior consistent across `protoc-http-go`, `protoc-http-py`, and `protoc-http-rs` when changing generator semantics.
- Update tests or fixtures in every affected language implementation when behavior changes are intended to be shared.
- Avoid broad rewrites across all implementations unless the requested change requires parity.
- Do not assume generated files are source of truth; inspect generator code and tests first.
- Use `rg` for searches and read large files in chunks.
- Do not remove user changes or generated examples unless explicitly asked.

## Proto Fixture Conventions

- Simple fixtures usually live under `proto/simple/`.
- Complex fixtures usually live under `proto/complex/` and may include imports, nested types, and enums.
- Imports generally use relative paths such as `import "common/common.proto"`.
- Target generated VB.NET code should include DTO classes, JSON serialization attributes, and HTTP client implementations for supported unary RPCs.

## When Modifying This File

- Keep this file concise and operational.
- Mirror durable workflow changes from `WARP.md` here when they affect coding agents.
- Prefer concrete commands over prose when documenting verification steps.
