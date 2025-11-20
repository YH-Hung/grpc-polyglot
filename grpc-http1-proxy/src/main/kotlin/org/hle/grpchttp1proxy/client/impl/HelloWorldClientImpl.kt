package org.hle.grpchttp1proxy.client.impl

import io.grpc.Context
import io.grpc.ManagedChannel
import io.grpc.examples.helloworld.GreeterGrpc
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.job
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
        return withContext(Dispatchers.IO) {
            // TODO: With Deadline
            val cancellableContext = Context.current()
                .withCancellation()

            // Cancelled by CancellableContext
            cancellableContext.use { ctx ->
                // Link coroutine cancellation to gRPC cancellation
                coroutineContext.job.invokeOnCompletion { cause ->
                    if (cause != null && !ctx.isCancelled) {
                        ctx.cancel(cause)
                    }
                }

                // Run gRPC call inside cancellable context
                ctx.call {
                    blockingStub.sayHello(request)
                }
            } // ctx.close() is automatically called here
        }
    }
}