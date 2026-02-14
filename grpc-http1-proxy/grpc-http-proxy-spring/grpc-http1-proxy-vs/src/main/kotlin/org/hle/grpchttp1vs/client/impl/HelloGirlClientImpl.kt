package org.hle.grpchttp1vs.client.impl

import io.grpc.ManagedChannel
import io.grpc.Metadata
import io.grpc.examples.hellogirl.GirlGreeterGrpc
import io.grpc.examples.hellogirl.HelloGirlReply
import io.grpc.examples.hellogirl.HelloGirlRequest
import io.grpc.stub.MetadataUtils
import org.hle.grpchttp1vs.client.HelloGirlClient
import org.springframework.stereotype.Service

@Service
class HelloGirlClientImpl(
    channel: ManagedChannel,
) : HelloGirlClient {

    private val blockingStub = GirlGreeterGrpc.newBlockingStub(channel)
        .withInterceptors(
            MetadataUtils.newAttachHeadersInterceptor(
                Metadata().apply {
                    put(
                        Metadata.Key.of("special_msg", Metadata.ASCII_STRING_MARSHALLER),
                        "greetings-from-girl-java-client"
                    )
                }
            )
        )

    override fun sayHello(request: HelloGirlRequest): HelloGirlReply {
        val grpcRequest = HelloGirlRequest.newBuilder()
            .setName(request.name)
            .setSpouse(request.spouse)
            .setFirstRound(request.firstRound)
            .build()

        return blockingStub.sayHello(grpcRequest)
    }
}
