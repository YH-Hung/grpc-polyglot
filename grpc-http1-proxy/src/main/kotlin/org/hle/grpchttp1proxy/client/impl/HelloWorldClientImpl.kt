package org.hle.grpchttp1proxy.client.impl

import io.grpc.Context
import io.grpc.ManagedChannel
import io.grpc.examples.helloworld.GreeterGrpc
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.hle.grpchttp1proxy.client.HelloWorldClient
import org.springframework.context.annotation.Primary
import org.springframework.stereotype.Service
import kotlinx.coroutines.Job
import kotlin.coroutines.coroutineContext

@Primary
@Service
class HelloWorldClientImpl(channel: ManagedChannel) : HelloWorldClient {

    private val blockingStub = GreeterGrpc.newBlockingStub(channel)

    override suspend fun sayHello(name: HelloRequest): HelloReply {
        // Convert from DTO to gRPC request
        val request = HelloRequest.newBuilder()
            .setName(name.name)
            .build()

        // Create a cancellable gRPC Context for this call
        val cancellableCtx = Context.current().withCancellation()

        // Tie coroutine cancellation (e.g., HTTP client disconnect) to gRPC call cancellation
        coroutineContext[Job]?.invokeOnCompletion { cause ->
            // Cancelling the Context cancels the client call started under it
            cancellableCtx.cancel(cause)
        }

        // Make the gRPC call on the IO dispatcher while the cancellable Context is attached
        val response = withContext(Dispatchers.IO) {
            val prev = cancellableCtx.attach()
            try {
                blockingStub.sayHello(request)
            } finally {
                cancellableCtx.detach(prev)
            }
        }

        return response
    }
}