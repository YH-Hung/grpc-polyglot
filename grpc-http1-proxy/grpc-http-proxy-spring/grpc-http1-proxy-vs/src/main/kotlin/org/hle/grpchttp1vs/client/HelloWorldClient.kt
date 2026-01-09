package org.hle.grpchttp1vs.client

import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest

interface HelloWorldClient {
    fun sayHello(name: HelloRequest): HelloReply
}
