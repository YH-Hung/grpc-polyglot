package org.hle.grpchttp1wf.client

import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest

interface HelloWorldClient {
    suspend fun sayHello(name: HelloRequest): HelloReply
}
