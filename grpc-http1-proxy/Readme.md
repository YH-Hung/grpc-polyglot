# gRPC HTTP/1 Proxy
This project provides a Spring Boot application that exposes an HTTP/1.1 endpoint proxying requests to a gRPC backend (HelloWorld Greeter service).

The project is structured as a multi-module Maven project to demonstrate and compare two different architectural approaches for handling high-concurrency proxying in the JVM.

## Project Structure

The project consists of two main modules:

1.  **`grpc-http1-proxy-vs`**: Spring MVC + Virtual Threads (Java 24).
2.  **`grpc-http1-proxy-wf-kt`**: Spring WebFlux + Kotlin Coroutines.

### Comparison of Tech Stacks

| Feature | `grpc-http1-proxy-vs` | `grpc-http1-proxy-wf-kt` |
| :--- | :--- | :--- |
| **Framework** | Spring MVC | Spring WebFlux |
| **Concurrency Model** | Virtual Threads (Project Loom) | Event Loop + Kotlin Coroutines |
| **Programming Style** | Imperative / Blocking | Functional / Non-blocking |
| **I/O Handling** | Blocking (efficiently handled by VT) | Non-blocking (Reactive) |
| **Java Version** | 24 | 24 |

#### 1. Spring MVC + Virtual Threads (`grpc-http1-proxy-vs`)
This module uses traditional Spring MVC but is configured to use Java Virtual Threads to handle incoming requests.

**Pros:**
- **Simplicity**: Follows the standard imperative programming model which is easy to write, read, and maintain.
- **Debuggability**: Provides meaningful stack traces and works well with standard debuggers and profilers.
- **Compatibility**: Works seamlessly with existing blocking libraries without needing reactive wrappers.
- **Low Overhead**: Virtual threads are extremely lightweight, allowing for massive concurrency without the memory overhead of platform threads.

**Cons:**
- **JVM Dependency**: Requires a recent JDK (21+) that supports stable Virtual Threads.
- **Pinning Risks**: Certain legacy synchronized blocks or native calls can "pin" virtual threads to platform threads, potentially limiting scalability if not managed.

#### 2. Spring WebFlux + Coroutines (`grpc-http1-proxy-wf-kt`)
This module uses the reactive Spring WebFlux framework combined with Kotlin Coroutines for a non-blocking asynchronous pipeline.

**Pros:**
- **Efficiency**: Highly efficient resource utilization, especially for I/O bound tasks, by never blocking the execution threads.
- **Resilience**: Naturally supports backpressure and is well-suited for streaming data.
- **Modern Syntax**: Kotlin Coroutines make reactive code look and feel more like imperative code while maintaining non-blocking benefits.

**Cons:**
- **Complexity**: Steeper learning curve compared to MVC; requires understanding of reactive streams and coroutine scopes.
- **Debugging**: Stack traces can be fragmented and harder to follow across asynchronous boundaries.
- **Library Ecosystem**: Requires using non-blocking drivers and libraries throughout the entire stack to avoid blocking the event loop.

---

## Prerequisites
- Maven and Java 24 installed
- A running gRPC Greeter server on `localhost:50051` that implements `helloworld.Greeter/SayHello` (see `src/main/proto/helloworld.proto` in either module).

The gRPC backend address is configured in `application.properties` of each module:
```properties
spring.grpc.client.channels.local.address=localhost:50051
```

## Run the application

You can run either module using the following commands:

### Running `grpc-http1-proxy-vs` (Virtual Threads)
```bash
./mvnw spring-boot:run -pl grpc-http1-proxy-vs
```

### Running `grpc-http1-proxy-wf-kt` (WebFlux)
```bash
./mvnw spring-boot:run -pl grpc-http1-proxy-wf-kt
```

- Default HTTP port: `8080` (Ensure only one is running at a time or change the port in `application.properties`).

## HTTP endpoint
- Method: `POST`
- Path: `/helloworld/SayHello`
- Content-Type: `application/json`
- Request body (`HelloRequest`):
  - `name` (string)
- Response body (`HelloReply`):
  - `message` (string)

### Examples
Using HTTPie:
```bash
http POST :8080/helloworld/SayHello name=Alice
```
Using curl:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice"}' \
  http://localhost:8080/helloworld/SayHello
```

## Run tests
To run tests for all modules:
```bash
./mvnw test
```
To run tests for a specific module:
```bash
./mvnw test -pl <module-name>
```

## OpenTelemetry Java agent
1. Start the bundled Grafana LGTM stack so the OTLP ports are available:
   ```bash
   docker run -p 3000:3000 -p 4317:4317 -p 4318:4318 --rm -ti grafana/otel-lgtm
   ```
2. The repo includes `otel-config.yaml`, which configures traces, metrics, and logs to export over OTLP/gRPC to `http://localhost:4317`.
3. Launch the app with the OpenTelemetry Java agent:
   ```bash
   JAVA_TOOL_OPTIONS="-javaagent:$HOME/Services/opentelemetry-javaagent.jar -Dotel.javaagent.configuration-file=$(pwd)/otel-config.yaml" \
   ./mvnw spring-boot:run -pl <module-name>
   ```
4. Open Grafana at `http://localhost:3000` (default `admin/admin`) to inspect the incoming telemetry.
