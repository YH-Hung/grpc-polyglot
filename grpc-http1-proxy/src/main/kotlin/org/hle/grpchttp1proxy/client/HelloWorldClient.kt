package org.hle.grpchttp1proxy.client

import org.hle.grpchttp1proxy.dto.HelloReplyDto
import org.hle.grpchttp1proxy.dto.HelloRequestDto

interface HelloWorldClient {
    suspend fun sayHello(name: HelloRequestDto): HelloReplyDto
}
