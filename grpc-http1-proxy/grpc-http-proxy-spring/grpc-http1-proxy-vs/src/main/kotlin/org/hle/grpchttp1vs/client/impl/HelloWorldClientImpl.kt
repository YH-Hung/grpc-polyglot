package org.hle.grpchttp1vs.client.impl

import io.grpc.ManagedChannel
import io.grpc.Metadata
import io.grpc.examples.helloworld.GreeterGrpc
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import io.grpc.stub.MetadataUtils
import org.hle.grpchttp1vs.client.HelloWorldClient
import org.springframework.context.annotation.Primary
import org.springframework.stereotype.Service

@Primary
@Service
class HelloWorldClientImpl(
    channel: ManagedChannel,
) : HelloWorldClient {

    private val blockingStub = GreeterGrpc.newBlockingStub(channel)
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

    override fun sayHello(name: HelloRequest): HelloReply {
        val request = HelloRequest.newBuilder()
            .setName(name.name)
            .build()

        return blockingStub.sayHello(request)
    }
}
