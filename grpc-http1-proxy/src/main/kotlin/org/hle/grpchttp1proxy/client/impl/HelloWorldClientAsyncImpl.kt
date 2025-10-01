package org.hle.grpchttp1proxy.client.impl

import io.grpc.ManagedChannel
import io.grpc.examples.helloworld.GreeterGrpc
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import io.grpc.stub.ClientCallStreamObserver
import io.grpc.stub.ClientResponseObserver
import io.grpc.stub.StreamObserver
import kotlinx.coroutines.suspendCancellableCoroutine
import org.hle.grpchttp1proxy.client.HelloWorldClient
import org.springframework.stereotype.Service
import kotlin.coroutines.resumeWithException
import kotlin.Result

@Service
class HelloWorldClientAsyncImpl(channel: ManagedChannel) : HelloWorldClient {

    private val asyncStub = GreeterGrpc.newStub(channel)

    override suspend fun sayHello(name: HelloRequest): HelloReply {
        // Convert from DTO to gRPC request
        val request = HelloRequest.newBuilder()
            .setName(name.name)
            .build()

        // Make the gRPC call in a non-blocking way using the async stub
        return suspendCancellableCoroutine { continuation ->
            // Only ClientCallStreamObserver has the cancel method.
            var callObserver: ClientCallStreamObserver<HelloRequest?>? = null

            // For unary call, ClientCallStreamObserver needs to be provided by ClientResponseObserver.
            val responseObserver = object : ClientResponseObserver<HelloRequest, HelloReply> {
                override fun beforeStart(p0: ClientCallStreamObserver<HelloRequest?>?) {
                    callObserver = p0
                }

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
            }
            asyncStub.sayHello(request, responseObserver)

            // Register cancellation handler
            continuation.invokeOnCancellation {
                // Cancel the gRPC call if the coroutine is cancelled
                callObserver?.cancel("Coroutine was cancelled", it)
            }
        }
    }
}
