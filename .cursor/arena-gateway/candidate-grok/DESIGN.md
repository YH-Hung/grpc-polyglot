# Gateway board

Sketch only. No product code changes in this pass.

The live service segment is `helloworld`. The brief's `hellow-world` is not a route. Both services stay on the protobuf they use today. `helloworld.Greeter/SayHello` and `hellogirl.GirlGreeter/SayHello`.

## Usage

Omit every `grpc.gateway.backends` key and the process is the current single-backend proxy. `POST /helloworld/say-hello` and `POST /hello-girl/say-hello` use the channel the module already dials (`local` on Spring, `hello` on Quarkus).

```properties
grpc.gateway.backends.p1.address=localhost:50061
grpc.gateway.backends.p2.address=localhost:50062
```

`p1` and `p2` are path prefixes. They are not Spring client names and not Quarkus `@GrpcClient` names. Both prefixes serve both protos.

```bash
curl -s -X POST -H 'Content-Type: application/json' -d '{"name":"Ada"}' \
  http://localhost:8080/helloworld/say-hello

curl -s -X POST -H 'Content-Type: application/json' -d '{"name":"Ada"}' \
  http://localhost:8080/p1/helloworld/say-hello

curl -s -X POST -H 'Content-Type: application/json' -d '{"name":"Ada"}' \
  http://localhost:8080/p2/hello-girl/say-hello

curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  -H 'Content-Type: application/json' -d '{"name":"Ada"}' \
  http://localhost:8080/nope/helloworld/say-hello
```

The last command prints `404`. The body is empty. No gRPC call runs.

HTTP shells call `handle` with the application path and the raw JSON bytes. They do not pass a channel, a prefix, or a protobuf message.

```kotlin
@RestController
class GatewayHttp(private val gateway: Gateway) {

    @PostMapping(
        path = ["/{first}/{second}", "/{first}/{second}/{third}"],
        consumes = [MediaType.APPLICATION_JSON_VALUE],
        produces = [MediaType.APPLICATION_JSON_VALUE],
    )
    fun post(request: HttpServletRequest, @RequestBody body: ByteArray): ResponseEntity<ByteArray> {
        val path = applicationPath(request)
        return when (val result = gateway.handle(path, body)) {
            is HandleResult.Ok ->
                ResponseEntity.ok().contentType(MediaType.APPLICATION_JSON).body(result.json)
            HandleResult.UnknownPrefix, HandleResult.NotARoute ->
                ResponseEntity.notFound().build()
            is HandleResult.BadJson ->
                ResponseEntity.badRequest().build()
        }
    }
}
```

WebFlux (wf-kt and wf-kt-native) uses the same `when`. The method is `suspend` and calls `handle` inside `withContext(Dispatchers.IO)`. Quarkus uses the same `when` on a JAX-RS resource with `@RunOnVirtualThread`. The resource methods take `byte[]`, not `HelloRequest`.

Wiring opens the board once. The borrowed channel is the existing bean. Owned channels come back from the dialer and are not beans. `localDeadline()` reads `spring.grpc.client.channels.local.default-deadline` and returns that `Duration`, or null when the property is absent.

```kotlin
@Bean
fun gateway(
    channel: ManagedChannel,
    codec: Codec,
    rpc: Rpc,
): Gateway {
    return Gateway.open(
        entries = selectBackendProperties(environmentToMap()),
        borrowed = channel,
        deadline = localDeadline(),
        dialer = VsOwnedDialer,
        codec = codec,
        rpc = rpc,
    )
}

@Bean
fun gatewayShutdown(gateway: Gateway): DisposableBean = DisposableBean { gateway.close() }
```

Quarkus passes `@GrpcClient("hello") Channel` as `borrowed` and reads `quarkus.grpc.clients.hello.deadline` for `deadline`. It observes `ShutdownEvent` and calls `gateway.close()`.

`GET /grpc/channels` stays as it is. It lists Spring client names. It does not list gateway prefixes.

## Data shape

The board is the whole gateway. It is built once inside `Gateway.open` and never mutated.

```text
Board
  borrowed: Channel                  field read for a path with no prefix
  owned: Map<Prefix, OwnedChannel>   get by prefix, also the only close set
```

`Channel` is the borrowed gRPC channel. The board stores it as `io.grpc.Channel`. That type has no `shutdown`. `close` cannot target it without a cast, and the code does not cast.

`OwnedChannel` holds an `io.grpc.ManagedChannel` plus an `AtomicBoolean`. One prefix has one owned channel. Both protos share that channel. The map is the index. There is no second index by service, and no later cache.

Unprefixed lookup reads `borrowed`. It does not call `Map.get`. Prefixed lookup parses the first segment to a `Prefix` and calls `owned[prefix]`. A miss is `UnknownPrefix`. Shutdown iterates `owned.values` only.

The map is a Kotlin immutable map published when `open` returns. Request threads only read it. `close` does not remove entries. Two request threads never write the board. The only write of the closed flag is `OwnedChannel.close`, and that flag is per channel.

An empty `owned` map is the current single-backend mode. `open` dials nothing in that case, so a missing gateway config still loads the context.

## Types and signatures

Package `org.hle.gateway`. One file, `Gateway.kt`. Private types stay in that file so a controller cannot import them.

```kotlin
package org.hle.gateway

import com.google.protobuf.Message
import io.grpc.CallOptions
import io.grpc.Channel
import io.grpc.ClientCall
import io.grpc.ClientInterceptor
import io.grpc.ForwardingClientCall
import io.grpc.ManagedChannel
import io.grpc.Metadata
import io.grpc.MethodDescriptor
import io.grpc.examples.hellogirl.HelloGirlReply
import io.grpc.examples.hellogirl.HelloGirlRequest
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import java.time.Duration
import java.util.concurrent.atomic.AtomicBoolean

const val BACKEND_PROPERTY_PREFIX: String = "grpc.gateway.backends."

/**
 * Drops [BACKEND_PROPERTY_PREFIX] from matching keys.
 * An empty result means single-backend mode.
 * A repeated key throws IllegalArgumentException.
 */
fun selectBackendProperties(all: Map<String, String>): Map<String, String> {
    // TODO: fold keys that start with BACKEND_PROPERTY_PREFIX.
    // Throw IllegalArgumentException on a repeated key.
    throw NotImplementedError("not implemented")
}

/** First URL segment of a gateway backend. Not a service name. */
class Prefix private constructor(val segment: String) {
    companion object {
        /**
         * Accepts one segment, [A-Za-z0-9][A-Za-z0-9._-]{0,63}, case sensitive.
         * Rejects empty, slash, ".", "..", and any segment in [reserved].
         * [reserved] is the service segments from [ServicePath].
         */
        fun parse(raw: String, reserved: Set<String>): Prefix? {
            throw NotImplementedError("not implemented")
        }
    }
}

/** host:port. Host is a DNS name or a dotted IPv4 literal. IPv6 is rejected. */
class SocketAddress private constructor(val host: String, val port: Int) {
    companion object {
        fun parse(raw: String): SocketAddress {
            // TODO: split on the last colon. Port must be 1..65535.
            // Throw IllegalArgumentException on a bad value.
            throw NotImplementedError("not implemented")
        }
    }
}

/**
 * JSON policy for one module. Two methods because there are two protos.
 * A new proto adds a method here, so every module codec fails the build until it handles it.
 */
interface Codec {
    fun helloWorld(json: ByteArray): Parsed<HelloRequest>
    fun helloGirl(json: ByteArray): Parsed<HelloGirlRequest>
    fun encode(message: Message): ByteArray
}

sealed interface Parsed<out T> {
    class Ready<T>(val value: T) : Parsed<T>
    class Rejected(val message: String) : Parsed<Nothing>
}

/**
 * The gRPC call for one module. [channel] is already wrapped with special_msg.
 * Implementations pass the decoded protobuf through. They do not rebuild it from a single field.
 */
interface Rpc {
    fun helloWorld(channel: Channel, request: HelloRequest): HelloReply
    fun helloGirl(channel: Channel, request: HelloGirlRequest): HelloGirlReply
}

/**
 * Dials one owned channel. The returned channel is not a Spring bean and not a Quarkus client.
 * Gateway closes it. The dialer does not keep a copy.
 * Deadline is not a dialer argument. [Gateway.call] applies it when the channel is owned.
 */
fun interface OwnedDialer {
    fun dial(address: SocketAddress): ManagedChannel
}

sealed interface HandleResult {
    class Ok(val json: ByteArray) : HandleResult
    data object UnknownPrefix : HandleResult
    data object NotARoute : HandleResult
    class BadJson(val message: String) : HandleResult
}

class Gateway private constructor(
    private val board: Board,
    private val deadline: Duration?,
    private val codec: Codec,
    private val rpc: Rpc,
) {
    /**
     * [path] starts with `/`, has no query, and is the path inside the application.
     * Unknown prefix returns before JSON parsing and before [Rpc].
     * Unprefixed routes use [Board.borrowed] and never return [HandleResult.UnknownPrefix].
     */
    fun handle(path: String, json: ByteArray): HandleResult {
        // TODO: when (match(path))
        // NotARoute -> HandleResult.NotARoute
        // Unprefixed(service) -> call(board.borrowed, service, json, deadline = null)
        // Prefixed(raw, service) ->
        //   Prefix.parse(raw, ServicePath.reserved) ?: return UnknownPrefix
        //   board.owned[prefix] ?: return UnknownPrefix
        //   call(owned.channel, service, json, deadline = this.deadline)
        throw NotImplementedError("not implemented")
    }

    /**
     * Idempotent. A second call returns. A crash halfway through leaves the remaining
     * owned channels in [Board.owned], so the next call finishes them.
     * Does not shut down [Board.borrowed].
     */
    fun close() {
        // TODO: board.owned.values.forEach { it.close() }
        throw NotImplementedError("not implemented")
    }

    private fun call(
        channel: Channel,
        service: ServicePath,
        json: ByteArray,
        deadline: Duration?,
    ): HandleResult {
        // TODO: start from channel. If deadline != null, intercept with a deadline
        // interceptor that sets CallOptions.withDeadlineAfter for that duration.
        // Then intercept with SpecialMsg. Pass that view to Rpc.
        // Exhaustive when on service.
        // HelloWorld -> codec.helloWorld, then rpc.helloWorld, then codec.encode.
        // HelloGirl -> codec.helloGirl, then rpc.helloGirl, then codec.encode.
        // Parsed.Rejected -> HandleResult.BadJson.
        // Do not catch StatusRuntimeException. The HTTP shell already turns that into 500.
        throw NotImplementedError("not implemented")
    }

    companion object {
        /**
         * Dials every backend before returning. If one dial throws, close the channels
         * already dialed and rethrow. Callers never see a partial board.
         * Empty [entries] returns a board whose owned map is empty.
         */
        fun open(
            entries: Map<String, String>,
            borrowed: Channel,
            deadline: Duration?,
            dialer: OwnedDialer,
            codec: Codec,
            rpc: Rpc,
        ): Gateway {
            // TODO: parse entries into Map<Prefix, SocketAddress>.
            // Keys look like "p1.address". Any other suffix throws.
            // A missing address throws. A reserved or illegal prefix throws.
            // val opened = mutableListOf<OwnedChannel>()
            // try { dial each; opened += ... } catch (e: Exception) {
            //   opened.forEach { it.close() }; throw e
            // }
            // return Gateway(Board(borrowed, opened.associateBy { it.prefix }), ...)
            throw NotImplementedError("not implemented")
        }
    }
}

/**
 * Immutable after [Gateway.open] returns.
 * Unprefixed access is the [borrowed] field.
 * Prefixed access is one [owned] get.
 * Close access is [owned] iteration. [borrowed] is absent from that loop by type.
 */
private class Board(
    val borrowed: Channel,
    val owned: Map<Prefix, OwnedChannel>,
)

private class OwnedChannel(
    val prefix: Prefix,
    val channel: ManagedChannel,
) {
    private val closed = AtomicBoolean(false)

    fun close() {
        // TODO: if (!closed.compareAndSet(false, true)) return
        // channel.shutdown()
        // await termination for 5 seconds
        // if still running, channel.shutdownNow()
        // The 5 seconds is the shutdown budget. It is not the RPC deadline.
        throw NotImplementedError("not implemented")
    }
}

/**
 * The only list of HTTP service paths.
 * [reserved] is derived from [entries]. Do not declare a second set.
 */
private enum class ServicePath(val segment: String, val method: String) {
    HelloWorld("helloworld", "say-hello"),
    HelloGirl("hello-girl", "say-hello"),
    ;

    companion object {
        val reserved: Set<String> = entries.map { it.segment }.toSet()
    }
}

private sealed interface PathMatch {
    class Unprefixed(val service: ServicePath) : PathMatch
    class Prefixed(val rawPrefix: String, val service: ServicePath) : PathMatch
    data object NotARoute : PathMatch
}

private fun match(path: String): PathMatch {
    // TODO: reject a query string. Split on '/'. Drop empty leading and trailing pieces.
    // Two pieces that equal a ServicePath segment and method -> Unprefixed.
    // Three pieces whose last two equal a ServicePath -> Prefixed(first, service).
    // Anything else, including "/p1" and "/helloworld/nope" -> NotARoute.
    // Do not look at the owned map here.
    throw NotImplementedError("not implemented")
}

/**
 * The only place that sets special_msg.
 * Header name special_msg. Value greetings-from-girl-java-client.
 * Applied per call on a fresh interceptor view, so a second call does not stack headers.
 */
private object SpecialMsg : ClientInterceptor {
    override fun <ReqT, RespT> interceptCall(
        method: MethodDescriptor<ReqT, RespT>,
        callOptions: CallOptions,
        next: Channel,
    ): ClientCall<ReqT, RespT> {
        throw NotImplementedError("not implemented")
    }
}
```

`ForwardingClientCall` is the same wrapper the existing interceptors use. The body is that wrapper, moved here, then the old classes go away.

## What the four paths do

`POST /helloworld/say-hello` matches `ServicePath.HelloWorld` with no prefix. `handle` reads `board.borrowed`, parses JSON with `Codec.helloWorld`, calls `Rpc.helloWorld`, encodes the reply. The owned map is not read. The same steps with `HelloGirl` serve `POST /hello-girl/say-hello`.

`POST /p1/helloworld/say-hello` matches a prefixed `HelloWorld`. `Prefix.parse("p1", reserved)` succeeds. `owned["p1"]` is the channel dialed for `grpc.gateway.backends.p1.address`. Both services on `p1` use that same channel. `POST /p2/hello-girl/say-hello` is the same lookup with `HelloGirl` and prefix `p2`.

`POST /nope/helloworld/say-hello` matches a prefixed `HelloWorld`, then `owned["nope"]` misses. Result is `UnknownPrefix`. `Codec` and `Rpc` are not called. With an empty owned map, every prefixed service path is `UnknownPrefix`, and both unprefixed paths still hit `borrowed`.

`POST /helloworld/nope` and `POST /p1` are `NotARoute`. The shell answers 404 for both `NotARoute` and `UnknownPrefix`. The result type still tells them apart, so a unit test can require that a missing prefix did not fall through to `borrowed`.

`close` walks `owned` only. Each `OwnedChannel.close` returns immediately when the flag is already set. The borrowed `local` or `hello` channel stays on the framework lifecycle that owns it today.

gRPC status is not mapped to HTTP status. A `StatusRuntimeException` leaves `handle` and the existing framework error path answers 500.

## Module map

Request path, two files. `GatewayHttp` reads the path and writes the status. `Gateway.handle` does the rest. The dialer runs at startup only.

Shared source, compiled into each app, not a Maven module and not copied.

- `grpc-http1-proxy/gateway-core/src/main/kotlin/org/hle/gateway/Gateway.kt`

Each app adds that directory with `build-helper-maven-plugin` `add-source`. Do not replace `sourceDirectory`. Do not make a second copy of the file.

Per app, two new files.

- `GatewayHttp` maps `POST /{first}/{second}` and `POST /{first}/{second}/{third}` to `gateway.handle`.
- `GatewayWiring` calls `Gateway.open`, supplies `Codec`, `Rpc`, and `OwnedDialer`, and calls `close` on shutdown.

Deletions in the same wave, so the old call path cannot stay alive next to `handle`.

- vs. `HelloWorldController`, `HelloGirlController`, `HelloWorldClient`, `HelloGirlClient`, and both `*ClientImpl` classes. The `ManagedChannel` `@Bean` in `GrpcConfig` stays. It is the borrowed channel. `HelloWorldControllerTest` stops mocking `HelloWorldClient` and drives `Gateway` with a recording `Rpc`. The other modules' HTTP tests move the same way.
- wf-kt. The same controllers and clients, plus `HelloWorldClientAsyncImpl`, `HelloWorldClientFutureImpl`, and the unregistered `HelloWorldHandler`. Do not add another `HelloWorldClient` bean. The interface goes away, so `@Primary` is not required to disambiguate it.
- wf-kt-native. The same controllers, `HelloWorldCoroutineClient`, `HelloGirlCoroutineClient`, and the unregistered `HelloWorldHandler`.
- quarkus-blocking-kt. `HelloWorldResource` and `HelloGirlResource` lose their stub fields and are replaced by `GatewayHttp`. `ProtobufJsonProvider` drops `@Provider` and becomes the `Codec`. `SpecialMsgInterceptor` is deleted after its header moves into `Gateway.kt`.

`GET /grpc/channels` in vs and wf-kt stays. Gateway prefixes are not added to `spring.grpc.client.channels`.

### Codec

One parser per module, the settings that module uses today.

- vs. `JsonFormat.parser()` and `JsonFormat.printer()`. Unknown fields fail. Output is pretty. Remove the `ProtobufJsonFormatHttpMessageConverter` bean so those settings exist only on the `Codec`.
- wf-kt and wf-kt-native. `JsonFormat.parser().ignoringUnknownFields()` and `JsonFormat.printer().omittingInsignificantWhitespace()`. Remove the WebFlux codec registration that currently constructs those same objects.
- quarkus. The parser and printer already on `ProtobufJsonProvider`. Ignoring unknown fields, compact output.

### Rpc

- vs and wf-kt. `GreeterGrpc.newBlockingStub(channel).sayHello(request)` and `GirlGreeterGrpc.newBlockingStub(channel).sayHello(request)`. Pass the parsed message through. The vs client currently rebuilds `HelloRequest` with only `name`. That rebuild is deleted with the client.
- wf-kt-native. The same blocking stubs. grpc-java codegen in that module already emits them. The HTTP method still hops to `Dispatchers.IO` before `handle`, which is what the current primary client does around its blocking stub.
- quarkus. Build the Mutiny stub on the channel `handle` passes in, then `sayHello(request).await().indefinitely()`, which is what the resource does today. Do not add a second protoc plugin to get `GreeterGrpc` into this module.

### Owned dialer

`ManagedChannelBuilder.forAddress(host, port).usePlaintext()`, then `build()`. The dialer does not set a deadline. `Gateway.call` adds a deadline interceptor only for owned channels, using the `Duration` passed to `open`. Wiring reads that duration from the borrowed channel's existing property (`spring.grpc.client.channels.local.default-deadline`, or `quarkus.grpc.clients.hello.deadline`). Do not write a second `25s` literal. The borrowed channel keeps the deadline the framework already installed. `call` does not add another one on that channel.

vs dialer also sets the retry service config that `GrpcConfig.channel` builds today. Move that map into one function both the borrowed bean and the dialer call. maxAttempts 4, initial backoff 0.1s, max backoff 1s, multiplier 2, retryable status `UNAVAILABLE`, then `enableRetry()`. The other three dialers do not add retry. Their borrowed channels have none today.

Owned channels are not registered with `GrpcChannelFactory.createChannel`. A second `createChannel` does not inherit the vs retry options, and a second unqualified `ManagedChannel` bean fails Spring startup. Quarkus does not gain a `@GrpcClient` name. A new name is fixed at build time and a missing name fails startup, so gateway config would not be opt-in.

### Shutdown

Spring `DisposableBean` calls `gateway.close()`. Quarkus `ShutdownEvent` does the same. Both can run twice. `OwnedChannel.close` is safe the second time. Neither hook closes the borrowed channel.

## Screen

Shallow module. The HTTP caller learns `handle` and four results. Dial, retry, header, prefix rules, and shutdown sit behind that. The composition interfaces (`Codec`, `Rpc`, `OwnedDialer`) are wider because each module's HTTP stack and codegen differ. Controllers do not take those interfaces.

Information leakage. `ManagedChannel` is not a parameter of `handle`. JSON bytes cross the HTTP boundary. Protobuf messages exist only after `Codec` returns. The header name lives in `SpecialMsg` only.

Temporal decomposition. `match`, select, decode, and call are private steps of `handle`. They are not types a caller chains. Decode runs after the prefix hit, so a missing prefix skips JSON.

Pass-through. `GatewayHttp` maps a result to an HTTP status. That is the HTTP policy. There is no `GatewayClient` that forwards `handle` onward.

Split ownership. The dialer returns a channel and does not store it. `Board.owned` is the only collection `close` walks. The framework keeps the borrowed channel.

Two ways. Production RPCs go through `Rpc`, called only from `handle`. The old client interfaces are deleted in the same wave. `HelloWorldHandler` is deleted. Registering it would add a second HTTP path.

Importable internals. `Board`, `OwnedChannel`, `ServicePath`, `match`, and `SpecialMsg` are private to `Gateway.kt`.

Hand-synced lists. Path segments live on `ServicePath`. Reserved prefixes are `entries.map { it.segment }`. A new enum constant breaks the exhaustive `when` in `handle` and in `match`. A new proto also adds a method on `Codec` and `Rpc`, which breaks the four implementors until they compile. Those are compiler failures, not a second handwritten path list.
