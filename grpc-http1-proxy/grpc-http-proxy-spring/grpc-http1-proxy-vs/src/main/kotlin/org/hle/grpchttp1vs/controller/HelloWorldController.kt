package org.hle.grpchttp1vs.controller

import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import org.hle.grpchttp1vs.client.HelloWorldClient
import org.springframework.http.MediaType
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/helloworld")
class HelloWorldController(private val helloWorldClient: HelloWorldClient) {

    @PostMapping("/say-hello", consumes = [MediaType.APPLICATION_JSON_VALUE], produces = [MediaType.APPLICATION_JSON_VALUE])
    fun helloWorld(@RequestBody request: HelloRequest): HelloReply {
        return helloWorldClient.sayHello(request)
    }
}
