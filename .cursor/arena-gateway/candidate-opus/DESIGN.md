# Gateway mode design (candidate: opus)

Sketch only. Bodies are `TODO("not implemented")`. Rationale lives in `RATIONALE.md`.

## 0. The data shape, before any logic

```text
Backends  (one per process, immutable after startup, read-only per request)
 ├── local: Backend                        unprefixed routes, channel "local" (Quarkus: client "hello")
 └── byName: Map<BackendName, Backend>     gateway routes, one entry per opted-in prefix

Backend   (one per distinct gRPC channel)
 ├── helloWorld: HelloWorldClient          stub bound to that channel
 └── helloGirl:  HelloGirlClient           stub bound to that channel
```

The organizing structure is a **prefix-major routing table**. The outer key is the backend, because
the backend (one channel) is the unit of config, retry policy, deadline, lifecycle, and failure. The
inner layer is a fixed record of service clients, because the set of services is fixed at compile
time and identical for every backend (shared protos).

Every request is one hash lookup plus one field read. Stubs are built once per backend at startup.
Nothing is created per request, so no cache is needed later.

The unprefixed route is not a special mode. It is the `local` entry of the same table, so
single-backend mode is exactly "gateway mode with an empty `byName`".

## 1. Caller's usage (the spec)

### README section, Spring modules (vs, wf-kt, wf-kt-native)

```properties
# Single-backend mode: unchanged. No gateway keys, no new routes.
spring.grpc.client.channels.local.address=localhost:50051
spring.grpc.client.channels.local.default-deadline=25s

# Gateway mode: opt in with application-gateway.properties (profile "gateway").
# A backend name is both the URL prefix and the spring-grpc channel name.
spring.grpc.client.channels.p1.address=10.0.0.1:50051
spring.grpc.client.channels.p1.default-deadline=25s
spring.grpc.client.channels.p2.address=10.0.0.2:50051
spring.grpc.client.channels.p2.default-deadline=25s
proxy.gateway.backends=p1,p2
```

```text
POST /helloworld/say-hello        -> channel "local"   (today's route, unchanged)
POST /hello-girl/say-hello        -> channel "local"   (today's route, unchanged)
POST /p1/helloworld/say-hello     -> channel "p1"
POST /p2/hello-girl/say-hello     -> channel "p2"
POST /p9/helloworld/say-hello     -> 404 (p9 not in proxy.gateway.backends)
```

Startup fails when a listed backend has no `spring.grpc.client.channels.<name>` block, or the name is
not a lowercase URL segment. Without that check spring-grpc silently dials the default
`localhost:9090` for an unknown channel name (`GrpcClientProperties.getChannel`, verified in 1.0.0
source).

### README section, Quarkus (quarkus-blocking-kt)

```properties
quarkus.grpc.clients.hello.host=localhost        # unprefixed, unchanged
quarkus.grpc.clients.p1.host=10.0.0.1
quarkus.grpc.clients.p1.port=50051
quarkus.grpc.clients.p1.deadline=25s
proxy.gateway.backends=p1
```

Quarkus ships build-time slots `p1` and `p2`. A slot routes only when listed in
`proxy.gateway.backends`. Adding `p3` means adding one slot class and rebuilding.

### Call site 1: vs controller (blocking, virtual threads)

```kotlin
@RestController
class HelloWorldController(private val backends: Backends) {

    @PostMapping(
        value = ["/helloworld/say-hello", "/{backend}/helloworld/say-hello"],
        consumes = [MediaType.APPLICATION_JSON_VALUE], produces = [MediaType.APPLICATION_JSON_VALUE],
    )
    fun sayHello(@PathVariable backend: String?, @RequestBody request: HelloRequest): HelloReply =
        backends.route(backend).helloWorld.sayHello(request)
}
```

### Call site 2: wf-kt-native controller (suspend)

```kotlin
@RestController
class HelloGirlController(private val backends: Backends) {

    @PostMapping(
        value = ["/hello-girl/say-hello", "/{backend}/hello-girl/say-hello"],
        consumes = [MediaType.APPLICATION_JSON_VALUE], produces = [MediaType.APPLICATION_JSON_VALUE],
    )
    suspend fun sayHello(@PathVariable backend: String?, @RequestBody request: HelloGirlRequest): HelloGirlReply =
        backends.route(backend).helloGirl.sayHello(request)
}
```

### Call site 3: Quarkus resource

```kotlin
@Path("/")
class HelloWorldResource(private val backends: Backends) {

    @POST @Path("helloworld/say-hello") @RunOnVirtualThread
    @Consumes(MediaType.APPLICATION_JSON) @Produces(MediaType.APPLICATION_JSON)
    fun sayHello(request: HelloRequest): HelloReply =
        backends.route(null).helloWorld.sayHello(request).await().indefinitely()

    @POST @Path("{backend}/helloworld/say-hello") @RunOnVirtualThread
    @Consumes(MediaType.APPLICATION_JSON) @Produces(MediaType.APPLICATION_JSON)
    fun sayHelloVia(@PathParam("backend") backend: String, request: HelloRequest): HelloReply =
        backends.route(backend).helloWorld.sayHello(request).await().indefinitely()
}
```

JAX-RS has no optional path segment on one method, so Quarkus gets two one-line methods that call the
same `route`. Both still go through one lookup.

### Call site 4: the behavior test (Spring)

```kotlin
// Two in-process gRPC servers answer "from p1" and "from p2"; "local" answers "from local".
// application-test: channels.local/p1/p2 point at in-process names; proxy.gateway.backends=p1,p2
post("/helloworld/say-hello", """{"name":"a"}""")    // message == "from local"
post("/p1/helloworld/say-hello", """{"name":"a"}""") // message == "from p1"
post("/p2/hello-girl/say-hello", """{"name":"a"}""") // message == "from p2"
post("/p9/helloworld/say-hello", """{"name":"a"}""") // status 404
```

The existing tests mock `HelloWorldClient` and cannot see which channel answered. This test can.

## 2. Type sketch (Spring; shown for vs, identical shape in wf-kt and wf-kt-native)

New package `org.hle.grpchttp1vs.gateway`. One file, `Backends.kt`. Everything a reader needs to trace
input to output is in it.

```kotlin
package org.hle.grpchttp1vs.gateway

import io.grpc.Channel
import org.hle.grpchttp1vs.client.HelloGirlClient
import org.hle.grpchttp1vs.client.HelloWorldClient
import org.hle.grpchttp1vs.client.impl.HelloGirlClientImpl
import org.hle.grpchttp1vs.client.impl.HelloWorldClientImpl
import org.springframework.boot.context.properties.ConfigurationProperties
import org.springframework.http.HttpStatus
import org.springframework.web.bind.annotation.ResponseStatus

/**
 * A backend's name. It is the URL prefix segment and the spring-grpc channel name.
 * Invariant: matches [a-z0-9]([a-z0-9-]*[a-z0-9])?, so it is always one path segment.
 */
@JvmInline
value class BackendName private constructor(val value: String) {
    companion object {
        /** Throws IllegalArgumentException naming the bad value. Called only at config parse time. */
        fun parse(raw: String): BackendName = TODO("not implemented")
    }
}

/**
 * Every unary client the proxy exposes, bound to one channel.
 * Adding a service adds a field here and a controller. Nothing else.
 * Invariant: all fields share the same channel.
 */
class Backend internal constructor(channel: Channel) {
    val helloWorld: HelloWorldClient = HelloWorldClientImpl(channel)
    val helloGirl: HelloGirlClient = HelloGirlClientImpl(channel)
}

/** Raw opt-in list. Absent key means an empty list, which means single-backend mode. */
@ConfigurationProperties("proxy.gateway")
data class GatewayProperties(val backends: List<String> = emptyList())

/** Thrown by [Backends.route] for a prefix that is not an opted-in backend. Maps to 404 in MVC and WebFlux. */
@ResponseStatus(HttpStatus.NOT_FOUND)
class UnknownBackendException(val prefix: String) : RuntimeException("unknown backend: $prefix")

/**
 * The routing table. Built once at startup, immutable, safe for concurrent reads.
 * Does not own channel lifecycle: the GrpcChannelFactory that opened the channels closes them.
 */
class Backends private constructor(
    private val local: Backend,
    private val byName: Map<String, Backend>,
) {
    /**
     * null prefix (unprefixed route) -> local.
     * Known prefix -> that backend.
     * Anything else -> UnknownBackendException.
     */
    fun route(prefix: String?): Backend = TODO("not implemented")

    companion object {
        /**
         * Validates the opt-in list, opens each distinct channel exactly once through [open],
         * and builds one Backend per channel. Listing "local" reuses the local channel.
         * Throws at startup with every bad name listed, so misconfiguration never reaches a request.
         */
        fun open(
            localChannel: String,
            gateway: GatewayProperties,
            configuredChannels: Set<String>,
            open: (channelName: String) -> Channel,
        ): Backends {
            // TODO
            // val names = parseGateway(gateway.backends, configuredChannels)
            // val channels = (listOf(localChannel) + names.map { it.value }).distinct().associateWith(open)
            // val backends = channels.mapValues { (_, ch) -> Backend(ch) }
            // return Backends(backends.getValue(localChannel), names.associate { it.value to backends.getValue(it.value) })
            TODO("not implemented")
        }
    }
}

/**
 * Pure. Parses the raw list into names.
 * Rejects: bad syntax, duplicates, and names with no spring.grpc.client.channels.<name> block.
 * Collects all errors before throwing, so one boot shows every mistake.
 */
internal fun parseGateway(raw: List<String>, configuredChannels: Set<String>): List<BackendName> =
    TODO("not implemented")
```

### GrpcConfig (vs) after the change

```kotlin
@Configuration
@EnableConfigurationProperties(GatewayProperties::class)
class GrpcConfig {

    /** The only place a channel is opened. Every backend, local included, gets the same retry policy. */
    private fun options(): ChannelBuilderOptions = TODO("not implemented") // today's retry map, unchanged

    @Bean
    fun backends(
        factory: GrpcChannelFactory,
        grpc: GrpcClientProperties,
        gateway: GatewayProperties,
    ): Backends =
        Backends.open("local", gateway, grpc.channels.keys) { name -> factory.createChannel(name, options()) }
}
```

The `ManagedChannel` bean is deleted. No code outside `GrpcConfig` opens a channel.

### Module deltas

| Module | `Backend` fields built from the channel | `open` lambda | special_msg |
|---|---|---|---|
| vs | `HelloWorldClientImpl`, `HelloGirlClientImpl` | `createChannel(name, retryOptions)` | per stub, inside each impl |
| wf-kt | `HelloWorldClientImpl` (blocking on `Dispatchers.IO`), `HelloGirlClientImpl` | `createChannel(name)` | `@GlobalClientInterceptor`, applied by the factory to every channel it opens |
| wf-kt-native | `HelloWorldCoroutineClient`, `HelloGirlCoroutineClient` | `createChannel(name)` | per stub, inside each client |

Client changes, all three Spring modules: drop `@Service` and `@Primary` from every client
implementation. Change the constructor parameter from `ManagedChannel` to `io.grpc.Channel`. In wf-kt
this also covers `HelloWorldClientAsyncImpl` and `HelloWorldClientFutureImpl`, which inject the
deleted `ManagedChannel` bean today. After the change no `HelloWorldClient` bean exists in any module,
so the `@Primary` ambiguity is gone, not worked around.

Controllers, all three Spring modules: inject `Backends`, map both paths on one handler, call
`backends.route(backend).<service>.sayHello(request)`.

## 3. Type sketch (Quarkus)

Quarkus client names are build-time, so a backend is a CDI bean per name, not a value built from a
channel. Quarkus keeps owning the clients, their deadline, `@GlobalInterceptor`, and their shutdown.

```kotlin
package org.hle.grpchttp1quarkusblocking.gateway

/**
 * One build-time backend slot. Subclasses inject Quarkus-managed clients for one client name.
 * Invariant: every @GrpcClient in a subclass uses that subclass's [name].
 */
abstract class Backend(val name: String) {
    abstract val helloWorld: Greeter
    abstract val helloGirl: GirlGreeter
}

@ApplicationScoped
class LocalBackend : Backend(NAME) {
    @GrpcClient(NAME) override lateinit var helloWorld: Greeter
    @GrpcClient(NAME) override lateinit var helloGirl: GirlGreeter
    companion object { const val NAME = "hello" }
}

@ApplicationScoped
class P1Backend : Backend(NAME) {
    @GrpcClient(NAME) override lateinit var helloWorld: Greeter
    @GrpcClient(NAME) override lateinit var helloGirl: GirlGreeter
    companion object { const val NAME = "p1" }
}

// P2Backend: same shape, NAME = "p2".

/** Thrown by [Backends.route]. JAX-RS maps it to 404. */
class UnknownBackendException(prefix: String) : NotFoundException("unknown backend: $prefix")

/**
 * The routing table. @Startup so a bad opt-in list fails boot, not the first request.
 * The slot list is derived from CDI (@All), never written by hand.
 */
@Startup
@ApplicationScoped
class Backends(
    @All slots: List<Backend>,
    @ConfigProperty(name = "proxy.gateway.backends") listed: Optional<List<String>>,
) {
    private val local: Backend = TODO("not implemented")              // the slot named LocalBackend.NAME
    private val byName: Map<String, Backend> = TODO("not implemented")
    // TODO
    // val names = parseGateway(listed.orElse(emptyList()), configured = slot names whose
    //     quarkus.grpc.clients.<name>.host is set)
    // byName = names.associate { it.value to slots.single { s -> s.name == it.value } }

    fun route(prefix: String?): Backend = TODO("not implemented")
}
```

`BackendName` and `parseGateway` are the same as in Spring. "Configured" in Quarkus means the slot
exists and `quarkus.grpc.clients.<name>.host` is set, because an unset host silently defaults to
`localhost:9000`.

The existing Quarkus test `@InjectMock @GrpcClient("hello") Greeter` still replaces the bean that
`LocalBackend` injects, so it stays valid.

## 4. Module map

```text
grpc-http1-proxy-vs/src/main/kotlin/org/hle/grpchttp1vs/
  gateway/Backends.kt              NEW  BackendName, Backend, GatewayProperties, UnknownBackendException, Backends, parseGateway
  config/GrpcConfig.kt             EDIT delete ManagedChannel bean, add Backends bean, one options() for all channels
  client/impl/*ClientImpl.kt       EDIT drop @Service/@Primary, take io.grpc.Channel
  controller/HelloWorldController  EDIT inject Backends, two paths, route(backend)
  controller/HelloGirlController   EDIT same
src/main/resources/application-gateway.properties   NEW  example p1/p2 opt-in profile
src/test/.../GatewayRoutingTest.kt                  NEW  in-process p1/p2/local, asserts which backend answered and 404

grpc-http1-proxy-wf-kt/...         same five edits, plus Async/Future impls lose @Service
grpc-http1-proxy-wf-kt-native/...  same five edits on the Coroutine clients

grpc-http1-proxy-quarkus-blocking-kt/src/main/kotlin/org/hle/grpchttp1quarkusblocking/
  gateway/Backends.kt              NEW  BackendName, Backend, LocalBackend, P1Backend, P2Backend, UnknownBackendException, Backends, parseGateway
  HelloWorldResource.kt            EDIT @Path("/"), two methods, route()
  HelloGirlResource.kt             EDIT same
```

Request trace in three files: controller -> `gateway/Backends.kt` -> client impl.

## 5. Behavior checklist

| Concern | Where it is decided |
|---|---|
| Config | `proxy.gateway.backends` plus the framework's own channel/client block per name. Parsed once in `parseGateway`. |
| Prefix lookup | `Backends.route`, one map lookup. |
| helloworld and hello-girl | One field each on `Backend`. One handler per RPC serves both path shapes. |
| Unprefixed routes | `route(null)` returns the `local` backend, which is built from the same `local` / `hello` channel as today. |
| Unknown prefix | `route` throws `UnknownBackendException`, which is a 404 in all four modules. Unknown service segments are the framework's own 404. |
| Shutdown | Spring: `DefaultGrpcChannelFactory.destroy()` shuts down every channel it created, gateway channels included (verified in spring-grpc 1.0.0 source). Quarkus: Quarkus closes its clients. `Backends` owns no lifecycle. |
| Retry parity (vs) | One `options()` used by the single `open` lambda. |
| special_msg | vs and native: inside each client constructor, so every backend gets it. wf-kt and Quarkus: global interceptor, applied to every framework-created channel. |
| Opt-in | Empty list means `byName` is empty. Only `local` is opened. Context load is identical to today. |
