# Synthesis decision

## Goal

`grpc-http1-proxy` stays an auxiliary in front of a gRPC server. A path prefix selects the channel. The same prefix rule applies to every HTTP route, including routes that are not written yet. `/p1/helloworld/say-hello` and `/p2/helloworld/say-hello` share the protobuf and use different channels. `/p1/anything/you/add/later` uses p1 as well. Unprefixed paths stay on today's channel.

## Base

candidate-opus for the channel table and spring-grpc ownership. The per-route prefix handler is withdrawn. A handler that names `helloworld` and `hello-girl` cannot see a route that does not exist yet.

## Shape

The prefix is a fact about the request, not about a controller method.

```text
request path
  └── first segment is a configured backend?
        yes → store that BackendName, dispatch the remaining path
        no  → store no name, dispatch the path unchanged

RoutingChannel (one Channel)
  └── newCall reads the request's BackendName
        none → local ManagedChannel
        name → the channel Backends opened for that name

Backends
  ├── local: Channel          the existing ManagedChannel bean
  └── byName: Map<BackendName, Channel>
```

One filter owns the path rule. One channel owns the call rule. A new `@PostMapping` needs no gateway annotation. A new client takes `Channel` and follows the same request.

`GatewayController` does not exist. It listed two routes and would miss the next one.

## Rules

- `parseGateway` still rejects illegal names, duplicates, reserved segments `helloworld` and `hello-girl`, and names with no channel block. Those two segments are today's route roots. A configured name owns that first segment for every path.
- An unknown first segment is left in the path. `/p9/helloworld/say-hello` matches no controller, returns 404, and makes no RPC.
- Empty `proxy.gateway.backends` strips nothing and dials nothing extra.
- Listing `local` reuses the existing bean. `createChannel` runs only for other names.
- vs retry stays one `options()` function, used by the local bean and by the gateway open lambda.
- `Backends` does not close channels.
- `special_msg` stays in the existing client constructors. Those clients are built on `RoutingChannel`.
- The path spelling is `helloworld`.

## This unit

Only `grpc-http-proxy-spring/grpc-http1-proxy-vs`.

Delete `GatewayController` if it is present. Add the filter and `RoutingChannel`. Point `HelloWorldClientImpl` and `HelloGirlClientImpl` at `RoutingChannel`. Keep `@Service` and `@Primary`. Keep the unprefixed controller methods. Keep the single `ManagedChannel` bean as the local target.

Proof that a route which does not exist in main still switches channel. A test-only controller mapped at `/probe/who` reads which channel the routing channel selected. `POST /probe/who` is local. `POST /p1/probe/who` is p1. `POST /p2/probe/who` is p2. `POST /p9/helloworld/say-hello` is 404 and neither server's RPC counter moves. The existing greeter routes with `/p1` and `/p2` still hit the matching server.

The other three modules get the same filter-and-routing-channel pair after this test is green. Quarkus uses a pre-matching request filter, because its stubs are not built from a shared `Channel`. That module is not this unit.

## Rejected

- A second mapping per RPC.
- Averaging the two sketches.
- Grok's catch-all that replaces controllers and codecs.
- Dialing with `ManagedChannelBuilder`.
- Deleting the `ManagedChannel` bean.
- The path spelling `hellow-world`.

## Checked against the tree

- `GatewayController` maps only `/{backend}/helloworld/say-hello` and `/{backend}/hello-girl/say-hello`. A route added later is invisible to it.
- `HelloWorldController` maps `/helloworld/say-hello` and injects `HelloWorldClient`. After the filter strips `/p1`, that same method handles the prefixed call.
- `GrpcConfig.channel` is the only `ManagedChannel` bean and the only place vs retry options are applied.
- `HelloWorldControllerTest` mocks `HelloWorldClient`. Leaving that injection in place keeps the unprefixed HTTP test.

The spring-grpc 1.0.0 claims (unknown channel name dials `localhost:9090`, factory `destroy()` closes every `createChannel`) come from the design judge's source check, not from a jar read in this session. `parseGateway` still rejects a listed name with no channel block.
