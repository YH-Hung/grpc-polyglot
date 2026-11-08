# Metrics

Metrics lets a caller read Prometheus text for proxy HTTP requests.

## Sub-features

- `metrics-after-greet` exposes the greeting route and a 2xx status after a successful say-hello.

## How to get to it (user POV)

- `GET /metrics` after at least one `POST /helloworld/SayHello`.

## Driving it with control-proxy

Preconditions:

- `control-proxy doctor` prints `ok`.

- **Produce a 2xx.** Greet Alice. Run `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy http POST /helloworld/SayHello '{"name":"Alice"}'`. `HTTP_STATUS=200`.
- **Read metrics.** GET the metrics path. Run `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy http GET /metrics`. `HTTP_STATUS=200` and the body contains `grpc_http1_proxy_http_request_duration_seconds`, `route="/helloworld/SayHello"`, and `status="2xx"`.
- **Proof.** Save the metrics body. Run `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy http GET /metrics | tee .cursor/skills/verify-grpc-http1-proxy-go/artifacts/metrics/response.txt`. The artifact contains those three strings.

## Gotchas

- Launch's `verify-ready` probe already records a 2xx on `/helloworld/SayHello`. The series can exist before this recipe's own POST. Still perform this recipe's POST, then read metrics, so the proof is tied to a greeting you issued.
- A 404 on `/metrics` means this launch did not pass a Prometheus registry. The stock `cmd/grpc-http1-proxy-go` binary does. Do not point the recipe at a unit-test server.
- Greeter metrics on `:9090/metrics` are a different process. Read `/metrics` on the proxy URL.
