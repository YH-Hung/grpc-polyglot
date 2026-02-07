package org.hle.grpchttp1wfn.client

import io.grpc.ManagedChannel
import io.grpc.examples.helloworld.GreeterGrpcKt.GreeterCoroutineStub
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Service
import java.util.concurrent.TimeUnit

@Service
class HelloWorldCoroutineClient(
    channel: ManagedChannel,
    @Value("\${grpc.client.deadline-ms:5000}") private val deadlineMs: Long
) : HelloWorldClient {
    private val stub = GreeterCoroutineStub(channel)
        .withDeadlineAfter(deadlineMs, TimeUnit.MILLISECONDS)

    override suspend fun sayHello(request: HelloRequest): HelloReply =
        stub.sayHello(request)
}
