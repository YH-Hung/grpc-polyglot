package org.hle.grpchttp1wf.controller

import org.springframework.beans.factory.annotation.Value
import org.springframework.core.io.Resource
import org.springframework.http.MediaType
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import java.util.Properties

@RestController
@RequestMapping("/grpc")
class GrpcChannelController(
    @Value("classpath:application.properties") private val propertiesResource: Resource,
) {

    @GetMapping("/channels", produces = [MediaType.APPLICATION_JSON_VALUE])
    fun listChannels(): List<String> {
        val properties = Properties()
        if (propertiesResource.exists()) {
            propertiesResource.inputStream.use { properties.load(it) }
        }

        val prefix = "spring.grpc.client.channels."
        return properties.stringPropertyNames()
            .asSequence()
            .filter { it.startsWith(prefix) }
            .map { it.removePrefix(prefix).substringBefore('.') }
            .toSet()
            .sorted()
    }
}
