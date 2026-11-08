---
name: verify-grpc-http1-proxy-go
description: "Drive the Go HTTP/1.1 greeter proxy (grpc-http1-proxy-go) and the routing Go greeter the way a caller does: POST /helloworld/SayHello, GET /healthz, and GET /metrics. Use when proving a change to that proxy, its greeter contract, or their local startup."
---

# Verify the Go HTTP greeter proxy

The primary surface in this repo that a caller touches is HTTP against `grpc-http1-proxy-go`. This skill starts that proxy and the routing Go greeter, drives them with `control-proxy`, and writes proof under `.cursor/skills/verify-grpc-http1-proxy-go/artifacts/`.

Other surfaces this skill does not drive: the Spring and Quarkus proxies under `grpc-http1-proxy/`, the `protoc-http-go`, `protoc-http-py`, and `protoc-http-rs` generator CLIs, and the APISIX demo in `routing/`. Those generators emit `/{file}/{kebab-method}/{version}`. This proxy serves `POST /helloworld/SayHello` only.

Run every command from the repository root. The harness is `.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy`.

## Launch

One greeter can run at a time. `routing/servers/go-server` always listens on `:50051` (gRPC) and `:9090` (its own metrics). The script refuses to start when either port is taken, and it never kills a process it did not start. The proxy port defaults to `127.0.0.1:18080` so a caller using `:8080` is left alone. Override it with `VERIFY_HTTP_PORT`. State (pids, logs, binaries) lives in `VERIFY_STATE_DIR`, default `/tmp/verify-grpc-http1-proxy-go`. Two verification runs cannot share the greeter ports. If the state directory already exists, launch refuses; run cleanup first.

From an empty state directory:

```bash
.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy launch
```

Launch builds `routing/servers/go-server` and `grpc-http1-proxy-go/cmd/grpc-http1-proxy-go` into the state directory, starts the greeter, then starts the proxy with `-http-listen 127.0.0.1:$VERIFY_HTTP_PORT -grpc-backend 127.0.0.1:50051`.

Ready means a caller can be greeted, not only that a process is bound:

- greeter log contains `gRPC server listening on :50051`
- proxy log contains `HTTP proxy listening`
- `GET /healthz` returns body `ok`
- `POST /helloworld/SayHello` with `{"name":"verify-ready"}` returns HTTP 200 and a JSON body containing `Hello verify-ready!`

`/healthz` stays `ok` even when the greeter is down. The greeting probe is what makes the instance usable. That probe is launch-only. It is not a feature proof.

Teardown is `control-proxy cleanup`. It sends TERM, then KILL, only to the pids stored in the state directory, then deletes that directory.

## Doctor

Run this first whenever a drive looks wrong. It is read-only: it does not greet and it does not restart anything.

```bash
.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy doctor
```

Exit 0 prints:

```text
ok
http=http://127.0.0.1:18080
greeter_pid=<pid>
proxy_pid=<pid>
revision=<git SHA recorded at launch>
dirty=true|false
health=ok
greeter_port=50051
greeter_metrics_port=9090
```

Doctor fails unless all of these hold:

- both pids are alive
- `:50051` and `:9090` are listened on by the greeter pid, and the HTTP port by the proxy pid
- workspace `HEAD` equals the revision recorded at launch
- `GET /healthz` returns exactly `ok`

A failed doctor means this instance is not worth driving. Relaunch after cleanup, or stop if the greeter ports belong to something else.

## Drive

`control-proxy http` prints the status, response headers, and body. It exits non-zero only when curl cannot complete. The feature file decides what the status and body must be.

```bash
.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy http METHOD PATH [JSON_BODY]
.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy greeter-log
```

Read `.cursor/skills/verify-grpc-http1-proxy-go/features/README.md` and drive the feature file that matches the change. A proof that uses one entry point does not cover entry points the map lists and the run did not exercise.

Stable handles are the paths `POST /helloworld/SayHello`, `GET /healthz`, and `GET /metrics`. There is no browser UI.

## Evidence

Write proof under `.cursor/skills/verify-grpc-http1-proxy-go/artifacts/<feature-id>/`. Cleanup must not delete that tree.

For every proof, record the feature id, the command, the stdout (status, headers, body), and a second view of the side effect:

- A greeting is proved only when the HTTP body contains the greeter message and `greeter-log` contains `Received request from: <name>`.
- Health is proved by the `ok` body. It has no greeter side effect. Do not treat it as proof the greeting path works.
- Metrics are proved by the Prometheus text after a greeting, including `grpc_http1_proxy_http_request_duration_seconds` and the labels `route="/helloworld/SayHello"` and `status="2xx"`.
- A rejected body is proved by HTTP 400 and `invalid JSON payload`, and by the greeter log not gaining a `Received request from:` line for that call.

Exercise the real proxy and the real greeter. Do not call `httpserver` handlers in-process, and do not point the proxy at a stub. There is no dry-run mode. The launch probe name `verify-ready` is not a substitute for the feature's own name.

## Cleanup

```bash
.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy cleanup
```

This stops the recorded greeter and proxy pids and deletes `/tmp/verify-grpc-http1-proxy-go` (or `VERIFY_STATE_DIR`). It does not delete `.cursor/skills/verify-grpc-http1-proxy-go/artifacts/`. After cleanup, the artifact files from the drive must still be readable. Run cleanup after a failed launch too; launch itself cleans up the processes it started if readiness fails.

## Helpers

`.cursor/skills/verify-grpc-http1-proxy-go/scripts/control-proxy` is the harness. Invoke it as shown above. Commands: `launch`, `doctor`, `http`, `greeter-log`, `cleanup`.

`launch` detaches both servers through:

```bash
python3 .cursor/skills/verify-grpc-http1-proxy-go/scripts/daemonize.py LOGFILE PIDFILE COMMAND [ARGS...]
```

That helper double-forks, starts a new session, and writes the daemon pid. Do not start the binaries in the shell's process group. A process group kill at the end of `launch` would take the proxy down before `doctor` can run.
