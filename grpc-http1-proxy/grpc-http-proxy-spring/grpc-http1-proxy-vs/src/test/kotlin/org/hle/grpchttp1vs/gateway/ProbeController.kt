package org.hle.grpchttp1vs.gateway

import io.grpc.Channel
import org.springframework.http.MediaType
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RestController

@RestController
class ProbeController(private val channel: Channel) {
    @PostMapping("/probe/who", produces = [MediaType.TEXT_PLAIN_VALUE])
    fun who(): String = (channel as RoutingChannel).selectedName()
}
