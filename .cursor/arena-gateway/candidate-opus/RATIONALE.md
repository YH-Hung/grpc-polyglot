# Rationale: gateway mode (candidate: opus)

## Problem

The four proxy modules each dial one gRPC backend at startup and expose two unary routes. The goal is
a gateway mode where `/p1/...` and `/p2/...` reach different backends that serve the same protos. The
existing unprefixed routes must keep working on today's channel. Phase A fixed these constraints.
Spring clients inject one unqualified `ManagedChannel`, and a second one breaks startup. wf-kt depends
on `@Primary` to pick among three `HelloWorldClient` beans. vs attaches a retry policy only to
`local`. vs and native attach `special_msg` per stub. Quarkus client names are fixed at build time.
Gateway config must be opt-in, and an unknown prefix is a 404. Two facts were verified in the
spring-grpc 1.0.0 source during this sketch. An unconfigured channel name silently dials
`localhost:9090` (`GrpcClientProperties.getChannel`). `DefaultGrpcChannelFactory.destroy()` already
shuts down every channel it created.

## Usage (caller's view)

See `DESIGN.md` section 1. An operator opts in with `proxy.gateway.backends=p1,p2` plus one channel
block per name. A controller reads `backends.route(prefix).helloWorld.sayHello(request)`, where
`prefix` is null on the unprefixed route. A test posts to `/p1/...` and `/p2/...` against two
in-process servers and asserts which one answered. The type sketch was derived from those call sites.
Two decisions came from the usage, not the types. `route` takes a nullable prefix so one handler
serves both path shapes. `local` is private, so callers cannot skip `route`.

## Shape

**Data first.** The shape is a prefix-major routing table: `Backends = local + Map<name, Backend>`,
where `Backend` is a fixed record of every service client bound to one channel. Per
model-the-domain, the table replaces any per-service branching on the prefix. The backend is the
outer key because it is the unit of config, retry, deadline, lifecycle, and failure. Services are the
inner record because they are fixed at compile time and identical across backends.

Access patterns traced through the structure:

- Prefixed request: one map lookup, one field read, then the call. Stubs are prebuilt, nothing per request.
- Unprefixed request: `route(null)` returns `local`, which wraps the same `local` / `hello` channel as today.
- Unknown prefix: a map miss throws `UnknownBackendException`, which is a 404.
- Startup: the raw list is parsed, each distinct channel is opened once, and one `Backend` is built per channel.
- Shutdown: the framework factory closes what it opened. `Backends` holds no lifecycle.
- Add a backend (Spring): config only. Add a service: one `Backend` field and one controller.

**Single-backend mode is the degenerate case, not a second mode.** Per
redesign-from-first-principles, the local channel is just the table's default entry. That deletes the
`ManagedChannel` bean, and with it the `@Primary` ambiguity in wf-kt. No client is a bean anymore, so
no injection can pick the wrong one. Opt-in falls out of the data. An empty list means an empty map,
and only `local` is opened.

**One opener per module.** `GrpcConfig` passes one `open(name)` lambda into `Backends.open`. In vs it
carries the retry options, so retry parity holds by construction instead of by a second call that
someone must remember. Per laziness-protocol (consolidate decisions).

**Boundaries.** Per boundary-discipline and type-system-discipline, `parseGateway` is a pure function
that runs once at startup. It turns raw strings into `BackendName`, a value class whose invariant is
"one lowercase path segment". It rejects names without a configured channel, which is required
because spring-grpc would otherwise dial the default address silently. It collects every error
before throwing. Request paths are not parsed into `BackendName`. A map miss is the whole check.

**Shared state.** Per separate-before-serializing-shared-state, the table is immutable after
construction. Request threads only read it, so concurrent requests share nothing writable. There is
no runtime reload.

**Lifecycle.** Per make-operations-idempotent, `Backends` deliberately has no `close`. The spring-grpc
factory already tracks and shuts down every channel from `createChannel`. A second closer would split
ownership of the same channels. `ManagedChannel.shutdown` is idempotent, so a double close would be
harmless, but it would leave readers asking which closer is authoritative.

**Interface depth.** The public surface is `route(prefix): Backend` plus `Backends.open(...)`, which
only `GrpcConfig` calls. Behind it are syntax validation, channel-existence validation, dedupe of
repeated channel names, channel opening with shared options, client construction, and the 404
policy. Controllers learn one method. `Backend` is a plain record of clients and adds no forwarding
methods, so there is no pass-through layer.

**What it does not do.** No gRPC-status-to-HTTP mapping, no hot reload, no per-backend proto
variation, no streaming, no `hellow-world` alias.

**Red-flag screen.** Two revisions came out of the screen.

- *Split ownership.* The first draft had `Backends : AutoCloseable` closing its channels. The
  factory already does that, so the draft was revised to give `Backends` no lifecycle.
- *Two ways to do one task.* The first draft exposed `backends.local` next to `route(null)`. `local`
  is now private.
- *Hand-synced list.* Spring keeps two lists: the opt-in list and the channel blocks. A mismatch fails
  boot. Quarkus derives its slot list from CDI (`@All List<Backend>`). Each slot repeats its name only
  through one `const NAME` in the same class.
- *Importable internals.* The `Backend` constructor is `internal`, but Kotlin `internal` covers the
  whole Maven module, which is the whole app. Client impls stay public classes, so another file could
  still construct one. This residual risk is accepted.
- *Shallow module, information leakage, temporal decomposition, pass-through.* None found. Parse and
  open live in one file and protect one invariant. `io.grpc.Channel` appears only in the `open`
  signature, which only `GrpcConfig` calls.

## Synthesis decision

Filled in by arena. This file is one candidate.

## Tradeoffs accepted

- We accept migrating the three Spring controller tests off `@MockitoBean HelloWorldClient`. In
  exchange we get a test that fails when routing is wrong. The mock seam cannot see which channel
  answered, per test-behavior-not-implementation.
- We accept that `UnknownBackendException` carries `@ResponseStatus` (Spring) or extends
  `NotFoundException` (Quarkus). The routing table knows it is HTTP-facing. In exchange, 404 has one
  owner and no exception handler class.
- We accept that wf-kt's `HelloWorldClientAsyncImpl` and `HelloWorldClientFutureImpl` stop being
  beans. They become unreferenced classes. Today they are unselected beans.
- We accept that Quarkus needs a rebuild to add a slot. In exchange, every Quarkus backend keeps
  Quarkus-managed deadline, interceptors, and shutdown.
- We accept a nullable `prefix` parameter as the encoding of "unprefixed". In exchange each RPC has
  one handler in Spring.
- We accept that listing two prefixes for distinct channel blocks with the same address opens two
  connections. Dedupe is by channel name, not by address.

## Alternatives considered

- **Service-major: each client bean holds `Map<prefix, stub>`, and `sayHello(prefix, request)`.**
  This keeps today's beans and test mocks. It lost because each service repeats the lookup and the
  404 policy, and the prefix type leaks into every client interface. Adding a backend touches no code,
  but adding a service duplicates the routing logic. The surface is wider and hides less.
- **Prefix equals channel name, with no opt-in list.** Every configured channel except `local` would
  become a route. That gives a true single list. It lost because declaring a channel for any other
  purpose would silently expose a public route. It also cannot express "configured but not routed".
- **Generated routes: functional `RouterFunction`s registered per configured prefix.** An unknown
  prefix would get the framework's natural 404, with no lookup code. It lost because JAX-RS cannot
  register routes from runtime config, so Quarkus would diverge. It also rewrites four sets of
  annotated controllers for no caller-visible gain.
- **Per-request stubs from a `Map<prefix, Channel>`.** Stubs are cheap, so this would be correct. It
  lost because vs and native would rebuild the `special_msg` interceptor on every call. It also
  splits "what a backend is" between the map and every client.
- **`Backends` owns and closes channels it opens.** It lost because the factory already does this
  (verified). See the lifecycle point under Shape.
- **Quarkus with hand-built `ManagedChannel`s from custom config.** This would make Quarkus backends
  configurable at runtime. It lost because deadline, `@GlobalInterceptor`, and shutdown would all have
  to be reimplemented next to Quarkus's copies.

## Open questions and risks

- The example uses `hellow-world`, but the live segment is `helloworld`. Should the gateway use
  `/p1/helloworld/say-hello`, as this sketch assumes, or add a `hellow-world` alias?
- Should wf-kt's unselected `HelloWorldClientAsyncImpl` and `HelloWorldClientFutureImpl` be deleted
  in the same change, since nothing will reference them?
- Does Quarkus `GrpcClient.Literal` programmatic lookup create clients for names that are known only
  from config? The class exists in quarkus-grpc-api 3.18.2. If yes, the slot classes collapse to a
  config read and Quarkus gains runtime backends. Unverified.
- Can two JAX-RS root resources both declare `@Path("/")` in RESTEasy Reactive? If not, the Quarkus
  unprefixed methods keep their class paths, and one `@Path("{backend}")` resource holds both gateway
  methods. Unverified.
- Does spring-grpc 1.0.0 accept an `in-process:<name>` channel address for the routing test? Inferred
  from `InProcessGrpcChannelFactory` in the jar, not run.
- Should a backend that is down return 404, 502, or today's implicit 500? This sketch leaves gRPC
  errors unmapped, as today.

## Next implementation step

Write `gateway/Backends.kt` and `GatewayRoutingTest` in vs, with two in-process servers. Make the test
fail on `/p1` versus `/p2` first, then fill in `parseGateway`, `Backends.open`, and `route`.
