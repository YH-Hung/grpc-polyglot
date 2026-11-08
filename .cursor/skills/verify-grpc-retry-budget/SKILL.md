---
name: verify-grpc-retry-budget
description: "Check that grpc-http1-proxy-go's unary SayHello retries only Unavailable, ResourceExhausted, and DeadlineExceeded, and never makes more backend attempts than MaxRetries. Use when a change touches grpcclient.New, grpcclient.SayHello, or GRPC_MAX_RETRIES."
---

# Verify the Go proxy retry budget

`grpcclient.New` and `grpcclient.SayHello` promise that a unary greeting retries only `Unavailable`, `ResourceExhausted`, and `DeadlineExceeded`, and that the greeter is contacted at most `MaxRetries` times (`MaxRetries` of 0 still makes the one original attempt). A break repeats a call the backend already canceled, or drops a retry the caller asked for.

This check runs that client. It is not a TLA+ model, so do not read it with `/statechart`. A model would restate the interceptor and can miss the branch that actually retries `Canceled`. No Go proof tool is required. `go test` drives `New` and `SayHello` against a local greeter.

## Coverage

Confirmed against commit `1fa44281b4563cd32248b75fc7b94dfe587c448b`.

- `grpc-http1-proxy-go/internal/grpcclient/client.go` — `New` builds the interceptor (`WithCodes`, `WithPerRetryTimeout`, and `WithMax` only when `MaxRetries > 0`). `SayHello` wraps the caller context with `cfg.Deadline` and invokes `Greeter.SayHello`.
- `github.com/grpc-ecosystem/go-grpc-middleware/v2` `v2.0.0` — `UnaryClientInterceptor`. `WithMax(n)` runs `attempt < n`, so `n` is the total number of attempts. The default max is 0. A `DeadlineExceeded` or `Canceled` status continues to the next attempt when the parent context is still active and a per-call timeout is set.

Move the commit above forward only after you confirm this description still matches `New` and `SayHello` at the new commit. If either function changes and you have not re-read it, the check needs another look before you trust a pass or a failure.

## Run

From `grpc-http1-proxy-go`:

```bash
go test -tags formalverify ./internal/grpcclient/ -run 'TestRetryBudget' -count=1 -timeout 120s
```

The `formalverify` tag keeps this check out of an ordinary `go test ./...`. The tag does not skip the `Canceled` rows. Those rows fail on the current client. That failure is the finding below. Any other failing row is a new break.

## What a failure means

Each row is one `SayHello` against a greeter that counts attempts. The greeter returns a scripted status for the first `failBefore` attempts, then succeeds. `fail=9` means every attempt inside this budget fails. `fail=0` means the first attempt succeeds.

- `backend attempts = N, want M` means the greeter's `SayHello` ran N times. That count is the product behavior.
- A row whose error text is `desc = scripted` came from the greeter.
- An error whose status is `DeadlineExceeded` and whose text is not `desc = scripted` means the client gave up before the greeter answered. That is a harness problem (dial or the 3s deadline). Do not change the expected attempt count to absorb it.

## Known finding

`Canceled` is retried when `MaxRetries` is 2.

1. `New` is called with `MaxRetries` 2, so the interceptor gets `WithMax(2)` and `WithPerRetryTimeout` of the same deadline, and `WithCodes(Unavailable, ResourceExhausted, DeadlineExceeded)`.
2. `SayHello` calls the greeter.
3. The greeter returns `Canceled` (`desc = scripted`) while the parent context is still active.
4. The per-call timeout is set, so the interceptor continues instead of stopping.
5. The greeter is called a second time. On `Canceled/max=2/fail=1` the second attempt succeeds and `SayHello` returns success (`err=<nil>`, attempts 2, want 1). On `Canceled/max=2/fail=9` the second attempt is also `Canceled` (attempts 2, want 1).

Do not delete or retarget those two rows to make the command pass. The current code breaks the promise. Leave the product code alone unless the user asks to change it.

Removing `codes.Unavailable` from `WithCodes` in `New` makes `Unavailable/max=2/fail=1` and `Unavailable/max=2/fail=9` fail as well (1 attempt, want 2). That scratch was restored. `client.go` is back to the finding-only result: those two `Canceled` rows, and no `Unavailable` rows.

## Scope

Checked: statuses `InvalidArgument`, `Internal`, `Canceled`, `Unavailable`, `ResourceExhausted`, and `DeadlineExceeded`; `MaxRetries` 0, 1, and 2; schedules success, one leading failure, and failure past the budget. The greeter answers immediately. The parent deadline is 3s, which is longer than the interceptor's default ~50ms backoff, so a second attempt still fits. A cancelled parent context makes at most one attempt (`TestRetryBudgetCancelledParent`).

Not checked: streaming RPCs, transport errors, a greeter that stalls until the deadline, backoff longer than the parent deadline, and the HTTP layer. `httpserver` turns every `SayHello` error into HTTP 502 `upstream error`, so this extra `Canceled` attempt is invisible on the HTTP status. That mapping is a separate check.
