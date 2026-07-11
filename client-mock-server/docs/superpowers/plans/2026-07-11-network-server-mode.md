# Network gRPC Server Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Spring-profile-selectable `network` mode that runs the mock `GirlService` as a real Netty gRPC server on a TCP port for external clients, alongside the existing in-process mode, with test coverage.

**Architecture:** Split the transport config out of `application.properties` into two profile files — `inprocess` (today's behavior, kept as the default) and `network` (Netty server on a port + a dogfooded client channel over TCP). No Java production code changes: `GirlService` and `GirlClient` are transport-agnostic and driven entirely by the `girl` channel/server config. A new `@SpringBootTest` integration test boots the `network` profile on a free port and verifies both a standalone external client and the embedded `GirlClient` reach the service over TCP.

**Tech Stack:** Java 21, Spring Boot 4.0.2, Spring gRPC 1.0.3 (`spring-grpc-spring-boot-starter`), grpc-java 1.77.1 (`grpc-netty` already on the classpath transitively), JUnit 5, AssertJ.

## Global Constraints

- **No new dependencies.** `grpc-netty` 1.77.1 is already resolved transitively; network mode is config-only.
- **Preserve in-process behavior.** The existing `ClientMockServerApplicationTests` must stay green unchanged.
- **Default mode is `inprocess`.** `./mvnw spring-boot:run` with no flags must behave exactly as today (in-process only, no port bound).
- **Network mode is plaintext.** No TLS/auth. Port `9090` (Spring gRPC default).
- **Confirmed property names (spring-grpc 1.0.3):**
  - Server: `spring.grpc.server.host`, `spring.grpc.server.port`, `spring.grpc.server.inprocess.name`, `spring.grpc.server.inprocess.exclusive`
  - Client: `spring.grpc.client.channels.<name>.address` (accepts `in-process:<name>` and `static://host:port`), `spring.grpc.client.channels.<name>.negotiation-type` (enum; default `PLAINTEXT`)
- Run commands from the module root: `/Users/yinghanhung/Projects/grpc-polyglot/client-mock-server`.

---

## File Structure

- `src/main/resources/application.properties` — **Modify.** Reduce to common config + default active profile.
- `src/main/resources/application-inprocess.properties` — **Create.** In-process server + in-process client channel (moved from `application.properties`).
- `src/main/resources/application-network.properties` — **Create.** Netty server on `:9090` + dogfooded TCP client channel.
- `src/test/java/org/hle/clientmockserver/ClientMockServerApplicationTests.java` — **Unchanged.** Existing in-process test (regression guard).
- `src/test/java/org/hle/clientmockserver/NetworkGirlServiceIntegrationTests.java` — **Create.** Network-mode integration test (external + embedded client over TCP).

---

### Task 1: Split transport config into `inprocess` profile with `inprocess` as default

**Files:**
- Modify: `src/main/resources/application.properties`
- Create: `src/main/resources/application-inprocess.properties`
- Test (regression): `src/test/java/org/hle/clientmockserver/ClientMockServerApplicationTests.java`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: an `inprocess` Spring profile that reproduces today's in-process wiring (server `girl-server`, `exclusive=true`, client channel `girl` → `in-process:girl-server`), active by default via `spring.profiles.active=inprocess`.

This task is configuration-only. There is no new production code to drive with a
failing unit test, so the "test" here is a **regression check**: the existing
in-process test must stay green after the config is moved into a profile.

- [ ] **Step 1: Confirm the existing test passes BEFORE any change (baseline)**

Run: `./mvnw -q -Dtest=ClientMockServerApplicationTests test`
Expected: BUILD SUCCESS, both `getGirlById_*` tests pass. (Baseline — proves the starting point is green.)

- [ ] **Step 2: Create the `inprocess` profile file with the moved config**

Create `src/main/resources/application-inprocess.properties`:

```properties
# Profile: inprocess (default) — serve GirlService over an in-process gRPC
# server only. 'exclusive=true' suppresses the Netty server factory, so nothing
# binds a network port.
spring.grpc.server.inprocess.name=girl-server
spring.grpc.server.inprocess.exclusive=true

# Client connects to the in-process server by name.
spring.grpc.client.channels.girl.address=in-process:girl-server
```

- [ ] **Step 3: Reduce `application.properties` to common config + default profile**

Replace the entire contents of `src/main/resources/application.properties` with:

```properties
spring.application.name=client-mock-server

# Default runtime mode. Override with: -Dspring-boot.run.profiles=network
spring.profiles.active=inprocess
```

- [ ] **Step 4: Run the existing test to confirm the split kept in-process green**

Run: `./mvnw -q -Dtest=ClientMockServerApplicationTests test`
Expected: BUILD SUCCESS, both tests pass. (If it fails to find the `girl`
channel, the `inprocess` profile file was not placed under
`src/main/resources/` — fix the path.)

- [ ] **Step 5: Commit**

```bash
git add src/main/resources/application.properties src/main/resources/application-inprocess.properties
git commit -m "refactor: move in-process gRPC config into inprocess profile (default)"
```

---

### Task 2: Add `network` profile and integration test (external + embedded client over TCP)

**Files:**
- Create: `src/main/resources/application-network.properties`
- Create: `src/test/java/org/hle/clientmockserver/NetworkGirlServiceIntegrationTests.java`

**Interfaces:**
- Consumes: the `network` Spring profile (created in this task); the existing
  `GirlService` bean (server impl) and `GirlClient` bean (`getGirlById(int)` →
  `org.hle.clientmockserver.model.Girl`); generated
  `org.hle.clientmockserver.model.GirlServiceGrpc` /
  `GirlRequest` / `Girl`.
- Produces: `application-network.properties` enabling
  `./mvnw spring-boot:run -Dspring-boot.run.profiles=network` to expose
  `GirlService` on a TCP port for external clients.

**Note on port choice:** The integration test picks a free TCP port at runtime
(via `TestSocketUtils`) and injects it with `@DynamicPropertySource`, so tests
never collide with a locally running server or parallel CI jobs on `9090`. The
`application-network.properties` file hard-codes `9090` for the production run
mode; that literal is verified by the manual step at the end, while the test
verifies the transport end-to-end on the free port.

- [ ] **Step 1: Create the `network` profile file**

Create `src/main/resources/application-network.properties`:

```properties
# Profile: network — serve GirlService over a real Netty gRPC server bound to a
# TCP port, so external clients can connect.
spring.grpc.server.host=0.0.0.0
spring.grpc.server.port=9090

# Dogfood: the embedded client dials the network server over TCP (plaintext).
spring.grpc.client.channels.girl.address=static://localhost:9090
spring.grpc.client.channels.girl.negotiation-type=plaintext
```

- [ ] **Step 2: Write the network integration test**

Create `src/test/java/org/hle/clientmockserver/NetworkGirlServiceIntegrationTests.java`:

```java
package org.hle.clientmockserver;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import org.hle.clientmockserver.client.GirlClient;
import org.hle.clientmockserver.model.Girl;
import org.hle.clientmockserver.model.GirlRequest;
import org.hle.clientmockserver.model.GirlServiceGrpc;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.util.TestSocketUtils;

import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Boots the application under the {@code network} profile, which runs
 * {@code GirlService} on a real Netty gRPC server bound to a TCP port. Verifies
 * that both a standalone external client and the embedded {@link GirlClient}
 * reach the service over the network.
 */
@SpringBootTest
@ActiveProfiles("network")
class NetworkGirlServiceIntegrationTests {

    // One free port, shared by the server bind and both clients.
    static final int PORT = TestSocketUtils.findAvailableTcpPort();

    @DynamicPropertySource
    static void grpcProperties(DynamicPropertyRegistry registry) {
        // Bind the network server to the free port...
        registry.add("spring.grpc.server.port", () -> PORT);
        // ...and point the dogfooded client channel at the same port.
        registry.add("spring.grpc.client.channels.girl.address", () -> "static://localhost:" + PORT);
    }

    @Autowired
    GirlClient client;

    @Test
    void externalClient_connectsOverTcp() throws InterruptedException {
        // A standalone channel, independent of any Spring bean — a real external client.
        ManagedChannel channel = ManagedChannelBuilder
                .forAddress("localhost", PORT)
                .usePlaintext()
                .build();
        try {
            GirlServiceGrpc.GirlServiceBlockingStub stub = GirlServiceGrpc.newBlockingStub(channel);

            Girl girl = stub.getGirlById(GirlRequest.newBuilder().setGirlId(7).build());

            assertThat(girl.getId()).isEqualTo(7);
            assertThat(girl.getName()).isEqualTo("Test Girl");
            assertThat(girl.getStyle()).isEqualTo("Classic");
            assertThat(girl.getRating()).isEqualTo(5);
        } finally {
            channel.shutdownNow().awaitTermination(5, TimeUnit.SECONDS);
        }
    }

    @Test
    void embeddedClient_roundTripsOverNetwork() {
        Girl girl = client.getGirlById(1);

        assertThat(girl.getId()).isEqualTo(1);
        assertThat(girl.getName()).isEqualTo("Test Girl");
        assertThat(girl.getStyle()).isEqualTo("Classic");
        assertThat(girl.getRating()).isEqualTo(5);
    }
}
```

- [ ] **Step 3: Run the network integration test**

Run: `./mvnw -q -Dtest=NetworkGirlServiceIntegrationTests test`
Expected: BUILD SUCCESS, both `externalClient_connectsOverTcp` and
`embeddedClient_roundTripsOverNetwork` pass. (If the context fails to start with
a Netty bind error, another process holds the chosen port — re-run; the port is
re-selected each run.)

- [ ] **Step 4: Run the full test suite (both profiles' tests together)**

Run: `./mvnw -q test`
Expected: BUILD SUCCESS — `ClientMockServerApplicationTests` (in-process) and
`NetworkGirlServiceIntegrationTests` (network) all pass.

- [ ] **Step 5: Manually verify the production run mode binds :9090**

In one terminal:

```bash
./mvnw spring-boot:run -Dspring-boot.run.profiles=network
```

Expected log: a Netty gRPC server starts and binds port `9090` (e.g. a
"gRPC Server started, listening on ... 9090" line). Confirm no in-process
`exclusive` message. Stop with Ctrl-C.

(Optional, if `grpcurl` is installed — proves an out-of-process external client
connects:)

```bash
grpcurl -plaintext -d '{"girl_id": 3}' localhost:9090 GirlService/GetGirlById
```

Expected: JSON `{"id": 3, "name": "Test Girl", "style": "Classic", "rating": 5}`.

- [ ] **Step 6: Commit**

```bash
git add src/main/resources/application-network.properties \
        src/test/java/org/hle/clientmockserver/NetworkGirlServiceIntegrationTests.java
git commit -m "feat: add network profile running GirlService as a real gRPC server"
```

---

## Self-Review

**Spec coverage:**
- Second mode selectable by profile → Task 1 (`inprocess` default) + Task 2 (`network`). ✓
- Real network gRPC server for external clients → `application-network.properties` (Netty `:9090`) + `externalClient_connectsOverTcp` standalone-channel test + manual `grpcurl` step. ✓
- Dogfooded embedded client over TCP → `application-network.properties` client channel + `embeddedClient_roundTripsOverNetwork`. ✓
- Two explicit profiles → `application-inprocess.properties` + `application-network.properties`, default `inprocess`. ✓
- Preserve in-process behavior → existing test kept unchanged and re-run in Task 1 Steps 1 & 4. ✓
- Dynamic free test port → `TestSocketUtils.findAvailableTcpPort()` + `@DynamicPropertySource`. ✓
- No new dependency → confirmed `grpc-netty` already resolved. ✓

**Placeholder scan:** No TBD/TODO; all config and test code is complete and literal.

**Type consistency:** `GirlClient.getGirlById(int)` returns `org.hle.clientmockserver.model.Girl`; `GirlServiceGrpc.newBlockingStub(...).getGirlById(GirlRequest)` returns `Girl` — both match the existing generated API and the existing in-process test's usage. Property keys match the verified spring-grpc 1.0.3 names in Global Constraints.

**Known deviation from strict TDD:** The feature is configuration-only (no new
production Java), so Task 1 uses a regression check rather than a new failing
unit test, and Task 2 creates the profile file before its integration test
(the test cannot meaningfully fail-first on a missing properties file because
`@DynamicPropertySource` supplies the port/address directly). This is called out
rather than faked with an artificial red step.
