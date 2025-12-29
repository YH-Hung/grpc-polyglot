package org.hle.grpchttp1vs.quarkus

import io.grpc.examples.helloworld.Greeter
import io.grpc.examples.helloworld.HelloReply
import io.quarkus.grpc.GrpcClient
import io.quarkus.test.InjectMock
import io.quarkus.test.junit.QuarkusTest
import io.restassured.RestAssured.given
import io.smallrye.mutiny.Uni
import org.hamcrest.CoreMatchers.`is`
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.mockito.ArgumentMatchers.any
import org.mockito.Mockito.`when`
import jakarta.ws.rs.core.MediaType

@QuarkusTest
class HelloWorldResourceTest {

    @InjectMock
    @GrpcClient("hello")
    lateinit var greeter: Greeter

    @BeforeEach
    fun setup() {
        `when`(greeter.sayHello(any())).thenReturn(
            Uni.createFrom().item(HelloReply.newBuilder().setMessage("Hello Quarkus User").build())
        )
    }

    @Test
    fun testSayHelloEndpoint() {
        given()
          .contentType(MediaType.APPLICATION_JSON)
          .body("""{"name": "Quarkus User"}""")
          .`when`().post("/helloworld/say-hello")
          .then()
             .statusCode(200)
             .body("message", `is`("Hello Quarkus User"))
    }
}
