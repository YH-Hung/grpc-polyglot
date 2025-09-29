package org.hle.grpchttp1proxy.client.impl

import io.grpc.Context
import io.grpc.ManagedChannel
import io.grpc.examples.helloworld.GreeterGrpc
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import io.grpc.stub.StreamObserver
import kotlinx.coroutines.CancellableContinuation
import kotlinx.coroutines.suspendCancellableCoroutine
import org.hle.grpchttp1proxy.client.HelloWorldClient
import org.springframework.stereotype.Service

@Service
class HelloWorldClientAsyncImpl(channel: ManagedChannel) : HelloWorldClient {

    private val asyncStub = GreeterGrpc.newStub(channel)

    override suspend fun sayHello(name: HelloRequest): HelloReply {
        // Convert from DTO to gRPC request
        val request = HelloRequest.newBuilder()
            .setName(name.name)
            .build()

        // Make the gRPC call in a non-blocking way using the async stub
        return suspendCancellableCoroutine { continuation: CancellableContinuation<HelloReply> ->
            // Create a cancellable gRPC Context for this call and attach it while starting the call
            val cancellableCtx = Context.current().withCancellation()
            val prevCtx = cancellableCtx.attach()
            try {
                asyncStub.sayHello(request, object : StreamObserver<HelloReply> {
                    override fun onNext(response: HelloReply) {
                        // Resume the coroutine if still active
                        if (continuation.isActive) {
                            continuation.resume(response, onCancellation = null)
                        }
                    }

                    override fun onError(error: Throwable) {
                        // If the continuation is still active, propagate the error
                        if (continuation.isActive) {
                            continuation.resumeWith(Result.failure(error))
                        }
                        // else ignore; the coroutine was already cancelled and we already cancelled the gRPC call
                    }

                    override fun onCompleted() {
                        // Unary call: onNext already delivered the value
                    }
                })
            } finally {
                // Detach immediately; the gRPC call has captured the current context already
                cancellableCtx.detach(prevCtx)
            }

            // Register cancellation handler to cancel the underlying gRPC call
            continuation.invokeOnCancellation {
                // Cancelling the Context cancels the client call started under it
                cancellableCtx.cancel(null)
            }
        }
    }
}
