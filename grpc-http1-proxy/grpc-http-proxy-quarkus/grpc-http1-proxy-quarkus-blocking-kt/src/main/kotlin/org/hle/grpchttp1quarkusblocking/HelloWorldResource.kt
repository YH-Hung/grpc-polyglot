package org.hle.grpchttp1quarkusblocking

import io.grpc.examples.helloworld.Greeter
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import io.quarkus.grpc.GrpcClient
import io.smallrye.common.annotation.RunOnVirtualThread
import jakarta.ws.rs.Consumes
import jakarta.ws.rs.POST
import jakarta.ws.rs.Path
import jakarta.ws.rs.Produces
import jakarta.ws.rs.core.MediaType

@Path("/helloworld")
class HelloWorldResource {

    @GrpcClient("hello")
    lateinit var greeter: Greeter

    @POST
    @Path("/say-hello")
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    @RunOnVirtualThread
    fun sayHello(request: HelloRequest): HelloReply {
        return greeter.sayHello(request).await().indefinitely()
    }
}
