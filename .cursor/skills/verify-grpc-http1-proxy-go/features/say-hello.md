# Say hello

Say hello lets a caller POST a name and receive the Go greeter's message as JSON.

## Sub-features

- `say-hello-greet` returns HTTP 200 and the greeter message for `Alice`.
- `say-hello-extra-field` still greets when the JSON has an unknown field.

## How to get to it (user POV)

- `POST /helloworld/SayHello` with `Content-Type: application/json` and body `{"name":"Alice"}`.
- `POST /helloworld/SayHello` with body `{"name":"Alice","extra":"ignored"}`.

## Driving it with control-proxy

Preconditions:

- `control-proxy doctor` prints `ok` and `http=http://127.0.0.1:18080` (or the `VERIFY_HTTP_PORT` you launched with).
- The greeter log does not yet contain `Received request from: Alice`. The launch probe uses `verify-ready`, which does not satisfy this feature.

- **Greet Alice.** POST the name. Run `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy http POST /helloworld/SayHello '{"name":"Alice"}'`. `HTTP_STATUS=200` and the body contains `"message":"Hello Alice! Greetings from Go Server v1"`.
- **Confirm the greeter saw Alice.** Run `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy greeter-log`. The log contains `Received request from: Alice`.
- **Ignore an extra field.** POST a body with `extra`. Run `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy http POST /helloworld/SayHello '{"name":"Alice","extra":"ignored"}'`. `HTTP_STATUS=200` and the body again contains `"message":"Hello Alice! Greetings from Go Server v1"`.
- **Proof.** Save the first response and the greeter line. Run `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy http POST /helloworld/SayHello '{"name":"Alice"}' | tee .cursor/skills/verify-grpc-http1-proxy-go/artifacts/say-hello/response.txt` and `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy greeter-log | tee .cursor/skills/verify-grpc-http1-proxy-go/artifacts/say-hello/greeter.log`. Both artifacts show `Alice`, and the response artifact shows HTTP 200.

## Gotchas

- The path is `/helloworld/SayHello`. `POST /helloworld/say-hello` and `POST /helloworld/say-hello/v1` are not this proxy. A 404 there is the wrong entry point.
- The README example body `{"message":"Hello, Alice"}` is not what this greeter returns. Assert `Hello Alice! Greetings from Go Server v1`.
- `/healthz` returning `ok` does not prove this feature.
- Unknown JSON fields are discarded. Assert the greeting, not that `extra` echoes back.
- The launch probe writes `Received request from: verify-ready`. Only an `Alice` line proves this feature.
