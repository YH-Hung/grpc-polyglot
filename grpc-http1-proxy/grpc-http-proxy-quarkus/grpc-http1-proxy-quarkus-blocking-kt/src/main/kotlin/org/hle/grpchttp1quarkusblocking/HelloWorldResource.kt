package org.hle.grpchttp1quarkusblocking

import io.grpc.examples.helloworld.Greeter
import io.grpc.examples.helloworld.HelloRequest
import io.quarkus.grpc.GrpcClient
import io.smallrye.common.annotation.RunOnVirtualThread
import jakarta.ws.rs.Consumes
import jakarta.ws.rs.POST
import jakarta.ws.rs.Path
import jakarta.ws.rs.Produces
import jakarta.ws.rs.core.MediaType
import org.hle.grpchttp1quarkusblocking.dto.HelloReplyDto
import org.hle.grpchttp1quarkusblocking.dto.HelloRequestDto

@Path("/helloworld")
class HelloWorldResource {

    @GrpcClient("hello")
    lateinit var greeter: Greeter

    @POST
    @Path("/say-hello")
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    @RunOnVirtualThread
    fun sayHello(request: HelloRequestDto): HelloReplyDto {
        val protoRequest = HelloRequest.newBuilder()
            .setName(request.name)
            .build()

        val protoReply = greeter.sayHello(protoRequest).await().indefinitely()

        return HelloReplyDto(protoReply.message)
    }
}
