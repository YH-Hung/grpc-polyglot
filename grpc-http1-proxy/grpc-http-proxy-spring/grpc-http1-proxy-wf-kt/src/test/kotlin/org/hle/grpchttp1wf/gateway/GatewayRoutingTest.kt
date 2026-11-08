package org.hle.grpchttp1wf.gateway

import io.grpc.Server
import io.grpc.ServerBuilder
import io.grpc.examples.hellogirl.GirlGreeterGrpc
import io.grpc.examples.hellogirl.HelloGirlReply
import io.grpc.examples.hellogirl.HelloGirlRequest
import io.grpc.examples.helloworld.GreeterGrpc
import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import io.grpc.stub.StreamObserver
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.webtestclient.autoconfigure.AutoConfigureWebTestClient
import org.springframework.http.MediaType
import org.springframework.test.context.DynamicPropertyRegistry
import org.springframework.test.context.DynamicPropertySource
import org.springframework.test.web.reactive.server.WebTestClient
import org.springframework.test.web.reactive.server.expectBody
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureWebTestClient
class GatewayRoutingTest {

    @Autowired
    private lateinit var webTestClient: WebTestClient

    @BeforeEach
    fun resetServers() {
        p1.reset()
        p2.reset()
    }

    @Test
    fun `prefixed routes reach the named server and an unknown prefix is 404`() {
        val reply = { path: String ->
            webTestClient.post()
                .uri(path)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("""{"name":"a"}""")
                .exchange()
        }

        val p1Hello = reply("/p1/helloworld/say-hello")
            .expectStatus().isOk
            .expectBody<String>()
            .returnResult()
            .responseBody
        assertTrue(p1Hello!!.contains("p1-hello"))
        assertEquals(1, p1.calls.get())
        assertEquals(0, p2.calls.get())

        val p2Hello = reply("/p2/helloworld/say-hello")
            .expectStatus().isOk
            .expectBody<String>()
            .returnResult()
            .responseBody
        assertTrue(p2Hello!!.contains("p2-hello"))
        assertEquals(1, p2.calls.get())

        val p2Girl = reply("/p2/hello-girl/say-hello")
            .expectStatus().isOk
            .expectBody<String>()
            .returnResult()
            .responseBody
        assertTrue(p2Girl!!.contains("p2-girl"))
        assertEquals(2, p2.calls.get())
        assertEquals(1, p1.calls.get())

        val p1Before = p1.calls.get()
        val p2Before = p2.calls.get()
        reply("/p9/helloworld/say-hello").expectStatus().isNotFound
        assertEquals(p1Before, p1.calls.get())
        assertEquals(p2Before, p2.calls.get())
    }

    @Test
    fun `a route that exists only in this test follows the same prefix`() {
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
                    val body = webTestClient.post()
                        .uri(if (p1Request) "/p1/helloworld/say-hello" else "/p2/helloworld/say-hello")
                        .contentType(MediaType.APPLICATION_JSON)
                        .bodyValue("""{"name":"a"}""")
                        .exchange()
                        .expectStatus().isOk
                        .expectBody<String>()
                        .returnResult()
                        .responseBody
                    val want = if (p1Request) "p1-hello" else "p2-hello"
                    assertTrue(body!!.contains(want), body)
                    want
                }
            }.map { it.get(30, TimeUnit.SECONDS) }
            assertEquals(20, results.count { it == "p1-hello" })
            assertEquals(20, results.count { it == "p2-hello" })
        } finally {
            pool.shutdown()
        }
    }

    private fun who(path: String): String? {
        return webTestClient.post()
            .uri(path)
            .accept(MediaType.TEXT_PLAIN)
            .exchange()
            .expectStatus().isOk
            .expectBody<String>()
            .returnResult()
            .responseBody
    }

    companion object {
        private val p1 = LoopbackGreeter("p1-hello", "p1-girl")
        private val p2 = LoopbackGreeter("p2-hello", "p2-girl")

        @DynamicPropertySource
        @JvmStatic
        fun gatewayChannels(registry: DynamicPropertyRegistry) {
            registry.add("spring.grpc.client.channels.p1.address") { "127.0.0.1:${p1.port}" }
            registry.add("spring.grpc.client.channels.p2.address") { "127.0.0.1:${p2.port}" }
            registry.add("proxy.gateway.backends") { "p1,p2" }
        }

        @AfterAll
        @JvmStatic
        fun stopServers() {
            p1.stop()
            p2.stop()
        }
    }
}

private class LoopbackGreeter(helloMessage: String, girlMessage: String) {
    val calls = AtomicInteger()
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
        server = ServerBuilder.forPort(0)
            .addService(greeter)
            .addService(girl)
            .build()
            .start()
    }

    val port: Int
        get() = server.port

    fun reset() {
        calls.set(0)
    }

    fun stop() {
        server.shutdownNow()
    }
}
