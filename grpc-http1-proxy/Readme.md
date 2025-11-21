# gRPC HTTP/1 Proxy

This Spring Boot application exposes an HTTP/1.1 endpoint that proxies requests to a gRPC backend (HelloWorld Greeter service).

Last updated: 2025-09-06

## Prerequisites
- Maven and Java installed
- A running gRPC Greeter server on `localhost:50051` that implements `helloworld.Greeter/SayHello` (see `src/main/proto/helloworld.proto`).

The gRPC backend address is configured in `src/main/resources/application.properties`:
```
spring.grpc.client.channels.local.address=localhost:50051
```

## Run the application
```
./mvnw spring-boot:run
```
- Default HTTP port: `8080`

## HTTP endpoint
- Method: `POST`
- Path: `/helloworld/SayHello`
- Content-Type: `application/json`
- Request body (HelloRequest):
  - `name` (string)
- Response body (HelloReply):
  - `message` (string)

### Examples
Using HTTPie:
```
http POST :8080/helloworld/SayHello name=Alice
```

Using curl:
```
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice"}' \
  http://localhost:8080/helloworld/SayHello
```

Expected response:
```
{
  "message": "Hello, Alice"
}
```

## Run tests
```
./mvnw test
```

## OpenTelemetry Java agent
1. Start the bundled Grafana LGTM stack so the OTLP ports are available:
   ```
   docker run -p 3000:3000 -p 4317:4317 -p 4318:4318 --rm -ti grafana/otel-lgtm
   ```
2. The repo includes `otel-config.yaml`, which configures traces, metrics, and logs to export over OTLP/gRPC to `http://localhost:4317`. Override the endpoint or headers via `OTEL_EXPORTER_OTLP_ENDPOINT` / `OTEL_EXPORTER_OTLP_HEADERS` environment variables if needed.
3. Launch the app with the OpenTelemetry Java agent (update the absolute paths for your environment):
   ```
   JAVA_TOOL_OPTIONS="-javaagent:$HOME/Services/opentelemetry-javaagent.jar -Dotel.javaagent.configuration-file=$(pwd)/otel-config.yaml" \
   ./mvnw spring-boot:run
   ```
4. Open Grafana at `http://localhost:3000` (default `admin/admin`) to inspect the incoming telemetry.
