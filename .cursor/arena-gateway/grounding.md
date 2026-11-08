# Grounding for the gateway design

Source: architecture explanation synthesized from four read-only traces of grpc-http1-proxy.

## What exists

Four copied apps. No shared library. Each process dials one gRPC backend at startup.

- grpc-http1-proxy-vs: Spring MVC, virtual threads, blocking stubs. GrpcConfig.channel() calls factory.createChannel("local", retry options). Retry is maxAttempts 4, UNAVAILABLE only. special_msg is attached per stub with withInterceptors.
- grpc-http1-proxy-wf-kt: WebFlux. Live client is @Primary HelloWorldClientImpl, a blocking stub on Dispatchers.IO. Async and future beans exist and are not selected. Removing @Primary makes HelloWorldClient injection ambiguous. special_msg is a @GlobalClientInterceptor.
- grpc-http1-proxy-wf-kt-native: WebFlux plus GreeterCoroutineStub. special_msg is per stub. createChannel("local") with no retry options.
- grpc-http1-proxy-quarkus-blocking-kt: JAX-RS, @RunOnVirtualThread, Mutiny. Both resources inject @GrpcClient("hello"). special_msg is @GlobalInterceptor.

Live routes, same in every module:

- POST /helloworld/say-hello -> helloworld.Greeter/SayHello. JSON name in, message out.
- POST /hello-girl/say-hello -> hellogirl.GirlGreeter/SayHello.

There is no hellow-world spelling. Streaming RPCs have no HTTP route. HelloWorldHandler in wf-kt and native is not registered.

Spring clients inject an unqualified ManagedChannel. A second unqualified ManagedChannel bean fails startup with NoUniqueBeanDefinitionException. Stubs are built in the constructor. sayHello takes only the protobuf message.

Quarkus clients are already name-qualified. A second @GrpcClient name does not disturb "hello".

vs and wf-kt Greeter clients rebuild HelloRequest with only name. Others pass the parsed message through. HelloRequest has only name today.

JSON codecs stay shared. vs rejects unknown fields and pretty-prints. The other three ignore unknown fields and emit compact JSON. No module maps gRPC status to HTTP status. Success is implicit 200.

Tests mock the client and lock POST /helloworld/say-hello. Adding routes keeps them green even if prefix resolution is wrong. A channel bean that must exist at startup with missing config fails context load. /hello-girl has no test.

Properties:

- spring.grpc.client.channels.local.address=localhost:50051
- spring.grpc.client.channels.local.default-deadline=25s
- quarkus.grpc.clients.hello.host=localhost, port 50051, deadline 25s

No application code shuts channels down. A later createChannel("p2") on vs does not inherit the retry options passed only to createChannel("local", options).

## Goal

Keep the single-backend auxiliary mode. Add a gateway mode that switches channel by path prefix. /p1/... and /p2/... reach different channels that share the same protobuf. The example spelling hellow-world does not match the live segment helloworld.

## Constraints a design must satisfy

- Leave POST /helloworld/say-hello and POST /hello-girl/say-hello on the existing local / hello channel.
- Do not add a second unqualified ManagedChannel bean.
- Do not add another HelloWorldClient bean in wf-kt.
- Unknown prefix is an explicit 404.
- Gateway config is opt-in. No gateway config means today's behavior, including context load.
- vs extra channels keep the same retry policy as local.
- vs and native per-call stubs still send special_msg.
- Channels created by a registry are closed on shutdown.
- Protos stay shared. The gateway chooses a channel, not a message type.
- Spring can add a backend by config. Quarkus client names are fixed at build time.
