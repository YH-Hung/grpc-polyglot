package org.hle.grpchttp1wfn.handler

import io.grpc.examples.helloworld.HelloRequest
import kotlinx.coroutines.reactor.awaitSingle
import org.hle.grpchttp1wfn.client.HelloWorldClient
import org.springframework.stereotype.Component
import org.springframework.web.reactive.function.server.ServerRequest
import org.springframework.web.reactive.function.server.ServerResponse
import org.springframework.web.reactive.function.server.bodyToMono
import org.springframework.web.reactive.function.server.bodyValueAndAwait

@Component
class HelloWorldHandler(private val helloWorldClient: HelloWorldClient) {

    suspend fun handleHelloWorld(request: ServerRequest): ServerResponse {
        val requestDto = request.bodyToMono<HelloRequest>().awaitSingle()
        val responseDto = helloWorldClient.sayHello(requestDto)
        return ServerResponse.ok().bodyValueAndAwait(responseDto)
    }
}
