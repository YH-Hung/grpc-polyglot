# Profile-selectable network gRPC server mode

**Date:** 2026-07-11
**Status:** Approved design, pending implementation plan
**Scope:** `client-mock-server`

## Goal

The mock `GirlService` currently runs only over an **in-process** gRPC server
(`spring.grpc.server.inprocess.exclusive=true`), with no network port bound, so
only the co-located `GirlClient` can reach it. Add a second runtime mode,
selected by Spring profile, that launches the service as a **real network gRPC
server** external clients can connect to over TCP. Provide test coverage for the
new mode.

## Non-goals

- TLS / authentication (network mode is plaintext; suitable for local/dev use).
- Changing the proto contract or `GirlService` behavior.
- Removing or altering the existing in-process behavior.

## Decisions (from brainstorming)

- **Two explicit profiles:** `inprocess` and `network`.
- **Network mode dogfoods the client:** the app's own `GirlClient` connects to
  the network server over TCP (in addition to being reachable by external
  clients).
- **Port:** `9090` (Spring gRPC default).
- **Test port:** discovered dynamically (free port) rather than hard-coded.

## Design

### Configuration layout

Transport-specific config moves out of `application.properties` into two
profile files. A default active profile keeps `./mvnw spring-boot:run` working
with no flags.

**`application.properties`** (common only):

```properties
spring.application.name=client-mock-server
# Default mode when no profile is supplied; override with -Dspring-boot.run.profiles=network
spring.profiles.active=inprocess
```

**`application-inprocess.properties`** (preserves today's behavior):

```properties
# Serve GirlService over an in-process gRPC server only (no network port).
spring.grpc.server.inprocess.name=girl-server
spring.grpc.server.inprocess.exclusive=true

# Client connects to the in-process server by name.
spring.grpc.client.channels.girl.address=in-process:girl-server
```

**`application-network.properties`** (new — real network server):

```properties
# Serve GirlService over a Netty gRPC server bound to a TCP port.
spring.grpc.server.host=0.0.0.0
spring.grpc.server.port=9090

# Dogfood: the embedded client connects to the network server over TCP (plaintext).
spring.grpc.client.channels.girl.address=static://localhost:9090
spring.grpc.client.channels.girl.negotiation-type=plaintext
```

Notes:
- `grpc-netty` is already on the classpath transitively via
  `spring-grpc-spring-boot-starter`; no new dependency is required.
- Exact client channel address scheme (`static://localhost:9090` vs
  `localhost:9090`) and the plaintext property key will be confirmed against
  spring-grpc 1.0.3 during implementation; the intent is a plaintext TCP channel
  to the local network server.

### Run modes

| Command | Mode | Transport |
| --- | --- | --- |
| `./mvnw spring-boot:run` | `inprocess` (default) | in-process, no port |
| `./mvnw spring-boot:run -Dspring-boot.run.profiles=network` | `network` | Netty on `:9090` |

External clients connect to network mode at `host:9090` using plaintext gRPC and
the `GirlService` contract from `girl.proto`.

### Components touched

- `src/main/resources/application.properties` — reduced to common config +
  default profile.
- `src/main/resources/application-inprocess.properties` — new; holds the moved
  in-process config.
- `src/main/resources/application-network.properties` — new; Netty server +
  dogfood client config.

No Java source changes are required: `GirlService` (server impl) and
`GirlClient` (channel over the `girl` channel name) are transport-agnostic and
work under either profile.

## Testing

### Existing test — unchanged

`ClientMockServerApplicationTests` (`@SpringBootTest` +
`@AutoConfigureInProcessTransport`) continues to exercise the in-process path.

### New test — `NetworkGirlServiceIntegrationTests`

- `@SpringBootTest` with `@ActiveProfiles("network")`.
- A free TCP port is discovered via
  `org.springframework.test.util.TestSocketUtils.findAvailableTcpPort()` and
  injected with `@DynamicPropertySource`, overriding both:
  - `spring.grpc.server.port` (the bound port), and
  - `spring.grpc.client.channels.girl.address` (so the dogfood client targets
    the same port).
  This avoids flaky collisions with a locally running server or parallel CI jobs
  on `9090`.

Two test methods:

1. **External-client round-trip** — the true "external client connects over TCP"
   proof. Build a standalone channel independent of the app's beans:
   ```java
   ManagedChannel channel = ManagedChannelBuilder
       .forAddress("localhost", port).usePlaintext().build();
   GirlServiceGrpc.GirlServiceBlockingStub stub = GirlServiceGrpc.newBlockingStub(channel);
   Girl girl = stub.getGirlById(GirlRequest.newBuilder().setGirlId(7).build());
   // assert id/name/style/rating; assert echoed id == 7
   channel.shutdownNow();
   ```
2. **Dogfood round-trip** — autowire the app's `GirlClient` and assert it
   round-trips over the network channel (e.g. `client.getGirlById(1)` returns the
   expected `Girl`).

### Verification

- `./mvnw test` passes (both in-process and network test classes).
- Manual: `./mvnw spring-boot:run -Dspring-boot.run.profiles=network` starts and
  logs a Netty server bound on `:9090`; an external tool (e.g. `grpcurl`) or the
  external-client test reaches `GirlService/GetGirlById`.

## Risks & mitigations

- **No default server if profile config is mis-split** — mitigated by
  `spring.profiles.active=inprocess` default in `application.properties`.
- **Existing in-process test regression** — `@AutoConfigureInProcessTransport`
  redirects the client to the in-process server independent of profile config;
  confirm the existing test stays green after the split.
- **Client channel scheme/plaintext property names** may differ in spring-grpc
  1.0.3 — confirm during implementation before finalizing the network profile.
