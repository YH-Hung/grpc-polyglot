package org.hle.grpchttp1wf.client.impl

import io.grpc.ManagedChannel
import io.grpc.examples.helloworld.GreeterGrpc
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import io.grpc.stub.ClientCallStreamObserver
import io.grpc.stub.ClientResponseObserver
import kotlinx.coroutines.suspendCancellableCoroutine
import org.hle.grpchttp1wf.client.HelloWorldClient
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Service
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resumeWithException

@Service
class HelloWorldClientAsyncImpl(
    channel: ManagedChannel,
    @Value("\${grpc.client.deadline-ms:5000}") private val deadlineMs: Long
) : HelloWorldClient {

    private val asyncStub = GreeterGrpc
        .newStub(channel)

    override suspend fun sayHello(name: HelloRequest): HelloReply {
        // Convert from DTO to gRPC request
        val request = HelloRequest.newBuilder()
            .setName(name.name)
            .build()

        val stubWithDeadline = asyncStub.withDeadlineAfter(deadlineMs, TimeUnit.MILLISECONDS)

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
            stubWithDeadline.sayHello(request, responseObserver)

            // Register cancellation handler
            continuation.invokeOnCancellation {
                // Cancel the gRPC call if the coroutine is cancelled
                callObserver?.cancel("Coroutine was cancelled", it)
            }
        }
    }
}
