package org.hle.grpchttp1vs.client.impl

import io.grpc.ManagedChannel
import io.grpc.examples.helloworld.GreeterGrpc
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import org.hle.grpchttp1vs.client.HelloWorldClient
import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Primary
import org.springframework.stereotype.Service
import java.util.concurrent.TimeUnit

@Primary
@Service
class HelloWorldClientImpl(
    channel: ManagedChannel,
    @Value("\${grpc.client.deadline-ms:5000}") private val deadlineMs: Long
) : HelloWorldClient {

    private val blockingStub = GreeterGrpc
        .newBlockingStub(channel)
        .withDeadlineAfter(deadlineMs, TimeUnit.MILLISECONDS)

    override fun sayHello(name: HelloRequest): HelloReply {
        val request = HelloRequest.newBuilder()
            .setName(name.name)
            .build()

        return blockingStub.sayHello(request)
    }
}
