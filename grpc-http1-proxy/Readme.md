# gRPC HTTP/1 Proxy
This project provides applications that expose an HTTP/1.1 endpoint proxying requests to a gRPC backend (HelloWorld Greeter service).

The project is structured as a multi-module Maven project grouped by framework.

## Project Structure

### Spring Modules (`grpc-http-proxy-spring/`)
1.  **`grpc-http1-proxy-vs`**: Spring MVC + Virtual Threads (Java 24).
2.  **`grpc-http1-proxy-wf-kt`**: Spring WebFlux + Kotlin Coroutines.

### Quarkus Modules (`grpc-http-proxy-quarkus/`)
1.  **`grpc-http1-proxy-vs-quarkus`**: Quarkus + Virtual Threads (Java 24).

### Comparison of Tech Stacks

| Feature | `grpc-http1-proxy-vs` | `grpc-http1-proxy-wf-kt` | `grpc-http1-proxy-vs-quarkus` |
| :--- | :--- | :--- | :--- |
| **Framework** | Spring MVC | Spring WebFlux | Quarkus |
| **Concurrency Model** | Virtual Threads | Event Loop + Coroutines | Virtual Threads |
| **Programming Style** | Imperative / Blocking | Functional / Non-blocking | Imperative (Blocking) |
| **I/O Handling** | Blocking (VT) | Non-blocking (Reactive) | Blocking (VT) |
| **Java Version** | 24 | 24 | 24 |

#### 1. Spring MVC + Virtual Threads (`grpc-http1-proxy-vs`)
This module uses traditional Spring MVC but is configured to use Java Virtual Threads to handle incoming requests.

#### 2. Spring WebFlux + Coroutines (`grpc-http1-proxy-wf-kt`)
This module uses the reactive Spring WebFlux framework combined with Kotlin Coroutines for a non-blocking asynchronous pipeline.

#### 3. Quarkus + Virtual Threads (`grpc-http1-proxy-vs-quarkus`)
This module uses Quarkus and leverages `@RunOnVirtualThread` for efficient blocking I/O on Virtual Threads.

---

## Prerequisites
- Maven and Java 24 installed
- A running gRPC Greeter server on `localhost:50051` that implements `helloworld.Greeter/SayHello` (see `src/main/proto/helloworld.proto` in any module).

The gRPC backend address is configured in `application.properties` of each module.

## Run the application

You can run any module using the following commands:

### Running `grpc-http1-proxy-vs` (Spring VT)
```bash
./mvnw spring-boot:run -pl grpc-http-proxy-spring/grpc-http1-proxy-vs
```

### Running `grpc-http1-proxy-wf-kt` (WebFlux)
```bash
./mvnw spring-boot:run -pl grpc-http-proxy-spring/grpc-http1-proxy-wf-kt
```

### Running `grpc-http1-proxy-vs-quarkus` (Quarkus VT)
```bash
./mvnw quarkus:dev -pl grpc-http-proxy-quarkus/grpc-http1-proxy-vs-quarkus
```

- Default HTTP port: `8080` (Ensure only one is running at a time or change the port in `application.properties`).

## HTTP endpoint
- Method: `POST`
- Path: `/helloworld/say-hello`
- Content-Type: `application/json`
- Request body:
  - `name` (string)
- Response body:
  - `message` (string)

### Examples
Using HTTPie:
```bash
http POST :8080/helloworld/say-hello name=Alice
```
Using curl:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice"}' \
  http://localhost:8080/helloworld/say-hello
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
