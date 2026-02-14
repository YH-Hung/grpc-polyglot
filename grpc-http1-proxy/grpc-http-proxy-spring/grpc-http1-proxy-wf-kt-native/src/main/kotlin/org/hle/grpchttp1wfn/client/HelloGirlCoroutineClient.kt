package org.hle.grpchttp1wfn.client

import io.grpc.ManagedChannel
import io.grpc.Metadata
import io.grpc.examples.hellogirl.GirlGreeterGrpcKt.GirlGreeterCoroutineStub
import io.grpc.examples.hellogirl.HelloGirlReply
import io.grpc.examples.hellogirl.HelloGirlRequest
import io.grpc.stub.MetadataUtils
import org.springframework.stereotype.Service

@Service
class HelloGirlCoroutineClient(
    channel: ManagedChannel,
) : HelloGirlClient {
    private val stub = GirlGreeterCoroutineStub(channel)
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

    override suspend fun sayHello(request: HelloGirlRequest): HelloGirlReply =
        stub.sayHello(request)
}
