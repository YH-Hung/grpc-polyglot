package org.hle.grpchttp1vs.controller

import org.springframework.boot.grpc.client.autoconfigure.GrpcClientProperties
import org.springframework.http.MediaType
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/grpc")
class GrpcChannelPropertiesController(
    private val grpcClientProperties: GrpcClientProperties,
) {

    @GetMapping("/channels", produces = [MediaType.APPLICATION_JSON_VALUE])
    fun listChannels(): List<String> {
        return grpcClientProperties.channels.keys.sorted()
    }
}
