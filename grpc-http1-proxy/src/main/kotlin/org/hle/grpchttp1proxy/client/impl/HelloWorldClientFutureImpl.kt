package org.hle.grpchttp1proxy.client.impl

import com.google.common.util.concurrent.MoreExecutors
import io.grpc.ManagedChannel
import io.grpc.examples.helloworld.GreeterGrpc
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import kotlinx.coroutines.suspendCancellableCoroutine
import org.hle.grpchttp1proxy.client.HelloWorldClient
import org.springframework.stereotype.Service
import kotlin.coroutines.resumeWithException
import kotlin.Result

@Service
class HelloWorldClientFutureImpl(channel: ManagedChannel) : HelloWorldClient {

    private val futureStub = GreeterGrpc.newFutureStub(channel)

    override suspend fun sayHello(name: HelloRequest): HelloReply {
        // Build the gRPC request from the incoming DTO
        val request = HelloRequest.newBuilder()
            .setName(name.name)
            .build()

        // Call the Future stub and bridge the ListenableFuture into a cancellable suspend function
        return suspendCancellableCoroutine { continuation ->
            val future = futureStub.sayHello(request)

            // Propagate coroutine cancellation to the gRPC call
            continuation.invokeOnCancellation {
                future.cancel(true)
            }

            // Complete the continuation when the future completes
            future.addListener({
                try {
                    val response = future.get() // safe here since the listener runs after completion
                    continuation.resumeWith(Result.success(response))
                } catch (t: Throwable) {
                    // Unwrap ExecutionException if present to surface the actual cause
                    val cause = t.cause ?: t
                    continuation.resumeWithException(cause)
                }
            }, MoreExecutors.directExecutor())
        }
    }
}
