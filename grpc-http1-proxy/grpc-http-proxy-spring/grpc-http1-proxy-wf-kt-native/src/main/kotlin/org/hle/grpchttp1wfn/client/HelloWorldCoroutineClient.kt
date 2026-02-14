package org.hle.grpchttp1wfn.client

import io.grpc.ManagedChannel
import io.grpc.examples.helloworld.GreeterGrpcKt.GreeterCoroutineStub
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import org.springframework.stereotype.Service

@Service
class HelloWorldCoroutineClient(
    channel: ManagedChannel,
) : HelloWorldClient {
    private val stub = GreeterCoroutineStub(channel)

    override suspend fun sayHello(request: HelloRequest): HelloReply =
        stub.sayHello(request)
}
