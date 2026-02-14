package org.hle.grpchttp1wf.client.impl

import io.grpc.Context
import io.grpc.ManagedChannel
import io.grpc.examples.hellogirl.GirlGreeterGrpc
import io.grpc.examples.hellogirl.HelloGirlReply
import io.grpc.examples.hellogirl.HelloGirlRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.job
import kotlinx.coroutines.withContext
import org.hle.grpchttp1wf.client.HelloGirlClient
import org.springframework.stereotype.Service

@Service
class HelloGirlClientImpl(
    channel: ManagedChannel,
) : HelloGirlClient {

    private val blockingStub = GirlGreeterGrpc
        .newBlockingStub(channel)

    override suspend fun sayHello(request: HelloGirlRequest): HelloGirlReply {
        val grpcRequest = HelloGirlRequest.newBuilder()
            .setName(request.name)
            .setSpouse(request.spouse)
            .setFirstRound(request.firstRound)
            .build()

        return withContext(Dispatchers.IO) {
            val cancellableContext = Context.current()
                .withCancellation()

            cancellableContext.use { ctx ->
                coroutineContext.job.invokeOnCompletion { cause ->
                    if (cause != null && !ctx.isCancelled) {
                        ctx.cancel(cause)
                    }
                }

                ctx.call {
                    blockingStub.sayHello(grpcRequest)
                }
            }
        }
    }
}
