# client-mock-server

A small Spring Boot + [Spring gRPC](https://docs.spring.io/spring-grpc/reference/) application that serves a mock `GirlService`. It can run in one of two transport modes, selected by Spring profile:

- **`inprocess`** (default) — the service runs on an in-process gRPC server with **no network port**. Only the co-located `GirlClient` (in the same JVM) can call it. Useful for wiring/contract tests and local demos with zero network footprint.
- **`network`** — the service runs on a real [Netty](https://grpc.io/) gRPC server bound to a **TCP port (`9090`)**, so **external clients** can connect over the network. The application's own `GirlClient` also dials the server over TCP (dogfooding).

The gRPC service and client code are transport-agnostic — switching modes is purely a matter of configuration.

## Requirements

- Java 21+
- Maven (use the bundled `./mvnw` wrapper)

No local `protoc` needed — the `protobuf-maven-plugin` generates the gRPC/protobuf stubs from `src/main/proto/girl.proto` at build time.

## The service contract

`src/main/proto/girl.proto`:

```proto
service GirlService {
  rpc GetGirlById(GirlRequest) returns (Girl);
}

message GirlRequest { int32 girl_id = 1; }
message Girl { int32 id = 1; string name = 2; string style = 3; int32 rating = 4; }
```

The mock implementation ([`GirlService`](src/main/java/org/hle/clientmockserver/service/GirlService.java)) echoes the requested `id` and returns fixed values: `name="Test Girl"`, `style="Classic"`, `rating=5`.

## Running

### `inprocess` mode (default)

```bash
./mvnw spring-boot:run
```

Starts the in-process gRPC server (no port is bound). This is the default because `application.properties` sets `spring.profiles.active=inprocess`.

### `network` mode

```bash
./mvnw spring-boot:run -Dspring-boot.run.profiles=network
```

Starts a Netty gRPC server listening on `0.0.0.0:9090` (plaintext). Look for a log line like:

```
gRPC Server started, listening on address: [/[0:0:0:0:0:0:0:0]:9090]
```

#### Connecting an external client

Any gRPC client that has the `girl.proto` contract can connect to `localhost:9090` over plaintext. For example, with [`grpcurl`](https://github.com/fullstorydev/grpcurl) (server reflection is enabled):

```bash
grpcurl -plaintext -d '{"girl_id": 3}' localhost:9090 GirlService/GetGirlById
```

Expected response:

```json
{
  "id": 3,
  "name": "Test Girl",
  "style": "Classic",
  "rating": 5
}
```

## Configuration

Transport config is split across profile-specific property files:

| File | Profile | Purpose |
| --- | --- | --- |
| `application.properties` | (common) | App name + `spring.profiles.active=inprocess` (default) |
| `application-inprocess.properties` | `inprocess` | In-process server (`exclusive=true`, no port) + in-process client channel |
| `application-network.properties` | `network` | Netty server on `:9090` + plaintext client channel to `localhost:9090` |

Key `network` settings:

```properties
spring.grpc.server.host=0.0.0.0
spring.grpc.server.port=9090
spring.grpc.client.channels.girl.address=static://localhost:9090
spring.grpc.client.channels.girl.negotiation-type=plaintext
```

## Testing

```bash
./mvnw test
```

Two test classes exercise the two modes:

- [`ClientMockServerApplicationTests`](src/test/java/org/hle/clientmockserver/ClientMockServerApplicationTests.java) — drives `GirlClient` against the in-process server (`@AutoConfigureInProcessTransport`).
- [`NetworkGirlServiceIntegrationTests`](src/test/java/org/hle/clientmockserver/NetworkGirlServiceIntegrationTests.java) — boots the `network` profile on a dynamically chosen free port (via `TestSocketUtils` + `@DynamicPropertySource`, so it never collides with a running `:9090`) and verifies:
  1. a **standalone external** `ManagedChannel` client connecting over TCP, and
  2. the **embedded** `GirlClient` round-tripping over the network.

## Project layout

```
src/main/proto/girl.proto                          # service + message contract
src/main/java/.../service/GirlService.java         # mock server implementation
src/main/java/.../client/GirlClient.java           # blocking-stub client over the "girl" channel
src/main/resources/application*.properties         # common + inprocess + network profiles
src/test/java/.../ClientMockServerApplicationTests.java     # inprocess test
src/test/java/.../NetworkGirlServiceIntegrationTests.java   # network test
```
