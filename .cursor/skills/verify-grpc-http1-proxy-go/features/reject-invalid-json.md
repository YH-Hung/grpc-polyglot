# Reject invalid JSON

Reject invalid JSON lets a caller see a 400 when the greeting body is not JSON, without the greeter receiving a name.

## Sub-features

- `reject-not-json` returns 400 for a non-JSON body.
- `reject-no-greeter-call` does not add a greeter access line for that body.

## How to get to it (user POV)

- `POST /helloworld/SayHello` with `Content-Type: application/json` and body `not-json`.

## Driving it with control-proxy

Preconditions:

- `control-proxy doctor` prints `ok`.
- Note the current greeter log length before the rejected call. The log must not gain `Received request from:` from this body. `not-json` has no name.

- **Send a bad body.** POST `not-json`. Run `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy http POST /helloworld/SayHello 'not-json'`. `HTTP_STATUS=400` and the body contains `"error":"invalid JSON payload"`.
- **Confirm the greeter was not asked to greet that body.** Run `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy greeter-log`. The log does not contain a new line caused by `not-json`. It may already contain `verify-ready` or `Alice` from other features.
- **Proof.** Save the HTTP response. Run `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy http POST /helloworld/SayHello 'not-json' | tee .cursor/skills/verify-grpc-http1-proxy-go/artifacts/reject-invalid-json/response.txt`. The artifact shows `HTTP_STATUS=400` and `invalid JSON payload`.

## Gotchas

- An empty body is also invalid JSON. This recipe uses `not-json` so the proof is unambiguous.
- `{"name":` is invalid JSON too. Do not substitute it and then claim this entry point passed.
- A 502 `upstream error` means the proxy called the greeter and the greeter failed. That is not this feature.
