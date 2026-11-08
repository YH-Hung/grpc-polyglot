package org.hle.grpchttp1wfn.client

import io.grpc.Channel
import io.grpc.Metadata
import io.grpc.examples.helloworld.GreeterGrpcKt.GreeterCoroutineStub
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import io.grpc.stub.MetadataUtils
import org.springframework.stereotype.Service

@Service
class HelloWorldCoroutineClient(
    channel: Channel,
) : HelloWorldClient {
    private val stub = GreeterCoroutineStub(channel)
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

    override suspend fun sayHello(request: HelloRequest): HelloReply =
        stub.sayHello(request)
}
