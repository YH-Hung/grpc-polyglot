package org.hle.grpchttp1proxy.client.impl

import io.grpc.ManagedChannel
import io.grpc.examples.helloworld.GreeterGrpc
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.hle.grpchttp1proxy.client.HelloWorldClient
import org.springframework.context.annotation.Primary
import org.springframework.stereotype.Service

@Primary
@Service
class HelloWorldClientImpl(channel: ManagedChannel) : HelloWorldClient {

    private val blockingStub = GreeterGrpc.newBlockingStub(channel)

    override suspend fun sayHello(name: HelloRequest): HelloReply {
        // Convert from DTO to gRPC request
        val request = HelloRequest.newBuilder()
            .setName(name.name)
            .build()

        // Make the gRPC call in a non-blocking way using Kotlin coroutines
        val response = withContext(Dispatchers.IO) {
            blockingStub.sayHello(request)
        }

        // Convert from gRPC response to DTO
        return response
    }
}