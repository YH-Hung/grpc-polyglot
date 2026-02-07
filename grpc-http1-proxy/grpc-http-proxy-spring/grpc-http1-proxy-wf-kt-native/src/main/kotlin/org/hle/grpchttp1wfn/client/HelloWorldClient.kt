package org.hle.grpchttp1wfn.client

import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest

interface HelloWorldClient {
    suspend fun sayHello(request: HelloRequest): HelloReply
}
