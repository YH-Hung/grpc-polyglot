package org.hle.grpchttp1vs.client

import io.grpc.examples.hellogirl.HelloGirlReply
import io.grpc.examples.hellogirl.HelloGirlRequest

interface HelloGirlClient {
    fun sayHello(request: HelloGirlRequest): HelloGirlReply
}
