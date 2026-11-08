# Gateway board rationale

## Problem

The four grpc-http1-proxy apps are copies. Each process dials one gRPC backend at startup and exposes `POST /helloworld/say-hello` and `POST /hello-girl/say-hello`. The new mode must switch channel by path prefix, so `/p1/helloworld/say-hello` and `/p2/helloworld/say-hello` reach different channels that share those protos. The live segment is `helloworld`. The brief's `hellow-world` is not a route.

Unprefixed routes stay on the current channel (`local` on Spring, `hello` on Quarkus). No gateway keys means today's behavior, including context load. An unknown prefix is a 404 and must not fall through to that channel. Spring cannot gain a second unqualified `ManagedChannel` bean. wf-kt cannot gain another `HelloWorldClient` bean. vs owned channels need the same UNAVAILABLE retry policy as `local`, because a later `createChannel` does not inherit the options passed only for `local`. Quarkus `@GrpcClient` names are fixed at build time, so a missing extra name fails startup. Channels this mode dials are closed on shutdown. The framework channel is not. No application code closes it today.

## Usage (caller's view)

Operators add backends as path prefixes. The prefix is the property key. It is not a Spring client name and not a Quarkus client name.

```properties
grpc.gateway.backends.p1.address=localhost:50061
grpc.gateway.backends.p2.address=localhost:50062
```

`POST /helloworld/say-hello` and `POST /hello-girl/say-hello` still hit the existing channel. `POST /p1/helloworld/say-hello` hits p1. `POST /p2/hello-girl/say-hello` hits p2. `POST /nope/helloworld/say-hello` returns an empty 404 and does not call gRPC. With no `grpc.gateway.backends` keys, the prefixed URL is that same 404 and the unprefixed URLs are unchanged.

The HTTP class calls one function. It does not pass a channel or a prefix.

```kotlin
when (val result = gateway.handle(applicationPath(request), body)) {
    is HandleResult.Ok -> ResponseEntity.ok().contentType(MediaType.APPLICATION_JSON).body(result.json)
    HandleResult.UnknownPrefix, HandleResult.NotARoute -> ResponseEntity.notFound().build()
    is HandleResult.BadJson -> ResponseEntity.badRequest().build()
}
```

WebFlux wraps that call in `withContext(Dispatchers.IO)`. Quarkus runs it on `@RunOnVirtualThread`. Both branches use the same `when`.

Wiring opens the board around the channel the app already has.

```kotlin
Gateway.open(
    entries = selectBackendProperties(environmentToMap()),
    borrowed = channel,
    deadline = localDeadline(),
    dialer = VsOwnedDialer,
    codec = codec,
    rpc = rpc,
)
```

`localDeadline()` reads `spring.grpc.client.channels.local.default-deadline`. Quarkus passes `@GrpcClient("hello") Channel` and reads `quarkus.grpc.clients.hello.deadline`. Shutdown calls `gateway.close()`.

## Shape

The data shape is a board. One `io.grpc.Channel` field holds the borrowed framework channel. One immutable `Map<Prefix, OwnedChannel>` holds the channels this mode dialed. Per foundational-thinking and model-the-domain, those are the two access paths. An unprefixed request reads the field and does not touch the map. A prefixed request is one `get`. Shutdown iterates the map only. The borrowed value is stored as `Channel`, which has no `shutdown`, so `close` cannot name it. Per type-system-discipline, that is the ownership invariant.

`Prefix` and `SocketAddress` have private constructors. Config parse is the only builder. A reserved prefix (`helloworld`, `hello-girl`, derived from the private `ServicePath` enum), a bad segment, or a bad `host:port` throws before any dial. Per boundary-discipline, `handle` trusts the board after that. Request parsing of an unknown or illegal prefix returns `UnknownPrefix` and returns before `Codec` or `Rpc`.

`Gateway.handle` is the request API. It hides matching, the map, the `special_msg` header, the owned-channel deadline interceptor, and the choice of stub. Callers see four results. `Ok`, `UnknownPrefix`, `NotARoute`, `BadJson`. The composition API is `open` plus `Codec`, `Rpc`, and `OwnedDialer`. Those exist because the four apps do not share a JSON printer or a generated stub class. vs rejects unknown JSON fields and pretty-prints. The other three ignore unknown fields and emit compact JSON. Quarkus has a Mutiny stub and no `GreeterGrpc`. Putting one stub implementation in the shared file would force a second code generator into Quarkus. The HTTP class still cannot see a `ManagedChannel`.

Per separate-before-serializing-shared-state, request threads only read the map. `close` does not remove entries. Each owned channel has its own `AtomicBoolean`. Two shutdown signals can both call `close`. The second returns. Per make-operations-idempotent, a failed `open` closes the channels it already dialed and does not return the board. A `close` that stops halfway leaves the remaining channels in the map, so the next `close` finishes them. There is no on-disk registry. A crashed process is replaced by a new process that dials from config again.

Per redesign-from-first-principles, the prefixed and unprefixed routes share `handle`. Per migrate-callers-then-delete-legacy-apis and subtract-before-you-add, the client interfaces, the unused async and future clients, the unregistered `HelloWorldHandler`, and the global `special_msg` interceptors are deleted in that same wave. The header is attached inside `handle` on a fresh interceptor view, so a second call does not stack it. vs stops rebuilding `HelloRequest` from `name` alone and passes the parsed message through, which is what the other modules already do.

Per minimize-reader-load, a request crosses two files. `GatewayHttp` and `Gateway.handle`. The dialer runs at startup. Per laziness-protocol, `gateway-core` is an extra source root compiled into each app, not a new Maven module and not four copied files.

`GET /grpc/channels` continues to list Spring client names. Gateway prefixes are a different map. Adding them to `spring.grpc.client.channels` would create a second registry and a second channel bean.

## Synthesis decision

This file is one candidate. Arena writes this section when it picks the base.

## Tradeoffs accepted

- We accept blocking `GreeterGrpc` stubs on wf-kt-native, with the HTTP method still hopping to `Dispatchers.IO`, in exchange for one `Rpc` shape on every Spring module. The coroutine stub leaves with the old client.
- We accept a Quarkus `Rpc` that still uses the Mutiny stub and `await().indefinitely()`, in exchange for leaving Quarkus codegen alone.
- We accept plaintext `ManagedChannelBuilder` dials for owned channels, in exchange for keeping gateway backends out of the framework client registry.
- We accept one shared RPC deadline for every owned channel, read from the borrowed channel's existing property, in exchange for a config file whose only per-backend field is `address`.
- We accept two owned channels when two prefixes share an address, in exchange for a `close` that never has to decide which prefix still needs the socket.
- We accept an empty 404 for both `UnknownPrefix` and `NotARoute`, in exchange for one HTTP mapping. Tests tell the results apart by calling `handle` directly.
- We accept a 5 second `shutdown` wait that is not the RPC deadline, in exchange for keeping the call budget and the process-exit budget separate.
- We accept that `Codec` and `Rpc` are a wider composition API than `handle`, in exchange for four different JSON and stub stacks behind one request function.

## Alternatives considered

A servlet or WebFlux filter that strips the prefix and stores the channel on the request. The public filter looks small, and it hides almost nothing. The controller, the client, and a shutdown hook still coordinate a mutable attribute. Two layers can write it. Per separate-before-serializing-shared-state, that lost.

One framework client name per prefix. Spring then has a second unqualified `ManagedChannel` bean and fails startup. A later `GrpcChannelFactory.createChannel` also drops the vs retry options. Quarkus `@GrpcClient` names are fixed at build time, so an unconfigured name fails context load and the mode is no longer opt-in. The public API becomes a bean per prefix per service. That lost.

Keeping `HelloWorldClient.sayHello(request)` for the unprefixed route and adding a channel argument, or a second client, for prefixes. Tests would stay green while prefix selection could be wrong, which is the failure the current client mocks already hide. Two call paths would remain for one RPC. That lost.

## Open questions and risks

Does this Quarkus version inject `@GrpcClient("hello") Channel`? The borrowed channel on that module depends on it.

Do the Graal images for quarkus-blocking-kt and wf-kt-native already keep `ManagedChannelBuilder.forAddress` reachable when the owned dialer calls it directly? The borrowed channel is built by the framework today, so a direct builder may need extra native-image registration.

Is plaintext the right dial for every owned address until a backend needs TLS?

## Next implementation step

Add `Gateway.kt` under `gateway-core` and a vs unit test that opens an empty property map, checks `/helloworld/say-hello` uses the borrowed channel, and checks `/p1/helloworld/say-hello` returns `UnknownPrefix` without calling `Rpc`.
