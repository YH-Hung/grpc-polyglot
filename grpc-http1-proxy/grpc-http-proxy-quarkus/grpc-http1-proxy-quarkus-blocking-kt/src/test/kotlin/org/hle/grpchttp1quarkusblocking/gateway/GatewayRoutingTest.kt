package org.hle.grpchttp1quarkusblocking.gateway

import io.grpc.Metadata
import io.grpc.Server
import io.grpc.ServerBuilder
import io.grpc.ServerCall
import io.grpc.ServerCallHandler
import io.grpc.ServerInterceptor
import io.grpc.ServerInterceptors
import io.grpc.examples.hellogirl.GirlGreeterGrpc
import io.grpc.examples.hellogirl.HelloGirlReply
import io.grpc.examples.hellogirl.HelloGirlRequest
import io.grpc.examples.helloworld.GreeterGrpc
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import io.grpc.stub.StreamObserver
import io.quarkus.test.common.QuarkusTestResourceLifecycleManager
import io.quarkus.test.common.WithTestResource
import io.quarkus.test.junit.QuarkusTest
import io.restassured.RestAssured.given
import jakarta.ws.rs.core.MediaType
import org.hamcrest.CoreMatchers.`is`
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

private val SPECIAL_MSG = Metadata.Key.of("special_msg", Metadata.ASCII_STRING_MARSHALLER)

@QuarkusTest
@WithTestResource(LoopbackServers::class)
class GatewayRoutingTest {

    @BeforeEach
    fun resetServers() {
        LoopbackServers.p1.reset()
        LoopbackServers.p2.reset()
    }

    @Test
    fun `prefixed routes reach the named server and an unknown prefix is 404`() {
        val p1 = LoopbackServers.p1
        val p2 = LoopbackServers.p2

        post("/p1/helloworld/say-hello").then().statusCode(200).body("message", `is`("p1-hello"))
        assertEquals(1, p1.calls.get())
        assertEquals(0, p2.calls.get())

        post("/p2/helloworld/say-hello").then().statusCode(200).body("message", `is`("p2-hello"))
        post("/p2/hello-girl/say-hello").then().statusCode(200).body("message", `is`("p2-girl"))
        assertEquals(1, p1.calls.get())
        assertEquals(2, p2.calls.get())

        post("/p9/helloworld/say-hello").then().statusCode(404)
        assertEquals(1, p1.calls.get())
        assertEquals(2, p2.calls.get())

        val headers = p1.specialMsgs + p2.specialMsgs
        assertEquals(List(3) { listOf("greetings-from-girl-java-client") }, headers)
    }

    @Test
    fun `a route that exists only in tests follows the same prefix`() {
        assertEquals("local", who("/probe/who"))
        assertEquals("p1", who("/p1/probe/who"))
        assertEquals("p2", who("/p2/probe/who"))
    }

    @Test
    fun `concurrent mixed prefixes stay on the channel named in each request`() {
        val pool = Executors.newFixedThreadPool(8)
        try {
            val results = (0 until 40).map { i ->
                pool.submit<String> {
                    val p1Request = i % 2 == 0
                    val message = given()
                        .contentType(MediaType.APPLICATION_JSON)
                        .body("""{"name":"a"}""")
                        .`when`().post(if (p1Request) "/p1/helloworld/say-hello" else "/p2/helloworld/say-hello")
                        .then().statusCode(200)
                        .extract().path<String>("message")
                    val want = if (p1Request) "p1-hello" else "p2-hello"
                    assertEquals(want, message)
                    want
                }
            }.map { it.get(30, TimeUnit.SECONDS) }
            assertEquals(20, results.count { it == "p1-hello" })
            assertEquals(20, results.count { it == "p2-hello" })
        } finally {
            pool.shutdown()
        }
    }

    private fun post(path: String) = given()
        .contentType(MediaType.APPLICATION_JSON)
        .body("""{"name":"a"}""")
        .`when`().post(path)

    private fun who(path: String): String = given()
        .accept(MediaType.TEXT_PLAIN)
        .`when`().post(path)
        .then().statusCode(200)
        .extract().asString()
}

class LoopbackServers : QuarkusTestResourceLifecycleManager {

    override fun start(): Map<String, String> {
        p1 = LoopbackGreeter("p1-hello", "p1-girl")
        p2 = LoopbackGreeter("p2-hello", "p2-girl")
        return mapOf("proxy.gateway.backends" to "p1,p2") +
            p1.clientConfig("p1") +
            p2.clientConfig("p2")
    }

    override fun stop() {
        p1.stop()
        p2.stop()
    }

    companion object {
        lateinit var p1: LoopbackGreeter
        lateinit var p2: LoopbackGreeter
    }
}

class LoopbackGreeter(helloMessage: String, girlMessage: String) {
    val calls = AtomicInteger()
    val specialMsgs = CopyOnWriteArrayList<List<String>>()
    private val server: Server

    init {
        val greeter = object : GreeterGrpc.GreeterImplBase() {
            override fun sayHello(request: HelloRequest, observer: StreamObserver<HelloReply>) {
                calls.incrementAndGet()
                observer.onNext(HelloReply.newBuilder().setMessage(helloMessage).build())
                observer.onCompleted()
            }
        }
        val girl = object : GirlGreeterGrpc.GirlGreeterImplBase() {
            override fun sayHello(request: HelloGirlRequest, observer: StreamObserver<HelloGirlReply>) {
                calls.incrementAndGet()
                observer.onNext(HelloGirlReply.newBuilder().setMessage(girlMessage).build())
                observer.onCompleted()
            }
        }
        val recordSpecialMsg = object : ServerInterceptor {
            override fun <ReqT, RespT> interceptCall(
                call: ServerCall<ReqT, RespT>,
                headers: Metadata,
                next: ServerCallHandler<ReqT, RespT>,
            ): ServerCall.Listener<ReqT> {
                specialMsgs += headers.getAll(SPECIAL_MSG)?.toList().orEmpty()
                return next.startCall(call, headers)
            }
        }
        server = ServerBuilder.forPort(0)
            .addService(ServerInterceptors.intercept(greeter, recordSpecialMsg))
            .addService(ServerInterceptors.intercept(girl, recordSpecialMsg))
            .build()
            .start()
    }

    fun clientConfig(name: String): Map<String, String> = mapOf(
        "quarkus.grpc.clients.$name.host" to "127.0.0.1",
        "quarkus.grpc.clients.$name.port" to "${server.port}",
        "quarkus.grpc.clients.$name.test-port" to "${server.port}",
    )

    fun reset() {
        calls.set(0)
        specialMsgs.clear()
    }

    fun stop() {
        server.shutdownNow()
    }
}
