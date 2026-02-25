package org.hle.grpchttp1quarkusblocking

import io.grpc.examples.hellogirl.GirlGreeter
import io.grpc.examples.hellogirl.HelloGirlReply
import io.grpc.examples.hellogirl.HelloGirlRequest
import io.quarkus.grpc.GrpcClient
import io.smallrye.common.annotation.RunOnVirtualThread
import jakarta.ws.rs.Consumes
import jakarta.ws.rs.POST
import jakarta.ws.rs.Path
import jakarta.ws.rs.Produces
import jakarta.ws.rs.core.MediaType

@Path("/hello-girl")
class HelloGirlResource {

    @GrpcClient("hello")
    lateinit var girlGreeter: GirlGreeter

    @POST
    @Path("/say-hello")
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    @RunOnVirtualThread
    fun sayHello(request: HelloGirlRequest): HelloGirlReply {
        return girlGreeter.sayHello(request).await().indefinitely()
    }
}
