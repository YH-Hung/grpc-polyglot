package org.hle.grpchttp1vs.controller

import io.grpc.examples.hellogirl.HelloGirlReply
import io.grpc.examples.hellogirl.HelloGirlRequest
import org.hle.grpchttp1vs.client.HelloGirlClient
import org.springframework.http.MediaType
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/hello-girl")
class HelloGirlController(private val helloGirlClient: HelloGirlClient) {

    @PostMapping("/say-hello", consumes = [MediaType.APPLICATION_JSON_VALUE], produces = [MediaType.APPLICATION_JSON_VALUE])
    fun sayHello(@RequestBody request: HelloGirlRequest): HelloGirlReply {
        return helloGirlClient.sayHello(request)
    }
}
