package org.hle.grpchttp1proxy.client.impl

import io.grpc.ManagedChannel
import io.grpc.examples.helloworld.GreeterGrpc
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import io.grpc.stub.StreamObserver
import kotlinx.coroutines.suspendCancellableCoroutine
import org.hle.grpchttp1proxy.client.HelloWorldClient
import org.springframework.stereotype.Service
import kotlin.coroutines.resumeWithException
import kotlin.Result

@Service
class HelloWorldClientAsyncImpl(private val channel: ManagedChannel) : HelloWorldClient {

    private val asyncStub = GreeterGrpc.newStub(channel)

    override suspend fun sayHello(name: HelloRequest): HelloReply {
        // Convert from DTO to gRPC request
        val request = HelloRequest.newBuilder()
            .setName(name.name)
            .build()

        // Make the gRPC call in a non-blocking way using the async stub
        return suspendCancellableCoroutine { continuation ->
            asyncStub.sayHello(request, object : StreamObserver<HelloReply> {
                override fun onNext(response: HelloReply) {
                    // Convert from gRPC response to DTO and resume the coroutine
                    continuation.resumeWith(Result.success(response))
                }

                override fun onError(error: Throwable) {
                    // Resume the coroutine with an exception
                    continuation.resumeWithException(error)
                }

                override fun onCompleted() {
                    // This is called after onNext for unary calls, so we don't need to do anything here
                }
            })

            // Register cancellation handler
            continuation.invokeOnCancellation {
                // Cancel the gRPC call if the coroutine is cancelled
                // Note: gRPC doesn't provide a direct way to cancel individual calls
                // This is a best-effort approach
            }
        }
    }
}
