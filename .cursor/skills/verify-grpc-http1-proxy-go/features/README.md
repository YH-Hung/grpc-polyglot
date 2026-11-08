# Go HTTP greeter proxy verification map

This directory is the maintained source for verifying the caller-facing behavior of `grpc-http1-proxy-go` in front of `routing/servers/go-server`. Read the index before driving, then use the matching feature file as the recipe.

## Baseline preconditions

- Launch with `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy launch` from the repository root.
- The proxy base URL is `http://127.0.0.1:18080` unless `VERIFY_HTTP_PORT` was set.
- The greeter owns `:50051` and `:9090`. Do not start another greeter or another verification run.
- `control-proxy doctor` prints `ok`, the expected URL, and the revision recorded at launch.
- Never drive an instance that was not started by this verification run.

## Driving conventions

- Start every recipe from the baseline state unless its preconditions say otherwise.
- Treat every command as literal. Keep quoted JSON and paths unchanged.
- Run HTTP through `control-proxy http`.
- Run greeter-log reads through `control-proxy greeter-log`.
- Leave proof artifacts in place during cleanup.

## Proof and skip reporting

- Capture the caller action and the resulting state, not only the final body.
- HTTP proof includes the command, `HTTP_STATUS`, headers, and body.
- A greeting proof also includes the matching greeter log line.
- Record the feature ID and entry point used with every artifact.
- Report an unreachable path with the attempted command and the unmet precondition.
- Do not report a skipped entry point as verified through a different path.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the caller-visible behavior. It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every caller entry point.
3. `Driving it with control-proxy` starts with `Preconditions:` and uses labeled bullets that pair each caller action with an exact command and observable result.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

## Features

- [Say hello](./say-hello.md) covers the JSON greeting round trip and ignored extra fields.
- [Health](./health.md) covers `GET /healthz`.
- [Metrics](./metrics.md) covers Prometheus text after a greeting.
- [Reject invalid JSON](./reject-invalid-json.md) covers a body the proxy refuses before calling the greeter.
