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
