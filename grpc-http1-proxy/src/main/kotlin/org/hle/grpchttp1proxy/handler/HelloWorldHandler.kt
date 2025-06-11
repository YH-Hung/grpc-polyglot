package org.hle.grpchttp1proxy.handler

import kotlinx.coroutines.reactor.awaitSingle
import org.hle.grpchttp1proxy.client.HelloWorldClient
import org.hle.grpchttp1proxy.dto.HelloRequestDto
import org.springframework.stereotype.Component
import org.springframework.web.reactive.function.server.ServerRequest
import org.springframework.web.reactive.function.server.ServerResponse
import org.springframework.web.reactive.function.server.bodyToMono
import org.springframework.web.reactive.function.server.bodyValueAndAwait

@Component
class HelloWorldHandler(private val helloWorldClient: HelloWorldClient) {

    suspend fun handleHelloWorld(request: ServerRequest): ServerResponse {
        val requestDto = request.bodyToMono<HelloRequestDto>().awaitSingle()
        val responseDto = helloWorldClient.sayHello(requestDto)
        return ServerResponse.ok().bodyValueAndAwait(responseDto)
    }
}