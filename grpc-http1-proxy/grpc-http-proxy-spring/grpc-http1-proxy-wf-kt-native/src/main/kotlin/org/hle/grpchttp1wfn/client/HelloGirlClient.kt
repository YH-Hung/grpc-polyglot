package org.hle.grpchttp1wfn.client

import io.grpc.examples.hellogirl.HelloGirlReply
import io.grpc.examples.hellogirl.HelloGirlRequest

interface HelloGirlClient {
    suspend fun sayHello(request: HelloGirlRequest): HelloGirlReply
}
