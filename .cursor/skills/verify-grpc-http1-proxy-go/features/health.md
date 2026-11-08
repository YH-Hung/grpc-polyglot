# Health

Health lets a caller check that the proxy process is answering HTTP.

## Sub-features

- `health-ok` returns the text `ok`.

## How to get to it (user POV)

- `GET /healthz`.

## Driving it with control-proxy

Preconditions:

- `control-proxy doctor` prints `ok` and `health=ok`.

- **Read health.** GET the health path. Run `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy http GET /healthz`. `HTTP_STATUS=200` and the body is `ok`.
- **Proof.** Save the response. Run `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy http GET /healthz | tee .cursor/skills/verify-grpc-http1-proxy-go/artifacts/health/response.txt`. The artifact shows `HTTP_STATUS=200` and `ok`.

## Gotchas

- `ok` does not mean the greeter accepted a call. Use the say-hello feature for that.
- The greeter's own metrics server on `:9090` also has `/health`. That is not this proxy. Drive `GET /healthz` on the proxy URL only.
