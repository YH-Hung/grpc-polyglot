package org.hle.grpchttp1wfn.gateway

import io.grpc.Channel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.springframework.http.MediaType
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RestController

@RestController
class ProbeController(private val channel: Channel) {
    @PostMapping("/probe/who", produces = [MediaType.TEXT_PLAIN_VALUE])
    suspend fun who(): String = withContext(Dispatchers.Default) {
        (channel as RoutingChannel).selectedName()
    }
}
