package org.hle.grpchttp1proxy.controller

import org.hle.grpchttp1proxy.client.HelloWorldClient
import org.hle.grpchttp1proxy.dto.HelloRequestDto
import org.hle.grpchttp1proxy.dto.HelloReplyDto
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RestController

@RestController
class HelloWorldController(private val helloWorldClient: HelloWorldClient) {

    @PostMapping("/helloworld")
    suspend fun helloWorld(@RequestBody request: HelloRequestDto): HelloReplyDto {
        return helloWorldClient.sayHello(request)
    }
}